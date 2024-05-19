from funda import Funda
from telegram_bot import TelegramBot
import os
import sys
import re
from openai import OpenAI

MESSAGE_TEMPLATE = """
*%s*

[check out on funda](%s)
"""

ENV_FUNDA_DB = "FUNDA_DB"
ENV_TELEGRAM_TOKEN = "TELEGRAM_TOKEN"
ENV_CHAT_ID = "CHAT_ID"
ENV_SEARCH_URL = "SEARCH_URL"
ENV_OPENAI_API_KEY = "OPENAI_API_KEY"
if (
    ENV_FUNDA_DB not in os.environ
    or ENV_TELEGRAM_TOKEN not in os.environ
    or ENV_CHAT_ID not in os.environ
    or ENV_OPENAI_API_KEY not in os.environ
):
    print(
        f"ERROR: The following environment variables must be set: {ENV_FUNDA_DB}, {ENV_TELEGRAM_TOKEN}, {ENV_CHAT_ID},  {ENV_SEARCH_URL} and ENV_OPENAI_API_KEY",
        file=sys.stderr,
    )
    exit(1)

sqlite_location = os.environ[ENV_FUNDA_DB]
telegram_token = os.environ[ENV_TELEGRAM_TOKEN]
chat_id = os.environ[ENV_CHAT_ID]
search_url = os.environ[ENV_SEARCH_URL]
openai_api_key = os.environ[ENV_OPENAI_API_KEY]

openai_client = OpenAI(api_key=openai_api_key)

funda = Funda(sqlite_location, openai_client, search_url)
telegramBot = TelegramBot(chat_id, telegram_token)


newListing = funda.fetchNew()
for listing in newListing:
    print("scraper: sending message over telegram")
    summary = (
        listing.summary.replace("**", "*")
        .replace(".", "\\.")
        .replace(">", "\\>")
        .replace("<", "\\<")
        .replace("_", "\\_")
        .replace("-", "\\-")
        .replace("(", "\\(")
        .replace(")", "\\)")
        .replace("k\\.k\\.", "")
        .replace("!", "\\!")
    )

    message = MESSAGE_TEMPLATE % (summary, listing.link)
    telegramBot.postMessage(message)
