# -*- coding: utf-8 -*-
# @时间 : 2020-03-13 20:20
# @作者 : 陈祥安
# @文件名 : test_pika.py
# @公众号: Python学习开发
import aiohttp
from util import RabbitMqPool
from config import RabbitmqConfig
import msgpack
import asyncio
from common.base_crawler import Crawler
from dataclasses import dataclass

DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36",
}
QUEUE_NAME = "test_seed"
results = []

@dataclass
class Sipder(Crawler):
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
                print(source)



async def init():
    """
    :return:
    """
    rabbitmq_pool = RabbitMqPool()
    rabbitmq_config = RabbitmqConfig
    await rabbitmq_pool.init(
        addr=rabbitmq_config["addr"],
        port=rabbitmq_config["port"],
        vhost=rabbitmq_config["vhost"],
        username=rabbitmq_config["username"],
        password=rabbitmq_config["password"],
        max_size=rabbitmq_config["max_size"],
    )
    return rabbitmq_pool


async def callback(msg):
    item = msgpack.unpackb(msg.body, raw=False)
    seed_id = item["id"]
    seed_value = item["value"]
    url = f"http://192.168.3.7:5000/index/?item_id={seed_id}&v={seed_value}"
    await Sipder().fetch_home(url)

    # await msg.ack()


async def test_publish():
    rabbitmq_pool = await init()
    for i in range(16):
        data = dict()
        data["country"] = "italy"
        data["format"] = "cd"
        data["year"] = 2001
        data["style"] = "dance"
        data["page"] = 1
        await rabbitmq_pool.publish(QUEUE_NAME, data)


async def test_subscribe():
    rabbitmq_pool = await init()
    await rabbitmq_pool.subscribe(QUEUE_NAME, callback)


if __name__ == '__main__':
    asyncio.run(test_subscribe())
