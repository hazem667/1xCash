import json
from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext

from database.db import (
    get_message, get_setting, create_withdraw_order,
    get_withdraw_order, update_withdraw_status,
    get_all_admins, set_live_chat, delete_live_chat,
    log_action, get_flow_steps, is_admin
)
from handlers.keyboards import (
    cancel_keyboard, main_menu_keyboard,
    withdraw_code_keyboard, withdraw_admin_keyboard,
    help_request_keyboard, withdraw_help_result_keyboard
)
from states.states import WithdrawStates, AdminStates
from datetime import datetime

router = Router()


def make_mention(user):
    if user.username:
        return f"@{user.username}"
    return f"[{user.full_name}](tg://user?id={user.id})"


@router.message(F.text == "💸 سحب")
async def withdraw_start(message: types.Message, state: FSMContext):
    await _withdraw_start(message, state)


async def _withdraw_start(message: types.Message, state: FSMContext):
    await state.clear()
    maint = await get_setting("maintenance_mode")
    if maint == "1" and not await is_admin(message.from_user.id):
        await message.answer("🔧 البوت في وضع الصيانة حالياً، برجاء المحاولة لاحقًا.")
        return

    enabled = await get_setting("withdraw_enabled")
    if enabled == "0":
        await message.answer("⚠️ خدمة السحب غير متاحة حالياً.")
        return

    intro = await get_message("withdraw_intro")
    steps = await get_flow_steps("withdraw")
    if not steps:
        await message.answer("⚠️ لا توجد خطوات للسحب.")
        return

    await state.set_state(WithdrawStates.in_flow)
    await state.update_data(step_index=0, responses={}, steps=[list(s) for s in steps])

    await message.answer(intro, parse_mode="Markdown")
    await ask_withdraw_step(message, state)


async def ask_withdraw_step(message: types.Message, state: FSMContext):
    data = await state.get_data()
    steps = data["steps"]
    idx = data["step_index"]

    if idx >= len(steps):
        return  # سيتم الإنهاء من الهاندلر

    step = steps[idx]
    step_id, order, label, question, answer_type, validation, options, is_photo, is_info_message, info_text = step

    if answer_type == "code_wait":
        await message.answer(question, reply_markup=withdraw_code_keyboard(), parse_mode="Markdown")
        await state.set_state(WithdrawStates.waiting_code_step)
    else:
        await message.answer(question, reply_markup=cancel_keyboard())


@router.message(WithdrawStates.waiting_code_step)
async def withdraw_code_step_handler(message: types.Message, state: FSMContext, bot: Bot):
    if message.text == "🔙 القائمة الرئيسية":
        await state.clear()
        welcome = await get_message("welcome")
        kb = await main_menu_keyboard()
        await message.answer(welcome, reply_markup=kb, parse_mode="Markdown")
        return

    if message.text == "🆘 طلب مساعدة":
        user = message.from_user
        mention = make_mention(user)
        data = await state.get_data()
        responses = data.get("responses", {})
        details = "\n".join([f"• {k}: {v}" for k, v in responses.items()])

        admin_text = (
            f"🆘 *طلب مساعدة في السحب*\n\n"
            f"👤 المستخدم: {mention}\n"
            f"🆔 Telegram ID: `{user.id}`\n"
            f"{details}"
        )
        admins = await get_all_admins()
        for admin_id in admins:
            try:
                await bot.send_message(admin_id, admin_text, reply_markup=help_request_keyboard(user.id), parse_mode="Markdown")
            except Exception:
                pass

        await set_live_chat(user.id, "pending", "withdraw_help")
        help_msg = await get_message("help_requested")
        await message.answer(help_msg, reply_markup=cancel_keyboard("❌ إلغاء"))
        await state.clear()
        return

    if message.text == "✅ تم الحصول على الكود":
        data = await state.get_data()
        steps = data["steps"]
        idx = data["step_index"]
        await state.update_data(step_index=idx + 1)
        await state.set_state(WithdrawStates.in_flow)
        await ask_withdraw_step(message, state)
        return

    await message.answer("⚠️ الرجاء اختيار أحد الأزرار.")


@router.message(WithdrawStates.in_flow)
async def withdraw_flow_handler(message: types.Message, state: FSMContext, bot: Bot):
    if message.text in ("❌ إلغاء", "🔙 القائمة الرئيسية"):
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
        await finish_withdraw(message, state, bot)
        return

    step = steps[idx]
    step_id, order, label, question, answer_type, validation, options, is_photo, is_info_message, info_text = step

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
        await finish_withdraw(message, state, bot)
    else:
        await ask_withdraw_step(message, state)


