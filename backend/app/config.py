"""Configuration settings for the Wind Forecast API."""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API
    app_name: str = "Wind Forecast Decision Support"
    debug: bool = False
    cors_origins: str = "http://localhost:5173,http://localhost:3000,https://*.vercel.app"

    # Elexon BMRS API
    elexon_base_url: str = "https://data.elexon.co.uk/bmrs/api/v1"
    elexon_rate_limit_per_second: float = 2.0  # conservative rate limit

    # Data
    data_dir: str = "./data"
    cache_db: str = "./data/cache.db"

    # January 2026 scope
    scope_start: str = "2026-01-01"
    scope_end: str = "2026-01-31"

    # Forecast fetch window (start earlier to capture early forecasts)
    forecast_fetch_start: str = "2025-12-15"

    # Default decision cutoff
    default_cutoff_hour: int = 9  # 09:00 Europe/London on D-1

    model_config = {
        "env_prefix": "WIND_",
        "env_file": str(Path(__file__).resolve().parents[2] / ".env"),
    }


settings = Settings()
