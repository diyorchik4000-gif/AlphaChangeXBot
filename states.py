from aiogram.fsm.state import State, StatesGroup


class RegisterState(StatesGroup):
    choosing_lang = State()
    entering_name = State()
    entering_surname = State()
    entering_phone = State()


class AdminState(StatesGroup):
    waiting_channel_id = State()
    waiting_channel_link = State()
    waiting_channel_name = State()
    waiting_remove_id = State()
    waiting_broadcast = State()


class SettingsState(StatesGroup):
    in_settings = State()
    changing_name = State()
    changing_surname = State()
    changing_phone = State()


class ExchangeState(StatesGroup):
    choosing_from = State()
    choosing_to = State()
    choosing_amount_type = State()
    entering_amount = State()
    entering_sender_card = State()
    entering_receiver_card = State()
    confirming = State()
    payment_pending = State()
