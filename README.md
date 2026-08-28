<p align="center">
  <img src="assets/bpla24_logo.png" alt="БПЛА24 Логотип" width="160" />
</p>

<p align="center">
  <img src="assets/westand.svg" alt="We Stand With Russia" />
</p>

# 🛰 БПЛА24 — Мониторинг угроз БПЛА и ракетной опасности РФ

<p align="center">
  <a href="https://t.me/bpla24bot">
    <img src="https://img.shields.io/badge/Telegram_Bot-@bpla24bot-2CA5E0?style=flat&logo=telegram&logoColor=white" alt="Telegram Bot" />
  </a>
  <a href="https://github.com/ehristoforu/bpla24">
    <img src="https://img.shields.io/badge/Fork-ehristoforu%2Fbpla24-181717?style=flat&logo=github&logoColor=white" alt="Fork Repository" />
  </a>
  <a href="https://github.com/MahasheDev/Russia-Alert-Bot">
    <img src="https://img.shields.io/badge/Based_on-MahasheDev%2FRussia--Alert--Bot-800080?style=flat&logo=icloud&logoColor=white" alt="Fork Repository" />
  </a>
  <a href="https://github.com/aiogram/aiogram">
    <img src="https://img.shields.io/badge/aiogram-v3.20-2ba84a?style=flat&logo=telegram&logoColor=white" alt="aiogram v3" />
  </a>
  <a href="https://www.python.org/">
    <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat&logo=python&logoColor=white" alt="Python 3.10+" />
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/License-GPL--3.0-0055ff?style=flat" alt="License: GPL-3.0" />
  </a>
</p>

**БПЛА24** — модульный асинхронный Telegram-бот с открытым исходным кодом для непрерывного мониторинга воздушной обстановки, угроз атак БПЛА, ракетной опасности и сигналов тревоги по всей территории Российской Федерации.

---

## 🛡 О проекте и создателях

* **Кто мы:** Команда и создатели проекта — граждане Российской Федерации, постоянно проживающие и находящиеся на территории РФ.
* **Цель проекта:** Защита жизни и здоровья гражданского населения, обеспечение своевременной информацией об угрозах и повышение осведомленности граждан о правилах безопасного поведения.
* **Источники:** Бот агрегирует информацию исключительно из открытых публичных источников (МЧС РФ, региональные оперативные штабы, открытые сводки и открытый Public Read-Only API Radar Russia).

---

## ⚖️ Правовая информация и дисклеймер

1. **Неофициальный статус:** Бот **не является** государственной системой оповещения (ГО ЧС/МЧС) и носит исключительно информационный характер. В любых экстренных ситуациях руководствуйтесь официальными оповещениями экстренных служб.
2. **Снятие ответственности:** Авторы и разработчики не несут ответственности за любые последствия, прямой или косвенный ущерб при использовании сервиса или технических сбоях сторонних каналов связи.
3. **Законодательство РФ (Запрет на съемку):**
   * ⚠️ **Категорически запрещено** снимать и публиковать в открытый доступ фото и видео полетов БПЛА, ракет, работы систем ПВО и мест падения обломков.
   * Распространение таких материалов влечет уголовную и административную ответственность (вплоть до ст. 275, 283.1 УК РФ).
   * При обнаружении подозрительных объектов не приближайтесь к ним и звоните **112**.

---

## 🏗 Архитектура и принципы (SOLID, Clean Architecture)

Проект спроектирован по слоям с полным разделением ответственности:

```text
bpla24/
├── app/
│   ├── config/           # Управление настройками (Pydantic Settings)
│   ├── models/           # Схемы данных и доменные сущности (Pydantic)
│   ├── database/         # Асинхронный слой хранения данных (aiosqlite + Repository Pattern)
│   ├── ingestion/        # Адаптеры парсинга источников (Telegram, RSS, HTML, Radar Russia API)
│   ├── nlp/              # Очистка шума, классификация угроз, извлечение гео и дедупликация
│   ├── services/         # Бизнес-логика: мониторинг, очередь рассылки, форматирование, памятки
│   └── bot/              # Интерфейс Telegram: роутеры, хэндлеры, inline/reply клавиатуры, FSM
├── data/
│   ├── sources.json      # Конфигурация источников и 89 регионов РФ
│   └── alerts_bot.sqlite3# База данных SQLite
├── main.py               # Точка входа в приложение
├── requirements.txt      # Зависимости
├── Dockerfile            # Контейнеризация
├── docker-compose.yml    # Управление контейнером
├── bpla24.service        # Systemd unit для Linux
└── LICENSE               # GNU General Public License v3.0
```

---

## 🚀 Быстрый запуск

### Вариант 1: Запуск через Docker Compose (Рекомендуемый)

1. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/your-username/bpla24.git
   cd bpla24
   ```

2. Создайте файл `.env`:
   ```bash
   cp .env.example .env
   nano .env
   ```
   Укажите ваш токен Telegram:
   ```env
   TELEGRAM_BOT_TOKEN=1234567890:AAExampleTokenHere
   ```

3. Запустите контейнер:
   ```bash
   docker compose up -d --build
   ```

---

### Вариант 2: Классический запуск на Linux VPS

1. Установите Python и venv:
   ```bash
   sudo apt update && sudo apt install -y python3 python3-venv python3-pip
   ```

2. Подготовьте окружение:
   ```bash
   cd /opt
   git clone https://github.com/your-username/bpla24.git
   cd bpla24
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env
   nano .env
   ```

3. Запустите бота:
   ```bash
   python main.py
   ```

---

### Вариант 3: Автозапуск через Systemd

1. Скопируйте файл сервиса:
   ```bash
   sudo cp bpla24.service /etc/systemd/system/bpla24.service
   sudo systemctl daemon-reload
   sudo systemctl enable bpla24
   sudo systemctl start bpla24
   ```

2. Просмотр логов:
   ```bash
   sudo journalctl -u bpla24 -f
   ```

---

## 📱 Функционал бота

* 🇷🇺 **Режимы оповещений:** Выбор между оповещениями «Вся Россия» или «Только мой регион/город».
* ⚡️ **Live Radar Russia API:** Интеграция с публичным потоком и снимком активности радара.
* 🚨 **Памятка безопасности:** Интерактивное руководство по поведению в помещении, на улице, в автомобиле и при обнаружении обломков.
* ⚖️ **Правовая справка:** Разъяснение ответственности за публикацию фото/видео работы ПВО и мест падения.
* 📊 **Мгновенный статус:** Просмотр последних актуальных угроз по выбранному региону в один клик.

---

## 📄 Лицензия

Проект распространяется под свободной лицензией **GNU General Public License v3.0 (GPL-3.0)**. См. файл [LICENSE](LICENSE).
