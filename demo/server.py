# -*- coding: utf-8 -*-
# @时间 : 2020-03-04 18:30
# @作者 : 陈祥安
# @文件名 : server.py
# @公众号: Python学习开发

from aiohttp import web


async def home(request: web.Request) -> web.Response:
    return web.Response(text="Hi")


async def init_app() -> web.Application:
    app = web.Application()
    app.add_routes([web.get("/", home)])
    return app


web.run_app(init_app(), port=5000)
