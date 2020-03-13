# -*- coding: utf-8 -*-
# @时间 : 2020-02-21 13:07
# @作者 : 陈祥安
# @文件名 : rabbitmq_helper.py
# @公众号: Python学习开发

from dataclasses import dataclass
from logging import getLogger, WARNING
from typing import Callable, Dict

import aio_pika
import msgpack
from aio_pika import connect_robust, Channel, pool, IncomingMessage, Message

from config import SpiderConfig
from util.decorators import decorator
from util.singleton import Singleton

CONCURRENCY_NUM = SpiderConfig.get("CONCURRENCY_NUM")


@dataclass
class RabbitMqPool(Singleton):
    _url: str = None
    _max_size: int = None
    _connection_pool: pool.Pool = None
    _channel_pool: pool.Pool = None

    def __post_init__(self):
        # Disable aio_pika log
        self._logger = getLogger()
        disable_aiopika_logger()

    async def init(self, addr: str, port: str, vhost: str, username: str, password: str, max_size: int):
        self._size = max_size
        self._url = f"amqp://{username}:{password}@{addr}:{port}/{vhost}"
        self._connection_pool = pool.Pool(
            self._get_connection, max_size=self._size)
        self._channel_pool = pool.Pool(self._get_channel, max_size=max_size)

        self._logger.debug(
            "Create rabbitmq connection pool success at %s:%s, max_size %s", addr, port, max_size)
        return self

    async def _get_connection(self) -> None:
        return await connect_robust(self._url)

    async def _get_channel(self) -> Channel:
        async with self._connection_pool.acquire() as connection:
            return await connection.channel()

    @decorator(False)
    async def subscribe(self, queue_name: str, callback: Callable[[IncomingMessage], None]) -> None:
        """
        Consumption of data in a queue
        """
        async with self._channel_pool.acquire() as channel:
            await channel.set_qos(CONCURRENCY_NUM)

            queue = await channel.declare_queue(
                name=queue_name, passive=True
            )
            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    await callback(message)
                    # Complete the task, has been added to each crawler file
                    # await message.ack()

    @decorator(False)
    async def publish(self, queue_name: str, msg: Dict[str, str]) -> None:
        """
        release the message
        """
        task = msgpack.packb(msg)
        async with self._channel_pool.acquire() as channel:
            # 创建队列
            await channel.declare_queue(queue_name)
            await channel.default_exchange.publish(
                Message(task), queue_name)


def disable_aiopika_logger():
    """
   Disable the log of aio-pika
     After calling this function, you can block the log output below aio-pika ``WARNING'' level
    """
    loggers = (
        aio_pika.channel.log,
        aio_pika.robust_channel.log,

        aio_pika.connection.log,
        aio_pika.robust_connection.log,

        aio_pika.exchange.log,
        aio_pika.robust_exchange.log,

        aio_pika.queue.log,
        aio_pika.robust_queue.log,

        aio_pika.pool.log,
        aio_pika.message.log,
        aio_pika.patterns.rpc.log,
        aio_pika.patterns.master.log,
    )
    for logger in loggers:
        logger.setLevel(WARNING)
