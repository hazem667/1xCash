from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


def main_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💵 إيداع"), KeyboardButton(text="💸 سحب")],
            [KeyboardButton(text="🎟 برومو كود")],
        ],
        resize_keyboard=True
    )


def admin_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📥 طلبات الإيداع"), KeyboardButton(text="📤 طلبات السحب")],
            [KeyboardButton(text="💬 المحادثات"), KeyboardButton(text="📣 إذاعة")],
            [KeyboardButton(text="📝 تعديل الرسائل"), KeyboardButton(text="⚙️ الإعدادات")],
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
        [InlineKeyboardButton(text="➕ إضافة أدمن", callback_data="admin_add")],
        [InlineKeyboardButton(text="➖ حذف أدمن", callback_data="admin_remove")],
    ])
