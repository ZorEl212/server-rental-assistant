import asyncio
import json
import tempfile
import time
import traceback
from datetime import datetime, timedelta

import redis.asyncio as redis
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.cron import CronTrigger
from jinja2 import Environment, FileSystemLoader
from telethon import Button
from weasyprint import HTML

from models import client, storage
from models.misc import Auth, SystemUserManager, Utilities
from models.telegram_users import TelegramUser
from resources.constants import ADMIN_ID


class SystemRoutes:
    """
    Routes for managing system-related tasks.
    """

    # /help command
    @Auth.authorized_user
    async def help_command(self, event):
        """
        Show the help message for admin commands.
        :param event: Event object.
        :return: None
        """
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
        """
        Generate the HTML content for the report. The report includes user details, payment history, and expiry status.
        The HTML template is rendered using Jinja2.
        :return: HTML content as a string.
        """

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

    @Auth.authorized_user
    async def generate_report(self, event):
        """
        A command handler for /gen_report command.
        Generate a report in PDF format containing user details, payment history, and expiry status.
        The PDF will be generated using HTML content generated from the Jinja2 template.
        :param event: Event object.
        :return: None
        """

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
        """
        A command handler for /broadcast command.
        Broadcast a message to all users with registered telegram accounts.
        :param event: Event object.
        :return: None
        """

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
        """
        A handler for the /who command. Returns `w` command output for all currently connected users.
        :param event: Event object.
        :return:
        """

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
        """
        Callback query handler for refreshing the connected users list.
        :param event: Event object.
        :return: None
        """
        await self.list_connected_users(event)

    # /start command
    async def start_command(self, event):
        """
        A handler for the /start command. This command can only be invoked using valid links
        generated by the bot to link a Telegram user to a system user.
        The link will contain a valid user UUID.
        :param event: Event object.
        :return:
        """

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
        """
        Callback query handler for cleaning user data from the database.
        :param event: Event object.
        :return:
        """

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

    async def run_command(self, event):
        """
        A handler for the /run command. This command is used to run commands on the server.
        :param event: Event object.
        :return:
        """

        if len(event.message.text.split()) <= 1:
            return

        command = event.message.text.split(" ", 1)[1]
        output = await SystemUserManager.run_command(command)
        await event.respond(f"```\n{output}\n```")


