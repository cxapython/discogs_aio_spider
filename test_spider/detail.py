# -*- coding: utf-8 -*-
# @时间 : 2020/3/15 5:20 下午
# @作者 : 陈祥安
# @文件名 : detail.py
# @公众号: Python学习开发
# -*- coding: utf-8 -*-
# @时间 : 2020/3/15 5:20 下午
# @作者 : 陈祥安
# @文件名 : index.py
# @公众号: Python学习开发

import asyncio
from util import MotorOperation
from loguru import logger as crawler
import datetime
from common.base_crawler import Crawler
import re
import math
from multidict import CIMultiDict
from urllib.parse import urljoin
import sys
from dataclasses import dataclass
import json

try:
    import uvloop

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    pass
BASE_URL = "http://192.168.3.7"
# 最终形式
DEFAULT_HEADERS = CIMultiDict({
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.121 Safari/537.36"),
})

QUEUE_NAME = "test_index"


@dataclass
class DetailSpider(Crawler):
    @Crawler.start(queue_name=QUEUE_NAME)
    async def fetch_detail_page(self, _item, msg) -> None:
        """
        访问列表，并开始解析
        :param msg:
        :param _item:
        :return:
        """
        item = _item
        seed_id = item["index_item_id"].split("_")[-1]
        seed_value = item["index_value"]
        url = f"http://192.168.3.7:5000/detail/?item_id={seed_id}&v={seed_value}"
        kwargs = {"headers": DEFAULT_HEADERS, "timeout": 15}
        # 修改种子URL的状态为1表示开始爬取。
        async with self.http_client() as client:
            response = await client.get_session(url, _kwargs=kwargs)
            if response.status == 200:
                source = response.source
                # 获取当前的链接然后构建所有页数的url。
                # 保存当一页的内容。
                await self.get_list_info(url, source)
                await msg.ack()

    async def get_list_info(self, url: str, source: str):
        """
        为了取得元素的正确性，这里按照块进行处理。
        :param url: 当前页的url
        :param source: 源码
        :return:
        """
        result = json.loads(source)
        result["crawler_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        await MotorOperation().save_data(self.mongo_pool, result,
                                         col="test_details_data", key="detail_item_id")


if __name__ == '__main__':
    python_version = sys.version_info
    s = DetailSpider()
    if python_version >= (3, 7):
        asyncio.run(s.fetch_detail_page())
    else:
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(s.fetch_detail_page())
        finally:
            loop.close()
