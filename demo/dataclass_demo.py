# -*- coding: utf-8 -*-
# @时间 : 2020-02-27 20:32
# @作者 : 陈祥安
# @文件名 : dataclass_demo.py
# @公众号: Python学习开发
from copy import deepcopy
import marshal
import timeit
from multidict import CIMultiDict


def test_deepcopy():
    _kwargs = CIMultiDict({
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Host": "www.discogs.com",
        "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.121 Safari/537.36"),
    })
    if _kwargs is None:
        _kwargs = dict()
    kwargs = deepcopy(_kwargs)


def test_marshal():
    _kwargs = CIMultiDict({
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Host": "www.discogs.com",
        "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.121 Safari/537.36"),
    })
    if _kwargs is None:
        _kwargs = dict()

    kwargs = marshal.loads(marshal.dumps(dict(_kwargs)))


if __name__ == '__main__':
    print(timeit.timeit(stmt=test_deepcopy, number=1000000))
    print("=" * 30)
    print(timeit.timeit(stmt=test_marshal, number=1000000))
