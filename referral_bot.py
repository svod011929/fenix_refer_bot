import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, Message
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.middleware import BaseMiddleware
from config import BOT_TOKEN, ADMINS
from aiogram import Router

# Логирование
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

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

# Middleware для логирования
class LoggingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        logging.info(f"Обработка события: {event}")
        return await handler(event, data)

dp.message.middleware(LoggingMiddleware())

# Проверка прав администратора
def is_admin(user_id: int) -> bool:
    return user_id in ADMINS

# Главное меню
def get_main_menu(user_id: int) -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text="Баланс"), KeyboardButton(text="Мои рефералы")],
        [KeyboardButton(text="Реферальная ссылка"), KeyboardButton(text="Мой уровень")]
    ]
    if is_admin(user_id):
        keyboard.append([KeyboardButton(text="Админ-панель")])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

# Команда /start
@dp.message(Command("start"))
async def start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username
    args = message.text.split()[1] if len(message.text.split()) > 1 else None

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
@dp.message(lambda message: message.text == "Баланс")
async def balance(message: Message):
    user_id = message.from_user.id
    balance = users[user_id]["balance"]
    await message.answer(f"Ваш баланс: {balance} рублей.")

# Команда "Мои рефералы"
@dp.message(lambda message: message.text == "Мои рефералы")
async def my_refs(message: Message):
    user_id = message.from_user.id
    refs = [u["username"] for u in users.values() if u["referrer_id"] == user_id]
    if refs:
        await message.answer(f"Ваши рефералы:\n" + "\n".join(refs))
    else:
        await message.answer("У вас пока нет рефералов.")

# Команда "Реферальная ссылка"
@dp.message(lambda message: message.text == "Реферальная ссылка")
async def referral_link(message: Message):
    user_id = message.from_user.id
    await message.answer(f"Ваша реферальная ссылка: https://t.me/{bot.username}?start={user_id}")

# Команда "Мой уровень"
@dp.message(lambda message: message.text == "Мой уровень")
async def my_level(message: Message):
    user_id = message.from_user.id
    level = users[user_id]["level"]
    await message.answer(f"Ваш уровень: {level}. Бонус за реферала: {LEVELS[level]['bonus']} рублей.")

# Админ-панель
@dp.message(lambda message: message.text == "Админ-панель" and is_admin(message.from_user.id))
async def admin_panel(message: Message):
    keyboard = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="Добавить баланс"), KeyboardButton(text="Списать баланс")],
        [KeyboardButton(text="Рассылка"), KeyboardButton(text="Главное меню")]
    ], resize_keyboard=True)
    await message.answer("Админ-панель:", reply_markup=keyboard)

# Админ-панель: добавление баланса
@dp.message(lambda message: message.text == "Добавить баланс" and is_admin(message.from_user.id))
async def admin_add_balance(message: Message):
    await message.answer("Введите ID пользователя и сумму для начисления (например, 123456 100):")

@dp.message(lambda message: is_admin(message.from_user.id) and message.text.split()[0].isdigit())
async def add_balance(message: Message):
    user_id, amount = map(int, message.text.split())
    users[user_id]["balance"] += amount
    transactions.append((user_id, amount, "Административное начисление"))
    await message.answer(f"Баланс пользователя {user_id} увеличен на {amount} рублей.")

# Админ-панель: рассылка сообщений
@dp.message(lambda message: message.text == "Рассылка" and is_admin(message.from_user.id))
async def admin_broadcast(message: Message):
    await message.answer("Введите сообщение для рассылки:")

@dp.message(lambda message: is_admin(message.from_user.id) and not message.text.startswith("/"))
async def broadcast_message(message: Message):
    for user_id in users:
        try:
            await bot.send_message(user_id, message.text)
        except Exception as e:
            logging.error(f"Ошибка при отправке сообщения пользователю {user_id}: {e}")
    await message.answer("Рассылка завершена.")

# Возврат в главное меню
@dp.message(lambda message: message.text == "Главное меню")
async def main_menu(message: Message):
    await message.answer("Выберите действие:", reply_markup=get_main_menu(message.from_user.id))

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
