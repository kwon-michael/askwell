import os

DEV_JWT_SECRET = "dev-only-secret-change-me-in-production"



def sqlalchemy_url(url: str) -> str:
    # Hosted Postgres (Neon, Render, Heroku) hands out postgres:// or
    # postgresql:// URLs, which SQLAlchemy maps to psycopg2. We use psycopg 3.
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


APP_ENV = os.environ.get("APP_ENV", "development")
DATABASE_URL = sqlalchemy_url(
    os.environ.get("DATABASE_URL", "postgresql+psycopg://askwell:askwell@localhost:5434/askwell")
)
JWT_SECRET = os.environ.get("JWT_SECRET", DEV_JWT_SECRET)
if APP_ENV == "production" and JWT_SECRET == DEV_JWT_SECRET:
    raise RuntimeError("Set JWT_SECRET in production; the dev default is public.")
JWT_TTL_HOURS = int(os.environ.get("JWT_TTL_HOURS", "72"))
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")
# Claude model for the moderation classifier. Credentials come from the usual
# Anthropic SDK sources (ANTHROPIC_API_KEY, or an `ant auth login` profile).
# Set to an empty string to turn the classifier off; held content then goes
# straight to human review.
MODERATION_MODEL = os.environ.get("MODERATION_MODEL", "claude-haiku-5-5")
