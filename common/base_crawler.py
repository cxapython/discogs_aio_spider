# -*- coding: utf-8 -*-
# @Time : 2019-03-22 15:05
# @Author : cxa
# @File : base_crawler.py
# @Software: PyCharm
# @公众号: Python学习开发

import asyncio
import hashlib
import logging
import traceback
from contextlib import asynccontextmanager
from contextvars import ContextVar
from copy import deepcopy
from dataclasses import dataclass
from functools import partial
from functools import wraps
from types import TracebackType
from typing import Optional, Dict, Any, Union, List, Callable, Type, AsyncIterator, Awaitable

import aioredis
import httpx
import msgpack
from loguru import logger as crawler
from lxml import html
from pydantic import BaseModel

from config import MongoConfig, RabbitmqConfig, SpiderConfig, RedisConfig
from util import RabbitMqPool, MongoPool, RedisPool
from util import aio_retry

asyncio.log.logger.setLevel(logging.ERROR)

Node = List[str]
run_flag: ContextVar = ContextVar('which function will run in decorator')

run_flag.set(False)

try:
    import uvloop

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    pass


class Response(BaseModel):
    status: int
    source: str


@dataclass
class HTTPClient:
    def __post_init__(self):
        self.spider_config = SpiderConfig
        proxies = {
            "all://": None,
        }
        if self.spider_config.get("USE_PROXY"):
            from config.proxy_config import PROXY_SERVER
            proxies = PROXY_SERVER
        self.session = httpx.AsyncClient(proxies=proxies)

    async def close(self):
        crawler.info("close session")
        return await self.session.aclose()

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
        method = kwargs.pop("method", "get")
        req = await getattr(self.session, method)(url, **kwargs)
        status = req.status_code
        if status in [status_code, 201]:
            if source_type == "text":
                source = req.text
            elif source_type == "buff":
                source = req.content
        crawler.info(f"get url:{url},status:{status}")
        res = Response(status=status, source=source)
        return res


@dataclass
class Crawler:
    session_flag: bool = False
    redis_client: Optional[aioredis.create_redis_pool] = None

    def __post_init__(self):
        self.spider_config = SpiderConfig
        self.rabbitmq_pool = RabbitMqPool()
        self.mongo_config = MongoConfig
        self.mongo_pool = MongoPool
        self.rabbitmq_config = RabbitmqConfig
        self.redis_pool = RedisPool
        self.redis_config = RedisConfig

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

    async def init_redis(self):
        loop = asyncio.get_running_loop()
        self.redis_client = self.redis_pool(redis_url=self.redis_config["REDIS_URL"], loop=loop)
        pool = await self.redis_client.create_redis_pool()
        return pool

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
        """
        Assign crawler tasks according to starts_url
        :param callback:
        :param init_rabbit:
        :param init_mongo:
        :param queue_name:
        :param starts_url:
        :return:
        """
        try:
            run_flag.set(True)
            await self.init_all(init_rabbit=init_rabbit, init_mongo=init_mongo)
            if starts_url is None:
                next_func = partial(self.request_seen, queue_name, callback)
                await self.rabbitmq_pool.subscribe(queue_name, next_func)
            else:
                res_list = [asyncio.ensure_future(getattr(self, callback.__name__)(url)) for url in starts_url]
                tasks = asyncio.wait(res_list)
                await tasks

        except (asyncio.CancelledError, asyncio.TimeoutError) as e:
            crawler.error("asyncio cancelle or timeout error")
        except Exception as e:
            crawler.error(f"else error:{traceback.format_exc()}")

    @staticmethod
    def request_fingerprint(data: Union[bytes, str]):
        """
        The result is converted to md5
        :param data:
        :return:
        """
        if isinstance(data, str):
            data = bytes(data, encoding="utf-8")
        m = hashlib.md5()
        m.update(data)
        return m.hexdigest()

    async def _request_seen(self, *, key, item, msg):
        """
        :param key: redis key
        :param item:
        :param msg:
        :return:
        """
        fp = self.request_fingerprint(item)
        pool = await self.init_redis()
        added = await pool.sadd(key, fp)
        flag = False
        if added == 0:
            await msg.ack()
        else:
            flag = True
        await self.redis_client.destroy_redis_pool()
        return flag

    async def request_seen(self, key_name, callback, msg):
        """
        :param key_name: redis key
        :param callback: will evaluate method
        :param msg: msg
        :return:
        """
        message = msg.body
        item = msgpack.unpackb(msg.body, raw=False)
        result = await self._request_seen(key=key_name, item=message, msg=msg)
        if result:
            await getattr(self, callback.__name__)(item, msg)

    @staticmethod
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
