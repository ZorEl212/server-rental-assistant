"""
This module sets up and initializes the server plan bot using the Telethon library.

The bot interacts with users and handles commands related to user management, payment management,
plan management, and system operations. It leverages the `DBStorage` class for database interactions
and organizes the commands into different modules for better separation of concerns.

Key Components:
----------------
1. **DBStorage**: The storage engine that interacts with the database.
   - Initialized and reloaded to set up the database session for the bot.

2. **TelegramClient**: The Telethon client used to interact with the Telegram API.
   - The `TelegramClient` is initialized with `API_ID` and `API_HASH` from the `resources.constants` module.
   - The bot client is named `"server_plan_bot"`.

3. **BotManager**: The main bot controller that manages routing and command handling.
   - Responsible for delegating commands to the appropriate handler functions (from `UserRoutes`, `PlanRoutes`, etc.).

4. **Command Modules**:
   - **UserRoutes**: Handles user-related commands like creating, deleting, listing, linking, and unlinking users.
   - **PlanRoutes**: Handles commands related to plan management, including reducing, extending, and canceling plans.
   - **PaymentRoutes**: Manages commands related to payment history, earnings, and payments (credit/debit).
   - **SystemRoutes**: Provides system-level operations like generating reports, broadcasting messages, and managing connected users.
   - **JobManager**: Handles scheduled or system-level jobs (details of job management not shown).

5. **Routes**: A dictionary that maps commands (strings like "/start", "/help", etc.) to their respective handler functions.
   - Example: `/start` maps to `system_routes.start_command`.

6. **Callbacks**: A dictionary for callback handlers (used with inline keyboards, etc.).
   - Example: `"cancel"` maps to `plan_routes.handle_cancel`.

Initialization Process:
----------------------
- The `DBStorage` is initialized and reloaded to ensure a session with the database is active.
- The `TelegramClient` is created using the `API_ID` and `API_HASH` from the constants.
- Various route and callback handlers are instantiated to handle bot commands.
- The `BotManager` is initialized with the `client`, `routes`, and `callbacks` to manage the bot's behavior.

Usage:
------
Once this module is executed, the bot is ready to listen for commands from users on Telegram. The routes map user commands to specific methods, and the callback functions handle inline keyboard interactions.

Example Routes:
---------------
- `/start`: Displays the start command message from `system_routes.start_command`.
- `/help`: Displays the help message from `system_routes.help_command`.
- `/reduce_plan`: Reduces the plan from `plan_routes.reduce_plan`.
- `/extend_plan`: Extends the plan from `plan_routes.extend_plan`.
- `/create_user`: Creates a new user from `user_routes.create_user`.
- `/delete_user`: Deletes a user from `user_routes.delete_user_command`.

Example Callback:
-----------------
- `"cancel"`: Cancels an ongoing plan operation, handled by `plan_routes.handle_cancel`.
"""

import logging

from telethon import TelegramClient
from resources.constants import API_HASH, API_ID

client = TelegramClient("server_plan_bot", API_ID, API_HASH)
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,
    filename="server_plan_bot.log",
    encoding="utf-8",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

from models.engine.db_engine import DBStorage

# Initialization of DBStorage and the bot client
storage = DBStorage()
storage.reload()


# Importing command handlers
from models.commands.main_bot import BotManager
from models.commands.payment import PaymentRoutes
from models.commands.rental import PlanRoutes
from models.commands.system import JobManager, SystemRoutes
from models.commands.user import UserRoutes

# Initialize command handlers for different sections
user_routes = UserRoutes()
plan_routes = PlanRoutes()
payment_routes = PaymentRoutes()
job_manager = JobManager()
system_routes = SystemRoutes()

# Define routes mapping for bot commands
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
    "/credit": payment_routes.credit_payment,
    "/debit": payment_routes.debit_payment,
    "/run": system_routes.run_command,
    "/check_disk": system_routes.check_disk_usage,
    "/status": system_routes.user_status,
}

# Define callback mappings for inline keyboard actions
callbacks = {
    "cancel": plan_routes.handle_cancel,
    "clean_db": system_routes.handle_clean_db,
    "refresh_connected_users": system_routes.refresh_connected_users,
    "delete_user": user_routes.delete_user_command, # Callback for deleting a user
}

# Initialize the BotManager with client, routes, and callbacks
bot = BotManager(client=client, routes=routes, callbacks=callbacks)
