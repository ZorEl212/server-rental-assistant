import typing
from typing import Dict

from telethon import TelegramClient, events

from resources.constants import API_HASH, API_ID, BOT_TOKEN


class BotManager:
    __client: TelegramClient = None

    def __init__(self, routes, client=None):
        self.__client = (
            TelegramClient("server_plan_bot", API_ID, API_HASH)
            if not client
            else client
        )
        self.ROUTES: Dict = routes

    def start(self):
        self.__client.start(bot_token=BOT_TOKEN)
        self.__client.add_event_handler(
            self.command_handler, events.NewMessage(pattern="/")
        )
        print("Bot is running...")
        self.__client.run_until_disconnected()

    @property
    def client(self):
        return self.__client

    async def command_handler(self, event):
        command = event.message.text.split()[0]
        handler = self.ROUTES.get(command)
        if handler:
            await handler(event)
        else:
            await event.respond("Unknown command. Type /help for available commands.")
