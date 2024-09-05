from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import CommandStart, StateFilter
import logging
import asyncio
from os import getenv

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Получение токена бота из переменных окружения
API_TOKEN = getenv('TELEGRAM_TOKEN')
if not API_TOKEN:
    logging.error("TELEGRAM_TOKEN не найден в переменных окружения")
    exit(1)

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Определение машины состояний
class Form(StatesGroup):
    gender = State()
    age = State()
    growth = State()
    weight = State()

# Класс для обработки состояний и логики расчета калорий
class CalorieCalculator:
    def __init__(self, state: FSMContext):
        self.state = state

    async def set_gender(self, call: CallbackQuery):
        inline_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Женщина", callback_data="female")],
                [InlineKeyboardButton(text="Мужчина", callback_data="male")]
            ]
        )
        await call.message.answer("Выберите ваш пол:", reply_markup=inline_keyboard)
        await call.answer()

    async def set_age(self, call: CallbackQuery):
        await self.state.update_data(gender=call.data)
        await call.message.answer("Пожалуйста, введите ваш возраст:")
        await self.state.set_state(Form.age)
        await call.answer()

    async def process_numeric_input(self, message: Message, key: str, prompt: str, next_state: State, callback=None):
        try:
            value = int(message.text)
            await self.state.update_data(**{key: value})
            if callback:
                await callback(message, self.state)
            else:
                data = await self.state.get_data()
                await message.reply(prompt.format(data=data))
                await self.state.set_state(next_state)
        except ValueError:
            await message.reply('Пожалуйста, введите корректное число.')
            await self.state.set_state(next_state)  # Сброс состояния в случае ошибки

    async def calculate_calories(self, message: Message):
        data = await self.state.get_data()
        if 'gender' not in data or 'age' not in data or 'growth' not in data or 'weight' not in data:
            await message.reply("Недостаточно данных для расчета калорий.")
            return
        age = data['age']
        growth = data['growth']
        weight = data['weight']
        gender = data['gender']

        if gender == "female":
            # Формула Миффлина - Сан Жеора для женщин
            calories = 10 * weight + 6.25 * growth - 5 * age - 161
        elif gender == "male":
            # Формула Миффлина - Сан Жеора для мужчин
            calories = 10 * weight + 6.25 * growth - 5 * age + 5
        else:
            await message.reply("Неизвестный пол.")
            return

        await message.reply(f'Ваша норма калорий: {calories:.2f} ккал в день.')
        await self.state.clear()

# Обработчик команды /start
@dp.message(CommandStart())
async def cmd_start(message: Message):
    inline_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Рассчитать норму калорий", callback_data="calories")],
            [InlineKeyboardButton(text="Формулы расчёта", callback_data="formulas")],
            [InlineKeyboardButton(text="Информация", callback_data="info")]
        ]
    )
    await message.answer("Добро пожаловать! Выберите действие:", reply_markup=inline_keyboard)

# Обработчик callback-запроса для расчета калорий
@dp.callback_query(F.data == "calories")
async def set_gender(call: CallbackQuery, state: FSMContext):
    calculator = CalorieCalculator(state)
    await calculator.set_gender(call)

# Обработчик выбора пола
@dp.callback_query(F.data.in_({"female", "male"}))
async def set_age(call: CallbackQuery, state: FSMContext):
    calculator = CalorieCalculator(state)
    await calculator.set_age(call)

# Обработчик ввода возраста
@dp.message(StateFilter(Form.age))
async def process_age(message: Message, state: FSMContext):
    calculator = CalorieCalculator(state)
    await calculator.process_numeric_input(message, 'age', "Теперь введите ваш рост:", Form.growth)

# Обработчик ввода роста
@dp.message(StateFilter(Form.growth))
async def process_growth(message: Message, state: FSMContext):
    calculator = CalorieCalculator(state)
    await calculator.process_numeric_input(message, 'growth', "Теперь введите ваш вес:", Form.weight)

# Обработчик ввода веса
@dp.message(StateFilter(Form.weight))
async def process_weight(message: Message, state: FSMContext):
    calculator = CalorieCalculator(state)
    await calculator.process_numeric_input(message, 'weight', "Спасибо за информацию! Ваш возраст: {data['age']}, рост: {data['growth']}, вес: {data['weight']}", None, calculator.calculate_calories)

# Обработчик callback-запроса для формул
@dp.callback_query(F.data == "formulas")
async def get_formulas(call: CallbackQuery):
    formula_women = "Формула Миффлина-Сан Жеора для женщин:\n" \
                    "10 * вес (кг) + 6.25 * рост (см) - 5 * возраст (лет) - 161"
    formula_men = "Формула Миффлина-Сан Жеора для мужчин:\n" \
                  "10 * вес (кг) + 6.25 * рост (см) - 5 * возраст (лет) + 5"
    await call.message.answer(f"{formula_women}\n\n{formula_men}")
    await call.answer()

# Обработчик callback-запроса для кнопки "Информация"
@dp.callback_query(F.data == "info")
async def show_info(call: CallbackQuery):
    await call.message.answer("Этот бот помогает рассчитать ваши ежедневные потребности в калориях.")
    await call.answer()

# Функция для перехвата сообщений
@dp.message()
async def handle_message(message: Message):
    await message.answer('Привет! Я бот, который поможет тебе рассчитать норму калорий. \nИспользуй команду /start, чтобы начать.')

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())