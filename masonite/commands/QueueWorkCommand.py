""" A QueueWorkCommand Command """

import inspect
import pickle

from cleo import Command

from config import queue
from masonite.exceptions import DriverLibraryNotFound


def callback(ch, method, properties, body):
    from wsgi import container
    job = pickle.loads(body)
    if inspect.isclass(job):
        job = container.resolve(job)
    job.handle()
    ch.basic_ack(delivery_tag=method.delivery_tag)


class QueueWorkCommand(Command):
    """
    Start the queue worker

    queue:work
        {--c|channel=default : The channel to listen on the queue}
        {--f|fair : Send jobs to queues that have no jobs instead of randomly selecting a queue}
    """

    def handle(self):
        try:
            import pika
        except ImportError:
            raise DriverLibraryNotFound(
                "Could not find the 'pika' library. Run pip install pika to fix this.")

        connection = pika.BlockingConnection(pika.URLParameters('amqp://{}:{}@{}:{}/%2F'.format(
            queue.DRIVERS['amqp']['username'], queue.DRIVERS['amqp']['password'], queue.DRIVERS['amqp']['host'], queue.DRIVERS['amqp']['port'],
        )))
        channel = connection.channel()

        channel.queue_declare(queue=self.option('channel'), durable=True)

        channel.basic_consume(callback,
                              queue=self.option('channel'))
        if self.option('fair'):
            channel.basic_qos(prefetch_count=1)

        self.info(' [*] Waiting to process jobs on the "{}" channel. To exit press CTRL+C'.format(
            self.option('channel')))
        channel.start_consuming()
