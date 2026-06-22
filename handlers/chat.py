from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext

from database.db import (
    get_message, get_setting, get_live_chat,
    delete_live_chat, is_admin, get_button_label, get_custom_buttons
)
from handlers.keyboards import main_menu_keyboard
from states.states import AdminStates

router = Router()


@router.message(AdminStates.chatting_with_user)
async def admin_chat_forward(message: types.Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    target = data.get("chatting_with")
    if not target:
        return
    if message.text in ("❌ إنهاء المحادثة", "/end"):
        await delete_live_chat(target)
        await state.clear()
        await message.answer("✅ تم إنهاء المحادثة.")
        return
    try:
        await bot.send_message(target, f"📨 رسالة من الإدارة:\n\n{message.text}")
    except Exception:
        await message.answer("⚠️ لم يتمكن البوت من إرسال الرسالة للعميل.")


@router.message(F.text)
async def user_chat_or_dynamic_buttons(message: types.Message, state: FSMContext, bot: Bot):
    """
    آخر هاندلر - يتعامل مع:
    1. رسائل العميل في محادثة مباشرة مع الأدمن
    2. الأزرار الديناميكية (لو اتغير اسمها)
    3. زرار Soon
    4. الأزرار المخصصة
    """
    user_id = message.from_user.id

    # أولاً: تحقق لو المستخدم في محادثة مباشرة
    live = await get_live_chat(user_id)
    if live and live[1] == "active":
        from database.db import get_all_admins
        admins = await get_all_admins()
        for admin_id in admins:
            try:
                await bot.send_message(
                    admin_id,
                    f"💬 رسالة من العميل `{user_id}`:\n\n{message.text}",
                    parse_mode="Markdown"
                )
            except Exception:
                pass
        return

    # ثانياً: تحقق من الأزرار الديناميكية (لو اتغير اسم زرار)
    dep_label = await get_button_label("deposit")
    wit_label = await get_button_label("withdraw")
    promo_label = await get_button_label("promo")
    soon_label = await get_button_label("soon")
    soon_url = await get_setting("soon_url")

    # زرار الإيداع بالاسم الجديد
    if message.text == dep_label and dep_label != "💵 إيداع":
        from handlers.deposit import _deposit_start
        await _deposit_start(message, state)
        return

    # زرار السحب بالاسم الجديد
    if message.text == wit_label and wit_label != "💸 سحب":
        from handlers.withdraw import _withdraw_start
        await _withdraw_start(message, state)
        return

    # زرار البرومو بالاسم الجديد
    if message.text == promo_label and promo_label != "🎟 برومو كود":
        from handlers.promo import send_promo
        await send_promo(message, state)
        return

    # زرار Soon
    if message.text == soon_label and soon_url:
        await message.answer(f"🔜 {message.text}\n\n{soon_url}")
        return

    # الأزرار المخصصة (روابط)
    custom = await get_custom_buttons()
    for btn in custom:
        btn_id, label, btn_type, url, position = btn
        if message.text == label:
            await message.answer(f"🔗 {label}\n\n{url}")
            return
