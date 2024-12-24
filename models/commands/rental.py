import asyncio
import time
from datetime import datetime, timedelta

from models import client, storage
from models.misc import Auth, Utilities
from models.payments import Payment


class PlanRoutes:
    @Auth.authorized_user
    async def reduce_plan(self, event):
        args = event.message.text.split()
        if len(args) < 3:
            await event.respond(
                "❓ Usage: /reduce_plan <username> <reduced_duration> \n"
                "For example: `/reduce_plan john 7d`"
            )
            return

        username = args[1]
        reduced_duration_seconds = Utilities.parse_duration(args[2])

        if username == "all":
            active_rentals = storage.join("Rental", ["User"], {"is_expired": 0})
            for rental in active_rentals:
                await rental.reduce_plan(reduced_duration_seconds)

            response = "🔄 All users' plans reduced!\n\n"
            response += "\n".join(
                [
                    f"👤 User `{rental.user.linux_username}`\n   "
                    f"📅 New expiry date: `{Utilities.get_date_str(rental.expiry_time)}`"
                    for rental in active_rentals
                ]
            )
            await event.respond(response)
        else:
            user = storage.query_object("User", linux_username=username)
            if not user:
                await event.respond(f"❌ User `{username}` not found.")
                return
            rental = storage.join(
                "Rental",
                ["TelegramUser", "User"],
                {"user_id": user.id, "is_expired": 0},
                True,
            )
            if not rental:
                await event.respond(f"❌ User `{username}` has no active rentals.")
                return
            await rental.reduce_plan(reduced_duration_seconds)
            await event.respond(
                f"🔄 User `{username}`'s plan reduced!\n\n"
                f"👤 User `{username}`\n   New expiry date: `{Utilities.get_date_str(rental.end_time)}`"
                f"⏳ Duration reduced by : {Utilities.parse_duration_to_human_readable(abs(reduced_duration_seconds))}"
            )

    # /extend_plan command
    @Auth.authorized_user
    async def extend_plan(self, event):
        args = event.message.text.split()
        if len(args) < 3:
            await event.respond(
                "❓ Usage: /extend_plan <username> <additional_duration> [amount] [currency]\n"
                "For example: `/extend_plan john 5d 500 INR`"
            )
            return

        await event.respond("🔄 Extending plan...")

        username = args[1]
        additional_duration_str = args[2]
        additional_seconds = Utilities.parse_duration(additional_duration_str)
        amount_inr = None

        if username == "all":
            active_rentals = storage.join("Rental", ["User"], {"is_active": 1})
            for rental in active_rentals:
                await rental.extend_plan(additional_seconds)

            response = "🔄 All users' plans extended!\n\n" + "\n".join(
                [
                    f"👤 User `{rental.user.linux_username}`\n"
                    f"📅 New expiry date: `{Utilities.get_date_str(rental.end_time)}`"
                    for rental in active_rentals
                ]
            )
            await event.respond(response)
            return

        if len(args) < 5:
            await event.respond(
                "❌ All arguments must be provided for a single user.\n"
                "Usage: /extend_plan <username> <additional_duration> <amount> <currency>"
            )
            return

        user = storage.query_object("User", linux_username=username)
        if not user:
            await event.respond(f"❌ User `{username}` not found.")
            return

        rental = storage.join(
            "Rental",
            ["TelegramUser", "User"],
            {"user_id": user.id, "is_active": 1},
            True,
            True,
        )
        if not rental:
            await event.respond(f"❌ User `{username}` has no active rentals.")
            return

        await rental.extend_plan(additional_seconds)

        try:
            amount_str = args[3]
            currency = args[4].upper()
            payment = await Payment.create(user.id, amount_str, currency)
            amount_inr = payment.amount
            await user.update_balance(payment.amount, "credit")
            payment.save()
        except ValueError:
            await event.respond("❌ Invalid amount or currency.")
            return

        await event.respond(
            f"🔄 User `{username}`'s plan extended!\n\n"
            f"👤 User `{username}`\n"
            f"📅 New expiry date: `{Utilities.get_date_str(rental.end_time)}`\n\n"
            f"⏳ Duration extended by: {Utilities.parse_duration_to_human_readable(additional_seconds)}\n\n"
            f"💰 Balance: `{user.balance:.2f} INR`"
        )

        if rental.telegram_user:
            message = (
                f"Dear {rental.telegram_user.tg_first_name},\n\n"
                f"🔥 Your plan has been extended by `{Utilities.parse_duration_to_human_readable(additional_seconds)}`.\n"
                f"📅 New expiry date: `{Utilities.get_date_str(rental.end_time)}`.\n\n Enjoy your server! 🚀"
            )
            await client.send_message(rental.telegram_id, message)

        if amount_inr is not None:
            await event.respond(
                f"✅ Amount `{amount_inr:.2f} INR` credited to user `{username}`."
            )

    async def handle_cancel(self, event):
        username = event.data.decode().split()[1]
        prev_msg = (
            f"⚠️ Plan for user `{username}` has expired. Please take necessary action."
        )
        rental = storage.query_object("Rental", user_id=username, is_expired=0)
        if rental:
            rental.is_expired = 1
            storage.save()
            await event.edit(prev_msg + "\n\n" + "🚫 Plan canceled.")
            return True
        await event.edit(prev_msg + "\n\n" + "❌ Plan not found.")

    async def run_daily_deduction(self):
        """Run the task daily at a fixed time."""
        while True:
            now = datetime.now()
            next_run = (now + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            wait_time = (next_run - now).total_seconds()

            rentals = storage.join("Rental", ["User"], {"is_active": 1})
            for rental in rentals:
                if rental.end_time < int(time.time()):
                    rental.is_expired = 1
                    storage.save()
                else:
                    user = rental.user
                    try:
                        await user.deduct_balance(rental.exchange_rate)
                    except ValueError:
                        rental.is_active = 0
                        print(
                            f"❌ User {user.linux_username} has insufficient balance. Plan canceled."
                        )
                        storage.save()
            storage.save()
            await asyncio.sleep(wait_time)
