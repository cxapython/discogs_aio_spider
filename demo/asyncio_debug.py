# -*- coding: utf-8 -*-
# @时间 : 2020-02-28 15:11
# @作者 : 陈祥安
# @文件名 : asyncio_debug.py
# @公众号: Python学习开发

import asyncio

async def test():
    print("never scheduled")

async def main():
    test()

asyncio.run(main(),debug=True)