import re
from typing import Dict

from telethon import TelegramClient, events

from resources.constants import API_HASH, API_ID, BOT_TOKEN


class BotManager:
    """
    Class to manage the Telegram bot.
        This class is responsible for handling commands and callbacks sent to the bot.
    """

    __client: TelegramClient = None

    def __init__(self, routes, callbacks, client=None):
        self.__client = (
            TelegramClient("server_plan_bot", API_ID, API_HASH)
            if not client
            else client
        )
        self.ROUTES: Dict = routes
        self.CALLBACKS: Dict = callbacks

    async def start(self):
        """
        Start the Telegram bot.
            Initialize the bot and start listening for events.
            The bot will be started and will run until disconnected.
        :return: None
        """

        await self.__client.start(bot_token=BOT_TOKEN)
        self.__client.add_event_handler(
            self.command_handler, events.NewMessage(pattern="/")
        )
        self.__client.add_event_handler(
            self.callback_handler, events.CallbackQuery(pattern=re.compile(r".*"))
        )
        print("Bot is running...")
        await self.__client.run_until_disconnected()

    @property
    def client(self):
        """
        Get the Telegram client.
        :return: the Telegram client instance
        """

        return self.__client

    async def command_handler(self, event):
        """
        Handle commands sent to the bot.
            This method will parse the command and call the appropriate handler.
        :param event: the event containing the command
        :return: None
        """

        command = event.message.text.split()[0]
        handler = self.ROUTES.get(command)
        if handler:
            await handler(event)
        else:
            await event.respond("Unknown command. Type /help for available commands.")

    async def callback_handler(self, event):
        """
        Handle callbacks sent to the bot.
            This method will parse the callback and call the appropriate handler.
        :param event: the event containing the callback
        :return: None
        """

        command = event.data.split()[0].decode("utf-8")
        handler = self.CALLBACKS.get(command)
        if handler:
            await handler(event)
