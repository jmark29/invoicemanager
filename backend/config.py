from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATA_DIR: Path = Path("./data")
    LOG_LEVEL: str = "INFO"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def DATABASE_URL(self) -> str:
        db_path = self.DATA_DIR / "invoices.db"
        return f"sqlite:///{db_path}"

    @property
    def TEMPLATES_DIR(self) -> Path:
        return self.DATA_DIR / "templates"

    @property
    def GENERATED_DIR(self) -> Path:
        return self.DATA_DIR / "generated"

    @property
    def CATEGORIES_DIR(self) -> Path:
        return self.DATA_DIR / "categories"

    @property
    def IMPORTS_DIR(self) -> Path:
        return self.DATA_DIR / "imports"


settings = Settings()
