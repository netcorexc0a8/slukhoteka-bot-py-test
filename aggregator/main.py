import asyncio
from tasks.sync import start_scheduler

async def main():
    print("Запуск Aggregator...")
    start_scheduler()

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Aggregator остановлен")

if __name__ == "__main__":
    asyncio.run(main())
