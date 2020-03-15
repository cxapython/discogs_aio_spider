# -*- coding: utf-8 -*-
# @Time : 2019-03-22 13:41
# @Author : cxa
# @File : seed.py
# @Software: PyCharm
# 2000-2009
import asyncio
from common.base_crawler import Crawler
from collections import deque
from itertools import product
import sys
from dataclasses import dataclass
import time

try:
    import uvloop

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    pass
START_URL_LIST = [f"http://192.168.3.7:5000/seed/?item_id={i}&v={i}"
                  for i in range(1, 2)]
DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36",
}


@dataclass
class SeedSpider(Crawler):
    @staticmethod
    def gen_url(item_id: int = 0, v: str = None):
        _url = f"http://192.168.3.7:5000/seed/?item_id={item_id}&v={v}"
        return _url

    @Crawler.start(init_mongo=False, starts_url=START_URL_LIST)
    async def fetch_home(self, url: str):
        """
        访问主页，并开始解析
        :param url:
        :return:
        """
        kwargs = {"headers": DEFAULT_HEADERS}
        async with self.http_client() as client:
            print(url)
            response = await client.get_session(url, _kwargs=kwargs)
            if response.status == 200:
                await self.parse()

    @staticmethod
    def create_url_gen():
        for i in range(100000):
            data = dict()
            data["id"] = i
            data["value"] = f"{i + int(time.time())}"
            yield data

    async def parse(self):

        url_gen = self.create_url_gen()
        for data in url_gen:
            await self.rabbitmq_pool.publish("test_seed", data)
            await asyncio.sleep(0.01)


def start_seed():
    python_version = sys.version_info
    s = SeedSpider()
    if python_version >= (3, 7):
        asyncio.run(s.fetch_home())
    else:
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(s.fetch_home())
        finally:
            loop.close()


if __name__ == '__main__':
    start_seed()
