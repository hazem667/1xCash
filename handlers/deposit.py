import os
from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext

from database.db import (
    get_message, get_setting, create_deposit_order,
    get_deposit_order, update_deposit_status, get_all_admins, log_action
)
from handlers.keyboards import (
    deposit_intro_keyboard, cancel_keyboard,
    main_menu_keyboard, deposit_admin_keyboard
)
from states.states import DepositStates
from datetime import datetime

router = Router()


@router.message(F.text == "💵 إيداع")
async def deposit_start(message: types.Message, state: FSMContext):
    await state.clear()
    enabled = await get_setting("deposit_enabled")
    if enabled == "0":
        await message.answer("⚠️ خدمة الإيداع غير متاحة حالياً.\nجاري التحديث والصيانة.")
        return

    intro = await get_message("deposit_intro")
    await message.answer(intro, reply_markup=deposit_intro_keyboard(), parse_mode="Markdown")


@router.message(F.text == "✅ متابعة")
async def deposit_continue(message: types.Message, state: FSMContext):
    current = await state.get_state()
    # فقط لو في بداية الإيداع
    if current is None or current == DepositStates.waiting_id:
        ask_id = await get_message("deposit_ask_id")
        await message.answer(ask_id, reply_markup=cancel_keyboard())
        await state.set_state(DepositStates.waiting_id)


@router.message(DepositStates.waiting_id)
async def deposit_get_id(message: types.Message, state: FSMContext):
    if message.text == "❌ إلغاء":
        await state.clear()
        welcome = await get_message("welcome")
        await message.answer(welcome, reply_markup=main_menu_keyboard(), parse_mode="Markdown")
        return

    if not message.text or not message.text.strip().isdigit():
        await message.answer("⚠️ الرجاء إدخال أرقام فقط.")
        return

    await state.update_data(account_id=message.text.strip())
    ask_photo = await get_message("deposit_ask_photo")
    await message.answer(ask_photo, reply_markup=cancel_keyboard())
    await state.set_state(DepositStates.waiting_photo)


@router.message(DepositStates.waiting_photo)
async def deposit_get_photo(message: types.Message, state: FSMContext):
    if message.text == "❌ إلغاء":
        await state.clear()
        welcome = await get_message("welcome")
        await message.answer(welcome, reply_markup=main_menu_keyboard(), parse_mode="Markdown")
        return

    if not message.photo:
        await message.answer("⚠️ الرجاء إرسال صورة إيصال التحويل.")
        return

    photo_id = message.photo[-1].file_id
    await state.update_data(photo_file_id=photo_id)
    ask_phone = await get_message("deposit_ask_phone")
    await message.answer(ask_phone, reply_markup=cancel_keyboard())
    await state.set_state(DepositStates.waiting_phone)


@router.message(DepositStates.waiting_phone)
async def deposit_get_phone(message: types.Message, state: FSMContext, bot: Bot):
    if message.text == "❌ إلغاء":
        await state.clear()
        welcome = await get_message("welcome")
        await message.answer(welcome, reply_markup=main_menu_keyboard(), parse_mode="Markdown")
        return

    if not message.text or not message.text.strip():
        await message.answer("⚠️ الرجاء إدخال الرقم.")
        return

    data = await state.get_data()
    account_id = data["account_id"]
    photo_file_id = data["photo_file_id"]
    phone = message.text.strip()

    user = message.from_user
    username = f"@{user.username}" if user.username else user.full_name

    order_id = await create_deposit_order(
        user_id=user.id,
        username=username,
        account_id=account_id,
        phone=phone,
        photo_file_id=photo_file_id
    )

    now = datetime.now()
    admin_text = (
        f"💵 *طلب إيداع جديد*\n\n"
        f"Order #{order_id}\n\n"
        f"👤 المستخدم: {username}\n"
        f"🆔 Telegram ID: `{user.id}`\n"
        f"💠 ID الحساب: `{account_id}`\n"
        f"📱 الرقم المحوّل منه: `{phone}`\n"
        f"🕒 الوقت: {now.strftime('%Y/%m/%d - %I:%M %p')}"
    )

    admins = await get_all_admins()
    for admin_id in admins:
        try:
            await bot.send_photo(
                chat_id=admin_id,
                photo=photo_file_id,
                caption=admin_text,
                reply_markup=deposit_admin_keyboard(order_id),
                parse_mode="Markdown"
            )
        except Exception:
            pass

    sent_msg = await get_message("deposit_sent")
    await message.answer(sent_msg, reply_markup=main_menu_keyboard())
    await state.clear()

    await log_action("deposit_created", user.id, order_id, f"order#{order_id}")


# ── Callbacks للأدمن ──────────────────────────────────────

@router.callback_query(F.data.startswith("dep_accept:"))
async def dep_accept(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    order_id = int(callback.data.split(":")[1])
    await state.update_data(pending_order_id=order_id, pending_type="deposit")
    await callback.message.answer("💰 أدخل مبلغ الإيداع:")
    from states.states import AdminStates
    await state.set_state(AdminStates.waiting_deposit_amount)
    await callback.answer()


@router.callback_query(F.data.startswith("dep_reject:"))
async def dep_reject(callback: types.CallbackQuery, bot: Bot):
    order_id = int(callback.data.split(":")[1])
    order = await get_deposit_order(order_id)
    if not order:
        await callback.answer("الطلب غير موجود!")
        return

    user_id = order[1]
    account_id = order[3]
    now = datetime.now()

    template = await get_message("deposit_rejected")
    user_text = template.format(
        account_id=account_id,
        date=now.strftime('%d/%m/%Y'),
        time=now.strftime('%I:%M %p')
    )

    try:
        await bot.send_message(user_id, user_text)
    except Exception:
        pass

    await update_deposit_status(order_id, "rejected")
    await callback.message.edit_caption(
        callback.message.caption + "\n\n❌ *تم الرفض*",
        parse_mode="Markdown"
    )
    await callback.answer("تم الرفض")


@router.callback_query(F.data.startswith("dep_reply:"))
async def dep_reply(callback: types.CallbackQuery, state: FSMContext):
    order_id = int(callback.data.split(":")[1])
    order = await get_deposit_order(order_id)
    if not order:
        await callback.answer("الطلب غير موجود!")
        return

    user_id = order[1]
    await state.update_data(reply_to_user_id=user_id)
    from states.states import AdminStates
    await state.set_state(AdminStates.waiting_reply_message)
    await callback.message.answer("💬 اكتب رسالتك للعميل:")
    await callback.answer()
