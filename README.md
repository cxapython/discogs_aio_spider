
# 基于Asyncio+Aiohttp+Motor的国外黑胶唱片信息网站Discogs内容的抓取。
# 使用版本3.6以及以上

### 修改内容
#### 1.调整了motor存储文件的方式,改为连接池
#### 2.队列改为rabbitmq，使用客户端为aio_pika,同样使用连接池的方式

### 将来要做的事
#### 1.async_retrying模块好像有问题，需继续观察
#### 2.async_timeout模块是否有问题调查
#### 3.参数配置化toml文件（ing）
#### 4.base_crawler是否可以继续有优化
#### 5.补充完整的docstring和type hint。
#### 6.deepcopy的代替方案