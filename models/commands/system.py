import asyncio
import tempfile
import time
import traceback
from datetime import datetime, timedelta

import aioredis
from apscheduler import events
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from jinja2 import Environment, FileSystemLoader
from telethon import Button
from weasyprint import HTML

from models import client, storage
from models.misc import Auth, SystemUserManager, Utilities
from models.telegram_users import TelegramUser
from resources.constants import ADMIN_ID


class SystemRoutes:
    # /help command
    @Auth.authorized_user
    async def help_command(self, event):
        help_text = """

        🔐 **Admin Commands:**

        - `/create_user <username> <plan_duration> <amount> <currency>`: Create a user with a plan duration and amount.
        - `/reduce_plan <username> <reduced_duration>`: Reduce the plan duration for a user.
        - `/sync_db`: Sync the database with the system.
        - `/debit <username> <amount> <currency>`: Debit the amount from the user.
        - `/credit <username> <amount> <currency>`: Credit the amount to the user.
        - `/earnings`: Show the total earnings.
        - `/delete_user <username>`: Delete a user.
        - `/extend_plan <username> <additional_duration> [amount] [currency]`: Extend a user's plan.
        - `/payment_history <username>`: Show the payment history for a user.
        - `/unlink_user <username>`: Clear the Telegram username and user id for a user.
        - `/list_users`: List all users along with their expiry dates and remaining time.
        - `/who`: List the currently connected users.
        - `/broadcast <message>`: Broadcast a message to all users.
        - `/link_user <username>`: Link a Telegram user to a system user.
        """

        await event.respond(help_text)

    def generate_html(self):
        # Load the template
        env = Environment(
            loader=FileSystemLoader("./resources")
        )  # Point to resources directory
        template = env.get_template("report_template.html")

        user_info = storage.join("User", ["Rental", "Payment"])
        processed_rows = [
            {
                "user_id": user.id,
                "username": user.linux_username,
                "creation_ist": Utilities.get_date_str(
                    int(user.created_at.timestamp())
                ),
                "expiry_ist": Utilities.get_date_str(user.rentals[0].end_time),
                "is_expired": user.rentals[0].is_expired,
                "total_payment": f"{sum([payment.amount for payment in user.payments]):.2f}",
                "currency": user.payments[0].currency,
                "payment_count": len(user.payments),
            }
            for user in user_info
        ]
        # Render the template with data
        return template.render(rows=processed_rows)

    async def generate_report(self, event):
        await event.respond("🔄 Generating report...")
        try:
            storage.reload()
            html_content = self.generate_html()

            # Generate PDF
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_pdf:
                HTML(string=html_content).write_pdf(temp_pdf.name)
                pdf_file_path = temp_pdf.name

            # Send PDF
            await client.send_file(
                event.chat_id,
                pdf_file_path,
                caption=f"📄 Report {Utilities.get_date_str(int(datetime.now().timestamp()))}",
            )

        except Exception as e:
            await event.respond(f"❌ Error generating report: {e}")
            traceback.print_exc()

    @Auth.authorized_user
    async def broadcast(self, event):

        if len(event.message.text.split()) < 2:
            await event.respond("❓ Usage: /broadcast <message>")
            return

        message = event.message.text.split(" ", 1)[1]

        # Prepend the message with the sender's name, along with the notice
        message = f"📢 **Broadcast Message**\n\n{message}"

        rentals = storage.join("Rental", ["TelegramUser"], {"is_active": 1})
        for rental in rentals:
            try:
                await client.send_message(rental.telegram_id, message)
            except Exception:
                pass

        await event.respond(f"✅ Broadcasted message to {len(rentals)} user(s).")

    # /who command
    @Auth.authorized_user
    async def list_connected_users(self, event):

        connected_users = await SystemUserManager.get_running_users()
        try:
            await event.edit(
                f"```\n{connected_users}\n```",
                buttons=[Button.inline("Refresh", data="refresh_connected_users")],
            )
        except:
            await event.respond(
                f"```\n{connected_users}\n```",
                buttons=[Button.inline("Refresh", data="refresh_connected_users")],
            )

    async def refresh_connected_users(self, event):
        await self.list_connected_users(event)

    # /start command
    async def start_command(self, event):
        if len(event.message.text.split()) <= 1:
            return

        user_uuid = event.message.text.split()[1]
        user = storage.query_object("User", uuid=user_uuid)

        if not user:
            await event.respond("❌ Invalid or expired link.")
            return

        username = user.linux_username
        print("Username:", username)
        rental = storage.query_object("Rental", user_id=user.id)
        tg_user = storage.query_object("TelegramUser", user_id=user.id)

        fetched_user_id = tg_user.tg_user_id if tg_user else None

        tg_user_id = event.sender_id
        new_tg_username = event.sender.username
        user_first_name = event.sender.first_name
        user_last_name = event.sender.last_name

        if fetched_user_id is None:
            if new_tg_username is None:
                new_tg_username = tg_user_id

            new_tg_user = TelegramUser(
                tg_user_id=tg_user_id,
                user_id=user.id,
                tg_username=new_tg_username,
                tg_first_name=user_first_name,
                tg_last_name=user_last_name,
            )
            storage.new(new_tg_user)
            storage.save()

            # Update users table as well
            rental.telegram_id = tg_user_id
            storage.save()

            # Tag the user for future refs
            msg = f"[{user_first_name}](tg://user?id={tg_user_id})\n\n"

            await event.respond(
                msg
                + f"🔑 **Username:** `{username}`\n🔒 **Password:** `{user.linux_password}`"
            )
            await client.send_message(
                ADMIN_ID,
                f"🔑 Password sent to user [{user_first_name}](tg://user?id={tg_user_id}).",
            )
        else:
            # Tag the user for future refs
            msg = f"[{user_first_name}](tg://user?id={tg_user_id})\n\n"

            if fetched_user_id == tg_user_id:
                await event.respond(
                    msg
                    + f"🔑 **Username:** `{username}`\n🔒 **Password:** `{user.linux_password}`"
                )
            else:
                await event.respond(
                    "❌ You are not authorized to get the password for this user."
                )

    @Auth.authorized_user
    async def handle_clean_db(self, event):
        username = event.data.decode().split()[1]
        user = storage.query_object("User", linux_username=username)
        rental = storage.query_object("Rental", user_id=user.id)
        if not rental:
            await event.edit(
                f"❌ Rental for user `{username}` not found in the database."
            )
            return
        rental.is_active = 1
        rental.save()
        status = "Expired" if rental.is_expired else "Active"
        await event.edit(
            f"✅ User `{username}` plan updated in the database. Status: `{status}`."
        )


