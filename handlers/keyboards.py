from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from database.db import get_button_label, get_custom_buttons, get_setting


async def main_menu_keyboard():
    dep = await get_button_label("deposit")
    wit = await get_button_label("withdraw")
    promo = await get_button_label("promo")
    soon_label = await get_button_label("soon")
    soon_url = await get_setting("soon_url")

    rows = [[KeyboardButton(text=dep), KeyboardButton(text=wit)]]

    # البرومو
    rows.append([KeyboardButton(text=promo)])

    # زرار Soon لو فيه رابط
    if soon_url:
        rows.append([KeyboardButton(text=soon_label)])

    # الأزرار المخصصة (لينكات)
    custom = await get_custom_buttons()
    for btn in custom:
        rows.append([KeyboardButton(text=btn[1])])

    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def admin_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📥 طلبات الإيداع"), KeyboardButton(text="📤 طلبات السحب")],
            [KeyboardButton(text="💬 المحادثات"), KeyboardButton(text="📣 إذاعة")],
            [KeyboardButton(text="📝 تعديل الرسائل"), KeyboardButton(text="⚙️ الإعدادات")],
            [KeyboardButton(text="🔘 إدارة الأزرار"), KeyboardButton(text="🔄 إدارة الخطوات")],
            [KeyboardButton(text="📊 الإحصائيات"), KeyboardButton(text="📜 السجلات")],
            [KeyboardButton(text="🚪 خروج من الإدارة")],
        ],
        resize_keyboard=True
    )


def cancel_keyboard(back_text="❌ إلغاء"):
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=back_text)]],
        resize_keyboard=True
    )


def deposit_intro_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ متابعة")],
            [KeyboardButton(text="🔙 القائمة الرئيسية")],
        ],
        resize_keyboard=True
    )


def withdraw_code_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ تم الحصول على الكود")],
            [KeyboardButton(text="🆘 طلب مساعدة")],
            [KeyboardButton(text="🔙 القائمة الرئيسية")],
        ],
        resize_keyboard=True
    )


def deposit_send_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ إرسال"), KeyboardButton(text="❌ إلغاء")],
        ],
        resize_keyboard=True
    )


def promo_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❓ استفسار", callback_data="promo_inquiry")],
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="back_main")],
    ])


def deposit_admin_keyboard(order_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ قبول", callback_data=f"dep_accept:{order_id}"),
            InlineKeyboardButton(text="❌ رفض", callback_data=f"dep_reject:{order_id}"),
        ],
        [InlineKeyboardButton(text="💬 رد على العميل", callback_data=f"dep_reply:{order_id}")],
    ])


def withdraw_admin_keyboard(order_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ عملية ناجحة", callback_data=f"wit_success:{order_id}"),
            InlineKeyboardButton(text="❌ عملية مرفوضة", callback_data=f"wit_reject:{order_id}"),
        ],
        [InlineKeyboardButton(text="💬 رد على العميل", callback_data=f"wit_reply:{order_id}")],
    ])


def help_request_keyboard(user_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 بدء المحادثة", callback_data=f"chat_start:{user_id}")],
        [InlineKeyboardButton(text="❌ تجاهل", callback_data=f"chat_ignore:{user_id}")],
    ])


def end_chat_keyboard(user_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ إنهاء المحادثة", callback_data=f"chat_end:{user_id}")],
    ])


def withdraw_help_result_keyboard(user_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ عملية ناجحة", callback_data=f"wit_help_success:{user_id}"),
            InlineKeyboardButton(text="❌ عملية مرفوضة", callback_data=f"wit_help_reject:{user_id}"),
        ],
    ])


def edit_messages_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 رسالة الترحيب", callback_data="edit_msg:welcome")],
        [InlineKeyboardButton(text="💵 مقدمة الإيداع", callback_data="edit_msg:deposit_intro")],
        [InlineKeyboardButton(text="💸 مقدمة السحب", callback_data="edit_msg:withdraw_intro")],
        [InlineKeyboardButton(text="🎟 رسالة البرومو كود", callback_data="edit_msg:promo")],
        [InlineKeyboardButton(text="📋 رسالة معلومات التحويل", callback_data="edit_msg:transfer_info")],
        [InlineKeyboardButton(text="✅ رسالة قبول الإيداع", callback_data="edit_msg:deposit_accepted")],
        [InlineKeyboardButton(text="❌ رسالة رفض الإيداع", callback_data="edit_msg:deposit_rejected")],
        [InlineKeyboardButton(text="✅ رسالة نجاح السحب", callback_data="edit_msg:withdraw_success")],
        [InlineKeyboardButton(text="❌ رسالة رفض السحب", callback_data="edit_msg:withdraw_rejected")],
    ])


def settings_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💵 تشغيل/إيقاف الإيداع", callback_data="toggle:deposit_enabled")],
        [InlineKeyboardButton(text="💸 تشغيل/إيقاف السحب", callback_data="toggle:withdraw_enabled")],
        [InlineKeyboardButton(text="🎟 تشغيل/إيقاف البرومو", callback_data="toggle:promo_enabled")],
        [InlineKeyboardButton(text="🔧 وضع الصيانة", callback_data="toggle:maintenance_mode")],
        [InlineKeyboardButton(text="🔗 تعديل رابط Soon", callback_data="set_soon_url")],
        [InlineKeyboardButton(text="➕ إضافة أدمن", callback_data="admin_add")],
        [InlineKeyboardButton(text="➖ حذف أدمن", callback_data="admin_remove")],
    ])


def buttons_manage_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ تغيير اسم زرار إيداع", callback_data="btn_label:deposit")],
        [InlineKeyboardButton(text="✏️ تغيير اسم زرار سحب", callback_data="btn_label:withdraw")],
        [InlineKeyboardButton(text="✏️ تغيير اسم زرار برومو", callback_data="btn_label:promo")],
        [InlineKeyboardButton(text="✏️ تغيير اسم زرار Soon", callback_data="btn_label:soon")],
        [InlineKeyboardButton(text="➕ إضافة زرار بلينك", callback_data="btn_add_custom")],
        [InlineKeyboardButton(text="🗑 حذف زرار مخصص", callback_data="btn_del_custom")],
    ])


async def flow_steps_keyboard(flow_type: str):
    from database.db import get_flow_steps
    steps = await get_flow_steps(flow_type)
    buttons = []
    for s in steps:
        step_id, order, label, question, *_ = s
        buttons.append([InlineKeyboardButton(
            text=f"✏️ خطوة {order}: {label}",
            callback_data=f"edit_step:{step_id}"
        )])
    buttons.append([InlineKeyboardButton(text="🔙 رجوع", callback_data="flow_back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
