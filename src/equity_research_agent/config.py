from __future__ import annotations

from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore", populate_by_name=True)

    # LLM provider selection: "openai" (default) | "anthropic"
    llm_provider: str = Field(default="openai", alias="LLM_PROVIDER")

    # Shared LLM settings (apply to whichever provider is active)
    llm_model: str = Field(default="gpt-4o-mini", alias="LLM_MODEL")
    llm_temperature: float = Field(default=0.1, alias="LLM_TEMPERATURE")
    llm_max_tokens: int = Field(default=1400, alias="LLM_MAX_TOKENS")

    # Azure OpenAI (LLM only — not storage)
    azure_api_key: str | None = Field(default=None, alias="AZURE_API_KEY")
    llm_endpoint: str | None = Field(default=None, alias="LLM_ENDPOINT")

    # OpenAI
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")

    # Anthropic
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")

    # SharePoint storage (via Microsoft Graph)
    sharepoint_tenant_id: str | None = Field(default=None, alias="SHAREPOINT_TENANT_ID")
    sharepoint_client_id: str | None = Field(default=None, alias="SHAREPOINT_CLIENT_ID")
    sharepoint_client_secret: SecretStr | None = Field(default=None, alias="SHAREPOINT_CLIENT_SECRET")
    sharepoint_drive_id: str | None = Field(default=None, alias="SHAREPOINT_DRIVE_ID")
    sharepoint_upload_base_path: str = Field(default="equity-research", alias="SHAREPOINT_UPLOAD_BASE_PATH")
    upload_to_sharepoint: bool = Field(default=False, alias="UPLOAD_TO_SHAREPOINT")

    local_output_dir: Path = Field(default=Path("output"), alias="LOCAL_OUTPUT_DIR")

    # Debate mode: run optimist + pessimist in parallel, then a judge synthesises
    enable_debate: bool = Field(default=False, alias="ENABLE_DEBATE")

    def validate_for_generation(self) -> None:
        if self.llm_provider == "azure":
            if not self.azure_api_key:
                raise ValueError("AZURE_API_KEY is required when LLM_PROVIDER=azure.")
            if not self.llm_endpoint:
                raise ValueError("LLM_ENDPOINT is required when LLM_PROVIDER=azure.")
        elif self.llm_provider == "openai":
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
        missing = [
            name
            for name, value in [
                ("SHAREPOINT_TENANT_ID", self.sharepoint_tenant_id),
                ("SHAREPOINT_CLIENT_ID", self.sharepoint_client_id),
                ("SHAREPOINT_CLIENT_SECRET", self.sharepoint_client_secret),
                ("SHAREPOINT_DRIVE_ID", self.sharepoint_drive_id),
            ]
            if not value
        ]
        if missing:
            raise ValueError(
                f"The following settings are required when UPLOAD_TO_SHAREPOINT=true: "
                f"{', '.join(missing)}"
            )
