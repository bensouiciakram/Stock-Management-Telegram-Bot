from telegram import  Update
from telegram.ext import ContextTypes,CallbackQueryHandler, ConversationHandler
from utils.command.base import BaseCommand
from utils.database import AdminDbService
from utils.config import MAIN_ADMIN_ID


class AdminCommands(BaseCommand):

    def __init__(self,admin_db:AdminDbService):
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
        