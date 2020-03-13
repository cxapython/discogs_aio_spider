# -*- coding: utf-8 -*-
# @Time    : 2018/03/28 15:35
# @Author  : cxa
# @File    : decorators.py
# @Software: PyCharm
from functools import wraps
from loguru import logger as crawler
import traceback
from inspect import iscoroutinefunction
from aiormq.exceptions import ChannelNotFoundEntity


def decorator(f=True):
    """
    日志装饰
    :param f:默认是不输出info，False的时候输出info信息。
    :return:
    """

    def flag(func):
        if iscoroutinefunction(func):
            @wraps(func)
            async def log(*args, **kwargs):
                try:
                    if f:
                        crawler.info(f"{func.__name__} is run")
                    return await func(*args, **kwargs)
                except ChannelNotFoundEntity as e:
                    crawler.error(f"{e.args}")
                except Exception as e:
                    crawler.error(f"{func.__name__} is error,here are details:{traceback.format_exc()}")
        else:
            @wraps(func)
            def log(*args, **kwargs):
                try:
                    if f:
                        crawler.info(f"{func.__name__} is run")
                    return func(*args, **kwargs)
                except Exception as e:
                    crawler.error(f"{func.__name__} is error,here are details:{traceback.format_exc()}")

        return log

    return flag
