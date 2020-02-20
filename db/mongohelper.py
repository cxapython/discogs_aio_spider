# -*- coding: utf-8 -*-
# @Time : 2019-02-13 10:44
# @Author : cxa
# @File : mongohelper.py
# @Software: PyCharm
# -*- coding: utf-8 -*-
# @Time : 2018/12/28 10:01 AM
# @Author : cxa
# @File : mongo_helper.py
# @Software: PyCharm
import asyncio
from loguru import logger as  storage
import datetime
from decorators.decorators import decorator
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import UpdateOne

from itertools import islice
import sys

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


class MotorOperation:
    _db = dict()

    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, "_ins"):
            cls._ins = super(MotorOperation, cls).__new__(cls, *args, **kwargs)
        return cls._ins

    def __init__(self, loop=None):
        self.__dict__.update(**db_configs)
        self.loop = loop or asyncio.get_event_loop()
        if sys.platform != "win32":
            watcher = asyncio.get_child_watcher()
            watcher.attach_loop(self.loop)

    def client(self):
        if self.user:
            motor_uri = (f"mongodb://{self.user}:{self.passwd}@{self.host}:"
                         f"{self.port}/{self.db_name}?authSource={self.db_name}")
        else:
            motor_uri = f"mongodb://{self.host}:{self.port}/{self.db_name}"
        return AsyncIOMotorClient(motor_uri, io_loop=self.loop)

    def get_db(self):
        db_name = self.db_name
        if asyncio.get_running_loop() != self.loop:
            self = MotorOperation()
        if db_name not in self._db:
            self._db[db_name] = self.client()[db_name]
        return self._db[db_name]

    async def save_data_with_status(self, items, col="discogs_seed_data"):
        mb = self.get_db()
        for i in range(0, len(items), 2000):
            tasks = list()
            for item in islice(items, i, i + 2000):
                data = dict()
                data["update_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                data["status"] = 0  # 0初始
                data["url"] = item
                tasks.append(data)
            # storage.info(f"存新的url:{tasks}")
            await mb[col].insert_many(tasks)

    async def add_index(self, col="discogs_seed_data"):
        # 添加索引
        mb = self.get_db()

        await mb[col].create_index('url')

    async def save_data(self, items, col="discogs_index_data", key="obj_id"):
        """
        :param items:
        :param col:
        :param key:
        :return:
        """
        mb = self.get_db()

        if isinstance(items, list):
            requests = list()
            r_a = requests.append
            # TODO:bulk_write:使用确认
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

    async def change_status(self, condition, col="discogs_seed_data", status_code=1):
        # status_code 0:初始,1:开始下载，2下载完了
        mb = self.get_db()

        try:
            item = dict()
            item["status"] = status_code
            # storage.info(f"修改状态,此时的数据是:{item}")
            await mb[col].update_one(condition, {'$set': item})
        except Exception as e:
            storage.error(f"修改状态出错:{e.args}此时的数据是:{item}")

    async def get_detail_datas(self):
        mb = self.get_db()

        data = mb.discogs_index.find({'status': 0})
        async for item in data:
            print(item)
        return data

    async def reset_status(self, col="discogs_seed_data"):
        mb = self.get_db()

        await mb[col].update_many({'status': 1}, {'$set': {"status": 0}})

    async def reset_all_status(self, col="discogs_seed_data"):
        mb = self.get_db()

        await mb[col].update_many({}, {'$set': {"status": 0}})

    async def find_data(self, col="discogs_seed_data"):
        """
        获取状态为0的数据，作为爬取对象。
        :return:AsyncGeneratorType
        """
        mb = self.get_db()

        cursor = mb[col].find({'status': 0}, {"_id": 0})
        async for item in cursor:
            yield item

    async def do_delete_many(self):
        mb = self.get_db()
        await mb.tiaopiao_data.delete_many({"flag": 0})

    async def branch(self, limit=10):
        coros = await self.find_data()
        from aiostream import stream
        index = 0
        while True:
            xs = stream.iterate(coros)
            ys = xs[index:index + limit]
            t = await stream.list(ys)
            print("t is ", t)
            if not t:
                break
            await asyncio.ensure_future(asyncio.wait(t))
            index += limit


if __name__ == '__main__':
    m = MotorOperation()
    asyncio.run(m.branch())
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(m.reset_all_status(col="discogs_index_data"))
