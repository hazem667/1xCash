from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext

from database.db import get_message, get_setting, get_all_admins
from handlers.keyboards import promo_keyboard, main_menu_keyboard

router = Router()


async def send_promo(message: types.Message, state: FSMContext):
    await state.clear()
    enabled = await get_setting("promo_enabled")
    if enabled == "0":
        await message.answer("⚠️ البرومو كود غير متاح حالياً.")
        return
    promo_text = await get_message("promo")
    await message.answer(promo_text, reply_markup=promo_keyboard(), parse_mode="Markdown")


@router.message(F.text == "🎟 برومو كود")
async def promo_start(message: types.Message, state: FSMContext):
    await send_promo(message, state)


@router.callback_query(F.data == "promo_inquiry")
async def promo_inquiry(callback: types.CallbackQuery, bot: Bot):
    user = callback.from_user
    mention = f"@{user.username}" if user.username else f"[{user.full_name}](tg://user?id={user.id})"

    admins = await get_all_admins()
    for admin_id in admins:
        try:
            await bot.send_message(
                admin_id,
                f"❓ *استفسار عن البرومو كود*\n\n"
                f"👤 المستخدم: {mention}\n"
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
    kb = await main_menu_keyboard()
    await callback.message.answer(welcome, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()
