import os
import sys

import dotenv


def check_env():
    if (
        not os.getenv("API_ID")
        or not os.getenv("API_HASH")
        or not os.getenv("BOT_TOKEN")
        or not os.getenv("ADMIN_ID")
    ):
        raise Exception(
            "Bot Environment variables are not set. Please set them in .env file."
        )
    if not os.getenv("SSH_PORT") or not os.getenv("SSH_HOSTNAME"):
        raise Exception(
            "SSH Environment variables are not set. Please set them in .env file."
        )

    if not os.getenv("GROUP_ID"):
        # Raise warning if GROUP_ID is not set
        print("Warning: GROUP_ID is not set in .env file. Continuing without it.")

    if not os.getenv("DB_STRING"):
        print("Error: DB_STRING is not set in .env file. Exiting...")
        sys.exit(1)


dotenv.load_dotenv()
check_env()

TIME_ZONE = "Asia/Kolkata"

# Take data from the notes.txt file
try:
    BE_NOTED_TEXT = open("notes.txt", "r").read()
except FileNotFoundError:
    BE_NOTED_TEXT = ""
SSH_PORT = os.getenv("SSH_PORT")
SSH_HOSTNAME = os.getenv("SSH_HOSTNAME")

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
GROUP_ID = int(os.getenv("GROUP_ID", 0))
EXCHANGE_API_ID = os.getenv("EXCHANGE_API_ID", "")
DB_STRING = os.getenv("DB_STRING")

ADJECTIVES = [
    "crazy",
    "sunny",
    "happy",
    "wild",
    "quick",
    "witty",
    "jolly",
    "zany",
    "lazy",
    "sleepy",
    "dopey",
    "grumpy",
    "bashful",
    "sneezy",
    "curly",
]
NOUNS = [
    "cat",
    "evening",
    "river",
    "breeze",
    "mountain",
    "ocean",
    "sun",
    "moon",
    "tree",
    "flower",
    "star",
    "space",
    "forest",
    "meadow",
    "rain",
    "snow",
    "wind",
]
