# 基于Asyncio+Aiohttp+Motor的国外黑胶唱片信息网站Discogs内容的抓取。

### 修改内容
#### 1.调整了motor存储文件的方式
#### 2.修改了base_crawler文件的unclose clientsession的错误
#### 3.改正branch分流的使用方式
#### 4.优化了部分代码规则【后续有时间继续】
#### 5.装饰器接受异步函数的时候做相应判断

### 将来要做的
#### 1。目前队列都是用的mongo，后期会将队列改为rabbitmq。
#### 2。async_retrying模块好像有问题，需继续观察
