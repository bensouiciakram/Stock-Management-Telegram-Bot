import os
import asyncio
from abc import ABC, abstractmethod
from telegram import Update,InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, ContextTypes,CallbackQueryHandler
from utils.config import (
    HELP_TEXT,
    TOKEN,
    MAIN_ADMIN_ID
)

from utils.database import (
    BaseDbService as AdminDbService,
    ClientDbService,
    NutDbService,
    RequestDbService
)

# ---------- CLIENT COMMANDS ----------
class BaseCommand(ABC):
    """Abstract base class for all bot command groups."""

    def __init__(self, db_service):
        self.db = db_service

    async def send_message(self, update: Update, text: str):
        """Common helper to send messages safely."""
        if update.message:
            await update.message.reply_text(text)
        elif update.callback_query:
            await update.callback_query.message.reply_text(text)

    @abstractmethod
    async def add_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Each subclass must implement the 'add' command."""
        pass

    @abstractmethod
    async def list_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Each subclass must implement the 'list' command."""
        pass



class ClientCommands(BaseCommand):
    def __init__(self, client_db:ClientDbService):
        super().__init__(client_db)

    async def add_cmd(self, update, context):
        if len(context.args) < 1:
            return await self.send_message(update, "Usage: /add_client <name> [credit]")
        
        name = context.args[0]
        credit = float(context.args[1]) if len(context.args) > 1 else 0
        await self.db.add(name=name, credit=credit)
        await self.send_message(update, f"✅ Client '{name}' added with credit {credit}.")

    async def list_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        clients = await self.db.list()
        if not clients:
            return await self.send_message(update, "No clients found.")
        
        text = "\n".join([f"{id}. {name} — 💰 {credit}" for id, name, credit in clients])
        await self.send_message(update, text)

    async def update_credit_cmd(self,update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 2:
            return await self.send_message(update,"Usage: /update_credit <client_name> <amount>")
        
        name = context.args[0]
        amount = float(context.args[1])
        client = await self.db.get(name)
        if not client:
            return await self.send_message(update,"Client not found.")
        
        await self.db.update(client[0], amount)
        await self.send_message(update,f"✅ Updated {name}'s credit by {amount:+}. New total: {client[2] + amount}")


class NutCommands(BaseCommand):
    def __init__(self, nut_db):
        super().__init__(nut_db)

    async def add_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 1:
            return await self.send_message(update, "Usage: /add_nut <nut_name> [packages]")
        
        name = context.args[0]
        packages = int(context.args[1]) if len(context.args) > 1 else 0
        await self.db.add(name=name, packages=packages)
        await self.send_message(update, f"🥜 Nut '{name}' added with {packages} packages.")

    async def list_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        nuts = await self.db.list()
        if not nuts:
            return await self.send_message(update, "No nuts found.")
        
        text = "\n".join([f"{id}. {name} — 📦 {packages} packages" for id, name, packages in nuts])
        await self.send_message(update, text)

class AdminCommands(BaseCommand):

    def __init__(self,admin_db):
        super().__init__(admin_db)

    async def add_cmd(self,update:Update,context:ContextTypes.DEFAULT_TYPE):
        """Only MAIN_ADMIN_ID can add new admins."""
        if str(update.effective_user.id) != str(MAIN_ADMIN_ID):
            return await self.send_message(update,"❌ You are not authorized to add admins.")

        if len(context.args) < 1:
            return await self.send_message(update,"Usage: /add_admin <admin_name>")

        name = " ".join(context.args)
        await self.db.add(name)
        await self.send_message(update,f"✅ Admin '{name}' added successfully.")

    async def list_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        admins = await self.db.list()
        if not admins:
            return await self.send_message(update, "No admins found.")
        
        text = "\n".join([f"{id}. {name}" for id, name in admins])
        await self.send_message(update, text)
        
        
class RequestCommands(BaseCommand):

    def __init__(self,request_db):
        super().__init__(request_db)
        self.nuts_db = NutDbService('nuts')

    async def add_cmd(self,update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Predefined admins only:
        /add_request <nut_name> <packages> <credit_paid> [description]
        """
        # Check args
        if len(context.args) < 3:
            return await self.send_message(update,"Usage: /add_request <nut_name> <packages> <credit_paid> [description]")

        # Identify the user (admin) by their full name
        admin_name = update.effective_user.full_name

        # Verify admin is predefined in DB
        admin = await self.db.get(admin_name)
        if not admin:
            return await self.send_message(update,"❌ You are not authorized to make requests. Contact the main admin to be added.")

        # Parse arguments
        nut_name = context.args[0]
        try:
            packages = int(context.args[1])
        except ValueError:
            return await self.send_message(update,"❌ Invalid packages value. Use an integer.")
        try:
            credit_paid = float(context.args[2])
        except ValueError:
            return await self.send_message(update,"❌ Invalid credit_paid value. Use a number.")

        description = " ".join(context.args[3:]) if len(context.args) > 3 else ""

        # Ensure nut exists
        nut = await self.nuts_db.get(nut_name)
        if not nut:
            return await self.send_message(update,"❌ Nut not found. Add it first with /add_nut.")

        # Insert request (admin[0] is admin id, nut[0] is nut id)
        await self.db.add(admin[0], nut[0], packages, credit_paid, description)

        await self.send_message(update,
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

    async def list_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        requests = await self.db.list()
        if not requests:
            return await self.send_message(update,"No requests found.")
        
        text = "\n".join([
            f"{id}. 👤 {admin} | 🥜 {nut} | 📦 {packages} | 💰 {credit_paid} | 📝 {description or '-'}"
            for id, admin, nut, packages, credit_paid, description in requests
        ])
        await self.send_message(update,text)





