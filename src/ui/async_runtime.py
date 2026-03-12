"""
비동기 런타임 설정.

sniffio 패치 + 백그라운드 이벤트 루프.
반드시 다른 라이브러리보다 먼저 import해야 한다.
"""

import asyncio
import threading

# ── sniffio 패치 ──
# Streamlit Cloud(uvloop)에서 sniffio가 비동기 백엔드를 감지하지 못하는 문제를 해결.
import sniffio

_sniffio_original = sniffio.current_async_library


def _patched_sniffio():
    try:
        return _sniffio_original()
    except sniffio.AsyncLibraryNotFoundError:
        return "asyncio"


sniffio.current_async_library = _patched_sniffio

# ── 백그라운드 이벤트 루프 ──
# uvloop(Streamlit Cloud)과 완전히 분리된 별도 루프이므로 nest_asyncio 불필요.
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx

_bg_loop = asyncio.DefaultEventLoopPolicy().new_event_loop()


def _run_loop():
    asyncio.set_event_loop(_bg_loop)
    _bg_loop.run_forever()


_bg_thread = threading.Thread(target=_run_loop, daemon=True)
_bg_thread.start()


def run_async(coro):
    """백그라운드 표준 asyncio 루프에서 코루틴을 실행한다."""
    ctx = get_script_run_ctx()

    async def _with_ctx():
        add_script_run_ctx(threading.current_thread(), ctx)
        return await coro

    future = asyncio.run_coroutine_threadsafe(_with_ctx(), _bg_loop)
    return future.result()
