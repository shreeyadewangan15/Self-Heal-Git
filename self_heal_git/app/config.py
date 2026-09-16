from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlmodel import create_engine

class Settings(BaseSettings):
    GITHUB_WEBHOOK_SECRET: str = "your_secret_here"
    GITHUB_TOKEN: str = ""  # GitHub personal access token or dummy placeholder
    DATABASE_URL: str = "sqlite:///./self_heal_git.db"
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    # JWT Authentication Settings
    SECRET_KEY: str = "self_heal_git_super_secret_jwt_key_change_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Google OAuth2 Settings
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/auth/google/callback"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()

# Create SQLModel engine using the DATABASE_URL with SQLite thread safety
engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

def get_session():
    """FastAPI dependency for obtaining a database session."""
    from sqlmodel import Session
    with Session(engine) as session:
        yield session
