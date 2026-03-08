from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore", populate_by_name=True)

    # LLM provider selection: "openai" (default) | "anthropic"
    llm_provider: str = Field(default="openai", alias="LLM_PROVIDER")

    # Shared LLM settings (apply to whichever provider is active)
    llm_model: str = Field(default="gpt-4o-mini", alias="LLM_MODEL")
    llm_temperature: float = Field(default=0.1, alias="LLM_TEMPERATURE")
    llm_max_tokens: int = Field(default=1400, alias="LLM_MAX_TOKENS")

    # OpenAI
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")

    # Anthropic
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")

    # Azure Blob Storage
    azure_storage_connection_string: str | None = Field(
        default=None, alias="AZURE_STORAGE_CONNECTION_STRING"
    )
    azure_blob_container: str = Field(default="equity-research-output", alias="AZURE_BLOB_CONTAINER")
    azure_blob_prefix: str = Field(default="equity-research", alias="AZURE_BLOB_PREFIX")
    upload_to_azure: bool = Field(default=False, alias="UPLOAD_TO_AZURE")

    local_output_dir: Path = Field(default=Path("output"), alias="LOCAL_OUTPUT_DIR")

    def validate_for_generation(self) -> None:
        if self.llm_provider == "openai":
            if not self.openai_api_key:
                raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai.")
        elif self.llm_provider == "anthropic":
            if not self.anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY is required when LLM_PROVIDER=anthropic.")
        else:
            raise ValueError(
                f"Unknown LLM_PROVIDER '{self.llm_provider}'. Use 'openai' or 'anthropic'."
            )

    def validate_for_upload(self) -> None:
        if not self.azure_storage_connection_string:
            raise ValueError(
                "AZURE_STORAGE_CONNECTION_STRING is required when upload is enabled."
            )
