from telegram import  Update
from telegram.ext import ContextTypes,CallbackQueryHandler, ConversationHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from utils.command.base import BaseCommand
from utils.database import ClientDbService,NutDbService,AdminDbService,RequestDbService
from utils.config import MAIN_ADMIN_ID


class RequestCommands(BaseCommand):

    def __init__(self,request_db:RequestDbService):
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

        # Insert request as pending (approved=0) and notify MAIN_ADMIN_ID with approval buttons
        request_id = await self.db.add(
            admin_id=admin[0],
            nut_id=nut[0],
            packages=packages,
            credit_paid=credit_paid,
            description=description,
            requester_id=update.effective_user.id,
            approved=0,
        )

        
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton('✅ Approve', callback_data=f'request:approve:{request_id}'),
            InlineKeyboardButton('❌ Reject', callback_data=f'request:reject:{request_id}')
        ]])

        if MAIN_ADMIN_ID:
            await context.bot.send_message(
                chat_id=MAIN_ADMIN_ID,
                text=(
                    f"📩 New request from {admin_name}\n"
                    f"Nut: {nut_name}\n"
                    f"Packages: {packages}\n"
                    f"Credit Paid: {credit_paid}\n"
                    f"Note: {description or '-'}"
                ),
                reply_markup=kb
            )

        await self.send_message(update, "✅ Your request has been recorded and is pending approval.")

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

        # Insert pending request and notify main admin
        request_id = await self.db.add(
            admin_id=admin[0],
            nut_id=nut[0],
            packages=packages,
            credit_paid=credit_paid,
            description=description,
            approved=0,
            requester_id=update.effective_user.id,
        )

        
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton('✅ Approve', callback_data=f'request:approve:{request_id}'),
            InlineKeyboardButton('❌ Reject', callback_data=f'request:reject:{request_id}')
        ]])

        if MAIN_ADMIN_ID:
            await context.bot.send_message(
                chat_id=MAIN_ADMIN_ID,
                text=(
                    f"📩 New request from {admin_name}\n"
                    f"Nut: {nut_name}\n"
                    f"Packages: {packages}\n"
                    f"Credit Paid: {credit_paid}\n"
                    f"Note: {description or '-'}"
                ),
                reply_markup=kb
            )

        await self.send_message(update, f"✅ Request recorded by {admin_name} and is pending approval.")

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
            for id, admin, nut, packages, credit_paid, description,_,_ in requests
        ])
        await self.send_message(update,text)

    async def handle_request_decision(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle approve/reject callbacks from the main admin."""
        query = update.callback_query
        await query.answer()
        data = query.data  # format: request:approve:<id> or request:reject:<id>

        parts = data.split(":")
        if len(parts) != 3:
            await query.edit_message_text("❌ Invalid action.")
            return

        action, req_id_str = parts[1], parts[2]
        try:
            req_id = int(req_id_str)
        except ValueError:
            await query.edit_message_text("❌ Invalid request id.")
            return

        # fetch request row
        req_row = await self.db.get_by_id(req_id)
        if not req_row:
            await query.edit_message_text("⚠️ This request was not found.")
            return

        # BaseDbService.get_by_id returns full row; columns are: id, admin_id, nut_id, packages, credit_paid, description, requester_id, approved
        _, admin_id, nut_id, packages, credit_paid, description, requester_id, approved = req_row

        # resolve names for messages
        admin = await self.admins_db.get_by_id(admin_id) if hasattr(self.admins_db, 'get_by_id') else None
        nut = await self.nuts_db.get_by_id(nut_id) if hasattr(self.nuts_db, 'get_by_id') else None
        admin_name = admin[1] if admin else 'Unknown'
        nut_name = nut[1] if nut else 'Unknown'

        # use stored requester_id (telegram chat id) to notify requester
        requester_chat_id = requester_id

        if action == 'approve':
            # set approved flag
            if hasattr(self.db, 'set_approved'):
                await self.db.set_approved(req_id, True)
            else:
                await self.db.update_by_id(req_id, approved=1)

            await query.edit_message_text(f"✅ Request approved by {update.effective_user.full_name} — {packages} × {nut_name} (paid: {credit_paid}).")
            # notify requester
            try:
                await context.bot.send_message(chat_id=requester_chat_id, text=f"✅ Your request for {packages} × {nut_name} was approved.")
            except Exception:
                pass
        else:
            # rejected: set approved to 0 explicitly and notify
            if hasattr(self.db, 'set_approved'):
                await self.db.set_approved(req_id, False)
            else:
                await self.db.update_by_id(req_id, approved=0)

            await query.edit_message_text(f"❌ Request rejected by {update.effective_user.full_name}.")
            try:
                await context.bot.send_message(chat_id=requester_chat_id, text=f"❌ Your request for {packages} × {nut_name} was rejected.")
            except Exception:
                pass


