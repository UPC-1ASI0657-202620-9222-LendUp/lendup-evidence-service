import asyncio
import json

import aio_pika


async def publish_event(settings, row):
    # A bounded attempt; durable messages plus publisher confirms.
    async with asyncio.timeout(10):
        connection = await aio_pika.connect(settings.rabbitmq_url, timeout=5)
        async with connection:
            channel = await connection.channel(publisher_confirms=True, on_return_raises=True)
            exchange = await channel.declare_exchange(settings.rabbitmq_exchange, aio_pika.ExchangeType.TOPIC,
                                                      durable=True)
            message = aio_pika.Message(
                body=json.dumps(row["envelope"], ensure_ascii=False, allow_nan=False).encode("utf-8"),
                content_type="application/json", delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                message_id=row["id"], correlation_id=row["envelope"]["correlation_id"],
                type=row["envelope"]["event_type"])
            confirmation = await exchange.publish(message, routing_key=row["routing_key"],
                                                  mandatory=row["mandatory"], timeout=5)
            # aio-pika/aiormq returns Basic.Ack for positive confirms.
            if confirmation is None or confirmation is False or type(confirmation).__name__ != "Ack":
                raise RuntimeError("RabbitMQ did not confirm publication")
