import json
from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext

from database.db import (
    get_message, get_setting, create_deposit_order,
    get_deposit_order, update_deposit_status,
    get_all_admins, log_action, get_flow_steps, get_button_label
)
from handlers.keyboards import (
    deposit_intro_keyboard, cancel_keyboard,
    main_menu_keyboard, deposit_admin_keyboard,
    deposit_send_keyboard
)
from states.states import DepositStates
from datetime import datetime

router = Router()


def make_mention(user):
    if user.username:
        return f"@{user.username}"
    return f"[{user.full_name}](tg://user?id={user.id})"


@router.message(F.text == "💵 إيداع")
async def deposit_start(message: types.Message, state: FSMContext):
    await _deposit_start(message, state)


async def _deposit_start(message: types.Message, state: FSMContext):
    await state.clear()
    maint = await get_setting("maintenance_mode")
    from database.db import is_admin
    if maint == "1" and not await is_admin(message.from_user.id):
        await message.answer("🔧 البوت في وضع الصيانة حالياً، برجاء المحاولة لاحقًا.")
        return

    enabled = await get_setting("deposit_enabled")
    if enabled == "0":
        await message.answer("⚠️ خدمة الإيداع غير متاحة حالياً.\nجاري التحديث والصيانة.")
        return

    intro = await get_message("deposit_intro")
    await message.answer(intro, reply_markup=deposit_intro_keyboard(), parse_mode="Markdown")


@router.message(F.text == "✅ متابعة")
async def deposit_continue(message: types.Message, state: FSMContext):
    cur = await state.get_state()
    if cur is not None and cur != DepositStates.in_flow:
        return
    steps = await get_flow_steps("deposit")
    if not steps:
        await message.answer("⚠️ لا توجد خطوات للإيداع، تواصل مع الإدارة.")
        return
    await state.set_state(DepositStates.in_flow)
    await state.update_data(step_index=0, responses={}, steps=[list(s) for s in steps])
    await ask_step(message, state)


async def ask_step(message: types.Message, state: FSMContext):
    data = await state.get_data()
    steps = data["steps"]
    idx = data["step_index"]

    if idx >= len(steps):
        await finish_deposit(message, state)
        return

    step = steps[idx]
    step_id, order, label, question, answer_type, validation, options, is_photo, is_info_message, info_text = step

    if is_info_message:
        info = await get_message("transfer_info")
        await message.answer(info, reply_markup=deposit_send_keyboard())
        await state.update_data(step_index=idx + 1)
        # ننتظر المستخدم يضغط إرسال
        return

    await message.answer(question, reply_markup=cancel_keyboard())


@router.message(DepositStates.in_flow)
async def deposit_flow_handler(message: types.Message, state: FSMContext, bot: Bot):
    if message.text == "❌ إلغاء":
        await state.clear()
        welcome = await get_message("welcome")
        kb = await main_menu_keyboard()
        await message.answer(welcome, reply_markup=kb, parse_mode="Markdown")
        return

    data = await state.get_data()
    steps = data["steps"]
    idx = data["step_index"]
    responses = data.get("responses", {})

    if idx >= len(steps):
        await finish_deposit(message, state, bot)
        return

    step = steps[idx]
    step_id, order, label, question, answer_type, validation, options, is_photo, is_info_message, info_text = step

    # لو المستخدم ضغط إرسال بعد رسالة المعلومات
    if message.text == "✅ إرسال":
        await ask_step(message, state)
        return

    # التحقق من الإجابة
    if is_photo:
        if not message.photo:
            await message.answer("⚠️ الرجاء إرسال صورة.")
            return
        responses[label] = message.photo[-1].file_id
        await state.update_data(responses=responses, photo_file_id=message.photo[-1].file_id)
    else:
        if not message.text:
            return
        val = message.text.strip()

        if validation == "digits" and not val.isdigit():
            await message.answer("⚠️ الرجاء إدخال أرقام فقط.")
            return

        responses[label] = val

    await state.update_data(responses=responses, step_index=idx + 1)

    next_idx = idx + 1
    if next_idx >= len(steps):
        await finish_deposit(message, state, bot)
    else:
        await ask_step(message, state)


async def finish_deposit(message: types.Message, state: FSMContext, bot: Bot = None):
    data = await state.get_data()
    responses = data.get("responses", {})
    photo_file_id = data.get("photo_file_id")

    user = message.from_user
    mention = make_mention(user)

    order_id = await create_deposit_order(
        user_id=user.id,
        username=mention,
        responses=responses,
        photo_file_id=photo_file_id
    )

    now = datetime.now()
    details_text = "\n".join([f"• {k}: {v}" for k, v in responses.items() if k not in ("photo",)])

    admin_text = (
        f"💵 *طلب إيداع جديد*\n\n"
        f"Order #{order_id}\n\n"
        f"👤 المستخدم: {mention}\n"
        f"🆔 Telegram ID: `{user.id}`\n\n"
        f"{details_text}\n"
        f"🕒 الوقت: {now.strftime('%Y/%m/%d - %I:%M %p')}"
    )

    admins = await get_all_admins()
    if bot:
        for admin_id in admins:
            try:
                if photo_file_id:
                    await bot.send_photo(
                        chat_id=admin_id,
                        photo=photo_file_id,
                        caption=admin_text,
                        reply_markup=deposit_admin_keyboard(order_id),
                        parse_mode="Markdown"
                    )
                else:
                    await bot.send_message(
                        chat_id=admin_id,
                        text=admin_text,
                        reply_markup=deposit_admin_keyboard(order_id),
                        parse_mode="Markdown"
                    )
            except Exception:
                pass

    sent_msg = await get_message("deposit_sent")
    kb = await main_menu_keyboard()
    await message.answer(sent_msg, reply_markup=kb)
    await state.clear()

    if bot:
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
    now = datetime.now()
    template = await get_message("deposit_rejected")
    user_text = template.format(date=now.strftime('%d/%m/%Y'), time=now.strftime('%I:%M %p'))

    try:
        await bot.send_message(user_id, user_text)
    except Exception:
        pass

    await update_deposit_status(order_id, "rejected")
    try:
        await callback.message.edit_caption(
            callback.message.caption + "\n\n❌ *تم الرفض*", parse_mode="Markdown"
        )
    except Exception:
        pass
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
