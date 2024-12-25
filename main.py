import asyncio

from models import bot, job_manager


async def main():
    await job_manager.init_redis()
    await bot.start()


event_loop = asyncio.get_event_loop()
event_loop.create_task(job_manager.schedule_jobs())
event_loop.run_until_complete(main())
