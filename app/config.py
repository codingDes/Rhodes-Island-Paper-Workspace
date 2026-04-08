from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv_if_present(dotenv_path: Path) -> None:
    """
    轻量 .env 加载器：不强依赖 python-dotenv，避免 Step1 就引入额外复杂度。
    规则：
    - 忽略空行和以 # 开头的注释行
    - 支持 KEY=VALUE（会去掉两侧空格）
    - 支持用单/双引号包裹 VALUE
    - 已存在的环境变量不覆盖
    """

    if not dotenv_path.exists():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


@dataclass(frozen=True)
class Settings:
    app_name: str = "RhodesIsland Archive Room"
    host: str = "127.0.0.1"
    port: int = 8000
    cors_allow_origins: str = "http://127.0.0.1:8000,http://localhost:8000"

    # OpenAI compatible
    openai_base_url: str = "https://api.deepseek.com/v1"
    openai_api_key: str = ""
    openai_model: str = "deepseek-chat"
    embedding_model: str = "deepseek-embedding"
    embedding_dim: int = 512

    data_dir: Path = Path("data")
    docs_dir: Path = Path("data/docs")
    index_dir: Path = Path("data/index")
    memory_dir: Path = Path("data/memory")

    @staticmethod
    def load() -> "Settings":
        _load_dotenv_if_present(Path(".env"))

        def _get(name: str, default: str) -> str:
            return os.getenv(name, default)

        def _get_int(name: str, default: int) -> int:
            raw = os.getenv(name)
            if raw is None or raw == "":
                return default
            try:
                return int(raw)
            except ValueError:
                return default

        return Settings(
            app_name=_get("APP_NAME", Settings.app_name),
            host=_get("HOST", Settings.host),
            port=_get_int("PORT", Settings.port),
            cors_allow_origins=_get("CORS_ALLOW_ORIGINS", Settings.cors_allow_origins),
            openai_base_url=_get("OPENAI_BASE_URL", Settings.openai_base_url),
            openai_api_key=_get("OPENAI_API_KEY", Settings.openai_api_key),
            openai_model=_get("OPENAI_MODEL", Settings.openai_model),
            embedding_model=_get("EMBEDDING_MODEL", Settings.embedding_model),
            embedding_dim=_get_int("EMBEDDING_DIM", Settings.embedding_dim),
        )

