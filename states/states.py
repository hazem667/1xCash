from aiogram.fsm.state import State, StatesGroup


class DepositStates(StatesGroup):
    waiting_id = State()
    waiting_photo = State()
    waiting_phone = State()


class WithdrawStates(StatesGroup):
    waiting_id = State()
    waiting_code_step = State()   # عرض زرار تم / طلب مساعدة
    waiting_code_value = State()  # إدخال الكود
    waiting_amount = State()
    waiting_method = State()


class AdminStates(StatesGroup):
    waiting_deposit_amount = State()
    waiting_reply_message = State()
    waiting_broadcast = State()
    waiting_edit_message_key = State()
    waiting_edit_message_value = State()
    waiting_add_admin = State()
    chatting_with_user = State()


class LiveChatStates(StatesGroup):
    in_chat = State()
