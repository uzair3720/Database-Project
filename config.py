"""
config.py
Loads values from .env via python-dotenv and exposes them as constants
the rest of the app imports. We keep it tiny on purpose -- one source of
truth for secrets and paths.
"""

import os
from dotenv import load_dotenv

# Read .env into os.environ. If .env is missing we still fall back to
# whatever is already in the environment, which is what we want in
# production where secrets are injected by the host.
load_dotenv()


# Flask --------------------------------------------------------------
SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev-secret-do-not-use-in-prod")


# Database -----------------------------------------------------------
DB_HOST     = os.environ.get("DB_HOST",     "localhost")
DB_PORT     = int(os.environ.get("DB_PORT", "5432"))
DB_NAME     = os.environ.get("DB_NAME",     "lmp_db")
DB_USER     = os.environ.get("DB_USER",     "lmp_user")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "lmp_pass")


# Uploads ------------------------------------------------------------
# We resolve UPLOAD_FOLDER relative to the project root so the app runs
# the same way from any working directory.
PROJECT_ROOT  = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(PROJECT_ROOT, os.environ.get("UPLOAD_FOLDER", "uploads"))

MAX_UPLOAD_MB    = int(os.environ.get("MAX_UPLOAD_MB", "16"))
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024

# File types we accept for attachments and submissions. Keep it boring
# and document-shaped -- we are not a media platform.
ALLOWED_EXTENSIONS = {
    "pdf", "doc", "docx", "txt", "md",
    "zip", "rar", "7z",
    "py", "ipynb", "c", "cpp", "h", "java", "sql",
    "png", "jpg", "jpeg", "gif",
}
