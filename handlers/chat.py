from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext

from database.db import get_live_chat, delete_live_chat, is_admin, get_all_admins
from states.states import AdminStates

router = Router()


# ── رسائل العميل أثناء المحادثة المباشرة ─────────────────

@router.message(F.text & ~F.text.startswith("/"))
async def relay_user_message(message: types.Message, bot: Bot, state: FSMContext):
    user_id = message.from_user.id

    # لو أدمن وشغال في شات
    current_state = await state.get_state()
    if current_state == AdminStates.chatting_with_user:
        data = await state.get_data()
        target_user = data.get("chatting_with")
        if target_user:
            try:
                await bot.send_message(
                    target_user,
                    f"📨 *رسالة من الإدارة:*\n\n{message.text}",
                    parse_mode="Markdown"
                )
                await message.answer("✅ تم الإرسال")
            except Exception:
                await message.answer("⚠️ تعذّر الإرسال للعميل.")
        return

    # لو مستخدم عادي وعنده شات نشط
    if await is_admin(user_id):
        return

    chat = await get_live_chat(user_id)
    if chat and chat[1] == "active":
        admins = await get_all_admins()
        username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.full_name
        for admin_id in admins:
            try:
                await bot.send_message(
                    admin_id,
                    f"💬 *رسالة من العميل* {username} (`{user_id}`):\n\n{message.text}",
                    parse_mode="Markdown"
                )
            except Exception:
                pass
