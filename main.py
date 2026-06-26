import sys
from pathlib import Path


backend_path = Path(__file__).parent / "backend"
sys.path.append(str(backend_path))

from app.main import app  # noqa: E402


__all__ = ["app"]
