# -*- coding: utf-8 -*-
# @时间 : 2020-02-27 21:59
# @作者 : 陈祥安
# @文件名 : async_retrying_test.py
# @公众号: Python学习开发
from async_retrying import retry
import asyncio

index= 0
class D:

    @retry(attempts=3)
    async def go(self):
        1 / 0
        global index
        print(f"{index=}")
        index += 1



if __name__ == '__main__':
    d = D()
    asyncio.run(d.go())
