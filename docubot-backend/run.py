"""
Development entry point for DocuBot backend on Windows.

Why this file exists
--------------------
`uvicorn app.main:app --reload` spawns a WatchFiles reloader in the current
process and a separate worker child process. On Windows with Python 3.12+,
the worker child needs to be told to use asyncio's ProactorEventLoop (which
asyncpg requires) BEFORE uvicorn creates its own event loop.

The correct way to do this is NOT `asyncio.set_event_loop_policy(...)` which
is deprecated and only affects the process it's called in. Instead, we pass
`--loop asyncio` to uvicorn, which internally calls
`asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())` in the
worker before starting — on Windows 3.12+ this IS the ProactorEventLoop by
default, so no extra policy call is needed.

Usage
-----
    uv run python run.py            # development (reload on)
    uv run python run.py --prod     # production-like (no reload, workers=4)

Or skip this file entirely and use uvicorn directly:
    uv run uvicorn app.main:app --reload --app-dir src --loop asyncio
"""

import sys
import uvicorn

# Validate we're not accidentally running this in production via a wrong command
if __name__ == "__main__":
    prod_mode = "--prod" in sys.argv

    if prod_mode:
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8001,
            app_dir="src",
            loop="asyncio",       # critical on Windows: tells uvicorn which loop to use
            workers=4,
            reload=False,
            access_log=True,
        )
    else:
        uvicorn.run(
            "app.main:app",
            host="localhost",
            port=8001,
            app_dir="src",
            loop="asyncio",       # critical: worker process uses asyncio's ProactorEventLoop
            reload=True,
            reload_dirs=["src"],
            access_log=True,
        )