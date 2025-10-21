

import asyncio
from utils.database import init_db
from telegram import Update,InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, ContextTypes,CallbackQueryHandler, ConversationHandler, MessageHandler, filters
from utils.config import TOKEN
from utils.ui_helper import (
    button_handler,
    help_cmd,
    start
)
from utils.database import (
    BaseDbService as AdminDbService,
    ClientDbService,
    NutDbService,
    RequestDbService
)
from utils.command import (
    ClientCommands,
    AdminCommands,
    NutCommands,
    RequestCommands
)

client_cmds = ClientCommands(ClientDbService('client'))
admin_cmds = AdminCommands(AdminDbService('admin'))
nut_cmds = NutCommands(NutDbService('nut'))
request_cmds = RequestCommands(RequestDbService('request'))

async def main():
    await init_db()

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    # Client commands
    conv_handler = client_cmds.generate_add_conversation_handler()
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("list_clients", client_cmds.list_cmd))
    app.add_handler(CommandHandler("update_credit", client_cmds.update_credit_cmd))

    # Nut commands
    app.add_handler(nut_cmds.generate_add_conversation_handler())
    app.add_handler(CommandHandler("list_nuts", nut_cmds.list_cmd))

    # Admin commands
    app.add_handler(admin_cmds.generate_add_conversation_handler())
    app.add_handler(CommandHandler("list_admins", admin_cmds.list_cmd))

    # Request commands
    app.add_handler(request_cmds.generate_add_conversation_handler())
    app.add_handler(CommandHandler("list_requests", request_cmds.list_cmd))

    # help commands: 
    app.add_handler(CommandHandler('help',help_cmd))

    app.add_handler(CallbackQueryHandler(button_handler))

    # ---- Manual control ----
    await app.initialize()
    await app.start()
    print("🤖 Bot is running...")

    # Keeps the bot running forever until you stop it
    await app.updater.start_polling()
    try:
        await asyncio.Future()  # run forever
    except KeyboardInterrupt:
        pass
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())