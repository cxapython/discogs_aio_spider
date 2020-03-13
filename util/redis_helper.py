# -*- coding: utf-8 -*-
# @时间 : 2020-03-13 21:21
# @作者 : 陈祥安
# @文件名 : redis_helper.py
# @公众号: Python学习开发
import aioredis
import asyncio


class RedisPool:
    def __init__(self, redis_url, loop=None, redis_pool_min=5, redis_pool_max=10):
        self.redis_url: str = redis_url
        self.redis_pool_min: int = redis_pool_min
        self.redis_pool_max: int = redis_pool_max
        self.pool = None
        self.loop = loop or asyncio.get_event_loop()

    async def create_redis_pool(self):
        """Initialise a new redis pool using the parameters passed to the class"""
        self.pool = await aioredis.create_redis_pool(
            self.redis_url,
            minsize=self.redis_pool_min,
            maxsize=self.redis_pool_max,
            loop=self.loop)
        return self.pool

    async def destroy_redis_pool(self):
        """Destroy this class's redis pool"""
        if self.pool is None:
            return
        self.pool.close()
        await self.pool.wait_closed()
