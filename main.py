# -*- coding: utf-8 -*-
# @时间 : 2020-03-13 19:54
# @作者 : 陈祥安
# @文件名 : main.py
# @公众号: Python学习开发

from spider import step1, step2, step3
import asyncio


async def main():
    await step1()


if __name__ == '__main__':
    asyncio.run(main())
