from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from .config import Settings
from .models import ResearchState
from .prompts import (
    BASE_SYSTEM_PROMPT,
    JUDGE_INSTRUCTIONS,
    OPTIMIST_PERSPECTIVE,
    PESSIMIST_PERSPECTIVE,
    TASK_SPECS,
    build_task_prompt,
)


class ResearchClient:
    def __init__(self, settings: Settings) -> None:
        settings.validate_for_generation()
        self._settings = settings
        if settings.llm_provider == "openai":
            self._llm = ChatOpenAI(
                api_key=settings.openai_api_key,
                model=settings.llm_model,
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,
            )
        else:
            self._llm = ChatAnthropic(
                api_key=settings.anthropic_api_key,
                model=settings.llm_model or "claude-sonnet-4-6",
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,
            )

    @property
    def debate_enabled(self) -> bool:
        return self._settings.enable_debate

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

    def generate_with_debate(self, task_key: str, state: ResearchState) -> tuple[str, str, str]:
        with ThreadPoolExecutor(max_workers=2) as pool:
            optimist_future = pool.submit(
                self._generate_with_perspective, task_key, state, OPTIMIST_PERSPECTIVE,
            )
            pessimist_future = pool.submit(
                self._generate_with_perspective, task_key, state, PESSIMIST_PERSPECTIVE,
            )
            optimist_output = optimist_future.result()
            pessimist_output = pessimist_future.result()

        judge_output = self._generate_judge(task_key, state, optimist_output, pessimist_output)
        return judge_output, optimist_output, pessimist_output

    def _generate_with_perspective(
        self, task_key: str, state: ResearchState, perspective: str,
    ) -> str:
        spec = TASK_SPECS[task_key]
        prompt = build_task_prompt(
            task_name=task_key,
            instructions=spec["instructions"],
            state=state,
            context_keys=spec["context"],
            perspective=perspective,
        )
        response = self._llm.invoke(
            [
                SystemMessage(content=BASE_SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ]
        )
        return self._normalise_response_text(response.content)

    def _generate_judge(
        self,
        task_key: str,
        state: ResearchState,
        optimist_output: str,
        pessimist_output: str,
    ) -> str:
        spec = TASK_SPECS[task_key]
        judge_preamble = JUDGE_INSTRUCTIONS.format(
            optimist_output=optimist_output,
            pessimist_output=pessimist_output,
        )
        prompt = build_task_prompt(
            task_name=task_key,
            instructions=judge_preamble + "\n\n" + spec["instructions"],
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


# Backward-compat alias
ClaudeResearchClient = ResearchClient
