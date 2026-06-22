from aiogram import Router, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext

from database.db import register_user, get_message, get_setting, is_admin, get_custom_buttons, get_button_label
from handlers.keyboards import main_menu_keyboard, admin_menu_keyboard

router = Router()


@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await register_user(message.from_user.id, message.from_user.username, message.from_user.full_name)

    maintenance = await get_setting("maintenance_mode")
    if maintenance == "1" and not await is_admin(message.from_user.id):
        await message.answer("🔧 البوت في وضع الصيانة حالياً، برجاء المحاولة لاحقًا.")
        return

    if await is_admin(message.from_user.id):
        await message.answer("👋 مرحبًا بك في لوحة الإدارة!", reply_markup=admin_menu_keyboard())
        return

    welcome_text = await get_message("welcome")
    kb = await main_menu_keyboard()
    await message.answer(welcome_text, reply_markup=kb, parse_mode="Markdown")


@router.message(Command("admin"))
async def cmd_admin(message: types.Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer("🛠 لوحة الإدارة", reply_markup=admin_menu_keyboard())


@router.message(F.text == "🚪 خروج من الإدارة")
async def exit_admin(message: types.Message, state: FSMContext):
    await state.clear()
    welcome_text = await get_message("welcome")
    kb = await main_menu_keyboard()
    await message.answer(welcome_text, reply_markup=kb, parse_mode="Markdown")


@router.message(F.text == "🔙 القائمة الرئيسية")
async def back_to_main(message: types.Message, state: FSMContext):
    await state.clear()
    welcome_text = await get_message("welcome")
    kb = await main_menu_keyboard()
    await message.answer(welcome_text, reply_markup=kb, parse_mode="Markdown")


@router.message(F.text)
async def handle_custom_link_buttons(message: types.Message, state: FSMContext):
    """يتعامل مع الأزرار المخصصة (لينكات) والزرار Soon"""
    soon_label = await get_button_label("soon")
    soon_url = await get_setting("soon_url")

    if message.text == soon_label and soon_url:
        await message.answer(f"🔜 {message.text}\n\n{soon_url}")
        return

    # الأزرار المخصصة
    custom = await get_custom_buttons()
    for btn in custom:
        btn_id, label, btn_type, url, position = btn
        if message.text == label:
            await message.answer(f"🔗 {label}\n\n{url}")
            return