class JobManager:
    redis_conn = None
    scheduler = None

    def __init__(self):
        self.job_id = None
        self.scheduler = AsyncIOScheduler()

    async def handle_expired_rental(self, rental_id):
        rental = storage.join("Rental", ["User"], {"id": rental_id}, fetch_one=True)

        if rental:
            user = rental.user
            telegram_id = rental.telegram_id

            message = (
                f"❌ Your plan for the user: `{user.linux_username}` has been expired."
                f"\n\nThanks for using our service. 🙏"
                f"\nFeel free to contact the admin for any queries. 📞"
            )

            new_password = await SystemUserManager.change_password(user.linux_username)

            status, removal_str = await SystemUserManager.remove_ssh_auth_keys(
                user.linux_username
            )

            if telegram_id:
                await client.send_message(telegram_id, message)

            await client.send_message(
                ADMIN_ID,
                f"⚠️ Plan for user `{user.linux_username}` has expired. Please take necessary action.",
                buttons=[
                    [Button.inline("Cancel", data=f"cancel {user.linux_username}")],
                    [
                        Button.inline(
                            "Delete User", data=f"delete_user {user.linux_username}"
                        )
                    ],
                ],
            )
            await client.send_message(
                ADMIN_ID,
                f"🔑 New password for user `{user.linux_username}`: `{new_password}`",
            )
            await client.send_message(ADMIN_ID, f"🔑 {removal_str}")

            rental.is_expired = 1
            rental.is_active = 0
        storage.save()

    def schedule_rental_expiration(self, rental):
        expiration_time = datetime.fromtimestamp(rental.end_time)
        job_id = f"expire_rental_{rental.id}"

        self.scheduler.add_job(
            self.handle_expired_rental,
            trigger=DateTrigger(run_date=expiration_time),
            job_id=job_id,
            args=[rental.id],
            replace_existing=True,
        )
        print(f"Scheduled expiration job for rental {rental.id} at {expiration_time}")

    def schedule_notification_job(self, rental):
        # Calculate notification time (24 hours before expiration)
        notification_time = datetime.fromtimestamp(rental.end_time) - timedelta(
            hours=24
        )
        job_id = f"notify_rental_{rental.id}"

        # Check if the notification time is more than 12 hours from now
        tolerance_window = timedelta(hours=12)
        time_remaining = notification_time - datetime.now()

        if time_remaining <= timedelta(0):  # Notification time has already passed
            print(
                f"Skipping notification job for rental {rental.id} as the time has already passed."
            )
            return
        elif time_remaining <= tolerance_window:
            print(
                f"Notification job for rental {rental.id} is within the tolerance window."
            )
            # Send the notification immediately
            asyncio.create_task(self.notify_rental(rental.id))
        else:
            # Schedule the notification job
            self.add_job(
                self.notify_rental,
                trigger=DateTrigger(run_date=notification_time),
                job_id=job_id,
                args=[rental.id],
                replace_existing=True,
            )
            print(
                f"Scheduled notification job for rental {rental.id} at {notification_time}"
            )

    async def schedule_all_notifications(self):
        rentals = storage.join(
            "Rental",
            ["User", "TelegramUser"],
            {"is_active": 1, "sent_expiry_notification": 0},
        )
        for rental in rentals if rentals else []:
            self.schedule_notification_job(rental)

    async def notify_rental(self, rental_id):
        rental = storage.join(
            "Rental", ["User", "TelegramUser"], {"id": rental_id}, fetch_one=True
        )

        if rental and not rental.sent_expiry_notification:
            user = rental.user
            tg_user = rental.telegram_user
            remaining_time = datetime.fromtimestamp(rental.end_time) - datetime.now()
            remaining_time_str = (
                f"{remaining_time.days} days, "
                f"{remaining_time.seconds // 3600} hours, "
                f"{(remaining_time.seconds // 60) % 60} minutes"
            )
            message = (
                f"⏰ [{tg_user.tg_first_name}](tg://user?id={rental.telegram_id}) Your plan for user `{user.linux_username}` "
                f"will expire in {remaining_time_str}."
                "\n\nPlease contact the admin if you want to extend the plan. 🔄"
                "\nYour data will be deleted after the expiry time. 🗑️"
            )

            await client.send_message(
                tg_user.tg_user_id if tg_user else ADMIN_ID, message
            )
            rental.sent_expiry_notification = 1
            storage.save()

    async def schedule_all_rentals(self):
        rentals = storage.join("Rental", ["User"], {"is_active": 1, "is_expired": 0})
        for rental in rentals if rentals else []:
            self.schedule_rental_expiration(rental)

    @staticmethod
    async def deduct_balance(rental_id):
        rental = storage.join("Rental", ["User"], {"id": rental_id}, fetch_one=True)
        if rental:
            user = rental.user
            try:
                user.deduct_balance(rental.price_rate)
                print(f"✅ Deducted balance for user {user.linux_username}")
                storage.save()
            except ValueError:
                print(
                    f"❌ User {user.linux_username} has insufficient balance.\n"
                    f"Please credit the user's account to extend the plan."
                )

    def job_listener(self, event):
        if event.exception:
            print(f"Job {event.job_id} failed")
        else:
            print(f"Job {event.job_id} executed successfully")

    def add_job(
        self, func, trigger, trigger_args, job_id=None, replace_existing=True, args=None
    ):
        """
        Dynamically add jobs to the scheduler.

        :param func: The function to be executed by the job
        :param trigger: The type of trigger (e.g., 'interval', 'date', 'cron')
        :param trigger_args: Arguments for the trigger (e.g., interval seconds, date time)
        :param job_id: An optional ID to uniquely identify the job
        :param replace_existing: Whether to replace an existing job with the same ID
        :param args: Arguments to be passed to the function
        """
        self.scheduler.add_job(
            func,
            trigger,
            id=job_id,
            replace_existing=replace_existing,
            **trigger_args,
            args=args,
        )

    async def schedule_jobs(self):
        self.scheduler.add_listener(
            self.job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR
        )
        self.scheduler.start()
        print("Scheduler started.")

        await self.schedule_all_notifications()

        # Schedule expiration jobs for all current rentals
        await self.schedule_all_rentals()

        # Keep the event loop running
        while True:
            await asyncio.sleep(1)

    async def init_redis(self):
        self.redis_conn = aioredis.from_url("redis://localhost", decode_responses=True)
