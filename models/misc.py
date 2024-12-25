import asyncio
import datetime
import random
import string
import subprocess
from functools import wraps

import aiohttp
import pytz

from models import storage
from resources.constants import ADJECTIVES, ADMIN_ID, EXCHANGE_API_ID, NOUNS, TIME_ZONE


class Auth:
    """
    Handles user authorization.
    Provides utility methods and decorators for checking if a user is authorized.
    """

    @staticmethod
    def is_authorized_user(user_id):
        """
        Check if the provided user ID matches the admin ID.

        Args:
            user_id (int): The ID of the user to check.

        Returns:
            bool: True if the user is authorized, False otherwise.
        """
        return user_id == ADMIN_ID

    @staticmethod
    def authorized_user(func):
        """
        Decorator to ensure that the function is only executed by authorized users.

        Args:
            func (callable): The function to wrap.

        Returns:
            callable: A wrapped function that checks authorization before execution.
        """

        @wraps(func)
        async def wrapper(self, event, *args, **kwargs):
            if not Auth.is_authorized_user(event.sender_id):
                await event.respond("❌ You are not authorized to use this command.")
                return
            return await func(self, event, *args, **kwargs)

        return wrapper


class Utilities:
    """
    A collection of utility methods for common tasks like generating passwords,
    parsing durations, and formatting dates.
    """

    @staticmethod
    def get_day_suffix(day):
        """
        Get the appropriate suffix (st, nd, rd, th) for a given day.

        Args:
            day (int): The day of the month.

        Returns:
            str: The suffix for the day.
        """
        if 11 <= day <= 13:
            return "th"
        return {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")

    @staticmethod
    def generate_password():
        """
        Generate a random password consisting of an adjective, a noun, and four digits.

        Returns:
            str: The generated password.
        """
        return (
            random.choice(ADJECTIVES)
            + random.choice(NOUNS)
            + "".join(random.choices(string.digits, k=4))
        )

    @staticmethod
    def parse_duration(duration_str: str):
        """
        Parse a duration string (e.g., '2h30m') into total seconds.

        Args:
            duration_str (str): The duration string to parse.

        Returns:
            int: Total duration in seconds.
        """
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
        """
        Convert an epoch timestamp into a human-readable date string.

        Args:
            epoch (int): The epoch timestamp to convert.

        Returns:
            str: The formatted date string in IST timezone.
        """
        ist = pytz.timezone(TIME_ZONE)
        date = datetime.datetime.fromtimestamp(epoch, ist)
        day_suffix = Utilities.get_day_suffix(date.day)
        day = date.day
        return date.strftime(f"{day}{day_suffix} %B %Y, %I:%M %p IST")

    @classmethod
    def parse_duration_to_human_readable(cls, duration_seconds: int) -> str:
        """
        Convert a duration in seconds to a human-readable format.

        Args:
            duration_seconds (int): The duration in seconds.

        Returns:
            str: The human-readable duration string.
        """
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
        """
        Fetch the exchange rate between two currencies using an external API.

        Args:
            from_currency (str): The source currency code.
            to_currency (str): The target currency code.

        Returns:
            float: The exchange rate.

        Raises:
            ValueError: If the API ID is not set.
        """
        if not EXCHANGE_API_ID:
            raise ValueError("Exchange API ID not set.")

        url = f"https://v6.exchangerate-api.com/v6/{EXCHANGE_API_ID}/latest/{from_currency}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
                return data["conversion_rates"][to_currency]


class SystemUserManager:
    """
    Handles operations related to system user management, such as creating,
    deleting, and modifying system users.
    """

    @staticmethod
    def create_user(username, password):
        """
        Create a new system user with the specified username and password.

        Args:
            username (str): The username for the new user.
            password (str): The password for the new user.

        Raises:
            subprocess.CalledProcessError: If user creation fails.
        """
        hashed_password = subprocess.run(
            ["openssl", "passwd", "-6", password],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        subprocess.run(
            [
                "sudo",
                "useradd",
                "-m",
                "-s",
                "/bin/bash",
                "-p",
                hashed_password,
                username,
            ],
            check=True,
        )
        print(f"System user {username} created successfully.")

    @staticmethod
    async def delete_system_user(username):
        """
        Delete a system user and clean up associated resources.

        Args:
            username (str): The username of the user to delete.

        Returns:
            bool: True if the user was deleted successfully, False otherwise.
        """
        subprocess.run(["sudo", "pkill", "-9", "-u", username], check=False)
        try:
            subprocess.run(["sudo", "userdel", "-r", username], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error deleting user {username}: {e}")
            return False
        user = storage.query_object("User", linux_username=username)
        if not user:
            print(f"User {username} not found in the database.")
            return False
        rental = storage.query_object("Rental", user_id=user.id)
        if rental:
            rental.is_active = 0
        storage.delete(user)
        storage.save()
        return True

    @classmethod
    async def change_password(cls, username):
        """
        Change the password for a system user.

        Args:
            username (str): The username of the user whose password will be changed.

        Returns:
            str: The new password.

        Raises:
            subprocess.CalledProcessError: If the password change fails.
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
        Remove SSH authorized keys for a system user.

        Args:
            username (str): The username of the user.

        Returns:
            tuple: (bool, str) A tuple containing a success flag and a message.
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
        """
        Retrieve the contents of the /etc/passwd file.

        Returns:
            list[str]: A list of lines from the /etc/passwd file.
        """
        with open("/etc/passwd", "r") as f:
            return f.readlines()

    @classmethod
    def is_user_exists(cls, username):
        """
        Check if a system user exists.

        Args:
            username (str): The username to check.

        Returns:
            bool: True if the user exists, False otherwise.
        """
        return any(line.startswith(username + ":") for line in cls.get_passwd_data())

    @classmethod
    async def get_running_users(cls):
        """
        Retrieve a list of currently logged-in users.

        Returns:
            str: Output of the `w` command showing logged-in users.
        """
        connected_users = await asyncio.create_subprocess_shell(
            "w", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await connected_users.communicate()
        connected_users = stdout.decode()
        return connected_users

    @classmethod
    async def run_command(cls, command):
        """
        Run a shell command and return the output.

        Args:
            command (str): The command to run.

        Returns:
            str: The output of the command.
        """
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await process.communicate()
        return stdout.decode()
