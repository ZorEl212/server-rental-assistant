import asyncio
import random

class Auth:
    # --- Authorization ---
    @staticmethod
    def is_authorized_user(user_id):
        return user_id == ADMIN_ID

    @staticmethod
    def authorized_user(func):
        async def wrapper(self, event, *args, **kwargs):
            # Check if the sender is authorized
            if not Auth.is_authorized_user(event.sender_id):
                await event.respond("❌ You are not authorized to use this command.")
                return
            # Proceed with the original function
            return await func(self, event, *args, **kwargs)

        return wrapper
