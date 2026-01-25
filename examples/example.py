# example.py
import asyncio
from poe_wrapper import PoeClient

async def main():
    # Создаём клиент
    client = PoeClient(default_model="gemini-2.5-flash-lite")
    
    # Проверяем баланс
    balance = await client.get_balance()
    print(f"💰 Баланс: {balance:,} поинтов\n")
    
    # Получаем список моделей (кэшируется)
    models = await client.get_models()
    print(f"📦 Доступно моделей: {len(models)}")
    print(f"   Примеры: {list(models.keys())[:5]}\n")
    
    # Отправляем сообщение
    print("📤 Отправляю запрос...")
    response = await client.send_message("Привет! напиши три коротких и простейших шутки?")
    print(f"📥 Ответ:\n{response}\n")
    
    # Второе сообщение
    response2 = await client.send_message("Напиши длиный манускрипт, на 2 страницы, об альфа-центавре")
    print(f"📥 Ответ 2:\n{response2}\n")
    
    # Статистика
    print(f"📊 Статистика:")
    print(f"   Вызовов: {client.get_call_count()}")
    print(f"   Токенов (локально): {client.get_local_tokens()}")
    
    # История
    print(f"\n📜 История ({len(client.get_history())} записей):")
    for entry in client.get_history():
        preview = entry.content[:50] + "..." if len(entry.content) > 50 else entry.content
        print(f"   [{entry.role}]: {preview}")
    
    # Потраченные поинты из API
    spent = await client.get_points_spent()
    print(f"\n💸 Потрачено поинтов (API): {spent:,}")

if __name__ == "__main__":
    asyncio.run(main())