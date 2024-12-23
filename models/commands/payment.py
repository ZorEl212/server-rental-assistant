from models import storage
from models.misc import Auth, Utilities
from models.payments import Payment
from models.users import User


class PaymentRoutes:
    # /earnings command
    @Auth.authorized_user
    async def show_earnings(self, event):
        all_payments = storage.all("Payment")
        total_earnings = sum(payment.amount for payment in all_payments.values())
        await event.respond(f"💰 **Total Earnings:** `{total_earnings:.2f} INR`")

    @Auth.authorized_user
    async def payment_history(self, event):

        if len(event.message.text.split()) < 2:
            await event.respond("❓ Usage: /payment_history <username>")
            return

        username = event.message.text.split()[1]
        user = storage.query_object("User", linux_username=username)
        if not user:
            await event.respond(f"❌ User `{username}` not found.")
            return
        payments = storage.all("Payment", {"user_id": user.id})

        if payments:
            response = f"💳 Payment History for `{username}`:\n\n"
            for payment in payments.values():
                payment_date_str = Utilities.get_date_str(payment.payment_date)
                response += f"💰 Amount: `{payment.amount:.2f} {payment.currency}`\n📅 Date: `{payment_date_str}`\n\n"
        else:
            response = f"🔍 No payment history found for `{username}`."

        await event.respond(response)

    @Auth.authorized_user
    async def credit_payment(self, event):
        args = event.message.text.split()
        if len(args) < 4:
            await event.respond(
                "❓ Usage: /credit_payment <username> <amount> <currency>\nFor example: `/credit_payment john 500 INR`"
            )
            return

        username = args[1]
        amount = float(args[2])
        currency = args[3]

        user: User = storage.query_object("User", linux_username=username)
        if not user:
            await event.respond(f"❌ User `{username}` not found.")
            return

        payment = await Payment.create(
            user_id=user.id, amount=amount, currency=currency
        )
        payment.save()
        await user.update_balance(payment.amount, "credit")
        storage.save()

        await event.respond(
            f"💳 Payment of `{amount:.2f} {currency}` credited to `{username}`.\n"
            f"💰 **Available Balance:** `{user.balance:.2f} INR`"
        )

    @Auth.authorized_user
    async def debit_payment(self, event):
        args = event.message.text.split()
        if len(args) < 4:
            await event.respond(
                "❓ Usage: /debit_payment <username> <amount> <currency>\nFor example: `/debit_payment john 500 INR`"
            )
            return

        username = args[1]
        amount = float(args[2])
        currency = args[3]

        user = storage.query_object("User", linux_username=username)
        if not user:
            await event.respond(f"❌ User `{username}` not found.")
            return

        payment = await Payment.create(
            user_id=user.id, amount=-amount, currency=currency
        )
        try:
            await user.update_balance(payment.amount, "debit")
            payment.save()
            storage.save()
        except ValueError as e:
            await event.respond(
                f"❌ Insufficient balance.\nAvailable balance: `{user.balance:.2f}`"
            )
            return

        await event.respond(
            f"💳 Payment of `{amount:.2f} {currency}` debited from `{username}`.\n"
            f"💰 **Available Balance:** `{user.balance:.2f} INR`"
        )
