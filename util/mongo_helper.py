# -*- coding: utf-8 -*-
# @时间 : 2020-02-21 12:24
# @作者 : 陈祥安
# @文件名 : mongo_helper.py
# @公众号: Python学习开发
from motor.motor_asyncio import AsyncIOMotorClient

from util.singleton import Singleton
import asyncio
from loguru import logger as storage
from pymongo import UpdateOne

try:
    import uvloop

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    pass

db_configs = {
    'host': '127.0.0.1',
    'port': '27017',
    'db_name': 'aio_spider_data',
    'user': ''
}


class MongoPool(AsyncIOMotorClient, Singleton):
    """
    全局mongo连接池
    """
    pass


class MotorOperation:
    def __init__(self):
        self.__dict__.update(**db_configs)

    async def add_index(self, col="discogs_details_data"):
        # 添加索引
        mb = self.get_db()

        await mb[col].create_index('url')

    async def save_data(self, pool, items, col="discogs_details_data", key="obj_id"):
        """
        :param items:
        :param col:
        :param key:
        :return:
        """
        mb = pool()[self.db_name]

        if isinstance(items, list):
            requests = list()
            r_a = requests.append
            for item in items:
                try:
                    r_a(UpdateOne({
                        key: item.get(key)},
                        {'$set': item},
                        upsert=True))
                except Exception as e:
                    storage.error(f"数据插入出错:{e.args}此时的item是:{item}")
            result = await mb[col].bulk_write(requests, ordered=False, bypass_document_validation=True)
            storage.info(f"modified_count:{result.modified_count}")
        elif isinstance(items, dict):
            try:
                await mb[col].update_one({
                    key: items.get(key)},
                    {'$set': items},
                    upsert=True)
            except Exception as e:
                storage.error(f"数据插入出错:{e.args}此时的item是:{items}")

    async def find_data(self, pool, col="discogs_details_data"):
        mb = pool()[self.db_name]

        cursor = mb[col].find({'status': 0}, {"_id": 0})
        async for item in cursor:
            yield item

    async def do_delete_many(self, pool):
        mb = pool()[self.db_name]
        await mb.discogs_details_data.delete_many({"flag": 0})
