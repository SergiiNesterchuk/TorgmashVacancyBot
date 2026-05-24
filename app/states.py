from aiogram.fsm.state import StatesGroup, State

class Form(StatesGroup):
    first_name = State()
    last_name = State()
    age = State()
    brovary = State()
    contact = State()
    confirm = State()
