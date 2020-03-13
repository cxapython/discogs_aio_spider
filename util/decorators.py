# -*- coding: utf-8 -*-
# @Time    : 2018/03/28 15:35
# @Author  : cxa
# @File    : decorators.py
# @Software: PyCharm
import traceback
from functools import wraps
from inspect import iscoroutinefunction

from aiormq.exceptions import ChannelNotFoundEntity, ChannelInvalidStateError
from loguru import logger as crawler


def decorator(f=True):
    """
    Log decoration
    :param f:The default is not to output info, when False, output info information.
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
                except ChannelInvalidStateError as e:
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
