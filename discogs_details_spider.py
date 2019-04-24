# -*- coding: utf-8 -*-
# @Time : 2019/3/24 2:05 AM
# @Author : cxa
# @File : discogs_details_spider.py
# @Software: PyCharm
import asyncio
from async_retrying import retry
import aiofiles
import aiohttp
from db.mongohelper import MotorOperation
from lxml import html
from logger.log import crawler, storage
from utils import proxy_helper
import async_timeout
from collections import namedtuple, deque
import datetime
import base64
from copy import copy
import os
from common.base_crawler import Crawler
from types import AsyncGeneratorType
from decorators.decorators import decorator
import re
import math
from urllib.parse import urljoin
from multidict import CIMultiDict
from itertools import islice

DEFAULT_HEADRS = CIMultiDict({
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Host": "www.discogs.com",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.121 Safari/537.36",
})
BASE_URL = "https://www.discogs.com"


class Details_Spider(Crawler):
    def __init__(self):
        self.page_pat = "&page=.*&"

    @decorator()
    async def start(self):
        # 获取mongo的数据,类型异步生成器。
        data: AsyncGeneratorType = await MotorOperation().find_data(col="discogs_index_data")
        await self.init_session()
        # 分流
        tasks = (asyncio.ensure_future(self.fetch_detail_page(item)) async for item in data)
        await self.branch(tasks)

    @decorator(False)
    async def fetch_detail_page(self, item: dict):
        '''
        访问详情页，开始解析
        :param url:
        :return:

        '''
        detail_url = item.get("detail_url")
        kwargs = {"headers": DEFAULT_HEADRS}
        # 修改种子URL的状态为1表示开始爬取。
        condition = {'detail_url': detail_url}
        await MotorOperation().change_status(condition, col="discogs_index_data", status_code=1)
        response = await self.get_session(detail_url, kwargs)
        if response.status == 200:
            source = response.source
            # await self.more_images(source)
            try:
                await self.get_list_info(item, detail_url, source)
            except:
                crawler.info(f"解析出错:{detail_url}")

    @retry(attempts=3)
    async def url2base64(self, url):
        res = await self.get_session(url, source_type="buff")
        base64_data = f"data:image/jpg;base64,{base64.b64encode(res.source).decode('utf-8')}"
        return base64_data

    @decorator(False)
    async def get_list_info(self, data_item, url, source):
        '''
        为了取得元素的正确性，这里按照块进行处理。
        :param url: 当前页的url
        :param source: 源码
        :return:
        '''
        cover_xpath = "//meta[@property='og:image']"
        track_div_xpath = "//div[@id='page_content']//table//tr"
        cover_url_list = self.xpath(source, cover_xpath, "content")
        cover_url = cover_url_list[0]
        base64url = await self.url2base64(cover_url)
        div_node_list = self.xpath(source, track_div_xpath)
        title_list = []
        save_dic = {}
        for index, item in enumerate(div_node_list, 1):
            try:
                artist_node = self.xpath(item, ".//td[@class='tracklist_track_artists']/a", "text")
                title_node = self.xpath(item, ".//td/a/span[@class='tracklist_track_title']", "text")
                artist = None
                title = None
                if title_node:
                    title = title_node[0]
                else:
                    break
                if artist_node:
                    artist = artist_node[0]
                    title = f"{artist}-{title}"
                title_list.append(f"{index}.{title}")
            except:
                pass
        save_dic.update(data_item)
        save_dic["cover_url"] = cover_url
        save_dic["base64url"] = base64url
        save_dic["title_list"] = title_list
        save_dic["crawler_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        save_dic.pop("status")
        await MotorOperation().save_data(save_dic, col="discogs_details_data", key="detail_url")
        # 修改种子URL的状态为2表示爬取成功。
        condition = {"detail_url": url}
        await MotorOperation().change_status(condition, col="discogs_index_data", status_code=2)

    @decorator()
    async def more_images(self, source):
        '''
        获取更多图片的链接
        :param source:
        :return:
        '''
        more_url_node = self.xpath(source, "//a[contains(@class,'thumbnail_link') and contains(@href,'images')]",
                                   "href")
        if more_url_node:
            _url = islice(more_url_node, 0)
            more_url = urljoin(BASE_URL, _url)
            kwargs = {"headers": DEFAULT_HEADRS}
            response = await self.get_session(more_url, kwargs)
            if response.status == 200:
                source = response.source
                await self.parse_images(source)

    async def get_image_buff(self, img_url):
        img_headers = copy(DEFAULT_HEADRS)
        img_headers["host"] = "img.discogs.com"
        kwargs = {"headers": img_headers}
        response = await self.get_session(img_url, kwargs, source_type="buff")
        buff = response.source
        await self.save_image(img_url, buff)

    @decorator()
    async def save_image(self, img_url, buff):
        image_name = img_url.split("/")[-1].replace(".jpeg", "")
        file_path = os.path.join(os.getcwd(), "discogs_images")
        image_path = os.path.join(file_path, image_name)
        if not os.path.exists(file_path):
            os.makedirs(file_path)
            # 文件是否存在
        if not os.path.exists(image_path):
            storage.info(f"SAVE_PATH:{image_path}")
            async with aiofiles.open(image_path, 'wb') as f:
                await f.write(buff)

    @decorator()
    async def parse_images(self, source):
        '''
        解析当前页所有图片的链接
        :param source:
        :return:
        '''
        image_node_list = self.xpath(source, "//div[@id='view_images']/p//img", "src")
        tasks = [asyncio.ensure_future(self.get_image_buff(url)) for url in image_node_list]
        await tasks


if __name__ == '__main__':
    s = Details_Spider()
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(s.start())
    finally:
        loop.close()
