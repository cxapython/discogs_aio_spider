# -*- coding: utf-8 -*-
# @Time : 2019-03-22 16:24
# @Author : cxa
# @File : __init__.py.py
# @Software: PyCharm
from config.config import config

c = config()
RabbitmqConfig = c.get("rabbitmq")
MongoConfig = c.get("mongo")
SpiderConfig = c.get("spider")
RedisConfig = c.get("redis")
__all__ = ["RabbitmqConfig", "MongoConfig", "SpiderConfig", "RedisConfig"]
