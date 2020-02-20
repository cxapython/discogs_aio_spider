# -*- coding: utf-8 -*-
# @Time : 2019-03-22 15:05
# @Author : cxa
# @File : base_crawler.py
# @Software: PyCharm

import asyncio
import aiohttp
from loguru import logger as crawler
import async_timeout
from collections import namedtuple
from config.config import *
from async_retrying import retry
from lxml import html
from aiostream import stream
from copy import deepcopy
import traceback
Response = namedtuple("Response",
                      ["status", "source"])

try:
    import uvloop

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    pass
sem = asyncio.Semaphore(CONCURRENCY_NUM)


class Crawler:
    def __init__(self):
        self.tc = None
        self.session = None
        self.session_flag = False

    @retry(attempts=MAX_RETRY_TIMES)
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
        if USE_PROXY:
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
        result = list()
        if _attr:
            if _attr == "text":
                result = [entry.text for entry in nodes]
            else:
                result = [entry.get(_attr) for entry in nodes]
        else:
            result = nodes
        return result

    async def branch(self, coros, limit=10):
        """
        使用aiostream模块对异步生成器做一个切片操作。这里并发量为10.
        :param coros: 是一个异步生成器函数调用之前的
        :param limit: 并发次数
        :return:
        """
        if callable(coros):
            index = 0
            while True:
                xs = stream.iterate(coros())
                ys = xs[index:index + limit]
                t = await stream.list(ys)
                if not t:
                    break
                await asyncio.wait(t)
                index += limit
                await asyncio.sleep(0.01)

    async def start(self):
        try:
            await self.init_session()
            tasks = self.create_task_gen
            await self.branch(tasks)
        except asyncio.CancelledError as e:
            crawler.error("CancelledError")
        except Exception as e:
            crawler.error(f"else error:{traceback.format_exc()}")
        finally:
            await self.close_session()

    # async def get_proxy(self) -> Optional[str]:
    #     """
    #     获取代理
    #     """
    #     while True:
    #         proxy = await proxy_helper.get_proxy(isown=1, protocol=2, site='dianping')
    #         if proxy:
    #             host = proxy[0].get('ip')
    #             port = proxy[0].get('port')
    #             ip = f"http://{host}:{port}"
    #             return ip
    #         else:
    #             crawler.info("代理超时开始等待")
    #
    #             await asyncio.sleep(5)

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


if __name__ == '__main__':
    c = Crawler().run()
