# -*- coding: utf-8 -*-
# @Time : 2019-03-22 15:05
# @Author : cxa
# @File : base_crawler.py
# @Software: PyCharm

import asyncio
import aiohttp
from loguru import logger as crawler
import async_timeout
from async_retrying import retry
from lxml import html
from util import RabbitMqPool, MongoPool
from config import MongoConfig, RabbitmqConfig, SpiderConfig
from functools import wraps
import traceback
import contextvars
from dataclasses import dataclass
from typing import Optional
from copy import deepcopy

run_flag = contextvars.ContextVar('which function will run in decorator')
run_flag.set(False)

try:
    import uvloop

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    pass


@dataclass
class Response:
    status: int
    source: str


@dataclass
class Crawler:
    tc: Optional[aiohttp.BaseConnector] = None
    session: Optional[aiohttp.ClientSession] = None
    session_flag: bool = False

    def __post_init__(self):
        self.rabbitmq_pool = RabbitMqPool()
        self.spider_config = SpiderConfig
        self.mongo_config = MongoConfig
        self.mongo_pool = MongoPool
        self.rabbitmq_config = RabbitmqConfig

    @retry(attempts=3)
    async def get_session(self, url, _kwargs=None, source_type="text", status_code=200) -> Response:
        """

        :param url:
        :param _kwargs:
        :param source_type:
        :param status_code:
        :return:
        """
        if _kwargs is None:
            _kwargs = dict()
        kwargs = deepcopy(_kwargs)
        if self.spider_config.get("USE_PROXY"):
            kwargs["proxy"] = await self.get_proxy()
        method = kwargs.pop("method", "get")
        timeout = kwargs.pop("timeout", 5)
        with async_timeout.timeout(timeout):
            async with getattr(self.session, method)(url, **kwargs) as req:
                status = req.status
                if status in [status_code, 201]:
                    if source_type == "text":
                        source = await req.text()
                    elif source_type == "buff":
                        source = await req.read()

        crawler.info(f"get url:{url},status:{status}")
        res = Response(status=status, source=source)
        return res

    @staticmethod
    def xpath(_response, rule, _attr=None):
        if isinstance(_response, Response):
            source = _response.text
            root = html.fromstring(source)

        elif isinstance(_response, str):
            source = _response
            root = html.fromstring(source)
        else:
            root = _response
        nodes = root.xpath(rule)
        if _attr:
            if _attr == "text":
                result = [entry.text for entry in nodes]
            else:
                result = [entry.get(_attr) for entry in nodes]
        else:
            result = nodes
        return result

    async def fetch_start(self, callback, queue_name="discogs_seed_spider"):
        try:
            run_flag.set(True)
            await self.init_all()
            await self.rabbitmq_pool.subscribe(queue_name, eval(f"self.{callback.__name__}"))
        except asyncio.CancelledError as e:
            crawler.error("CancelledError")
        except Exception as e:
            crawler.error(f"else error:{traceback.format_exc()}")
        finally:
            await self.close_session()

    async def init_all(self):
        """
        :return:
        """
        await self.init_session()
        if self.rabbitmq_pool:
            crawler.info("init rabbit_mq")
            await self.rabbitmq_pool.init(
                addr=self.rabbitmq_config["addr"],
                port=self.rabbitmq_config["port"],
                vhost=self.rabbitmq_config["vhost"],
                username=self.rabbitmq_config["username"],
                password=self.rabbitmq_config["password"],
                max_size=self.rabbitmq_config["max_size"],
            )
        if self.mongo_pool:
            crawler.info("init mongo")

            self.mongo_pool(
                host=self.mongo_config["host"],
                port=self.mongo_config["port"],
                maxPoolSize=self.mongo_config["max_pool_size"],
                minPoolSize=self.mongo_config["min_pool_size"]
            )

    async def get_proxy(self):
        """
        代理部分
        :return:
        """
        pass

    async def init_session(self):
        """
        创建Tcpconnector，包括ssl和连接数的限制
        创建一个全局session。
        :return:
        """
        crawler.info("init session")
        self.tc = aiohttp.connector.TCPConnector(limit=300, force_close=True,
                                                 enable_cleanup_closed=True,
                                                 verify_ssl=False)

        self.session = aiohttp.ClientSession(connector=self.tc)
        self.session_flag = True
        return self.session

    async def close_session(self):
        if self.session_flag:
            crawler.info("close session")
            await self.tc.close()
            await self.session.close()

    def start(queue_name=None):
        def __start(func):
            @wraps(func)
            async def _wrap(self, *args, **kwargs):
                try:
                    flag = run_flag.get()
                    if not flag:
                        await self.fetch_start(func, queue_name=queue_name)
                    else:
                        await func(self, *args, **kwargs)
                except asyncio.CancelledError as e:
                    crawler.error(e.args)

            return _wrap

        return __start
