from aiogram.fsm.state import State, StatesGroup


class DepositStates(StatesGroup):
    in_flow = State()       # يسير خطوة خطوة


class WithdrawStates(StatesGroup):
    in_flow = State()       # يسير خطوة خطوة
    waiting_code_step = State()  # شاشة "تم / طلب مساعدة"


class AdminStates(StatesGroup):
    waiting_deposit_amount = State()
    waiting_reply_message = State()
    waiting_broadcast = State()
    waiting_edit_message_key = State()
    waiting_edit_message_value = State()
    waiting_add_admin = State()
    chatting_with_user = State()
    # تعديل أسماء الأزرار
    waiting_button_label_key = State()
    waiting_button_label_value = State()
    # إضافة زرار مخصص
    waiting_custom_btn_label = State()
    waiting_custom_btn_url = State()
    # تعديل خطوات الفلو
    waiting_flow_step_question = State()
    waiting_new_step_label = State()
    waiting_new_step_question = State()
    waiting_new_step_type = State()
    # إعداد رابط Soon
    waiting_soon_url = State()


class LiveChatStates(StatesGroup):
    in_chat = State()
