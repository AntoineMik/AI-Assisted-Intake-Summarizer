from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseModel):
    llm_provider: str = os.getenv("LLM_PROVIDER", "mock")
    llm_model: str = os.getenv("LLM_MODEL", "gpt-5.2")
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")

def get_settings() -> Settings:
    # re-read env each time (good for tests)
    return Settings()