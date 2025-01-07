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
    """
    Routes for managing users.
    """

    async def create_user(self, event):
        """
        A handler for /create_user command.
        Create a new user with the specified plan duration and amount.
        :param event: Event object.
        :return: None
        """

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
            price_rate=36.0,  # TO DO: Use current price per day
        )
        storage.new(rental)
        storage.save()
        await client.send_message(
            event.chat_id,
            message_str,
            buttons=[[Button.url("Get Password", password_url)]],
        )
        from models import job_manager

        job_manager.add_job(
            job_manager.deduct_balance,
            "interval",
            {"hours": 24},
            name="deduction",
            job_id=f"deduct_balance_{rental.id}",
            args=[rental.id],
            replace_existing=True,
        )
        job_manager.schedule_notification_job(rental)
        job_manager.schedule_rental_expiration(rental)
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
        A handler for /delete_user command to delete a user from the system or database.

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

        rental = storage.query_object("Rental", user_id=user_in_db.id)
        # If user exists in both the database and the system, proceed with deletion
        if await SystemUserManager.delete_system_user(username):
            rental.is_active = 0
            storage.save()
            await event.respond(f"🗑️ User `{username}` deleted successfully.")
        else:
            await event.respond(f"❌ Error deleting user `{username}`.")

    # /list_users command
    @Auth.authorized_user
    async def list_users(self, event):
        """List all users with their rental and status details.
        All users with their rental details are listed along with their status with no exceptions or filters.
        :param event: Event object.
        """

        users = storage.join("User", ["Rental", "TelegramUser"], outer=True)
        if not users:
            await event.respond("🔍 No users found.")
            return

        ist = pytz.timezone(TIME_ZONE)
        response = f"👥 Total Users: {len(users)}\n\n"

        for user in users:
            rental = user.rentals[0] if user.rentals else None
            telegram_user = user.telegram_user[0] if user.telegram_user else None

            if rental:
                expiry_date_ist = datetime.fromtimestamp(rental.end_time, ist)
                expiry_date_str = Utilities.get_date_str(rental.end_time)
                now = datetime.now(pytz.utc).astimezone(ist)

                if rental.is_expired or not rental.is_active:
                    elapsed_time = now - expiry_date_ist
                    elapsed_time_str = f"{elapsed_time.days} days, {elapsed_time.seconds // 3600} hours, {(elapsed_time.seconds // 60) % 60} minutes"

                    tg_tag = (
                        f"[{telegram_user.tg_first_name}](tg://user?id={telegram_user.tg_user_id})"
                        if telegram_user
                        else "Not set"
                    )

                    response += (
                        f"❌ Username: `{user.linux_username}`\n"
                        f"   Telegram: {tg_tag}\n"
                        f"   Expiry Date: `{expiry_date_str}`\n"
                        f"   Elapsed Time: `{elapsed_time_str}`\n"
                        f"   Status: `Expired`\n\n"
                    )
                else:
                    remaining_time = expiry_date_ist - now
                    remaining_time_str = (
                        f"{remaining_time.days} days, {remaining_time.seconds // 3600} hours, "
                        f"{(remaining_time.seconds // 60) % 60} minutes"
                    )

                    tg_tag = (
                        f"[{telegram_user.tg_first_name}](tg://user?id={telegram_user.tg_user_id})"
                        if telegram_user
                        else "Not set"
                    )

                    response += (
                        f"✨ Username: `{user.linux_username}`\n"
                        f"   Telegram: {tg_tag}\n"
                        f"   Plan: {Utilities.parse_duration_to_human_readable(rental.plan_duration)}\n"
                        f"   Expiry Date: `{expiry_date_str}`\n"
                        f"   Remaining Time: `{remaining_time_str}`\n"
                        f"   Status: `Active`\n\n"
                    )
            else:
                response += f"❌ Username: `{user.linux_username}` (No rental information available)\n\n"

        await event.respond(response)

    # /clear_user command
    @Auth.authorized_user
    async def clear_user(self, event):
        """
        A handler for /unlink_user command to clear the Telegram user linked to a system user.
        :param event: Event object.
        :return: None
        """

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
        """
        Link a Telegram user to a system user.
        :param event: Event object.
        :return: None
        """

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
        """
        A callback handler for the button to delete a user from the database.
        :param event: Event object.
        :return: None
        """
        username = event.data.decode().split()[1]

        if await SystemUserManager.delete_system_user(username):
            await event.respond(f"🗑️ User `{username}` deleted successfully.")
        else:
            await event.respond(f"❌ Error deleting user `{username}`.")
