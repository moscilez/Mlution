from redis import Redis
from rq import Worker, Queue
from .settings import get_settings


def main():
    connection = Redis.from_url(get_settings().redis_url)
    Worker([Queue("mlution", connection=connection)], connection=connection).work(with_scheduler=True)


if __name__ == "__main__":
    main()
