# -*- coding: utf-8 -*-
# @时间 : 2020-03-13 19:58
# @作者 : 陈祥安
# @文件名 : __init__.py.py
# @公众号: Python学习开发
from .discogs_seed_spider import SeedSpider
from .discogs_index_spider import IndexSpider
from .discogs_details_spider import DetailsSpider

step1 = SeedSpider.fetch_home
step2 = IndexSpider.fetch_index_page
step3 = DetailsSpider.fetch_detail_page

__all__ = ["step1", "step2", "step3"]
