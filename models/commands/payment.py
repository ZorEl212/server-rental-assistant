from models import storage
from models.misc import Auth, Utilities


class PaymentRoutes:
    # /earnings command
    @Auth.authorized_user
    async def show_earnings(self, event):
        all_payments = storage.all("Payment")
        total_earnings = sum(payment.amount for payment in all_payments)
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
