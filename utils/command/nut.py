from telegram import  Update
from telegram.ext import ContextTypes,CallbackQueryHandler, ConversationHandler
from utils.command.base import BaseCommand
from utils.database import NutDbService


class NutCommands(BaseCommand):
    def __init__(self, nut_db:NutDbService):
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