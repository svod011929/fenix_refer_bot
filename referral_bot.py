import logging
import sqlite3
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Updater, CommandHandler, CallbackContext, ConversationHandler, MessageHandler, Filters
from config import BOT_TOKEN, ADMINS  # Импорт конфигурации

# Логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Состояния для админ-панели
ADD_BALANCE, REMOVE_BALANCE, BROADCAST_MESSAGE = range(3)

# Уровни и бонусы
LEVELS = {
    1: {"bonus": 100, "required_refs": 0},
    2: {"bonus": 200, "required_refs": 5},
    3: {"bonus": 300, "required_refs": 10},
    4: {"bonus": 500, "required_refs": 20},
}

# Подключение к базе данных
def get_db_connection():
    return sqlite3.connect('referral_bot.db')

# Проверка прав администратора
def is_admin(user_id: int) -> bool:
    return user_id in ADMINS

# Главное меню
def main_menu(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [KeyboardButton("Баланс"), KeyboardButton("Мои рефералы")],
        [KeyboardButton("Реферальная ссылка"), KeyboardButton("Мой уровень")]
    ]
    if is_admin(update.message.from_user.id):
        keyboard.append([KeyboardButton("Админ-панель")])

    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    update.message.reply_text("Выберите действие:", reply_markup=reply_markup)

# Команда /start
def start(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    username = update.message.from_user.username
    args = context.args

    conn = get_db_connection()
    cursor = conn.cursor()

    # Проверка, зарегистрирован ли пользователь
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()

    if not user:
        # Регистрация нового пользователя
        cursor.execute('INSERT INTO users (user_id, username) VALUES (?, ?)', (user_id, username))
        conn.commit()

    # Реферальная система
    if args:
        referrer_id = int(args[0])
        if referrer_id != user_id:
            cursor.execute('UPDATE users SET referrer_id = ? WHERE user_id = ?', (referrer_id, user_id))
            conn.commit()

            # Начисление вознаграждения рефереру
            cursor.execute('SELECT level FROM users WHERE user_id = ?', (referrer_id,))
            referrer_level = cursor.fetchone()[0]
            bonus = LEVELS[referrer_level]["bonus"]

            cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (bonus, referrer_id))
            cursor.execute('INSERT INTO transactions (user_id, amount, description) VALUES (?, ?, ?)',
                           (referrer_id, bonus, f'Реферальное вознаграждение за пользователя {username}'))
            conn.commit()

            # Проверка уровня реферера
            cursor.execute('SELECT COUNT(*) FROM users WHERE referrer_id = ?', (referrer_id,))
            ref_count = cursor.fetchone()[0]

            for level, data in LEVELS.items():
                if ref_count >= data["required_refs"]:
                    cursor.execute('UPDATE users SET level = ? WHERE user_id = ?', (level, referrer_id))
                    conn.commit()

            update.message.reply_text(f"Вы присоединились по реферальной ссылке пользователя {referrer_id}.")
        else:
            update.message.reply_text("Вы не можете использовать свою собственную реферальную ссылку.")
    else:
        update.message.reply_text(f"Добро пожаловать! Ваша реферальная ссылка: https://t.me/{context.bot.username}?start={user_id}")

    conn.close()
    main_menu(update, context)

