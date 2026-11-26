"""Durable subscription; acknowledge only after the database commits."""
import asyncio
import json
import logging

import aio_pika
from sqlalchemy.exc import OperationalError

from app.infrastructure.messaging.loan_inbox import process_loan_event

logger = logging.getLogger(__name__)
QUEUE = "evidence.events.v1"
DLQ = QUEUE + ".dlq"


async def handle_message(message):
    try:
        raw = json.loads(message.body)
        for attempt in range(3):
            try:
                await asyncio.to_thread(process_loan_event, message.routing_key, raw)
                break
            except OperationalError:
                if attempt == 2:
                    raise
                await asyncio.sleep(2 ** attempt)
    except Exception as exc:
        logger.warning("Loan event rejected: %s", type(exc).__name__)
        await message.reject(requeue=False)
    else:
        await message.ack()


async def consume_loans(settings, stop):
    while not stop.is_set():
        try:
            connection = await aio_pika.connect(settings.rabbitmq_url, timeout=5)
            async with connection:
                channel = await connection.channel()
                await channel.set_qos(prefetch_count=1)
                exchange = await channel.declare_exchange(settings.rabbitmq_exchange, aio_pika.ExchangeType.TOPIC, durable=True)
                dlx = await channel.declare_exchange(settings.rabbitmq_exchange + ".dlx", aio_pika.ExchangeType.DIRECT, durable=True)
                dead = await channel.declare_queue(DLQ, durable=True)
                await dead.bind(dlx, routing_key=DLQ)
                queue = await channel.declare_queue(QUEUE, durable=True, arguments={
                    "x-dead-letter-exchange": dlx.name, "x-dead-letter-routing-key": DLQ})
                await queue.bind(exchange, routing_key="prestamos.*.v1")
                # Poll with a bounded wait; no detached callbacks on shutdown.
                while not stop.is_set() and not connection.is_closed:
                    message = await queue.get(fail=False, timeout=5)
                    if message is not None:
                        await handle_message(message)
                    else:
                        try:
                            await asyncio.wait_for(stop.wait(), timeout=1)
                        except TimeoutError:
                            pass
        except Exception as exc:
            logger.warning("Loan consumer unavailable: %s", type(exc).__name__)
            try:
                await asyncio.wait_for(stop.wait(), timeout=5)
            except TimeoutError:
                pass
