# -*- coding: utf-8 -*-
# @时间 : 2020-02-21 12:26
# @作者 : 陈祥安
# @文件名 : singleton.py
# @公众号: Python学习开发
# -*- coding: utf-8 -*-


class SingletonMetaclass(type):

    _instances = {}

    def __call__(cls, *args: tuple, **kwargs: dict):
        instances = cls._instances

        if cls not in instances:
            instances[cls] = super(SingletonMetaclass, cls).__call__(*args, **kwargs)

        return instances[cls]


class Singleton(metaclass=SingletonMetaclass):
    pass