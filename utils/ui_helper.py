from telegram import Update,InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, ContextTypes,CallbackQueryHandler
from utils.database import (
    BaseDbService as AdminDbService,
    ClientDbService,
    NutDbService,
    RequestDbService
)

from utils.bot import (
    ClientCommands,
    AdminCommands,
    NutCommands,
    RequestCommands
)

# initialisations:
client_cmds = ClientCommands(ClientDbService('client'))
admin_cmds = AdminCommands(AdminDbService('admin'))
nut_cmds = NutCommands(NutDbService('nut'))
request_cmds = RequestCommands(RequestDbService('request'))

HELP_TEXT = """*
🧭 *Available Commands*

👤 *Client Commands*
• `/start` — Start the bot and receive a welcome message
• `/add_client <name> [credit]` — Add a new client (optional starting credit)
• `/list_clients` — View all clients
• `/update_credit <client_name> <amount>` — Update a client's credit balance

🥜 *Nut Commands*
• `/add_nut <nut_name> [packages]` — Add a new type of nut (optional package count)
• `/list_nuts` — View all nut types

🧑‍💼 *Admin Commands* (Main admin only)
• `/add_admin <admin_name>` — Add a new admin
• `/list_admins` — View all admins

📦 *Request Commands*
• `/add_request <nut_name> <packages> <credit_paid> [description]` — Record a new request
• `/list_requests` — View all requests

💡 *Example Usage:*
• `/add_client John 500` — Adds a client named John with 500 credit
"""


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "add_client":
        await query.edit_message_text("Use `/add_client <name> [credit]`", parse_mode="Markdown")
    elif data == "list_clients":
        await client_cmds.list_cmd(update, context)
    elif data == "update_credit":
        await query.edit_message_text("Use `/update_credit <client_name> <amount>`", parse_mode="Markdown")
    elif data == "add_nut":
        await query.edit_message_text("Use `/add_nut <nut_name> [packages]`", parse_mode="Markdown")
    elif data == "list_nuts":
        await nut_cmds.list_cmd(update, context)
    elif data == "add_admin":
        await query.edit_message_text("Use `/add_admin <admin_name>`", parse_mode="Markdown")
    elif data == "list_admins":
        await admin_cmds.list_cmd(update, context)
    elif data == "add_request":
        await query.edit_message_text("Use `/add_request <nut_name> <packages> <credit_paid> [description]`", parse_mode="Markdown")
    elif data == "list_requests":
        await request_cmds.list_cmd(update, context)
    elif data == "help":
        await help_cmd(update, context)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.message.reply_text(HELP_TEXT, parse_mode="MarkdownV2")



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("➕ Add Client", callback_data="add_client"),
            InlineKeyboardButton("📋 List Clients", callback_data="list_clients")
        ],
        [
            InlineKeyboardButton("💸 Update Credit", callback_data="update_credit"),
            InlineKeyboardButton("🥜 Add Nut", callback_data="add_nut")
        ],
        [
            InlineKeyboardButton("📦 List Nuts", callback_data="list_nuts"),
            InlineKeyboardButton("🧑‍💼 Add Admin", callback_data="add_admin")
        ],
        [
            InlineKeyboardButton("📋 List Admins", callback_data="list_admins"),
            InlineKeyboardButton(" Add Request", callback_data="add_request")
        ],
        [
            InlineKeyboardButton("📜 List Requests", callback_data="list_requests"),
            InlineKeyboardButton("❓ Help", callback_data="help")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text("🥜 Welcome to the Nuts Credit Manager Bot!\n\n")
    HELP_TEXT
    await update.message.reply_text(
        HELP_TEXT+'\n\nChoose a command:',
        reply_markup=reply_markup
    )