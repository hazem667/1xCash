from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext

from database.db import (
    get_live_chat, delete_live_chat, is_admin,
    get_all_admins, get_button_label, get_custom_buttons, get_setting
)
from handlers.keyboards import main_menu_keyboard
from states.states import AdminStates

router = Router()


@router.message(AdminStates.chatting_with_user)
async def admin_chat_relay(message: types.Message, state: FSMContext, bot: Bot):
    """الأدمن يبعت رسالة للعميل"""
    data = await state.get_data()
    target = data.get("chatting_with")
    if not target:
        return
    if message.text in ("❌ إنهاء", "/end"):
        await delete_live_chat(target)
        await state.clear()
        await message.answer("✅ تم إنهاء المحادثة.", reply_markup=admin_menu_keyboard())
        return
    try:
        await bot.send_message(target, f"📨 *رسالة من الإدارة:*\n\n{message.text}", parse_mode="Markdown")
        await message.answer("✅ تم الإرسال")
    except Exception:
        await message.answer("⚠️ تعذّر الإرسال للعميل.")


@router.message(F.text & ~F.text.startswith("/"))
async def catch_all(message: types.Message, state: FSMContext, bot: Bot):
    """
    آخر هاندلر - يعمل حاجتين:
    1. يبعت رسالة العميل للأدمن لو في شات نشط
    2. يتعامل مع أزرار اللينك المخصصة + Soon
    """
    user_id = message.from_user.id

    # العميل في شات نشط → ابعت للأدمن
    if not await is_admin(user_id):
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
            return

    # تحقق من زرار Soon
    soon_label = await get_button_label("soon")
    soon_enabled = await get_setting("soon_enabled")
    soon_url = await get_setting("soon_url")
    if message.text == soon_label and soon_enabled == "1":
        if soon_url:
            await message.answer(f"🔜 {soon_label}\n\n{soon_url}")
        else:
            await message.answer("🔜 قريبًا!")
        return

    # تحقق من الأزرار المخصصة (لينكات)
    custom = await get_custom_buttons()
    for btn in custom:
        btn_id, label, url, position = btn
        if message.text == label:
            await message.answer(f"🔗 {label}\n\n{url}")
            return

    # تحقق من الأزرار لو اتغير اسمها
    dep_label = await get_button_label("deposit")
    wit_label = await get_button_label("withdraw")
    promo_label = await get_button_label("promo")

    if message.text == dep_label and dep_label != "💵 إيداع":
        from handlers.deposit import _deposit_start
        await _deposit_start(message, state)
        return

    if message.text == wit_label and wit_label != "💸 سحب":
        from handlers.withdraw import _withdraw_start
        await _withdraw_start(message, state)
        return

    if message.text == promo_label and promo_label != "🎟 برومو كود":
        from handlers.promo import send_promo
        await send_promo(message, state)
        return
