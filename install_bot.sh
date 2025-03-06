#!/bin/bash

# Установка зависимостей
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git

# Клонирование репозитория
git clone https://github.com/svod011929/fenix_refer_bot.git /root/referral_bot
cd /root/referral_bot

# Создание виртуального окружения
python3 -m venv venv
source /root/referral_bot/venv/bin/activate

# Установка Python-зависимостей внутри виртуального окружения
pip install -r requirements.txt

# Настройка systemd
sudo cp systemd/referral_bot.service /etc/systemd/system/

# Обновление пути к Python и активации виртуального окружения в сервисе
sudo sed -i "s|ExecStart=/usr/bin/python3 /root/referral_bot/referral_bot.py|ExecStart=/root/referral_bot/venv/bin/python3 /root/referral_bot/referral_bot.py|" /etc/systemd/system/referral_bot.service

# Перезагрузка и запуск сервиса
sudo systemctl daemon-reload
sudo systemctl start referral_bot.service
sudo systemctl enable referral_bot.service

echo "Бот успешно установлен и запущен в виртуальном окружении!"
