# ValutaTrade Hub

Платформа для отслеживания и симуляции торговли валютами с поддержкой фиатных и криптовалют.

## Идея проекта

ValutaTrade Hub - это платформа, которая позволяет пользователям:
- Регистрироваться и управлять виртуальным портфелем валют
- Совершать сделки по покупке/продаже валют
- Отслеживать актуальные курсы в реальном времени
- Работать как с фиатными (USD, EUR, GBP, RUB, JPY), так и с криптовалютами (BTC, ETH, LTC, ADA)

Система состоит из двух основных сервисов:
- **Core Service** - основное приложение с CLI интерфейсом
- **Parser Service** - микросервис для получения актуальных курсов валют

## Структура проекта
```markdown
finalproject_vakhnenko_m25-555/
│
├── data/ # Хранилище данных
│ ├── users.json # пользователи системы
│ ├── portfolios.json # портфели и кошельки
│ ├── rates.json # локальный кэш текущих курсов
│ └── exchange_rates.json # исторические данные парсера
│
├── logs/ # Логи приложения
│ └── actions.log
│
├── valutatrade_hub/ # Основной код проекта
│ ├── logging_config.py # настройка логирования
│ ├── decorators.py # декораторы для логирования операций
│ ├── core/ # Бизнес-логика
│ │ ├── currencies.py # иерархия валют (Currency, FiatCurrency, CryptoCurrency)
│ │ ├── exceptions.py # пользовательские исключения
│ │ ├── models.py # модели данных (User, Wallet, Portfolio)
│ │ ├── usecases.py # бизнес-логика операций
│ │ └── utils.py # вспомогательные функции
│ ├── infra/ # Инфраструктура
│ │ ├── settings.py # Singleton SettingsLoader
│ │ └── database.py # Singleton DatabaseManager
│ ├── parser_service/ # Сервис парсинга курсов
│ │ ├── config.py # конфигурация API
│ │ ├── api_clients.py # клиенты внешних API
│ │ ├── updater.py # логика обновления курсов
│ │ └── storage.py # работа с хранилищем
│ └── cli/
│ └── interface.py # CLI интерфейс
│
├── config.json #файл с конфигурацией приложения
├── main.py # Точка входа
├── Makefile # Автоматизация задач
├── pyproject.toml # Конфигурация Poetry
└── README.md # Документация
```

## Установка

### Предварительные требования
- Python 3.8+
- Poetry (менеджер зависимостей)

### Установка зависимостей
```bash
# Установка через Makefile
make install

# Или напрямую через Poetry
poetry install
```

## Запуск

```bash
# Запуск через Makefile
make project

# Или напрямую через Poetry
poetry run python main.py
```

## Дополнительные команды Makefile
```bash
make install      # Установка зависимостей через Poetry
make project      # Запуск проекта в интерактивном режиме
make build        # Сборка пакета для распространения
make publish      # Публикация пакета в репозиторий (если настроено)
make package-install # Установка собранного пакета через pip
make lint         # Проверка кода линтером (ruff)
```

## Поддерживаемые валюты
### Фиатные валюты
USD (базовая), EUR, GBP, RUB, JPY

### Криптовалюты
BTC (Bitcoin), ETH (Ethereum), LTC (Litecoin), ADA (Cardano)

## TTL (Time To Live)
Курсы считаются "свежими" в течение 5 минут (300 секунд)
По истечении TTL система предлагает обновить данные
TTL настраивается в infra/settings.py

## Обработка ошибок
Система обрабатывает следующие ошибки:

 - InsufficientFundsError - недостаточно средств
 - CurrencyNotFoundError - неизвестная валюта
 - ApiRequestError - ошибки внешних API
 - UserNotFoundError - пользователь не найден
 - InvalidPasswordError - неверный пароль

##  Логирование
Логи хранятся в logs/actions.log
Формат: LEVEL TIMESTAMP LOGGER_NAME MESSAGE
Логируются все ключевые операции (регистрация, вход, покупка, продажа)

## Как подключить собственный ключ API
Создайте файл .env в корне проекта и пропишите там переменную 

EXCHANGERATE_API_KEY=<Ваш ключ API>

## Команды
### Основные операции 
```bash
# Регистрация
register --username <username> --password <password>

# Вход в систему  
login --username <username> --password <password>

# Просмотр портфеля
show-portfolio [--base <currency>]

# Покупка валюты
buy --currency <code> --amount <amount>

# Продажа валюты
sell --currency <code> --amount <amount>

# Получение курса
get-rate --from <currency> --to <currency>
```
### Работа с курсами 
```bash
# Обновление всех курсов
update-rates

# Обновление только криптовалют
update-rates --source coingecko

# Обновление только фиатных валют  
update-rates --source exchangerate

# Просмотр кэшированных курсов
show-rates [--currency <code>] [--top <N>] [--base <currency>]

# Список поддерживаемых валют
list-currencies
```
## Примеры использования
### 
```bash
# Полный цикл работы
register --username alice --password 1234
login --username alice --password 1234
update-rates
buy --currency BTC --amount 0.01
buy --currency EUR --amount 100
show-portfolio
sell --currency BTC --amount 0.005
show-portfolio --base EUR
```
### Аскинема

[![asciicast](https://asciinema.org/a/6EXpARlOBJ6TQpXb.svg)](https://asciinema.org/a/6EXpARlOBJ6TQpXb)

