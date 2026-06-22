from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from database.db import get_live_chat, delete_live_chat, get_all_admins, is_admin
from states.states import AdminStates

router = Router()


@router.message(AdminStates.chatting_with_user)
async def admin_chat_send(message: types.Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    user_id = data.get("chatting_with")
    if not user_id:
        return
    try:
        await bot.copy_message(user_id, message.chat.id, message.message_id)
    except Exception:
        await message.answer("⚠️ لم يتمكن البوت من إرسال الرسالة.")


@router.message(F.text)
async def user_chat_relay(message: types.Message, bot: Bot):
    """يحوّل رسائل المستخدم للأدمن لو في محادثة نشطة"""
    if await is_admin(message.from_user.id):
        return
    chat = await get_live_chat(message.from_user.id)
    if not chat or chat[1] != "active":
        return

    admins = await get_all_admins()
    for admin_id in admins:
        try:
            await bot.copy_message(admin_id, message.chat.id, message.message_id)
        except Exception:
            pass
