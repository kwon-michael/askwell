import os

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+psycopg://askwell:askwell@localhost:5434/askwell"
)
JWT_SECRET = os.environ.get("JWT_SECRET", "dev-only-secret-change-me-in-production")
JWT_TTL_HOURS = int(os.environ.get("JWT_TTL_HOURS", "72"))
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")
# Claude model for the moderation classifier. Credentials come from the usual
# Anthropic SDK sources (ANTHROPIC_API_KEY, or an `ant auth login` profile).
# Set to an empty string to turn the classifier off; held content then goes
# straight to human review.
MODERATION_MODEL = os.environ.get("MODERATION_MODEL", "claude-haiku-5-5")
