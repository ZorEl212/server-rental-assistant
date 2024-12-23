import time
import uuid
from datetime import datetime

import pytz
from telethon import Button

from models import client, storage
from models.misc import Auth, SystemUserManager, Utilities
from models.payments import Payment
from models.rentals import Rental
from models.telegram_users import TelegramUser
from models.users import User
from resources.constants import (
    ADMIN_ID,
    BE_NOTED_TEXT,
    SSH_HOSTNAME,
    SSH_PORT,
    TIME_ZONE,
)


class UserRoutes:
    async def create_user(self, event):
        args = event.message.text.split()
        if len(args) < 4:
            await event.respond(
                "❓ Usage: /create_user <username> <plan_duration> <amount> <currency (INR/USD)> \nFor example: `/create_user john 7d 500 INR`"
            )
            return

        await event.respond("🔐 Creating user...")

        username = args[1]
        plan_duration_seconds = Utilities.parse_duration(args[2])
        amount = args[3]
        currency = args[4].upper()

        user = storage.query_object("User", linux_username=username)
        if SystemUserManager.is_user_exists(username) or user:
            await event.respond(f"❌ User `{username}` already exists.")
            return

        password = Utilities.generate_password()
        expiry_time = int(time.time()) + plan_duration_seconds
        user_uuid = str(uuid.uuid4())

        user = User(
            linux_username=username, linux_password=password, uuid=user_uuid, balance=0
        )
        try:
            payment = await Payment.create(
                user_id=user.id, amount=amount, currency=currency
            )
            print(payment.amount)
            await user.update_balance(payment.amount, "credit")
            SystemUserManager.create_user(username, password)
            payment.save()
            user.save()
        except Exception as e:
            await event.respond(f"❌ Error creating user `{username}`: {e}")
            return

        expiry_date_str = Utilities.get_date_str(expiry_time)
        ssh_command = f"ssh {username}@{SSH_HOSTNAME} -p {SSH_PORT}"

        message_str = (
            f"✅ User `{username}` created successfully.\n\n"
            f"🔐 **Username:** `{username}`\n"
            f"📅 **Expiry Date:** {expiry_date_str}\n"
            f"\n"
            f"🔗 **SSH Command:**\n"
            f"`{ssh_command}`\n"
            f"\n"
            f"🔑 **Password:** Please click the button below to get your password.\n\n"
        )

        if BE_NOTED_TEXT:
            message_str += f"**ℹ️ Notes:**\n{BE_NOTED_TEXT}\n"

        password_url = (
            f"https://t.me/{(await client.get_me()).username}?start={user_uuid}"
        )

        rental = Rental(
            user_id=user.id,
            start_time=int(time.time()),
            end_time=expiry_time,
            plan_duration=plan_duration_seconds,
            amount=amount,
            currency=currency,
        )
        storage.new(rental)
        storage.save()

        await client.send_message(
            event.chat_id,
            message_str,
            buttons=[[Button.url("Get Password", password_url)]],
        )
        message_str = (
            f"🔐 **Username:** `{username}`\n"
            f"🔑 **Password:** `{password}`\n"
            f"📅 **Expiry Date:** {expiry_date_str}\n"
            f"💰 **Amount:** `{payment.amount:.2f} INR`\n"
            f"📅 **Payment Date:** {Utilities.get_date_str(payment.payment_date)}\n"
        )
        await client.send_message(ADMIN_ID, message_str)

    # /delete_user command
    @Auth.authorized_user
    async def delete_user_command(self, event):
        """
        Command to delete a user from the system or database.

        Args:
            event: The event containing the user command and context.
        """
        # Extract and validate the username from the command
        command_parts = event.message.text.split()
        if len(command_parts) < 2:
            await event.respond("❓ Usage: /delete_user <username>")
            return

        username = command_parts[1]

        # Check if the user exists in the database and system
        user_in_db = storage.query_object("User", linux_username=username)
        user_in_system = SystemUserManager.is_user_exists(username)

        if not user_in_db:
            await event.respond(f"❌ User `{username}` not found in database.")
            return

        if not user_in_system:
            # User not in the system; confirm if they should be removed from the database
            await event.respond(
                f"❌ User `{username}` is not found in the system.\n"
                f"❓ Do you want to delete user `{username}` from the database?",
                buttons=[
                    [Button.inline("Yes", data=f"clean_db {username}")],
                    [Button.inline("No", data="cancel")],
                ],
            )
            return

        # If user exists in both the database and the system, proceed with deletion
        if await SystemUserManager.delete_system_user(username):
            await event.respond(f"🗑️ User `{username}` deleted successfully.")
        else:
            await event.respond(f"❌ Error deleting user `{username}`.")

    # /list_users command
    @Auth.authorized_user
    async def list_users(self, event):

        users = storage.join("User", ["Rental", "TelegramUser"], outer=True)
        if not users:
            await event.respond("🔍 No users found.")
            return

        # Get the number of active users
        active_users = [user for user in users if user.rentals[0].is_active]

        response = f"👥 Total Users: {len(active_users)}\n\n"
        ist = pytz.timezone(TIME_ZONE)

        for user in users:
            expiry_date_ist = datetime.fromtimestamp(user.rentals[0].end_time, ist)
            expiry_date_str = Utilities.get_date_str(user.rentals[0].end_time)

            if not user.rentals[0].is_expired:
                remaining_time = expiry_date_ist - datetime.now(pytz.utc).astimezone(
                    ist
                )
                remaining_time_str = ""
                if remaining_time.days > 0:
                    remaining_time_str += f"{remaining_time.days} days, "
                remaining_time_str += f"{remaining_time.seconds // 3600} hours, "
                remaining_time_str += f"{(remaining_time.seconds // 60) % 60} minutes"

                tg_user_id = (
                    str(user.telegram_user[0].tg_user_id)
                    if user.telegram_user
                    else None
                )
                tg_user_first_name = (
                    user.telegram_user[0].tg_first_name if user.telegram_user else None
                )

                if tg_user_id and tg_user_first_name:
                    tg_tag = f"[{tg_user_first_name}](tg://user?id={tg_user_id})"
                else:
                    tg_tag = tg_user_first_name if tg_user_first_name else "Not set"

                response += (
                    f"✨ Username: `{user.linux_username}`\n"
                    f"   Telegram: {tg_tag}\n"
                    f"   Plan: {Utilities.parse_duration_to_human_readable(user.rentals[0].plan_duration)}\n"
                    f"   Expiry Date: `{expiry_date_str}`\n"
                    f"   Remaining Time: `{remaining_time_str}`\n"
                    f"   Status: `Active`\n\n"
                )

            else:
                elapsed_time = datetime.now(pytz.utc).astimezone(ist) - expiry_date_ist
                elapsed_time_str = ""
                tg_user_first_name = user.telegram_users[0].tg_first_name
                tg_user_id = str(user.telegram_users[0].tg_user_id)
                if elapsed_time.days > 0:
                    elapsed_time_str += f"{elapsed_time.days} days, "
                elapsed_time_str += f"{elapsed_time.seconds // 3600} hours, "
                elapsed_time_str += f"{(elapsed_time.seconds // 60) % 60} minutes"

                response += (
                    f"❌ Username: `{user.linux_username}`\n"
                    f"   Telegram: [{tg_user_first_name}](tg://user?id={tg_user_id})\n"
                    f"   Expiry Date: `{expiry_date_str}`\n"
                    f"   Elapsed Time: `{elapsed_time_str}`\n"
                    f"   Status: `Expired`\n\n"
                )

        await event.respond(response)

    # /clear_user command
    @Auth.authorized_user
    async def clear_user(self, event):

        if len(event.message.text.split()) < 2:
            await event.respond("❓ Usage: /unlink_user <username>")
            return

        username = event.message.text.split()[1]
        user = storage.query_object(User, linux_username=username)
        if not user:
            await event.respond(f"❌ No user found for username:`{username}`.")
            return

        telegram_id = storage.query_object(TelegramUser, user_id=user.id)
        if not telegram_id:
            await event.respond(f"❌ No Telegram account is linked with {username}.")
            return

        storage.delete(telegram_id)
        storage.save()

        await event.respond(
            f"✅ Cleared Telegram username and user id for user `{username}`."
        )

    # Link a Telegram user to a system user
    # Create a button to link the user
    # clicks the button and the bot sends the user's Telegram ID to the server
    @Auth.authorized_user
    async def link_user(self, event):

        if len(event.message.text.split()) < 2:
            await event.respond("❓ Usage: /link_user <username>")
            return

        bot_username = await client.get_me()

        username = event.message.text.split()[1]
        user = storage.query_object(User, linux_username=username)

        if not user:
            await event.respond(f"❌ User `{username}` not found.")
            return

        tg_user = storage.query_object(TelegramUser, user_id=user.id)
        tg_user_id = tg_user.tg_user_id if tg_user else None
        if tg_user_id:
            await event.respond(
                f"❌ User `{username}` is already linked to a Telegram user."
            )
            return

        unique_id = user.uuid

        if not unique_id:
            await event.respond(
                f"❌ User `{username}` doesn't have a valid UUID, randomizing..."
            )
            unique_id = str(uuid.uuid4())
            user.uuid = unique_id
            storage.save(user)

        await event.respond(
            f"🔗 Click the button below to link the Telegram user to the system user `{username}`.",
            buttons=[
                Button.url(
                    "Link User",
                    f"https://t.me/{bot_username.username}?start={unique_id}",
                )
            ],
        )

    async def handle_delete_user(self, event):
        username = event.data.decode().split()[1]

        if await SystemUserManager.delete_system_user(username):
            await event.respond(f"🗑️ User `{username}` deleted successfully.")
        else:
            await event.respond(f"❌ Error deleting user `{username}`.")

    async def handle_tglink(self, event):
        username = event.data.decode().split()[1]

        # Get the user_id from the event
        user_id = event.sender_id
        user_first_name = event.sender.first_name
        user_last_name = event.sender.last_name
        tg_username = event.sender.username

        # Update the user's Telegram ID in the database
        user = storage.query_object(User, linux_username=username)
        if not user:
            await event.respond(f"❌ User `{username}` not found.")
            return
        tg_user = storage.query_object(TelegramUser, user_id=user.id)
        tg_user.tg_user_id = user_id
        tg_user.tg_first_name = user_first_name
        tg_user.tg_last_name = user_last_name
        tg_user.tg_username = tg_username
        tg_user.save()

        # Tag the user for future refs
        msg = f"[{user_first_name}](tg://user?id={user_id})\n\n"
        await event.edit(
            msg + f"✅ User `{username}` linked to Telegram user `{tg_username}`."
        )
