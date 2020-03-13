# -*- coding: utf-8 -*-
# @Time : 2019/3/24 2:05 AM
# @Author : cxa
# @File : discogs_details_spider.py
# @Software: PyCharm
import asyncio
from util import aio_retry
import aiofiles
from loguru import logger as  crawler
from loguru import logger as  storage
import datetime
import base64
from copy import copy
import os
from common.base_crawler import Crawler
import sys
from multidict import CIMultiDict
from itertools import islice
from util import decorator, MotorOperation
import msgpack
from urllib.parse import urljoin
from dataclasses import dataclass

DEFAULT_HEADERS = CIMultiDict({
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Host": "www.discogs.com",
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.121 Safari/537.36"),
})


@dataclass
class DetailsSpider(Crawler):

    @Crawler.start(queue_name="discogs_index_spider")
    async def fetch_detail_page(self, msg: str):
        """
        访问详情页，开始解析
        :param msg:队列消息，包括info和body
        :return:
        """
        url = msgpack.unpackb(msg.body, raw=False).get("url")
        kwargs = {"headers": DEFAULT_HEADERS}
        async with self.http_client() as client:
            detail_url = urljoin(self.spider_config["BASE_URL"], url)
            response = await client.get_session(detail_url, _kwargs=kwargs)
            if response.status == 200:
                source = response.source
                if self.spider_config["SAVE_IMG_FILE"]:
                    await self.more_images(source)
                try:
                    await self.get_list_info(detail_url, source)
                    await msg.ack()
                except Exception as e:
                    crawler.info(f"解析出错:{detail_url}")

    @aio_retry(attempts=3)
    async def url2base64(self, url):
        """
        将图片专为base64保存
        :param url:
        :return:
        """
        async with self.http_client() as client:
            res = await client.get_session(url, source_type="buff")
            base64_data = f"data:image/jpg;base64,{base64.b64encode(res.source).decode('utf-8')}"
            return base64_data

    async def get_list_info(self, url, source):
        """
        为了取得元素的正确性，这里按照块进行处理。
        :param url: 当前页的url
        :param source: 源码
        :return:
        """
        cover_xpath = "//meta[@property='og:image']"
        track_div_xpath = "//div[@id='page_content']//table//tr"
        cover_url_list = self.xpath(source, cover_xpath, "content")
        cover_url = cover_url_list[0]
        if self.spider_config["SAVE_IMG_BASE64"]:
            base64url = await self.url2base64(cover_url)
        div_node_list = self.xpath(source, track_div_xpath)
        title_list = list()
        for index, item in enumerate(div_node_list, 1):
            try:
                artist_node = self.xpath(item, ".//td[@class='tracklist_track_pos']", "text")
                title_node = self.xpath(item, ".//td//span[@class='tracklist_track_title']", "text")
                if title_node:
                    title = title_node[0]
                else:
                    break
                if artist_node:
                    artist = artist_node[0]
                    title = f"{artist}-{title}"

                title_list.append(f"{index}.{title}")
            except Exception as e:
                crawler.warning(f"{e.args}")

        save_dic = dict()

        save_dic["obj_id"] = url.split('/')[-1]
        save_dic["cover_url"] = cover_url
        if self.spider_config["SAVE_IMG_BASE64"]:
            save_dic["base64url"] = base64url
        save_dic["title_list"] = title_list
        save_dic["crawler_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # 根据obj_id更新
        await MotorOperation().save_data(self.mongo_pool, save_dic,
                                         col="discogs_details_data", key="obj_id")

    @decorator()
    async def more_images(self, source):
        """
        获取更多图片的链接
        :param source:
        :return:
        """
        more_url_node = self.xpath(source, "//a[contains(@class,'thumbnail_link') and contains(@href,'images')]",
                                   "href")
        if more_url_node:
            _url = islice(more_url_node, 0)
            more_url = urljoin(self.spider_config["BASE_URL"], _url)
            kwargs = {"headers": DEFAULT_HEADERS}
            async with self.http_client() as client:
                response = await client.get_session(more_url, _kwargs=kwargs)
                if response.status == 200:
                    source = response.source
                    await self.parse_images(source)

    async def get_image_buff(self, img_url):
        img_headers = copy(DEFAULT_HEADERS)
        img_headers["host"] = "img.discogs.com"
        kwargs = {"headers": img_headers}
        async with self.http_client() as client:
            response = await client.get_session(img_url, _kwargs=kwargs, source_type="buff")
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
        """
        解析当前页所有图片的链接
        :param source:
        :return:
        """
        image_node_list = self.xpath(source, "//div[@id='view_images']/p//img", "src")
        tasks = [asyncio.ensure_future(self.get_image_buff(url)) for url in image_node_list]
        await tasks


if __name__ == '__main__':
    s = DetailsSpider()
    python_version = sys.version_info
    if python_version >= (3, 7):
        asyncio.run(s.fetch_detail_page())
    else:
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(s.fetch_detail_page())
        finally:
            loop.close()
