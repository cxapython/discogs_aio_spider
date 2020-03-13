# -*- coding: utf-8 -*-
# @时间 : 2020-02-21 12:26
# @作者 : 陈祥安
# @文件名 : singleton.py
# @公众号: Python学习开发
# -*- coding: utf-8 -*-
"""单例类 模块"""


class SingletonMetaclass(type):
    """单例元类"""

    _instances = {}

    def __call__(cls, *args: tuple, **kwargs: dict):
        """调用 魔术方法"""
        instances = cls._instances

        if cls not in instances:
            instances[cls] = super(SingletonMetaclass, cls).__call__(*args, **kwargs)

        return instances[cls]


class Singleton(metaclass=SingletonMetaclass):
    """单例基类
    所有继承此类的类都将成为单例类，在本次项目
    运行的全部周期中成为唯一的单一实例。
    """
    pass