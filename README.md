# poe-wrapper

Асинхронная Python-обёртка для Poe REST API.

## Установка

```bash
uv add "git+ssh://git@codeberg.org/femto/poe_wrapper.git"
```

Или в `pyproject.toml` вашего проекта:

```toml
[project]
dependencies = [
    "poe-wrapper @ git+ssh://git@codeberg.org/femto/poe_wrapper.git",
]
```

## Настройка

Создайте `.env` файл в корне проекта:

```bash
POE_API_KEY="ваш-ключ-от-poe"
```

## Использование

```python
import asyncio
from poe_wrapper import PoeClient

async def main():
    client = PoeClient(default_model="gemini-2.5-flash-lite")
    
    # Проверка баланса
    balance = await client.get_balance()
    print(f"Баланс: {balance:,} поинтов")
    
    # Список моделей
    models = await client.get_models()
    print(f"Доступно моделей: {len(models)}")
    
    # Отправка сообщения
    response = await client.send_message("Привет!")
    print(response)
    
    # С параметрами
    response = await client.send_message(
        "Объясни квантовую физику",
        model="gemini-3-flash",
        temperature=0.5,
        max_tokens=4096
    )
    
    # Статистика
    print(f"Вызовов: {client.get_call_count()}")
    print(f"Токенов: {client.get_local_tokens()}")
    
    # Потраченные поинты (из API)
    spent = await client.get_points_spent()
    print(f"Потрачено: {spent:,} поинтов")

asyncio.run(main())
```

## API

### PoeClient

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| `default_model` | `str` | `"gemini-3-flash"` | Модель по умолчанию |
| `base_url` | `str` | `"https://api.poe.com"` | URL API |

### Методы

| Метод | Описание |
|-------|----------|
| `send_message(message, model?, temperature?, max_tokens?, use_history?)` | Отправить сообщение |
| `get_models(force_refresh?)` | Список доступных моделей (кэшируется) |
| `get_balance()` | Текущий баланс поинтов |
| `get_points_spent(limit?)` | Сумма потраченных поинтов |
| `get_history(count?)` | История сообщений сессии |
| `clear_history()` | Очистить историю |
| `reset_stats()` | Сбросить статистику и историю |

## Требования

- Python ≥ 3.13.11
- aiohttp
- fastapi-poe
- python-dotenv