# Команда "Баланс"
def balance(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
    balance = cursor.fetchone()[0]

    update.message.reply_text(f"Ваш баланс: {balance} рублей.")
    conn.close()

# Команда "Мои рефералы"
def my_refs(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT user_id, username FROM users WHERE referrer_id = ?', (user_id,))
    refs = cursor.fetchall()

    if refs:
        refs_list = "\n".join([f"{ref[1]} (ID: {ref[0]})" for ref in refs])
        update.message.reply_text(f"Ваши рефералы:\n{refs_list}")
    else:
        update.message.reply_text("У вас пока нет рефералов.")

    conn.close()

# Команда "Реферальная ссылка"
def referral_link(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    update.message.reply_text(f"Ваша реферальная ссылка: https://t.me/{context.bot.username}?start={user_id}")

# Команда "Мой уровень"
def my_level(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT level FROM users WHERE user_id = ?', (user_id,))
    level = cursor.fetchone()[0]

    update.message.reply_text(f"Ваш уровень: {level}. Бонус за реферала: {LEVELS[level]['bonus']} рублей.")
    conn.close()

# Админ-панель
def admin_panel(update: Update, context: CallbackContext) -> None:
    if not is_admin(update.message.from_user.id):
        update.message.reply_text("У вас нет прав администратора.")
        return

    keyboard = [
        [KeyboardButton("Добавить баланс"), KeyboardButton("Списать баланс")],
        [KeyboardButton("Рассылка"), KeyboardButton("Главное меню")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    update.message.reply_text("Админ-панель:", reply_markup=reply_markup)

# Админ-панель: добавление баланса
def admin_add_balance(update: Update, context: CallbackContext) -> int:
    if not is_admin(update.message.from_user.id):
        update.message.reply_text("У вас нет прав администратора.")
        return ConversationHandler.END

    update.message.reply_text("Введите ID пользователя и сумму для начисления (например, 123456 100):")
    return ADD_BALANCE

def add_balance(update: Update, context: CallbackContext) -> int:
    user_id, amount = map(int, update.message.text.split())

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
    cursor.execute('INSERT INTO transactions (user_id, amount, description) VALUES (?, ?, ?)',
                   (user_id, amount, 'Административное начисление'))
    conn.commit()

    update.message.reply_text(f"Баланс пользователя {user_id} увеличен на {amount} рублей.")
    conn.close()

    return ConversationHandler.END

# Админ-панель: удаление баланса
def admin_remove_balance(update: Update, context: CallbackContext) -> int:
    if not is_admin(update.message.from_user.id):
        update.message.reply_text("У вас нет прав администратора.")
        return ConversationHandler.END

    update.message.reply_text("Введите ID пользователя и сумму для списания (например, 123456 100):")
    return REMOVE_BALANCE

def remove_balance(update: Update, context: CallbackContext) -> int:
    user_id, amount = map(int, update.message.text.split())

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('UPDATE users SET balance = balance - ? WHERE user_id = ?', (amount, user_id))
    cursor.execute('INSERT INTO transactions (user_id, amount, description) VALUES (?, ?, ?)',
                   (user_id, -amount, 'Административное списание'))
    conn.commit()

    update.message.reply_text(f"Баланс пользователя {user_id} уменьшен на {amount} рублей.")
    conn.close()

    return ConversationHandler.END

# Админ-панель: рассылка сообщений
def admin_broadcast(update: Update, context: CallbackContext) -> int:
    if not is_admin(update.message.from_user.id):
        update.message.reply_text("У вас нет прав администратора.")
        return ConversationHandler.END

    update.message.reply_text("Введите сообщение для рассылки:")
    return BROADCAST_MESSAGE

def broadcast_message(update: Update, context: CallbackContext) -> int:
    message = update.message.text

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT user_id FROM users')
    users = cursor.fetchall()

    for user in users:
        try:
            context.bot.send_message(chat_id=user[0], text=message)
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения пользователю {user[0]}: {e}")

    update.message.reply_text("Рассылка завершена.")
    conn.close()

    return ConversationHandler.END

# Отмена
def cancel(update: Update, context: CallbackContext) -> int:
    update.message.reply_text("Действие отменено.")
    return ConversationHandler.END

# Основная функция
def main() -> None:
    updater = Updater(BOT_TOKEN)

    dispatcher = updater.dispatcher

    # Регистрация команд
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.text("Баланс"), balance))
    dispatcher.add_handler(MessageHandler(Filters.text("Мои рефералы"), my_refs))
    dispatcher.add_handler(MessageHandler(Filters.text("Реферальная ссылка"), referral_link))
    dispatcher.add_handler(MessageHandler(Filters.text("Мой уровень"), my_level))
    dispatcher.add_handler(MessageHandler(Filters.text("Админ-панель"), admin_panel))
    dispatcher.add_handler(MessageHandler(Filters.text("Главное меню"), main_menu))

    # Админ-панель
    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(Filters.text("Добавить баланс"), admin_add_balance),
            MessageHandler(Filters.text("Списать баланс"), admin_remove_balance),
            MessageHandler(Filters.text("Рассылка"), admin_broadcast)
        ],
        states={
            ADD_BALANCE: [MessageHandler(Filters.text & ~Filters.command, add_balance)],
            REMOVE_BALANCE: [MessageHandler(Filters.text & ~Filters.command, remove_balance)],
            BROADCAST_MESSAGE: [MessageHandler(Filters.text & ~Filters.command, broadcast_message)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    dispatcher.add_handler(conv_handler)

    # Запуск бота
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
