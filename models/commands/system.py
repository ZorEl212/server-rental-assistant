import asyncio
import time
import traceback
from datetime import datetime

from telethon import Button

from models import storage
from models.misc import Auth, Utilities, SystemUserManager
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
import tempfile

from models.telegram_users import TelegramUser
from resources.constants import ADMIN_ID
from models import client


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

    async def notify_expiry(self):
        while True:
            now = int(time.time())
            twelve_hours_from_now = now + (12 * 60 * 60)

            rentals = storage.join(
                "Rental", ["TelegramUser", "User"], {"sent_expiry_notification": 0}
            )
            expiring_rentals = [
                rental
                for rental in rentals
                if twelve_hours_from_now >= rental.end_time > now
            ]

            for rental in expiring_rentals:
                rental.sent_expiry_notification = 1
                storage.save()

                user = rental.User
                tg_user = rental.TelegramUser

                remaining_time = (
                    datetime.fromtimestamp(rental.end_time) - datetime.now()
                )
                remaining_time_str = ""
                if remaining_time.days > 0:
                    remaining_time_str += f"{remaining_time.days} days, "
                remaining_time_str += f"{remaining_time.seconds // 3600} hours, "
                remaining_time_str += f"{(remaining_time.seconds // 60) % 60} minutes"

                if tg_user:
                    message = f"⏰ [{tg_user.first_name}](tg://user?id={tg_user.telegram_id}) Your plan for user `{user.linux_username}` will expire in {remaining_time_str}."
                else:
                    message = f"⏰ Plan for user `{user.linux_username}` will expire in {remaining_time_str}."
                message += (
                    "\n\nPlease contact the admin if you want to extend the plan. 🔄"
                )
                message += "\nYour data will be deleted after the expiry time. 🗑️"

                if tg_user:
                    await client.send_message(tg_user.telegram_id, message)
                else:
                    await client.send_message(ADMIN_ID, message)

                # Alert the admin about the expiring user
                admin_message = f"⏰ Plan for user `{user.linux_username}` will expire in {remaining_time_str}."
                await client.send_message(ADMIN_ID, admin_message)

            expired_rentals = [
                rental
                for rental in rentals
                if rental.end_time <= now and rental.is_expired == 0
            ]

            for rental in expired_rentals:
                rental.is_expired = 1
                storage.save()

                user = rental.users[0]
                tg_user = rental.telegram_users[0]

                message = f"❌ Your plan for the user: `{user.linux_username}` has been expired."
                message += "\n\nThanks for using our service. 🙏"
                message += "\nFeel free to contact the admin for any queries. 📞"

                new_password = await SystemUserManager.change_password(
                    user.linux_username
                )

                # Remove the authorized ssh keys
                status, removal_str = await SystemUserManager.remove_ssh_auth_keys(
                    user.linux_username
                )

                if tg_user:
                    await client.send_message(tg_user.telegram_id, message)

                # Notify admin about the expired user
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

            await asyncio.sleep(60)  # Check every minute

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
