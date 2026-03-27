from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from openai import AzureOpenAI
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

API_VERSION = "2024-12-01-preview"

class ResearchClient:
    def __init__(self, settings: Settings) -> None:
        settings.validate_for_generation()
        self._settings = settings
        self._provider = settings.llm_provider.lower().strip() if settings.llm_provider else ""

        self._azure_client: AzureOpenAI | None = None
        self._llm: ChatOpenAI | ChatAnthropic | None = None

        if self._provider == "azure":
            # Azure client: constructor takes endpoint, api_version, api_key only.
            # Model (deployment name), temperature, max_tokens are passed per-call.
            self._azure_client = AzureOpenAI(
                api_version=API_VERSION,
                azure_endpoint=settings.llm_endpoint,  # type: ignore[arg-type]
                api_key=settings.azure_api_key,
            )

        elif self._provider == "openai":
            self._llm = ChatOpenAI(
                api_key=settings.openai_api_key,  # type: ignore[arg-type]
                model=settings.llm_model,
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,  # type: ignore[call-arg]
            )

        elif self._provider == "anthropic":
            self._llm = ChatAnthropic(
                api_key=settings.anthropic_api_key,  # type: ignore[arg-type]
                model=settings.llm_model or "claude-sonnet-4-6",  # type: ignore[call-arg]
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,  # type: ignore[call-arg]
            )

        else:
            raise ValueError("No or unsupported LLM provider specified. Use 'azure', 'openai', or 'anthropic'.")

    @property
    def debate_enabled(self) -> bool:
        return self._settings.enable_debate

    def _call_provider(self, system_prompt: str, user_prompt: str) -> str:
        if self._provider == "azure":
            assert self._azure_client is not None
            response = self._azure_client.chat.completions.create(
                model=self._settings.llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=self._settings.llm_temperature,
                max_tokens=self._settings.llm_max_tokens,
            )
            content: str | None = None
            if response.choices and response.choices[0].message:
                content = response.choices[0].message.content
            return self._normalise_response_text(content or "")
        assert self._llm is not None
        llm_response = self._llm.invoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
        )
        return self._normalise_response_text(llm_response.content)

    def generate(self, task_key: str, state: ResearchState) -> str:
        if task_key not in TASK_SPECS:
            raise KeyError(f"Unknown task key: {task_key}")

        spec = TASK_SPECS[task_key]
        prompt = build_task_prompt(
            task_name=task_key,
            instructions=str(spec["instructions"]),
            state=state,
            context_keys=spec["context"],
        )
        return self._call_provider(BASE_SYSTEM_PROMPT, prompt)

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
            instructions=str(spec["instructions"]),
            state=state,
            context_keys=spec["context"],
            perspective=perspective,
        )
        return self._call_provider(BASE_SYSTEM_PROMPT, prompt)

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
            instructions=judge_preamble + "\n\n" + str(spec["instructions"]),
            state=state,
            context_keys=spec["context"],
        )
        return self._call_provider(BASE_SYSTEM_PROMPT, prompt)

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
