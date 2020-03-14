# -*- coding: utf-8 -*-
# @时间 : 2020-03-13 19:54
# @作者 : 陈祥安
# @文件名 : main.py
# @公众号: Python学习开发

from spider import step1, step2, step3
import asyncio
import threading
import time
from loguru import logger
from multiprocessing import Process


def get_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()


def start():

    loop = asyncio.new_event_loop()
    t = threading.Thread(target=get_loop, args=(loop,))
    p = Process(target=step1)
    p.start()
    t.start()
    time.sleep(30)
    asyncio.run_coroutine_threadsafe(step2(), loop)
    time.sleep(5)
    logger.info("start step3")
    asyncio.run_coroutine_threadsafe(step3(), loop)


if __name__ == '__main__':
    start()
