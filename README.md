# Telegram Referral Bot от Fenix.dev

Этот бот реализует реферальную систему с начислением вознаграждений, админ-панелью, функцией рассылки и системой уровней для рефералов.

## Установка

1. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```

2. Заполните файл `config.py`:
   - `BOT_TOKEN`: Токен вашего бота.
   - `ADMINS`: Список ID администраторов.

3. Запустите бота:
   ```bash
   python referral_bot.py
   ```
### Автоматическая установка

1. На сервере выполните команду для автоматической установки:
   ```bash
   bash <(curl -s https://raw.githubusercontent.com/svod011929/fenix_refer_bot/main/install_bot.sh)
   ```

2. После установки бот будет запущен и настроен на авторестарт через `systemd`.

### Пример использования:
1. Запуск сервиса:
   ```bash
   sudo systemctl start referral_bot.service
   ```

2. Проверка статуса:
   ```bash
   sudo systemctl status referral_bot.service
   ```

3. Перезапуск сервиса:
   ```bash
   sudo systemctl restart referral_bot.service
   ```

4. Остановка сервиса:
   ```bash
   sudo systemctl stop referral_bot.service
   ```

5. Просмотр логов:
   ```bash
   sudo journalctl -u referral_bot.service
   ```
