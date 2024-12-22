from models import storage
from models.misc import Auth, Utilities, SystemUserManager

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

