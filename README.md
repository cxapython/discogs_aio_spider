
# 基于Asyncio+Aiohttp+Motor+Aio-Pika+Aioredis的国外黑胶唱片信息网站Discogs内容的抓取。
# 使用版本Python3.8

![项目流程图](discogs项目流程图.jpg)

### 安装依赖
```
pip install -r requirements.txt
```
### 如何运行
点击```main.py```运行即可。
注意事项如下:
step1要先生成任务队列，否则step2出错。同理step3要等step2生成任务队列。
可以根据实际业务情况，优化文件之间的调用。（其中step1、step2、step3是函数的别名）

