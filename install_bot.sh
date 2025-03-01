# install_bot.sh
#!/bin/bash

# Установка зависимостей
sudo apt update
sudo apt install -y python3 python3-pip git

# Клонирование репозитория
git clone https://github.com/svod011929/fenix_refer_bot.git /root/referral_bot
cd /root/referral_bot

# Установка Python-зависимостей
pip3 install -r requirements.txt

# Настройка systemd
sudo cp systemd/referral_bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl start referral_bot.service
sudo systemctl enable referral_bot.service

echo "Бот успешно установлен и запущен!"
