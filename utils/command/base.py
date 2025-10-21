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
    AdminDbService,
    ClientDbService,
    NutDbService,
    RequestDbService
)

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

    
    async def update_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Each subclass must implement the 'update' command."""
        pass

    # @abstractmethod
    def define_states(self) -> dict:
        """Each subclass must implement the 'define_states' for interaction """
        self.states = {}

    async def handle_add_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if context.args:
            return await self.add_cmd(update, context)
        return await self.start_interactive(update, context)
    
    async def handle_update_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if context.args:
            return await self.update_cmd(update, context)
        return await self.start_interactive(update, context)
    
    async def start_interactive(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            CallbackQueryHandler(self.start_interactive, pattern=f'^add_{self.model_name}$')
        ],
        states={
            key:[MessageHandler(filters.TEXT & ~filters.COMMAND, callback)]
            for key,callback in self.states.items()
        },
        fallbacks=[CommandHandler('cancel', self.cancel)],
        allow_reentry=True
    )

    def generate_update_conversation_handler(self):
        return ConversationHandler(
        entry_points=[
            CommandHandler(f'update_credit', self.handle_update_command),
            CallbackQueryHandler(self.start_interactive, pattern=f'^update_credit$')
        ],
        states={
            key:[MessageHandler(filters.TEXT & ~filters.COMMAND, callback)]
            for key,callback in self.update_states.items()
        },
        fallbacks=[CommandHandler('cancel', self.cancel)],
        allow_reentry=True
    )

