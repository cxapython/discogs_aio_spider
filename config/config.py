# -*- coding: utf-8 -*-
# @Time : 2019-03-22 15:08
# @Author : cxa
# @File : config.py.py
# @Software: PyCharm
import toml
from loguru import logger
import traceback
import os

_temp = os.path.dirname(os.path.abspath(__file__))

toml_file = os.path.join(_temp, "config.toml")


#
# def _load_pyproject(source_dir):
#     with open(os.path.join(source_dir, 'pyproject.toml')) as f:
#         pyproject_data = toml.load(f)
#     buildsys = pyproject_data['build-system']
#     return (
#         buildsys['requires'],
#         buildsys['build-backend'],
#         buildsys.get('backend-path'),
#     )

def config():
    data = ""
    try:
        with open(toml_file, mode="r", encoding="utf-8") as fs:
            data = toml.load(fs)
    except Exception as e:
        logger.error(f"读取配置错误！:{traceback.format_exc()}")
    config_data=dict()
    return data


if __name__ == '__main__':
    print(config())
