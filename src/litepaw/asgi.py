# -*- coding: utf-8 -*-
"""ASGI application entry point for uvicorn/gunicorn.

Usage:
    uvicorn litepaw.asgi:app --host 0.0.0.0 --port 8765
"""

import os
from litepaw.config.settings import Settings
from litepaw.server.ws_server import create_app

# Load settings from environment or config file
app = create_app(Settings.from_env())
