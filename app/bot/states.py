from aiogram.fsm.state import State, StatesGroup


class SetupState(StatesGroup):
    region = State()
    city = State()
