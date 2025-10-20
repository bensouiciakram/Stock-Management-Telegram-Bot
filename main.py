

import asyncio
from utils.database import init_db
from telegram import Update,InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, ContextTypes,CallbackQueryHandler
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
from utils.bot import (
    ClientCommands,
    AdminCommands,
    NutCommands,
    RequestCommands
)

client_cmds = ClientCommands(ClientDbService('clients'))
admin_cmds = AdminCommands(AdminDbService('admins'))
nut_cmds = NutCommands(NutDbService('nuts'))
request_cmds = RequestCommands(RequestDbService('requests'))

async def main():
    await init_db()

    app = Application.builder().token(TOKEN).build()

    # Client commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add_client", client_cmds.add_cmd))
    app.add_handler(CommandHandler("list_clients", client_cmds.list_cmd))
    app.add_handler(CommandHandler("update_credit", client_cmds.update_credit_cmd))

    # Nut commands
    app.add_handler(CommandHandler("add_nut", nut_cmds.add_cmd))
    app.add_handler(CommandHandler("list_nuts", nut_cmds.list_cmd))

    # Admin commands
    app.add_handler(CommandHandler("add_admin", admin_cmds.add_cmd))

    # Request commands
    app.add_handler(CommandHandler("add_request", request_cmds.add_cmd))
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