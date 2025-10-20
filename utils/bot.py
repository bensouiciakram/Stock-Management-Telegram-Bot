import os
import asyncio
from abc import ABC, abstractmethod
from telegram import Update,InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, ContextTypes,CallbackQueryHandler, ConversationHandler, MessageHandler, filters
from utils.config import (
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
        self.model_name = db_service.table_name
        self.define_states()
        self.states_keys = list(self.states.keys())

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

    @abstractmethod
    async def start_interactive_add(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Each subclass must implement the 'start_interactive_add' """
        pass

    # @abstractmethod
    def define_states(self) -> dict:
        """Each subclass must implement the 'define_states' for interaction """
        self.states = {}

    async def handle_add_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if context.args:
            return await self.add_cmd(update, context)
        return await self.start_interactive_add(update, context)
    
    async def start_interactive_add(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.message.reply_text(f"Please enter the {self.model_name}'s name:")\
                if not self.model_name == 'request' else\
                await update.callback_query.message.reply_text(f"Please enter the nut's name:")
        else:
            await self.send_message(update, f"Please enter the {self.model_name}'s name:")
        return self.states_keys[0]
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keys_to_remove = [k for k in context.user_data if self.model_name in k]
        for k in keys_to_remove:
            del context.user_data[k]
        await self.send_message(update, f"❌ Add {self.model_name} cancelled.")
        return ConversationHandler.END
    
    def generate_add_conversation_handler(self):
        return ConversationHandler(
        entry_points=[
            CommandHandler(f'add_{self.model_name}', self.handle_add_command),
            CallbackQueryHandler(self.start_interactive_add, pattern=f'^add_{self.model_name}$')
        ],
        states={
            key:[MessageHandler(filters.TEXT & ~filters.COMMAND, callback)]
            for key,callback in self.states.items()
        },
        fallbacks=[CommandHandler('cancel', self.cancel)],
        allow_reentry=True
    )


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

    def define_states(self):
        self.NAME, self.CREDIT = range(2)
        self.states = {
            self.NAME:self.receive_name,
            self.CREDIT:self.receive_credit
        }

    async def receive_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Receive the client's name and prompt for credit."""
        if not update.message or not update.message.text:
            await self.send_message(update, "❌ Invalid name. Please send the client's name as text.")
            return self.NAME

        name = update.message.text.strip()
        context.user_data['new_client_name'] = name
        await update.message.reply_text("Please enter starting credit (number). Send 0 for none:")
        return self.CREDIT

    async def receive_credit(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Receive credit amount, validate, create client and finish conversation."""
        if not update.message or not update.message.text:
            await self.send_message(update, "❌ Invalid credit. Please send a number.")
            return self.CREDIT

        text = update.message.text.strip()
        try:
            credit = float(text)
        except ValueError:
            await update.message.reply_text("❌ Invalid number. Please enter a valid credit amount (e.g. 100 or 0):")
            return self.CREDIT

        name = context.user_data.get('new_client_name')
        if not name:
            await update.message.reply_text("❌ Missing client name. Please start again with /add_client or the button.")
            return ConversationHandler.END

        await self.db.add(name=name, credit=credit)
        await update.message.reply_text(f"✅ Client '{name}' added with credit {credit}.")

        # cleanup
        context.user_data.pop('new_client_name', None)
        return ConversationHandler.END

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

    def define_states(self):
        # states: ask for nut name, then packages
        self.NAME, self.PACKAGES = range(2)
        self.states = {
            self.NAME: self.receive_name,
            self.PACKAGES: self.receive_packages
        }

    async def receive_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message or not update.message.text:
            await self.send_message(update, "❌ Invalid name. Please send the nut name as text.")
            return self.NAME

        name = update.message.text.strip()
        context.user_data['new_nut_name'] = name
        await update.message.reply_text("Please enter packages count (integer). Send 0 for none:")
        return self.PACKAGES

    async def receive_packages(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message or not update.message.text:
            await self.send_message(update, "❌ Invalid packages. Please send an integer.")
            return self.PACKAGES

        text = update.message.text.strip()
        try:
            packages = int(text)
        except ValueError:
            await update.message.reply_text("❌ Invalid number. Please enter a valid integer for packages (e.g. 10 or 0):")
            return self.PACKAGES

        name = context.user_data.get('new_nut_name')
        if not name:
            await update.message.reply_text("❌ Missing nut name. Please start again with /add_nut or the button.")
            return ConversationHandler.END

        await self.db.add(name=name, packages=packages)
        await update.message.reply_text(f"🥜 Nut '{name}' added with {packages} packages.")
        context.user_data.pop('new_nut_name', None)
        return ConversationHandler.END

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

    def define_states(self):
        # only need the admin name
        self.NAME = 0
        self.states = {self.NAME: self.receive_name}

    async def start_interactive_add(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Only allow main admin to add new admins interactively
        if str(update.effective_user.id) != str(MAIN_ADMIN_ID):
            return await self.send_message(update, "❌ You are not authorized to add admins.")
        return await super().start_interactive_add(update, context)

    async def receive_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message or not update.message.text:
            await self.send_message(update, "❌ Invalid name. Please send the admin's name as text.")
            return self.NAME

        name = update.message.text.strip()
        await self.db.add(name=name)
        await self.send_message(update, f"✅ Admin '{name}' added successfully.")
        return ConversationHandler.END

    async def list_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        admins = await self.db.list()
        if not admins:
            return await self.send_message(update, "No admins found.")
        
        text = "\n".join([f"{id}. {name}" for id, name in admins])
        await self.send_message(update, text)
        
        
class RequestCommands(BaseCommand):

    def __init__(self,request_db):
        super().__init__(request_db)
        self.nuts_db = NutDbService('nut')
        # Admins DB used to validate the admin making the request
        self.admins_db = AdminDbService('admin')

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
        admin = await self.admins_db.get(admin_name)
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

    def define_states(self):
        # states: nut name, packages, credit_paid, description
        self.NUT_NAME, self.PACKAGES, self.CREDIT_PAID, self.DESCRIPTION = range(4)
        self.states = {
            self.NUT_NAME: self.receive_nut_name,
            self.PACKAGES: self.receive_packages,
            self.CREDIT_PAID: self.receive_credit_paid,
            self.DESCRIPTION: self.receive_description
        }

    async def start_interactive_add(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Verify user is a predefined admin before starting the request flow
        admin_name = update.effective_user.full_name
        # Akram Brnsouici
        admin = await self.admins_db.get(name=admin_name)
        if not admin:
            return await self.send_message(update, "❌ You are not authorized to make requests. Contact the main admin to be added.")
        return await super().start_interactive_add(update, context)

    async def receive_nut_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message or not update.message.text:
            await self.send_message(update, "❌ Invalid nut name. Please send the nut name as text.")
            return self.NUT_NAME

        nut_name = update.message.text.strip()
        context.user_data['new_request_nut_name'] = nut_name
        await update.message.reply_text("Please enter number of packages (integer):")
        return self.PACKAGES

    async def receive_packages(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message or not update.message.text:
            await self.send_message(update, "❌ Invalid packages. Please send an integer.")
            return self.PACKAGES

        try:
            packages = int(update.message.text.strip())
        except ValueError:
            await update.message.reply_text("❌ Invalid number. Please enter an integer for packages:")
            return self.PACKAGES

        context.user_data['new_request_packages'] = packages
        await update.message.reply_text("Please enter credit paid (number):")
        return self.CREDIT_PAID

    async def receive_credit_paid(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message or not update.message.text:
            await self.send_message(update, "❌ Invalid credit. Please send a number.")
            return self.CREDIT_PAID

        try:
            credit_paid = float(update.message.text.strip())
        except ValueError:
            await update.message.reply_text("❌ Invalid number. Please enter a valid credit amount:")
            return self.CREDIT_PAID

        context.user_data['new_request_credit_paid'] = credit_paid
        await update.message.reply_text("Optional: enter a description or send /skip to leave blank:")
        return self.DESCRIPTION

    async def receive_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # description can be empty
        description = update.message.text.strip() if update.message and update.message.text else ""

        nut_name = context.user_data.get('new_request_nut_name')
        packages = context.user_data.get('new_request_packages')
        credit_paid = context.user_data.get('new_request_credit_paid')

        admin_name = update.effective_user.full_name
        admin = await self.admins_db.get(admin_name)
        if not admin:
            await self.send_message(update, "❌ You are not authorized to make requests. Contact the main admin to be added.")
            return ConversationHandler.END

        nut = await self.nuts_db.get(nut_name)
        if not nut:
            await self.send_message(update, "❌ Nut not found. Add it first with /add_nut.")
            return ConversationHandler.END

        await self.db.add(admin_id=admin[0],nut_id=nut[0],packages=packages,credit_paid=credit_paid, description=description)

        await self.send_message(update, f"✅ Request recorded by {admin_name} for {packages} × {nut_name} (paid: {credit_paid}).")

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

        # cleanup
        for k in ('new_request_nut_name', 'new_request_packages', 'new_request_credit_paid'):
            context.user_data.pop(k, None)
        return ConversationHandler.END

    async def list_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        requests = await self.db.list()
        if not requests:
            return await self.send_message(update,"No requests found.")
        
        text = "\n".join([
            f"{id}. 👤 {admin} | 🥜 {nut} | 📦 {packages} | 💰 {credit_paid} | 📝 {description or '-'}"
            for id, admin, nut, packages, credit_paid, description in requests
        ])
        await self.send_message(update,text)





