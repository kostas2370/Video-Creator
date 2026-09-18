import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

ENV = os.getenv("ENV", "dev")

if ENV == "prod":
    from .production import *  # noqa: F401,F403
else:
    from .local import *  # noqa: F401,F403
