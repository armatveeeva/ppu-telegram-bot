from aiogram.fsm.state import State, StatesGroup

class ProposalForm(StatesGroup):
    department = State()
    process = State()
    fio = State()
    position = State()
    reward = State()
    problem = State()
    solution = State()
    result = State()
    photo_before = State()
    photo_after = State()
