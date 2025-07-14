# -*- coding: utf-8 -*-
# @时间 : 2020-03-03 20:05
# @作者 : 陈祥安
# @文件名 : retry_helper.py
# @公众号: Python学习开发
import asyncio
import random
import traceback
from functools import wraps

from loguru import logger


class RetryTimeout(Exception):
    def __init__(self, info):
        self.info = info

    def __str__(self):
        return self.info


def aio_retry(**kwargs):
    max_sleep_time: int = kwargs.pop("max", None)
    min_sleep_time: int = kwargs.pop("min", 0)
    attempts: int = kwargs.pop("attempts", 3)

    def retry(func):
        @wraps(func)
        async def decorator(*args, **_kwargs):
            retry_count = 1
            error_info = ""
            while True:
                if retry_count > attempts:
                    if error_info:
                        raise RetryTimeout("Too many errors")
                    else:
                        logger.error(f"After retries {retry_count} times, an error occurred.here is detail{error_info}")
                        break
                try:
                    result = await func(*args, **_kwargs)
                    return result
                except Exception as e:
                    if retry_count == attempts:
                        error_info = f"{traceback.format_exc()}"
                    else:
                        if max_sleep_time:
                            sleep_time = random.randint(min_sleep_time, max_sleep_time)
                            await asyncio.sleep(sleep_time)
                    retry_count += 1
        

        return decorator

    return retry
