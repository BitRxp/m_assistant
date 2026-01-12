from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    backend_host: str = "127.0.0.1"
    backend_port: int = 8000

    stt_backend: str = "stub"  # stub | faster-whisper
    stt_model: str = "small"
    stt_device: str = "cpu"

    opentts_base_url: str = "http://localhost:5500"
    opentts_voice: str = "coqui-tts:en_vctk#p228"


settings = Settings()
