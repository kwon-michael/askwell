import os

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+psycopg://askwell:askwell@localhost:5432/askwell"
)
JWT_SECRET = os.environ.get("JWT_SECRET", "dev-only-secret-change-me-in-production")
JWT_TTL_HOURS = int(os.environ.get("JWT_TTL_HOURS", "72"))
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")
