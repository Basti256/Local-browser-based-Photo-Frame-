"""Festgelegte Pfade relativ zur Installationswurzel."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
WEB_DIR = BASE_DIR / "web"
PROJECTS_DIR = BASE_DIR / "projects"
BIN_DIR = BASE_DIR / "bin"
DEPLOY_DIR = BASE_DIR / "deploy"

RUNTIME_FILE = DATA_DIR / "runtime.json"
AUTH_FILE = DATA_DIR / "auth.json"
SECRET_FILE = DATA_DIR / "secret.key"


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
