"""
Development entry point for DocuBot backend.
"""

import sys
import uvicorn


def start():
    """Start the FastAPI application with Uvicorn."""
    prod_mode = "--prod" in sys.argv

    if prod_mode:
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8001,
            app_dir="src",
            loop="asyncio",
            workers=4,
            reload=False,
            access_log=True,
            log_level="info",
        )
    else:
        uvicorn.run(
            "app.main:app",
            host="localhost",
            port=8001,
            app_dir="src",
            loop="asyncio",
            reload=True,
            reload_dirs=["src"],
            reload_excludes=[
                "*.log",
                "logs/*",
                "*.pyc",
                "*__pycache__*",
                "*.pyo",
                "*.sqlite",
                "*.db",
                ".pytest_cache/*",
            ],
            log_level="info",
            access_log=True,
        )


if __name__ == "__main__":
    start()