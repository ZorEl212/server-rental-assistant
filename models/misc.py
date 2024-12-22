import asyncio
import random
import string
import datetime
import pytz
import aiohttp
import subprocess
from models import storage


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


class SystemUserManager:
    @staticmethod
    def create_user(username, password):
        hashed_password = subprocess.run(
            ["openssl", "passwd", "-6", password],
            check=True, capture_output=True, text=True
        ).stdout.strip()
        subprocess.run(
            ["sudo", "useradd", "-m", "-s", "/bin/bash", "-p", hashed_password, username],
            check=True
        )
        print(f"System user {username} created successfully.")

    @staticmethod
    async def delete_system_user(username):
        #await client.send_message(ADMIN_ID, f"🗑️ Deleting user `{username}`...")
        subprocess.run(["sudo", "pkill", "-9", "-u", username], check=False)
        try:
            subprocess.run(["sudo", "userdel", "-r", username], check=True)
        except subprocess.CalledProcessError as e:
            return False
        user = storage.query_object('User', linux_username=username)
        if not user:
            return False
        rental = storage.query_object('Rental', user_id=user.id)
        if rental:
            rental.is_active = 0
        storage.delete(user)
        storage.save()
        return True

    @classmethod
    async def change_password(cls, username):
        """
        Change the password of a system user
        """
        password = Utilities.generate_password()
        hashed_password = subprocess.run(
            ["openssl", "passwd", "-6", password],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        subprocess.run(
            ["sudo", "usermod", "-p", hashed_password, username],
            check=True,
        )
        return password

    @classmethod
    async def remove_ssh_auth_keys(cls, username) -> tuple[bool, str]:
        """
        Remove the SSH authorized keys for a system user
        """
        try:
            subprocess.run(
                ["sudo", "rm", f"/home/{username}/.ssh/authorized_keys"], check=True
            )
        except subprocess.CalledProcessError:
            return False, f"No authorized keys found for user {username}."
        return True, f"Authorized keys removed for user {username}."

    @classmethod
    def get_passwd_data(cls):
        with open("/etc/passwd", "r") as f:
            return f.readlines()

    @classmethod
    def is_user_exists(cls, username):
        return any(line.startswith(username + ":") for line in cls.get_passwd_data())

    @classmethod
    async def get_running_users(cls):
        connected_users = await asyncio.create_subprocess_shell(
            "w", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await connected_users.communicate()
        connected_users = stdout.decode()
        return connected_users