async def finish_withdraw(message: types.Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    responses = data.get("responses", {})
    user = message.from_user
    mention = make_mention(user)

    order_id = await create_withdraw_order(
        user_id=user.id,
        username=mention,
        responses=responses
    )

    now = datetime.now()
    details_text = "\n".join([f"• {k}: {v}" for k, v in responses.items()])

    admin_text = (
        f"💸 *طلب سحب جديد*\n\n"
        f"Order #{order_id}\n\n"
        f"👤 المستخدم: {mention}\n"
        f"🆔 Telegram ID: `{user.id}`\n\n"
        f"{details_text}\n"
        f"🕒 الوقت: {now.strftime('%Y/%m/%d - %I:%M %p')}"
    )

    admins = await get_all_admins()
    for admin_id in admins:
        try:
            await bot.send_message(admin_id, admin_text, reply_markup=withdraw_admin_keyboard(order_id), parse_mode="Markdown")
        except Exception:
            pass

    sent_msg = await get_message("withdraw_sent")
    kb = await main_menu_keyboard()
    await message.answer(sent_msg, reply_markup=kb)
    await state.clear()
    await log_action("withdraw_created", user.id, order_id, f"order#{order_id}")


# ── Callbacks ─────────────────────────────────────────────

@router.callback_query(F.data.startswith("wit_success:"))
async def wit_success(callback: types.CallbackQuery, bot: Bot):
    order_id = int(callback.data.split(":")[1])
    order = await get_withdraw_order(order_id)
    if not order:
        await callback.answer("الطلب غير موجود!")
        return

    user_id = order[1]
    now = datetime.now()
    template = await get_message("withdraw_success")
    user_text = template.format(date=now.strftime('%d/%m/%Y'), time=now.strftime('%I:%M %p'))

    try:
        await bot.send_message(user_id, user_text)
    except Exception:
        pass

    await update_withdraw_status(order_id, "accepted")
    try:
        await callback.message.edit_text(callback.message.text + "\n\n✅ *تمت الموافقة*", parse_mode="Markdown")
    except Exception:
        pass
    await callback.answer("تمت الموافقة")


@router.callback_query(F.data.startswith("wit_reject:"))
async def wit_reject(callback: types.CallbackQuery, bot: Bot):
    order_id = int(callback.data.split(":")[1])
    order = await get_withdraw_order(order_id)
    if not order:
        await callback.answer("الطلب غير موجود!")
        return

    user_id = order[1]
    now = datetime.now()
    template = await get_message("withdraw_rejected")
    user_text = template.format(date=now.strftime('%d/%m/%Y'), time=now.strftime('%I:%M %p'))

    try:
        await bot.send_message(user_id, user_text)
    except Exception:
        pass

    await update_withdraw_status(order_id, "rejected")
    try:
        await callback.message.edit_text(callback.message.text + "\n\n❌ *تم الرفض*", parse_mode="Markdown")
    except Exception:
        pass
    await callback.answer("تم الرفض")


@router.callback_query(F.data.startswith("wit_reply:"))
async def wit_reply(callback: types.CallbackQuery, state: FSMContext):
    order_id = int(callback.data.split(":")[1])
    order = await get_withdraw_order(order_id)
    if not order:
        await callback.answer("الطلب غير موجود!")
        return
    user_id = order[1]
    await state.update_data(reply_to_user_id=user_id)
    await state.set_state(AdminStates.waiting_reply_message)
    await callback.message.answer("💬 اكتب رسالتك للعميل:")
    await callback.answer()


@router.callback_query(F.data.startswith("chat_start:"))
async def chat_start(callback: types.CallbackQuery, bot: Bot, state: FSMContext):
    user_id = int(callback.data.split(":")[1])
    await set_live_chat(user_id, "active", "withdraw_help")
    connected_msg = await get_message("admin_connected")
    try:
        await bot.send_message(user_id, connected_msg)
    except Exception:
        pass
    await state.update_data(chatting_with=user_id)
    await state.set_state(AdminStates.chatting_with_user)
    await callback.message.edit_reply_markup(reply_markup=withdraw_help_result_keyboard(user_id))
    await callback.message.answer(f"💬 أنت الآن متصل بالعميل `{user_id}`\nكل ما تكتبه سيصله مباشرة.", parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data.startswith("chat_ignore:"))
async def chat_ignore(callback: types.CallbackQuery):
    user_id = int(callback.data.split(":")[1])
    await delete_live_chat(user_id)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer("تم التجاهل")


@router.callback_query(F.data.startswith("wit_help_success:"))
async def wit_help_success(callback: types.CallbackQuery, bot: Bot, state: FSMContext):
    user_id = int(callback.data.split(":")[1])
    now = datetime.now()
    await state.clear()
    await delete_live_chat(user_id)
    try:
        template = await get_message("withdraw_success")
        await bot.send_message(user_id, template.format(date=now.strftime('%d/%m/%Y'), time=now.strftime('%I:%M %p')))
    except Exception:
        pass
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("✅ تم إرسال رسالة النجاح للعميل وإنهاء المحادثة.")
    await callback.answer()


@router.callback_query(F.data.startswith("wit_help_reject:"))
async def wit_help_reject(callback: types.CallbackQuery, bot: Bot, state: FSMContext):
    user_id = int(callback.data.split(":")[1])
    now = datetime.now()
    await state.clear()
    await delete_live_chat(user_id)
    try:
        template = await get_message("withdraw_rejected")
        await bot.send_message(user_id, template.format(date=now.strftime('%d/%m/%Y'), time=now.strftime('%I:%M %p')))
    except Exception:
        pass
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("❌ تم إرسال رسالة الرفض للعميل وإنهاء المحادثة.")
    await callback.answer()
