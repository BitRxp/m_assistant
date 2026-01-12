from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    backend_host: str = "127.0.0.1"
    backend_port: int = 8000

    database_url: str = "sqlite:///./m_assistant.db"

    memory_enabled: bool = True
    retrieval_top_k: int = 5
    retrieval_max_chars: int = 2000
    embedder_backend: str = "stub"  # stub | fastembed
    embedder_model: str = "BAAI/bge-small-en-v1.5"

    stt_backend: str = "stub"  # stub | faster-whisper
    stt_model: str = "small"
    stt_device: str = "cpu"

    tts_backend: str = "stub"  # stub | opentts

    wake_enabled: bool = False
    wake_backend: str = "stub"  # stub | porcupine
    wake_porcupine_access_key: str = ""
    wake_porcupine_keywords: str = "computer"  # comma-separated
    wake_porcupine_sensitivity: float = 0.5

    dialog_enabled: bool = False
    llm_backend: str = "stub"  # stub | proxy

    llm_routing_mode: str = "priority"  # priority | weighted
    llm_primary_provider: str = "ollama"  # openai | ollama
    llm_secondary_provider: str = "openai"  # openai | ollama
    llm_primary_weight: float = 1.0
    llm_secondary_weight: float = 0.0
    llm_timeout_s: float = 20.0
    llm_max_retries: int = 2

    openai_base_url: str = "https://api.openai.com"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"

    opentts_base_url: str = "http://localhost:5500"
    opentts_voice: str = "coqui-tts:en_vctk#p228"


settings = Settings()
