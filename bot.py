import os
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database import *


# Getting config from environment variables
TOKEN = os.environ.get('TOKEN')
MAIN_ADMIN_ID = os.environ.get('MAIN_ADMIN_ID')


# ---------- BASIC ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🥜 Welcome to the Nuts Credit Manager Bot!")


# ---------- CLIENT COMMANDS ----------
async def add_client_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        return await update.message.reply_text("Usage: /add_client <name> [credit]")
    
    name = context.args[0]
    credit = float(context.args[1]) if len(context.args) > 1 else 0
    await add_client(name, credit)
    await update.message.reply_text(f"✅ Client '{name}' added with credit {credit}.")


async def list_clients(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clients = await get_clients()
    if not clients:
        return await update.message.reply_text("No clients found.")
    
    text = "\n".join([f"{id}. {name} — 💰 {credit}" for id, name, credit in clients])
    await update.message.reply_text(text)


async def update_credit_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        return await update.message.reply_text("Usage: /update_credit <client_name> <amount>")
    
    name = context.args[0]
    amount = float(context.args[1])
    client = await get_client_by_name(name)
    if not client:
        return await update.message.reply_text("Client not found.")
    
    await update_credit(client[0], amount)
    await update.message.reply_text(f"✅ Updated {name}'s credit by {amount:+}. New total: {client[2] + amount}")


# ---------- NUT COMMANDS ----------
async def add_nut_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        return await update.message.reply_text("Usage: /add_nut <nut_name> [packages]")
    
    name = context.args[0]
    packages = int(context.args[1]) if len(context.args) > 1 else 0
    await add_nut(name, packages)
    await update.message.reply_text(f"🥜 Nut '{name}' added with {packages} packages.")


async def list_nuts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nuts = await get_nuts()
    if not nuts:
        return await update.message.reply_text("No nuts found.")
    
    text = "\n".join([f"{id}. {name} — 📦 {packages} packages" for id, name, packages in nuts])
    await update.message.reply_text(text)

# ---------- ADD ADMIN -------------
async def add_admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Only MAIN_ADMIN_ID can add new admins."""
    if str(update.effective_user.id) != str(MAIN_ADMIN_ID):
        return await update.message.reply_text("❌ You are not authorized to add admins.")

    if len(context.args) < 1:
        return await update.message.reply_text("Usage: /add_admin <admin_name>")

    name = " ".join(context.args)
    await add_admin(name)
    await update.message.reply_text(f"✅ Admin '{name}' added successfully.")


# ---------- ADMIN REQUEST COMMAND ----------
async def add_request_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Predefined admins only:
    /add_request <nut_name> <packages> <credit_paid> [description]
    """
    # Check args
    if len(context.args) < 3:
        return await update.message.reply_text("Usage: /add_request <nut_name> <packages> <credit_paid> [description]")

    # Identify the user (admin) by their full name
    admin_name = update.effective_user.full_name

    # Verify admin is predefined in DB
    admin = await get_admin_by_name(admin_name)
    if not admin:
        return await update.message.reply_text("❌ You are not authorized to make requests. Contact the main admin to be added.")

    # Parse arguments
    nut_name = context.args[0]
    try:
        packages = int(context.args[1])
    except ValueError:
        return await update.message.reply_text("❌ Invalid packages value. Use an integer.")
    try:
        credit_paid = float(context.args[2])
    except ValueError:
        return await update.message.reply_text("❌ Invalid credit_paid value. Use a number.")

    description = " ".join(context.args[3:]) if len(context.args) > 3 else ""

    # Ensure nut exists
    nut = await get_nut_by_name(nut_name)
    if not nut:
        return await update.message.reply_text("❌ Nut not found. Add it first with /add_nut.")

    # Insert request (admin[0] is admin id, nut[0] is nut id)
    await add_request(admin[0], nut[0], packages, credit_paid, description)

    await update.message.reply_text(
        f"✅ Request recorded by {admin_name} for {packages} × {nut_name} (paid: {credit_paid})."
    )

    # Notify main admin if set
    if MAIN_ADMIN_ID:
        await context.bot.send_message(
            chat_id=MAIN_ADMIN_ID,
            text=(
                f"📩 New request from {admin_name}\n"
                f"Nut: {nut_name}\n"
                f"Packages: {packages}\n"
                f"Credit Paid: {credit_paid}\n"
                f"Note: {description or '-'}"
            )
        )


async def list_requests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    requests = await get_requests()
    if not requests:
        return await update.message.reply_text("No requests found.")
    
    text = "\n".join([
        f"{id}. 👤 {admin} | 🥜 {nut} | 📦 {packages} | 💰 {credit_paid} | 📝 {description or '-'}"
        for id, admin, nut, packages, credit_paid, description in requests
    ])
    await update.message.reply_text(text)


# ---------- MAIN ----------
# async def main():
#     await init_db()
#     app = Application.builder().token(TOKEN).build()

#     # Client commands
#     app.add_handler(CommandHandler("start", start))
#     app.add_handler(CommandHandler("add_client", add_client_cmd))
#     app.add_handler(CommandHandler("list_clients", list_clients))
#     app.add_handler(CommandHandler("update_credit", update_credit_cmd))

#     # Nut commands
#     app.add_handler(CommandHandler("add_nut", add_nut_cmd))
#     app.add_handler(CommandHandler("list_nuts", list_nuts))

#     # Admin commands
#     app.add_handler(CommandHandler("add_admin", add_admin_cmd))

#     # Request commands
#     app.add_handler(CommandHandler("add_request", add_request_cmd))
#     app.add_handler(CommandHandler("list_requests", list_requests))

#     print("🤖 Bot is running...")
#     # await app.run_polling()
#     async with app :
#         await app.initialize()
#         await app.start()
#         await app.updater.start_polling()
#         await init_db()

#     # await app.updater.start_{webhook, polling}()
#     # # Start other asyncio frameworks here
#     # # Add some logic that keeps the event loop running until you want to shutdown
#     # # Stop the other asyncio frameworks here
#     # await app.updater.stop()
#     # await app.stop()
#     # await app.shutdown()

# if __name__ == "__main__":
#     asyncio.run(main())

async def main():
    await init_db()

    app = Application.builder().token(TOKEN).build()

    # Client commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add_client", add_client_cmd))
    app.add_handler(CommandHandler("list_clients", list_clients))
    app.add_handler(CommandHandler("update_credit", update_credit_cmd))

    # Nut commands
    app.add_handler(CommandHandler("add_nut", add_nut_cmd))
    app.add_handler(CommandHandler("list_nuts", list_nuts))

    # Admin commands
    app.add_handler(CommandHandler("add_admin", add_admin_cmd))

    # Request commands
    app.add_handler(CommandHandler("add_request", add_request_cmd))
    app.add_handler(CommandHandler("list_requests", list_requests))

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