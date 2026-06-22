from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from database.db import get_message, get_setting, is_admin
from handlers.keyboards import promo_keyboard, main_menu_keyboard

router = Router()


@router.message(F.text == "🎟 برومو كود")
async def send_promo(message: types.Message, state: FSMContext = None):
    maint = await get_setting("maintenance_mode")
    if maint == "1" and not await is_admin(message.from_user.id):
        await message.answer("🔧 البوت في وضع الصيانة حالياً.")
        return

    enabled = await get_setting("promo_enabled")
    if enabled == "0":
        await message.answer("⚠️ البرومو كود غير متاح حالياً.")
        return

    promo_text = await get_message("promo")
    await message.answer(promo_text, reply_markup=promo_keyboard(), parse_mode="Markdown")


@router.callback_query(F.data == "promo_inquiry")
async def promo_inquiry(callback: types.CallbackQuery):
    support = await get_setting("support_username")
    await callback.message.answer(f"للاستفسار تواصل مع: @{support}")
    await callback.answer()


@router.callback_query(F.data == "back_main")
async def back_main(callback: types.CallbackQuery):
    from handlers.keyboards import main_menu_keyboard
    kb = await main_menu_keyboard()
    await callback.message.delete()
    await callback.answer()
