from __future__ import annotations

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from .config import Settings
from .models import ResearchState
from .prompts import BASE_SYSTEM_PROMPT, TASK_SPECS, build_task_prompt


class ClaudeResearchClient:
    def __init__(self, settings: Settings) -> None:
        settings.validate_for_generation()
        self._settings = settings
        self._llm = ChatAnthropic(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model,
            temperature=settings.anthropic_temperature,
            max_tokens=settings.anthropic_max_tokens,
        )

    def generate(self, task_key: str, state: ResearchState) -> str:
        if task_key not in TASK_SPECS:
            raise KeyError(f"Unknown task key: {task_key}")

        spec = TASK_SPECS[task_key]
        prompt = build_task_prompt(
            task_name=task_key,
            instructions=spec["instructions"],
            state=state,
            context_keys=spec["context"],
        )

        response = self._llm.invoke(
            [
                SystemMessage(content=BASE_SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ]
        )
        return self._normalise_response_text(response.content)

    @staticmethod
    def _normalise_response_text(content: object) -> str:
        if isinstance(content, str):
            return content.strip()

        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict) and "text" in item:
                    parts.append(str(item["text"]))
                else:
                    parts.append(str(item))
            return "\n".join(part.strip() for part in parts if str(part).strip()).strip()

        return str(content).strip()
