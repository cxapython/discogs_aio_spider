# -*- coding: utf-8 -*-
# @Time : 2019-03-22 13:41
# @Author : cxa
# @File : discogs_index_spider.py
# @Software: PyCharm
# 2000-2009
import asyncio
import sys
import traceback

sys.path.append("..")
from util import MotorOperation
from loguru import logger as crawler
import datetime
from common.base_crawler import Crawler
import re
import math
from urllib.parse import urljoin
import sys
from dataclasses import dataclass

try:
    import uvloop

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    pass
BASE_URL = "https://www.discogs.com"
DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Host": "www.discogs.com",
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.121 Safari/537.36"),
}

QUEUE_NAME = "discogs_seed_spider"


@dataclass
class IndexSpider(Crawler):
    page_pat: str = "&page=.*&"

    @Crawler.start(queue_name=QUEUE_NAME)
    async def fetch_index_page(self, _item, msg) -> None:
        """
        Visit the list page and start parsing
        :param msg:
        :param _item:
        :return:
        """
        item = _item
        country = item["country"]
        _format = item["format"]
        year = item["year"]
        style = item["style"]
        url = (f"https://www.discogs.com/search/?layout=sm&country_exact={country}&"
               f"format_exact={_format}&limit=100&year={year}&style_exact={style}&page=1&decade=2000")
        # headers's value must be dict type.
        kwargs = {"headers": DEFAULT_HEADERS, "timeout": 15}
        # Modifying the status of the seed link to 1 means that crawling has started.
        async with self.http_client() as client:
            response = await client.get_session(url, _kwargs=kwargs)
            if response.status == 200:
                source = response.source
                # Get the current link and construct the url of all pages.
                # Save the html source of the current page.
                have_more = await self.get_list_info(url, source)
                # Successfully completed the task
                await msg.ack()
                if have_more:
                    await self.max_page_index(url, source)
                else:
                    crawler.info(f"No more content in this category ,now {url=}")
                    return True

    async def get_list_info(self, url: str, source: str):
        """
        In order to obtain the correctness of the elements, the processing is performed in blocks.
        :param url: The url of the current page
        :param source: html source
        :return:
        """
        have_more = False
        div_xpath = "//div[@class='cards cards_layout_text-only']/div"
        div_node_list = self.xpath(source, div_xpath)
        task = []
        for div_node in div_node_list:
            try:
                dic = dict()
                dic["obj_id"] = self.xpath(div_node, "@data-object-id")[0]
                dic["artist"] = self.xpath(div_node, ".//div[@class='card_body']/h4/span/a", "text")[0]
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
                country_arr = self.xpath(div_node, f"{card_info_xpath}/span[@class='card_release_country']", "text")
                dic["country"] = country_arr[0] if country_arr else "UnKnow"
                dic["url"] = url
                dic["page_index"] = 1
                dic["crawler_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                task.append(dic)
                """
                https://www.discogs.com/Mary-Griffin-Perfect-Moment/master/98792
                https://www.discogs.com+作者+歌名+master+obj_id 
                """
                await self.rabbitmq_pool.publish("discogs_index_spider",
                                                 {"url": _detail_url})

            except IndexError as e:
                # https://www.discogs.com/search/?layout=sm&country_exact=Unknown&format_exact=Cassette&limit=100&year=2000&style_exact=House&page=1&decade=2000
                crawler.error(f"Parsing error, the url at this time is:{url=},detail:{traceback.format_exc()}")
        if task:
            have_more = True
            await MotorOperation().save_data(self.mongo_pool, task)
        return have_more

    async def max_page_index(self, url: str, source: str):
        """
        :param url:
        :param source:
        :return:
        """
        total_page_node = self.xpath(source, "//strong[@class='pagination_total']", "text")
        if total_page_node:
            total_page = total_page_node[0].split("of")[-1].strip().replace(",", "")
            _max_page_index = math.ceil(int(total_page) / 100)
            if _max_page_index > 1:
                for i in range(2, _max_page_index + 1):
                    new_url = re.sub(self.page_pat, f"&page={i}&", url)
                    country = re.findall("country_exact=(.*?)&", new_url)[0]
                    _format = re.findall("format_exact=(.*?)&", new_url)[0]
                    year = re.findall("year=(.*?)&", new_url)[0]
                    style = re.findall("style_exact=(.*?)&", new_url)[0]
                    page = re.findall("page=(.*?)&", new_url)[0]
                    data = dict()
                    data["country"] = country
                    data["format"] = _format
                    data["year"] = year
                    data["style"] = style
                    data["page"] = page
                    await self.rabbitmq_pool.publish("discogs_seed_spider", data)


if __name__ == '__main__':
    python_version = sys.version_info
    s = IndexSpider()
    if python_version >= (3, 7):
        asyncio.run(s.fetch_index_page())
    else:
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(s.fetch_index_page())
        finally:
            loop.close()
