from telegram import  Update
from telegram.ext import ContextTypes,CallbackQueryHandler, ConversationHandler
from utils.command.base import BaseCommand
from utils.database import ClientDbService


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
