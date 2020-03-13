# -*- coding: utf-8 -*-
# @时间 : 2020-03-13 20:20
# @作者 : 陈祥安
# @文件名 : test_pika.py
# @公众号: Python学习开发
import pytest
from util import RabbitMqPool
from config import RabbitmqConfig
import msgpack
from collections.abc import Mapping
import asyncio


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
    print(item)
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
        await rabbitmq_pool.publish("discogs_seed_spider", data)


async def test_subscribe():
    rabbitmq_pool = await init()
    await rabbitmq_pool.subscribe("discogs_seed_spider", callback)


if __name__ == '__main__':
    asyncio.run(test_publish())
