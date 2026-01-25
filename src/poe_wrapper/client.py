# poe_client.py
"""
Асинхронная прослойка для Poe REST API.
Требования: pip install aiohttp python-dotenv
"""

import os
import json
import aiohttp
from dotenv import load_dotenv
from dataclasses import dataclass, field
from typing import Optional

# Загрузка API ключа
load_dotenv()
POE_API_KEY = os.getenv("POE_API_KEY")

@dataclass
class HistoryEntry:
    role: str
    content: str

@dataclass 
class PoeClient:
    """Клиент для работы с Poe API."""
    
    base_url: str = "https://api.poe.com"
    default_model: str = "Claude-Sonnet-4"
    api_key: str = field(default_factory=lambda: POE_API_KEY)
    
    # Статистика
    call_count: int = 0
    total_points: int = 0
    history: list = field(default_factory=list)
    
    # Кэш моделей
    _models_cache: dict = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.api_key:
            raise ValueError("POE_API_KEY не найден в .env")
        self._headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    # === Список моделей ===
    async def get_models(self, force_refresh: bool = False) -> dict:
        """
        Получить список доступных моделей.
        Кэширует результат для повторных вызовов.
        """
        if self._models_cache and not force_refresh:
            return self._models_cache
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/v1/models",
                headers=self._headers
            ) as resp:
                if resp.status != 200:
                    raise Exception(f"Ошибка получения моделей: {resp.status}")
                data = await resp.json()
        
        # Парсим модели в удобный формат
        for model in data.get("data", []):
            model_id = model["id"]
            self._models_cache[model_id] = {
                "description": model.get("description", ""),
                "owner": model.get("owned_by", ""),
                "input_modalities": model.get("architecture", {}).get("input_modalities", ["text"]),
                "output_modalities": model.get("architecture", {}).get("output_modalities", ["text"]),
                "pricing": model.get("pricing"),
                # Простые флаги (на основе описания/имени)
                "supports_thinking": "thinking" in model.get("description", "").lower() 
                                    or "reason" in model.get("description", "").lower(),
                "supports_web": "web" in model.get("description", "").lower() 
                               or "search" in model.get("description", "").lower(),
            }
        
        return self._models_cache
    
    # === Отправка сообщения ===
    async def send_message(
        self, 
        message: str, 
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        use_history: bool = True
    ) -> str:
        """
        Отправить сообщение модели и получить текстовый ответ.
        """
        model = model or self.default_model
        
        # Проверка существования модели
        if self._models_cache and model not in self._models_cache:
            await self.get_models()
            if model not in self._models_cache:
                raise ValueError(f"Модель '{model}' не найдена. Доступные: {list(self._models_cache.keys())[:10]}...")
        
        # Экранирование проблемных символов в JSON
        safe_message = message.replace("\\", "\\\\").replace('"', '\\"')
        
        # Собираем сообщения (с историей или без)
        messages = []
        if use_history:
            for entry in self.history:
                messages.append({"role": entry.role, "content": entry.content})
        messages.append({"role": "user", "content": message})
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/v1/chat/completions",
                headers=self._headers,
                json=payload
            ) as resp:
                data = await resp.json()
                
                if resp.status == 429:
                    raise Exception("Rate limit exceeded. Подождите и попробуйте снова.")
                elif resp.status == 402:
                    raise Exception("Недостаточно поинтов на балансе.")
                elif resp.status == 401:
                    raise Exception("Неверный API ключ.")
                elif resp.status != 200:
                    error_msg = data.get("error", {}).get("message", str(data))
                    raise Exception(f"Ошибка API ({resp.status}): {error_msg}")
        
        # Извлекаем текст ответа
        response_text = data["choices"][0]["message"]["content"]
        
        # Обновляем статистику
        self.call_count += 1
        usage = data.get("usage", {})
        self.total_points += usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)
        
        # Добавляем в историю
        self._add_to_history("user", message)
        self._add_to_history("assistant", response_text)
        
        return response_text
    
    # === История ===
    def _add_to_history(self, role: str, content: str):
        """Добавить запись в историю."""
        self.history.append(HistoryEntry(role=role, content=content))
    
    def get_history(self, count: Optional[int] = None) -> list:
        """Получить историю (всю или последние N записей)."""
        if count is None:
            return self.history
        return self.history[-count:]
    
    def clear_history(self):
        """Очистить историю."""
        self.history = []
    
    # === Статистика ===
    def get_call_count(self) -> int:
        """Получить количество вызовов."""
        return self.call_count
    
    def get_local_tokens(self) -> int:
        """Получить локальный счётчик токенов."""
        return self.total_points
    
    async def get_points_spent(self, limit: Optional[int] = None) -> int:
        """
        Получить сумму потраченных поинтов из API.
        limit - количество последних записей для суммирования.
        """
        limit = limit or self.call_count or 20
        limit = min(limit, 100)  # API max
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/usage/points_history",
                headers=self._headers,
                params={"limit": limit}
            ) as resp:
                if resp.status != 200:
                    raise Exception(f"Ошибка получения истории: {resp.status}")
                data = await resp.json()
        
        total = sum(entry.get("cost_points", 0) for entry in data.get("data", []))
        return total
    
    async def get_balance(self) -> int:
        """Получить текущий баланс поинтов."""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/usage/current_balance",
                headers=self._headers
            ) as resp:
                if resp.status != 200:
                    raise Exception(f"Ошибка получения баланса: {resp.status}")
                data = await resp.json()
        
        return data.get("current_point_balance", 0)
    
    # === Сброс статистики ===
    def reset_stats(self):
        """Сбросить всю статистику и историю."""
        self.call_count = 0
        self.total_points = 0
        self.history = []