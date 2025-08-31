import time
from aiogram import BaseMiddleware
from typing import Callable, Dict, Any, Awaitable

from ..config import RATE_LIMIT_COUNT, RATE_LIMIT_SECONDS
from ..db import add_rate_event, count_recent_rate_events, prune_rate_events

class RateLimitMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: Dict[str, Any]
    ) -> Any:
        user = getattr(event, "from_user", None)
        if user is None:
            return await handler(event, data)

        now = time.time()
        window_start = now - RATE_LIMIT_SECONDS

        await prune_rate_events(window_start)
        await add_rate_event(user.id, now)
        cnt = await count_recent_rate_events(user.id, window_start)
        if cnt > RATE_LIMIT_COUNT:
            try:
                await event.answer("Слишком много действий. Попробуй чуть позже.")
            except Exception:
                pass
            return
        return await handler(event, data)
