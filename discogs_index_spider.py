# -*- coding: utf-8 -*-
# @Time : 2019-03-22 13:41
# @Author : cxa
# @File : discogs_index_spider.py
# @Software: PyCharm
# 2000-2009
import asyncio
from db.mongohelper import MotorOperation
from loguru import logger as  crawler
from collections import namedtuple, deque
import datetime
from common.base_crawler import Crawler
from types import AsyncGeneratorType
from decorators.decorators import decorator
import re
import math
from urllib.parse import urljoin
from typing import Mapping, Dict
import sys
import traceback

Response = namedtuple("Response",
                      ["status", "text"])
try:
    import uvloop

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    pass
BASE_URL = "https://www.discogs.com"
# 最终形式
DEFAULT_HEADRS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Host": "www.discogs.com",
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2)" \
                   " AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.121 Safari/537.36"),
}


class IndexSpider(Crawler):
    def __init__(self):
        self.page_pat = "&page=.*&"

    async def create_task_gen(self):
        data: AsyncGeneratorType = MotorOperation().find_data()
        async for item in data:
            yield asyncio.ensure_future(self.fetch_index_page(item))

    async def fetch_index_page(self, item: Dict[str, str]):
        """
        访问列表，并开始解析
        :param item:
        :return:
        """
        url = item.get("url")
        kwargs = {"headers": DEFAULT_HEADRS, "timeout": 15}
        # 修改种子URL的状态为1表示开始爬取。
        condition = {'url': url}
        await MotorOperation().change_status(condition, status_code=1)
        response = await self.get_session(url, kwargs)
        if response.status == 200:
            source = response.source
            # 获取当前的链接然后构建所有页数的url。
            # 保存当一页的内容。
            no_more = await self.get_list_info(url, source)
            if no_more:
                await self.max_page_index(url, source)
            else:
                crawler.info(f"该分类没有更多内容:{url}")

    async def get_list_info(self, url, source):
        """
        为了取得元素的正确性，这里按照块进行处理。
        :param url: 当前页的url
        :param source: 源码
        :return:
        """
        no_more = False
        div_xpath = "//div[@class='cards cards_layout_text-only']/div"
        div_node_list = self.xpath(source, div_xpath)
        tasks = list()
        t_append = tasks.append
        for div_node in div_node_list:
            try:
                dic = dict()
                dic["obj_id"] = self.xpath(div_node, "@data-object-id")[0]
                dic["artist"] = self.xpath(div_node, ".//div[@class='card_body']/h4/span/a", "text")[0]
                # dic["artist"] = self.xpath(div_node, ".//div[@class='card_body']/h4/span", "text")[0]
                dic["title"] = \
                    self.xpath(div_node, ".//div[@class='card_body']/h4/a[@class='search_result_title ']", "text")[0]
                _detail_url = \
                    self.xpath(div_node, ".//div[@class='card_body']/h4/a[@class='search_result_title ']", "href")[0]
                dic["detail_url"] = urljoin(BASE_URL, _detail_url)

                card_info_xpath = ".//div[@class='card_body']/p[@class='card_info']"
                dic["label"] = self.xpath(div_node, f"{card_info_xpath}/a", "text")[0]
                dic["catalog_number"] = \
                    self.xpath(div_node, f"{card_info_xpath}/span[@class='card_release_catalog_number']", "text")[0]
                dic["format"] = self.xpath(div_node, f"{card_info_xpath}/span[@class='card_release_format']", "text")[0]
                dic["year"] = self.xpath(div_node, f"{card_info_xpath}/span[@class='card_release_year']", "text")[0]
                dic["country"] = self.xpath(div_node, f"{card_info_xpath}/span[@class='card_release_country']", "text")[
                    0]
                dic["url"] = url
                dic["page_index"] = 1
                dic["status"] = 0
                dic["crawler_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                t_append(dic)
            except IndexError as e:
                # https://www.discogs.com/search/?layout=sm&country_exact=Unknown&format_exact=Cassette&limit=100&year=2000&style_exact=House&page=1&decade=2000
                crawler.error(f"解析出错，此时的url是:{url}")
        condition = {"url": url}
        status_code = 2
        if tasks:
            no_more = True
            await MotorOperation().save_data(tasks)
        else:
            status_code = 4
        await MotorOperation().change_status(condition, status_code=status_code)
        return no_more

    @decorator(False)
    async def max_page_index(self, url, source):
        """
        :param url:
        :param source:
        :return:
        """
        total_page_node = self.xpath(source, "//strong[@class='pagination_total']", "text")
        if total_page_node:
            total_page = total_page_node[0].split("of")[-1].strip().replace(",", "")
            _max_page_index = math.ceil(int(total_page) / 100)
            new_url_list = deque()
            n_append = new_url_list.append
            if _max_page_index > 1:
                for i in range(2, _max_page_index + 1):
                    new_url = re.sub(self.page_pat, f"&page={i}&", url)
                    n_append(new_url)
                await MotorOperation().save_data_with_status(new_url_list)


if __name__ == '__main__':
    python_version = sys.version_info
    s = IndexSpider()
    if python_version >= (3, 7):
        asyncio.run(s.start())
    else:
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(s.start())
        finally:
            loop.close()
