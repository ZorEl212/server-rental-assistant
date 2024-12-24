import asyncio

from models import bot, plan_routes, system_routes


async def main():
    await bot.start()


event_loop = asyncio.get_event_loop()
event_loop.create_task(plan_routes.run_daily_deduction())
event_loop.create_task(system_routes.notify_expiry())
event_loop.run_until_complete(main())
