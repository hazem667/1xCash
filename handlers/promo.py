from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext

from database.db import get_message, get_setting, get_all_admins
from handlers.keyboards import promo_keyboard, main_menu_keyboard

router = Router()


@router.message(F.text == "🎟 برومو كود")
async def promo_start(message: types.Message, state: FSMContext):
    await state.clear()
    enabled = await get_setting("promo_enabled")
    if enabled == "0":
        await message.answer("⚠️ البرومو كود غير متاح حالياً.")
        return

    promo_text = await get_message("promo")
    await message.answer(promo_text, reply_markup=promo_keyboard(), parse_mode="Markdown")


@router.callback_query(F.data == "promo_inquiry")
async def promo_inquiry(callback: types.CallbackQuery, bot: Bot):
    user = callback.from_user
    username = f"@{user.username}" if user.username else user.full_name

    admins = await get_all_admins()
    for admin_id in admins:
        try:
            await bot.send_message(
                admin_id,
                f"❓ *استفسار عن البرومو كود*\n\n"
                f"👤 المستخدم: {username}\n"
                f"🆔 Telegram ID: `{user.id}`",
                parse_mode="Markdown"
            )
        except Exception:
            pass

    await callback.answer("✅ تم إرسال استفسارك للإدارة، سيتم الرد عليك قريبًا.")


@router.callback_query(F.data == "back_main")
async def back_main_cb(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    welcome = await get_message("welcome")
    await callback.message.answer(welcome, reply_markup=main_menu_keyboard(), parse_mode="Markdown")
    await callback.answer()
