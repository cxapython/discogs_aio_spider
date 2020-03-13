# -*- coding: utf-8 -*-
# @Time : 2019-03-22 13:41
# @Author : cxa
# @File : discogs_seed_spider.py
# @Software: PyCharm
# 2000-2009
import asyncio
from common.base_crawler import Crawler
from collections import deque
from itertools import product
import sys
from dataclasses import dataclass

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


@dataclass
class SeedSpider(Crawler):
    @Crawler.start(init_mongo=False, starts_url=START_URL_LIST)
    async def fetch_home(self, url: str):
        """
        访问主页，并开始解析
        :param url:
        :return:
        """
        kwargs = {"headers": DEFAULT_HEADERS}
        async with self.http_client() as client:
            response = await client.get_session(url, _kwargs=kwargs)
            if response.status == 200:
                source = response.source
                await self.parse(source)

    async def parse(self, source: str):
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

        for item in product([2000, 2001], style_dic["url_name"], format_dic["url_name"],
                            country_dic["url_name"]):
            data = dict()
            country = item[3]
            _format = item[2]
            year = item[0]
            style = item[1]
            data["country"] = country
            data["format"] = _format
            data["year"] = year
            data["style"] = style
            data["page"] = 1
            await self.rabbitmq_pool.publish("discogs_seed_spider", data)


if __name__ == '__main__':
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
