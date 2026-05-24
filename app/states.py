from aiogram.fsm.state import StatesGroup, State

class Form(StatesGroup):
    full_name = State()
    age = State()
    experience = State()
    experience_details = State()
    brovary = State()
    travel_time = State()
    can_arrive = State()
    contact = State()
    confirm = State()
