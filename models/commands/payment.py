from models import storage
from models.misc import Auth, Utilities
from models.payments import Payment
from models.users import User


class PaymentRoutes:
    """
    Routes for managing payments and
    All payment related commands are defined here.
    """

    # /earnings command
    @Auth.authorized_user
    async def show_earnings(self, event):
        """
        Show total earnings from all payments.
        Includes payments and refunds from all users in INR.
        :param event: Event object.
        :return: None
        """

        all_payments = storage.all("Payment")
        total_earnings = sum(payment.amount for payment in all_payments.values())
        await event.respond(f"💰 **Total Earnings:** `{total_earnings:.2f} INR`")

    @Auth.authorized_user
    async def payment_history(self, event):
        """
        Show payment history for a user.
        Shows all payments made by a user including refunds.
        :param event: Event object.
        :return: None
        """

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
        """
        Credit payment to a user.
        Add a payment to a user's balance.
        :param event: Event object.
        :return: None
        """

        args = event.message.text.split()
        if len(args) < 4:
            await event.respond(
                "❓ Usage: /credit_payment <username> <amount> <currency>\nFor example: `/credit_payment john 500 INR`"
            )
            return

        username = args[1]
        try:
            amount = float(args[2])
        except ValueError:
            await event.respond("❌ Invalid amount. Please provide a valid number.")
            return

        currency = args[3]

        user: User = storage.query_object("User", linux_username=username)
        if not user:
            await event.respond(f"❌ User `{username}` not found.")
            return

        if not user.rentals:
            await event.respond(f"❌ User `{username}` has no active rentals.")
            return

        payment = await Payment.create(
            user_id=user.id, amount=amount, currency=currency
        )

        amount = payment.amount

        # Update the user's balance with the new amount
        await user.update_balance(amount, "credit")
        payment.save()

        await event.respond(
            f"💳 Payment of `{payment.amount:.2f} {currency}` credited to `{username}`.\n"
            f"💰 **Available Balance:** `{user.balance:.2f} {currency}`"
        )

    @Auth.authorized_user
    async def debit_payment(self, event):
        """
        Refund payment to a user. Deduct payment from a user's balance.
        :param event: Event object.
        :return: None
        """

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
        except ValueError as e:
            await event.respond(
                f"❌ Insufficient balance.\n"
                f"💰 Available balance: `{user.balance:.2f}`"
            )
            return

        await event.respond(
            f"💳 Payment of `{amount:.2f} {currency}` debited from `{username}`.\n"
            f"💰 **Available Balance:** `{user.balance:.2f} INR`"
        )
