"""Compatibility entrypoint — delegates to the minimal local web UI.

Prefer: ``python webapp.py`` or ``python shortstory.py``.
This module exists so older docs/commands that say ``python app.py`` still work.
"""

from __future__ import annotations

import os

from webapp import app, create_app

__all__ = ["app", "create_app"]


if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "5000"))
    app.run(host=host, port=port, debug=os.getenv("FLASK_ENV") == "development")
