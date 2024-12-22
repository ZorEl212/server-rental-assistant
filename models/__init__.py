from models.engine.db_engine import DBStorage

from telethon import TelegramClient
from resources.constants import API_ID, API_HASH

storage = DBStorage()
storage.reload()

client = TelegramClient("server_plan_bot", API_ID, API_HASH)

from models.commands.user import UserRoutes
from models.commands.rental import PlanRoutes
from models.commands.payment import PaymentRoutes
from models.commands.system import SystemRoutes
from models.commands.main_bot import BotManager


user_routes = UserRoutes()
plan_routes = PlanRoutes()
payment_routes = PaymentRoutes()
system_routes = SystemRoutes()

routes = {
    "/start": system_routes.start_command,
    "/help": system_routes.help_command,
    "/reduce_plan": plan_routes.reduce_plan,
    "/extend_plan": plan_routes.extend_plan,
    "/create_user": user_routes.create_user,
    "/delete_user": user_routes.delete_user_command,
    "/list_users": user_routes.list_users,
    "/payment_history": payment_routes.payment_history,
    "/gen_report": system_routes.generate_report,
    "/broadcast": system_routes.broadcast,
    "/unlink_user": user_routes.clear_user,
    "/link_user": user_routes.link_user,
    "/who": system_routes.list_connected_users,
    "/earnings": payment_routes.show_earnings,
}

bot = BotManager(client=client, routes=routes)
