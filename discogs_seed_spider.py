# -*- coding: utf-8 -*-
# @Time : 2019-03-22 13:41
# @Author : cxa
# @File : discogs_seed_spider.py
# @Software: PyCharm
# 2000-2009
import asyncio
from db.mongohelper import MotorOperation
from collections import namedtuple
from common.base_crawler import Crawler
from decorators.decorators import decorator
import re
from collections import deque
from itertools import product
from loguru import logger
import sys

Response = namedtuple("Response",
                      ["status", "text"])
try:
    import uvloop

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    pass
START_URL_LIST = [f"https://www.discogs.com/search/?limit=25&layout=sm&decade=2000&year={i}&page=1"
                  for i in range(2000, 2001)]
# 最终形式
BASE_URL = ("https://www.discogs.com/search/?layout=sm&country_exact=UK&format_exact=Vinyl&limit=100&year=2000&"
            "style_exact=House&page=2&decade=2000")
DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Host": "www.discogs.com",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36",
}


class SeedSpider(Crawler):

    async def start(self):
        try:
            await self.init_session()
            res_list: list = [asyncio.ensure_future(self.fetch_home(url)) for url in START_URL_LIST]
            tasks = asyncio.wait(res_list)
            await tasks
        except Exception as e:
            logger.error(f"{e.args}")
        finally:
            await self.close_session()

    async def fetch_home(self, url: str):
        """
        访问主页，并开始解析
        :param url:
        :return:
        :param url:
        :return:
        """
        kwargs = {"headers": DEFAULT_HEADERS}
        response = await self.get_session(url, kwargs)
        if response.status == 200:
            source = response.source
            await self.parse(source)

    async def parse(self, source):
        """
        # ul分四块处理, 风格，唱片类型，国家。
        # 分块处理
        :param source: 
        :return: 
        """
        # keyword = ["Italodance", "House", "Trance"]
        style_dic = dict()
        format_dic = dict()
        country_dic = dict()
        type_dic = {"style": style_dic, "format": format_dic, "country": country_dic}
        xpath_id_dic = {"style": "facets_style_exact", "format": "facets_format_exact",
                        "country": "facets_country_exact"}

        for k, v in xpath_id_dic.items():
            x = f"//div[@id='{v}']/ul/li/a"
            node_list = self.xpath(source, x)
            for item in node_list:
                count = self.xpath(item, ".//small", "text")[0].replace(",", "")
                _type = self.xpath(item, "@href")[0]
                name = self.xpath(item, ".//span[@class='facet_name']", "text")[0].strip("\n").strip()
                url_name = name.replace(" ", "+")
                # r = v.split("facets_")[1]
                # pat = re.compile(f"{r}=(.*?)&")
                # url_name = pat.findall(_type)[0]
                if k == "style":
                    if (
                            "ITALO" in name.upper() or "DANCE" in name.upper() or "HOUSE" in name.upper() or "TECHNO" in name.upper()
                            or "CORE" in name.upper() or "HARD" in name.upper()
                            or "EURO" in name.upper()):
                        type_dic[k].setdefault("url_name", deque()).append(url_name)
                        type_dic[k].setdefault("name", deque()).append(name)
                        type_dic[k].setdefault("count", deque()).append(count)
                else:
                    type_dic[k].setdefault("url_name", deque()).append(url_name)
                    type_dic[k].setdefault("name", deque()).append(name)
                    type_dic[k].setdefault("count", deque()).append(count)

        tasks = deque()
        t_append = tasks.append
        for item in product([2000, 2001, 2002, 2003], style_dic["url_name"], format_dic["url_name"],
                            country_dic["url_name"]):
            country = item[3]
            _format = item[2]
            year = item[0]
            style = item[1]
            url = (f"https://www.discogs.com/search/?layout=sm&country_exact={country}&"
                   f"format_exact={_format}&limit=100&year={year}&style_exact={style}&page=1&decade=2000")
            t_append(url)
        await MotorOperation().save_data_with_status(tasks)


if __name__ == '__main__':
    python_version = sys.version_info
    s = SeedSpider()
    if python_version >= (3, 7):
        asyncio.run(s.start())
    else:
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(s.start())
        finally:
            loop.close()