class JobManager:
    """
    A class to manage scheduled jobs using APScheduler.
    """

    redis_conn = None
    scheduler = None
    DEDUCTION_HOUR = 6

    def __init__(self):
        self.scheduler: AsyncIOScheduler = AsyncIOScheduler()

    async def save_job_to_redis(
        self, job_id, func_name, trigger_type, trigger_args, args, name
    ):
        """
        Save job information to Redis. The job data is stored as a JSON object.
        In cases where the trigger is of type 'DateTrigger', the run_date is serialized as an ISO string.
        :param job_id: The unique ID of the job.
        :param func_name: The name of the function (method) to be executed
        :param trigger_type: The type of trigger (e.g., 'interval', 'date', 'cron')
        :param trigger_args: Arguments for the trigger (e.g., interval seconds, date time)
        :param args: Arguments to be passed to the function
        :param name: The name of the job (typically the schedule type for our use case).
        :return: None
        """

        job_data = {
            "job_id": job_id,
            "func_name": func_name,
            "trigger_type": trigger_type,
            "trigger_args": trigger_args,
            "args": args,
            "name": name,
        }
        await self.redis_conn.hset("jobs", job_id, json.dumps(job_data))
        print(f"Job {job_id} saved to Redis.")

    async def remove_job_from_redis(self, job_id):
        """
        Remove a job from Redis using the job ID.
        This will be called only when the job is considered complete or no longer needed.
        :param job_id:  The unique ID of the job.
        :return: None
        """

        await self.redis_conn.hdel("jobs", job_id)
        print(f"Job {job_id} removed from Redis.")

    async def load_jobs_from_redis(self, job_data):
        """
        Load jobs from Redis and schedule them using the scheduler.
        :param job_data: A dictionary containing job data (job ID as key and job info as value).
        :return: None
        """

        for job_id, job_info in job_data.items():
            job_info = json.loads(job_info)
            func = getattr(self, job_info["func_name"], None)
            if (
                job_info["name"] != "deduction"
                and job_info["trigger_type"]["type"] == "DateTrigger"
            ):
                run_date = datetime.fromisoformat(
                    job_info["trigger_type"]["run_date"]
                ).replace(tzinfo=None)
                if run_date < datetime.now():
                    await self.remove_job_from_redis(job_id)
                    continue
                job_info["trigger_type"] = DateTrigger(
                    run_date=datetime.fromisoformat(
                        job_info["trigger_type"]["run_date"]
                    )
                )
            if job_info["name"] == "deduction" or job_info["job_id"] == "deduction":
                if job_info["trigger_type"]["type"] == "CronTrigger":
                    job_info["trigger_type"] = CronTrigger(
                        hour=job_info["trigger_type"]["hour"],
                        minute=job_info["trigger_type"]["min"],
                    )
            if func:
                self.add_job(
                    func=func,
                    trigger=job_info["trigger_type"],
                    trigger_args=job_info["trigger_args"],
                    job_id=job_id,
                    args=job_info["args"],
                    new_job=False,
                )
                print(f"Job {job_id} reloaded from Redis.")

    async def handle_expired_rental(self, rental_id):
        """
        Handle the expiration of a rental plan. This method will be called when a rental plan expires.
        The user will be notified, and the necessary actions will be taken.
        Normally this should be called by the scheduler when the rental plan expires but can be called manually.
        :param rental_id: The ID of the rental plan.
        :return: None
        """
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

    async def deduct_daily_rental(self):
        """
        Deducts rental charges from user balances on a daily basis.
        """
        # Get all active rentals
        active_rentals = storage.all(
            "Rental", filters={"is_active": 1, "is_expired": 0}
        )

        current_time = int(time.time())  # Get current time in Unix timestamp

        for rental in active_rentals.values():
            # Ensure the user has enough balance to cover the deduction
            user = rental.user  # Assuming a relationship exists between Rental and User
            full_day = (current_time - user.last_deduction_time) // 86400  # days
            total_deduction = full_day * rental.price_rate
            if full_day >= 1 and user.balance >= total_deduction:
                new_balance = user.balance - total_deduction
                await user.update_balance(
                    new_balance, "debit"
                )  # Update balance with deduction
                user.last_deduction_time = int(
                    datetime.now()
                    .replace(
                        hour=self.DEDUCTION_HOUR, minute=0, second=0, microsecond=0
                    )
                    .timestamp()
                )
                storage.save()

                # Respond to the user or log the deduction (optional)
                print(
                    f"Deducted {total_deduction} {rental.currency} from {user.linux_username}'s balance."
                )
            else:
                # Handle case when balance is insufficient
                print(
                    f"Insufficient balance for {user.linux_username} to deduct rental fee."
                    f" Balance: {user.balance}, Deduction: {total_deduction}"
                )

    def schedule_rental_expiration(self, rental):
        """
        Schedule the expiration job for a rental plan.
        A job will be scheduled to handle the expiration of the rental plan.
        Most of the time, this method will be called when a new rental plan is created.
        :param rental: The rental plan object.
        :return: None
        """

        expiration_time = datetime.fromtimestamp(rental.end_time)
        job_id = f"expire_rental_{rental.id}"

        self.add_job(
            self.handle_expired_rental,
            trigger=DateTrigger(run_date=expiration_time),
            job_id=job_id,
            args=[rental.id],
            replace_existing=True,
        )
        print(f"Scheduled expiration job for rental {rental.id} at {expiration_time}")

    def schedule_notification_job(self, rental):
        """
        Schedule a notification job for a rental plan. The notification will be sent 24 hours before the plan expires.
        This should be called when a new rental plan is created otherwise it is used as a helper method to schedule
        notification jobs for all active rentals.
        With a tolerance window of 12 hours, the notification will be sent immediately if the time is within the window.
        :param rental: The rental plan object.
        :return: None
        """

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
        """
        Schedule notification jobs for all active rentals.
        This method will be called when the system starts to schedule notification jobs for all active rentals.
        :return: None
        """

        rentals = storage.join(
            "Rental",
            ["User", "TelegramUser"],
            {"is_active": 1, "sent_expiry_notification": 0},
            outer=True,
        )
        for rental in rentals if rentals else []:
            self.schedule_notification_job(rental)

    async def notify_rental(self, rental_id):
        """
        Send a notification to the user when the rental plan is about to expire.
        This method will be called by the scheduler when the notification job is triggered.
        :param rental_id: The ID of the rental plan.
        :return: None
        """

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
        """
        Schedule expiration jobs for all active rentals.
        This method will be called when the system starts to schedule expiration jobs for all active rentals.
        If the rental plan has already expired and notifications have been sent, the expiration job will not be scheduled.
        :return: None
        """

        rentals = storage.join("Rental", ["User"], {"is_active": 1, "is_expired": 0})
        for rental in rentals if rentals else []:
            self.schedule_rental_expiration(rental)

    async def schedule_deduction(self):
        """
        Schedule the daily deduction job for all active rentals.
        This method will be called when the system starts to schedule daily deduction jobs for all active rentals.
        :return: None
        """

        self.add_job(
            self.deduct_daily_rental,
            trigger=CronTrigger(hour=self.DEDUCTION_HOUR, minute=0),
            job_id="deduction",
            replace_existing=True,
            name="deduction",
        )
        print("Scheduled daily deduction job.")

    def job_listener(self, event):
        """
        A listener to handle job execution events.
        Used to log job execution status.
        :param event: The event object. Note that this is an APScheduler event object.
        :return: None
        """

        if event.exception:
            print(f"Job {event.job_id} failed")
        else:
            print(f"Job {event.job_id} executed successfully")

    def serialize_trigger(self, trigger):
        """
        Serialize the trigger object to JSON.
        DateTrigger objects will be serialized as a dictionary containing the run_date.
        This is a helper method to serialize the trigger object before saving it to Redis.
        :param trigger: The trigger object. (e.g., DateTrigger, IntervalTrigger)
        :return: A serialized JSON object.
        """

        if isinstance(trigger, DateTrigger):
            return {
                "type": "DateTrigger",
                "run_date": trigger.run_date.isoformat(),  # Serialize datetime as ISO string
            }
        elif isinstance(trigger, CronTrigger):
            return {
                "type": "CronTrigger",
                "hour": int(str(trigger.fields[5])),
                "min": int(str(trigger.fields[6])),
            }
        raise TypeError(f"Cannot serialize trigger of type {type(trigger).__name__}")

    def add_job(
        self,
        func,
        trigger,
        trigger_args=None,
        job_id=None,
        replace_existing=True,
        args=None,
        new_job=True,
        name=None,
    ):
        """
        Dynamically add jobs to the scheduler and save to Redis.

        :param name: The name of the job (typically the schedule type)
        :param new_job: A flag to determine whether to save the job to Redis
        :param func: The function to be executed by the job
        :param trigger: The type of trigger (e.g., 'interval', 'date', 'cron')
        :param trigger_args: Arguments for the trigger (e.g., interval seconds, date time)
        :param job_id: An optional ID to uniquely identify the job
        :param replace_existing: Whether to replace an existing job with the same ID
        :param args: Arguments to be passed to the function
        """
        if trigger_args is None:
            trigger_args = {}
        self.scheduler.add_job(
            func,
            trigger,
            id=job_id,
            replace_existing=replace_existing,
            **trigger_args if trigger_args else {},
            args=args,
            name=name,
        )
        if isinstance(trigger, DateTrigger) or isinstance(trigger, CronTrigger):
            trigger = self.serialize_trigger(trigger)
        if new_job:
            asyncio.create_task(
                self.save_job_to_redis(
                    job_id, func.__name__, trigger, trigger_args, args, name
                )
            )

    async def schedule_jobs(self):
        """
        Initialize the Redis connection and schedule jobs.
        Handles the main event loop for the scheduler.
        :return: None
        """

        self.scheduler.add_listener(
            self.job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR
        )
        await self.init_redis()
        self.scheduler.start()
        print("Scheduler started.")

        job_data = await self.redis_conn.hgetall("jobs")
        if job_data:
            await self.load_jobs_from_redis(job_data)
        else:
            await self.schedule_all_notifications()

            # Schedule expiration jobs for all current rentals
            await self.schedule_all_rentals()
            await self.schedule_deduction()

        current_time = datetime.now()
        if (
            current_time.hour >= self.DEDUCTION_HOUR and current_time.minute > 0
        ):  # Deduct if the current time is past the deduction hour (When the script starts)
            await self.deduct_daily_rental()

        # Keep the event loop running
        while True:
            await asyncio.sleep(1)

    async def init_redis(self):
        """
        Initialize the Redis connection.
        :return: None
        """

        self.redis_conn = redis.Redis(
            host="localhost", port=6379, db=0, decode_responses=True
        )
