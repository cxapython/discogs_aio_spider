# -*- coding: utf-8 -*-
# @Time : 2019-03-22 15:05
# @Author : cxa
# @File : base_crawler.py
# @Software: PyCharm

import asyncio
import aiohttp
from loguru import logger as crawler
import async_timeout
from util import aio_retry
from lxml import html
from util import RabbitMqPool, MongoPool
from config import MongoConfig, RabbitmqConfig, SpiderConfig
from functools import wraps
from dataclasses import dataclass
from typing import Optional, Dict, Any, Union, List, Callable, Type, AsyncIterator, Awaitable
from types import TracebackType
from copy import deepcopy
from contextvars import ContextVar
from contextlib import asynccontextmanager
import traceback

Node = List[str]
run_flag: ContextVar = ContextVar('which function will run in decorator')

run_flag.set(False)

try:
    import uvloop

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    pass


@dataclass(frozen=True)
class Response:
    status: int
    source: str


@dataclass
class HTTPClient:
    def __post_init__(self):
        self.spider_config = SpiderConfig

        self.tc = aiohttp.connector.TCPConnector(limit=300, force_close=True,
                                                 enable_cleanup_closed=True,
                                                 ssl=False)

        self.session = aiohttp.ClientSession(connector=self.tc)

    async def close(self):
        crawler.info("close session")
        return await asyncio.gather(self.tc.close(), self.session.close())

    async def __aenter__(self) -> "HTTPClient":
        return self

    async def __aexit__(self,
                        exc_type: Optional[Type[BaseException]],
                        exc_val: Optional[BaseException],
                        exc_tb: Optional[TracebackType], ) -> Optional[bool]:
        await self.close()
        return None

    @aio_retry()
    async def get_session(self, url: str, _kwargs: Optional[Dict[str, Any]] = None,
                          source_type: str = "text",
                          status_code: int = 200) -> Response:
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


@dataclass
class Crawler:
    session_flag: bool = False

    def __post_init__(self):
        self.spider_config = SpiderConfig
        self.rabbitmq_pool = RabbitMqPool()
        self.mongo_config = MongoConfig
        self.mongo_pool = MongoPool
        self.rabbitmq_config = RabbitmqConfig

    @classmethod
    @asynccontextmanager
    async def http_client(cls) -> AsyncIterator[HTTPClient]:
        client = HTTPClient()
        try:
            yield client
        finally:
            await client.close()

    async def init_all(self, *, init_rabbit, init_mongo) -> None:
        """
        :return:
        """
        if init_rabbit and self.rabbitmq_pool:
            crawler.info("init rabbit_mq")
            await self.rabbitmq_pool.init(
                addr=self.rabbitmq_config["addr"],
                port=self.rabbitmq_config["port"],
                vhost=self.rabbitmq_config["vhost"],
                username=self.rabbitmq_config["username"],
                password=self.rabbitmq_config["password"],
                max_size=self.rabbitmq_config["max_size"],
            )
        if init_mongo and self.mongo_pool:
            crawler.info("init mongo")
            self.mongo_pool(
                host=self.mongo_config["host"],
                port=self.mongo_config["port"],
                maxPoolSize=self.mongo_config["max_pool_size"],
                minPoolSize=self.mongo_config["min_pool_size"]
            )

    @staticmethod
    def xpath(_response: Union[Response, str],
              rule: str, _attr: Optional[str] = None) -> Node:
        """
        :param _response: response object or text
        :param rule: xpath rule
        :param _attr: attr
        :return:
        """
        if isinstance(_response, Response):
            source = _response.source
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

    async def fetch_start(self, callback: Callable[..., Awaitable],
                          init_rabbit=True, init_mongo=True,
                          queue_name: Optional[str] = None, starts_url=None) -> None:
        try:
            run_flag.set(True)
            await self.init_all(init_rabbit=init_rabbit, init_mongo=init_mongo)

            if starts_url is None:
                await self.rabbitmq_pool.subscribe(queue_name, eval(f"self.{callback.__name__}"))
            else:
                res_list = [asyncio.ensure_future(getattr(self, callback.__name__)(url)) for url in starts_url]
                tasks = asyncio.wait(res_list)
                await tasks

        except (asyncio.CancelledError, asyncio.TimeoutError) as e:
            crawler.error("asyncio cancelle or timeout error")
        except Exception as e:
            crawler.error(f"else error:{traceback.format_exc()}")

    async def get_proxy(self):
        """
        代理部分
        :return:
        """
        pass

    def start(init_mongo: bool = True,
              init_rabbit: bool = True,
              queue_name: str = None,
              starts_url: List[str] = None):

        def __start(func):
            @wraps(func)
            async def _wrap(self, *args, **_kwargs):
                try:
                    flag = run_flag.get()
                    if not flag:
                        await self.fetch_start(func, queue_name=queue_name,
                                               init_mongo=init_mongo, init_rabbit=init_rabbit,
                                               starts_url=starts_url
                                               )
                    else:
                        await func(self, *args, **_kwargs)
                except asyncio.CancelledError as e:
                    crawler.error(e.args)

            return _wrap

        return __start
