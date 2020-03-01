# -*- coding: utf-8 -*-
# @时间 : 2020-02-27 17:06
# @作者 : 陈祥安
# @文件名 : decorator_test.py.py
# @公众号: Python学习开发
from functools import wraps
import asyncio
import contextvars
import wrapt
# 申明Context变量
run_flag = contextvars.ContextVar('decorator run function flag')
index = 0

run_flag.set(False)

class D():
    async def main(self):
        run_flag.set(True)
        await self.fetch_index()

    def start(name=None):
        def __start(func):
            @wraps(func)
            async def _wrap(self, *args, **kwargs):
                try:
                    print(func.__name__, name)
                    flag = run_flag.get()
                    if not flag:
                        await self.main()
                    else:
                        await func(self, *args, **kwargs)
                except asyncio.CancelledError as e:
                    print("error")

            return _wrap

        return __start

    @start(name="discogs_index_spider")
    async def fetch_index(self):
        print("in fetch")

if __name__ == '__main__':
    d = D()
    asyncio.run(d.fetch_index())
