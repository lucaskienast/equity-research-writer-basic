from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore", populate_by_name=True)

    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(default="claude-sonnet-4-6", alias="ANTHROPIC_MODEL")
    anthropic_temperature: float = Field(default=0.1, alias="ANTHROPIC_TEMPERATURE")
    anthropic_max_tokens: int = Field(default=1400, alias="ANTHROPIC_MAX_TOKENS")

    azure_storage_connection_string: str | None = Field(
        default=None, alias="AZURE_STORAGE_CONNECTION_STRING"
    )
    azure_blob_container: str = Field(default="equity-research-output", alias="AZURE_BLOB_CONTAINER")
    azure_blob_prefix: str = Field(default="equity-research", alias="AZURE_BLOB_PREFIX")
    upload_to_azure: bool = Field(default=False, alias="UPLOAD_TO_AZURE")

    local_output_dir: Path = Field(default=Path("output"), alias="LOCAL_OUTPUT_DIR")

    def validate_for_generation(self) -> None:
        if not self.anthropic_api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY is required to generate research output. "
                "Set it in your shell or .env file."
            )

    def validate_for_upload(self) -> None:
        if not self.azure_storage_connection_string:
            raise ValueError(
                "AZURE_STORAGE_CONNECTION_STRING is required when upload is enabled."
            )
