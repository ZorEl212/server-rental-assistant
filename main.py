import asyncio

from models import bot, job_manager
from models.misc import Utilities


async def main():
    await job_manager.init_redis()
    await bot.start()

# Check if redis is running
if not Utilities.check_redis():
    print("\033[91mRedis is not running. Exiting...\033[0m")
    exit()


event_loop = asyncio.get_event_loop()
event_loop.create_task(job_manager.schedule_jobs())
event_loop.create_task(Utilities.deactivate_expired_rentals())
event_loop.run_until_complete(main())
