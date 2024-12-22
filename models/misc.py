import asyncio
import random
import aiohttp
import subprocess

from resources.constants import (
    ADJECTIVES,
    ADMIN_ID,
    NOUNS,
    TIME_ZONE,
)

class Auth:
    # --- Authorization ---
    @staticmethod
    def is_authorized_user(user_id):
        return user_id == ADMIN_ID

    @staticmethod
    def authorized_user(func):
        async def wrapper(self, event, *args, **kwargs):
            # Check if the sender is authorized
            if not Auth.is_authorized_user(event.sender_id):
                await event.respond("❌ You are not authorized to use this command.")
                return
            # Proceed with the original function
            return await func(self, event, *args, **kwargs)

        return wrapper


class Utilities:
    @staticmethod
    def get_day_suffix(day):
        if 11 <= day <= 13:
            return "th"
        return {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")

    @staticmethod
    def generate_password():
        return (
                random.choice(ADJECTIVES)
                + random.choice(NOUNS)
                + "".join(random.choices(string.digits, k=4))
        )

    @staticmethod
    def parse_duration(duration_str: str):
        duration_str = duration_str.lower()
        total_seconds = 0
        current_number = ""
        for char in duration_str:
            if char.isdigit():
                current_number += char
            else:
                if char == "d":
                    total_seconds += int(current_number) * 24 * 60 * 60
                elif char == "h":
                    total_seconds += int(current_number) * 60 * 60
                elif char == "m":
                    total_seconds += int(current_number) * 60
                elif char == "s":
                    total_seconds += int(current_number)
                current_number = ""
        return total_seconds

    @staticmethod
    def get_date_str(epoch: int):
        ist = pytz.timezone(TIME_ZONE)
        date = datetime.datetime.fromtimestamp(epoch, ist)
        day_suffix = Utilities.get_day_suffix(date.day)
        day = date.day
        return date.strftime(f"{day}{day_suffix} %B %Y, %I:%M %p IST")

    @classmethod
    def parse_duration_to_human_readable(cls, duration_seconds: int) -> str:
        if duration_seconds <= 0:
            return "Expired"
        duration_str = ""
        if duration_seconds // (24 * 3600) > 0:
            duration_str += f"{duration_seconds // (24 * 3600)} days, "
            duration_seconds %= 24 * 3600
        if duration_seconds // 3600 > 0:
            duration_str += f"{duration_seconds // 3600} hours, "
            duration_seconds %= 3600
        if duration_seconds // 60 > 0:
            duration_str += f"{duration_seconds // 60} minutes, "
            duration_seconds %= 60
        if duration_seconds > 0:
            duration_str += f"{duration_seconds} seconds"
        return duration_str

    @classmethod
    async def get_exchange_rate(cls, from_currency, to_currency):
        url = f"https://api.exchangerate-api.com/v4/latest/{from_currency}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
                return data["rates"][to_currency]


