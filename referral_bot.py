import logging
from aiogram import Bot, Dispatcher, types
from aiogram.middlewares import LoggingMiddleware
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
from config import BOT_TOKEN, ADMINS

# Логирование
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

# Уровни и бонусы
LEVELS = {
    1: {"bonus": 100, "required_refs": 0},
    2: {"bonus": 200, "required_refs": 5},
    3: {"bonus": 300, "required_refs": 10},
    4: {"bonus": 500, "required_refs": 20},
}

# База данных (в памяти для примера)
users = {}
transactions = []

# Проверка прав администратора
def is_admin(user_id: int) -> bool:
    return user_id in ADMINS

# Главное меню
def get_main_menu(user_id: int) -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("Баланс"), KeyboardButton("Мои рефералы")],
        [KeyboardButton("Реферальная ссылка"), KeyboardButton("Мой уровень")]
    ]
    if is_admin(user_id):
        keyboard.append([KeyboardButton("Админ-панель")])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Команда /start
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username
    args = message.get_args()

    if user_id not in users:
        users[user_id] = {"username": username, "balance": 0, "referrer_id": None, "level": 1}

    if args:
        referrer_id = int(args)
        if referrer_id != user_id:
            users[user_id]["referrer_id"] = referrer_id

            # Начисление вознаграждения рефереру
            referrer_level = users[referrer_id]["level"]
            bonus = LEVELS[referrer_level]["bonus"]
            users[referrer_id]["balance"] += bonus
            transactions.append((referrer_id, bonus, f"Реферальное вознаграждение за пользователя {username}"))

            # Проверка уровня реферера
            ref_count = sum(1 for u in users.values() if u["referrer_id"] == referrer_id)
            for level, data in LEVELS.items():
                if ref_count >= data["required_refs"]:
                    users[referrer_id]["level"] = level

            await message.answer(f"Вы присоединились по реферальной ссылке пользователя {referrer_id}.")
        else:
            await message.answer("Вы не можете использовать свою собственную реферальную ссылку.")
    else:
        await message.answer(f"Добро пожаловать! Ваша реферальная ссылка: https://t.me/{bot.username}?start={user_id}")

    await message.answer("Выберите действие:", reply_markup=get_main_menu(user_id))

# Команда "Баланс"
@dp.message_handler(lambda message: message.text == "Баланс")
async def balance(message: types.Message):
    user_id = message.from_user.id
    balance = users[user_id]["balance"]
    await message.answer(f"Ваш баланс: {balance} рублей.")

# Команда "Мои рефералы"
@dp.message_handler(lambda message: message.text == "Мои рефералы")
async def my_refs(message: types.Message):
    user_id = message.from_user.id
    refs = [u["username"] for u in users.values() if u["referrer_id"] == user_id]
    if refs:
        await message.answer(f"Ваши рефералы:\n" + "\n".join(refs))
    else:
        await message.answer("У вас пока нет рефералов.")

# Команда "Реферальная ссылка"
@dp.message_handler(lambda message: message.text == "Реферальная ссылка")
async def referral_link(message: types.Message):
    user_id = message.from_user.id
    await message.answer(f"Ваша реферальная ссылка: https://t.me/{bot.username}?start={user_id}")

# Команда "Мой уровень"
@dp.message_handler(lambda message: message.text == "Мой уровень")
async def my_level(message: types.Message):
    user_id = message.from_user.id
    level = users[user_id]["level"]
    await message.answer(f"Ваш уровень: {level}. Бонус за реферала: {LEVELS[level]['bonus']} рублей.")
# Админ-панель
@dp.message_handler(lambda message: message.text == "Админ-панель" and is_admin(message.from_user.id))
async def admin_panel(message: types.Message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("Добавить баланс"), KeyboardButton("Списать баланс"))
    keyboard.add(KeyboardButton("Рассылка"), KeyboardButton("Главное меню"))
    await message.answer("Админ-панель:", reply_markup=keyboard)

# Админ-панель: добавление баланса
@dp.message_handler(lambda message: message.text == "Добавить баланс" and is_admin(message.from_user.id))
async def admin_add_balance(message: types.Message):
    await message.answer("Введите ID пользователя и сумму для начисления (например, 123456 100):")

@dp.message_handler(lambda message: is_admin(message.from_user.id) and message.text.split()[0].isdigit())
async def add_balance(message: types.Message):
    user_id, amount = map(int, message.text.split())
    users[user_id]["balance"] += amount
    transactions.append((user_id, amount, "Административное начисление"))
    await message.answer(f"Баланс пользователя {user_id} увеличен на {amount} рублей.")

# Админ-панель: рассылка сообщений
@dp.message_handler(lambda message: message.text == "Рассылка" and is_admin(message.from_user.id))
async def admin_broadcast(message: types.Message):
    await message.answer("Введите сообщение для рассылки:")

@dp.message_handler(lambda message: is_admin(message.from_user.id) and not message.text.startswith("/"))
async def broadcast_message(message: types.Message):
    for user_id in users:
        try:
            await bot.send_message(user_id, message.text)
        except Exception as e:
            logging.error(f"Ошибка при отправке сообщения пользователю {user_id}: {e}")
    await message.answer("Рассылка завершена.")

# Возврат в главное меню
@dp.message_handler(lambda message: message.text == "Главное меню")
async def main_menu(message: types.Message):
    await message.answer("Выберите действие:", reply_markup=get_main_menu(message.from_user.id))

# Запуск бота
if name == 'main':
    executor.start_polling(dp, skip_updates=True)
