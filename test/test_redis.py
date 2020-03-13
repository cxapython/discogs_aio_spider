# -*- coding: utf-8 -*-
# @时间 : 2020-03-13 21:36
# @作者 : 陈祥安
# @文件名 : test_redis.py
# @公众号: Python学习开发
from util import RedisPool
import asyncio
import traceback
import aioredis
from functools import wraps

QUEUQ_PAGES = "discogs_seed"

REDIS_POOL_KEY = 'redis_pool'
REDIS_URL = "redis://@127.0.0.1:6379/0"
REDIS_POOL_MIN = 5
REDIS_POOL_MAX = 10


async def test_sadd():
    loop = asyncio.get_event_loop()
    pool = RedisPool(redis_url=REDIS_URL, loop=loop)

    for i in range(10):
        redis = await pool.create_redis_pool()

        url = f"http://www.xxx.com/{i}"
        try:
            result = await redis.sadd("test", url)
            print(result)
        except  aioredis.errors.PoolClosedError as e:
            print(e.args)
        except Exception as e:
            print(traceback.format_exc())
        await pool.destroy_redis_pool(redis)


async def test_spop():
    loop = asyncio.get_event_loop()
    pool = RedisPool(redis_url=REDIS_URL, loop=loop)
    redis = await pool.create_redis_pool()
    for i in range(10):
        url = f"http://www.xxx.com/{i}"
        try:
            result = await redis.spop("test")
            print(result)
        except  aioredis.errors.PoolClosedError as e:
            print(e.args)
        except Exception as e:
            print(traceback.format_exc())
    await pool.destroy_redis_pool(redis)


if __name__ == '__main__':
    asyncio.run(test_sadd())
