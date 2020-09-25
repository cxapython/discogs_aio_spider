
#Based on Asyncio+Httpx+Motor+Aio-Pika+Aioredis  foreign vinyl record information website Discogs  crawling.
# Python3.8

![项目流程图](discogs项目流程图.jpg)

### install poetry
```
curl -sSL https://raw.githubusercontent.com/sdispater/poetry/master/get-poetry.py | python3
```
### install dependencies
```
portry install 
```

### run
```
portry run python main.py
```

注意事项如下:
step1要先生成任务队列，否则step2出错。同理step3要等step2生成任务队列。
可以根据实际业务情况，优化文件之间的调用。（其中step1、step2、step3是函数的别名）

