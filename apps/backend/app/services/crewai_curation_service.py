import json
import os
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, Field

from app.core.config import Settings
from app.schemas.video import VideoItem

try:
    from crewai import Agent, Crew, Process, Task
    from crewai.llms.base_llm import BaseLLM
except Exception:  # pragma: no cover - optional dependency
    Agent = BaseLLM = Crew = Process = Task = None

CrewAIBaseLLM = BaseLLM if BaseLLM is not None else object


class KeywordPlan(BaseModel):
    keywords: list[str] = Field(default_factory=list)


class ReviewDecision(BaseModel):
    bvid: str
    keep: bool
    reason: str


class ReviewPlan(BaseModel):
    decisions: list[ReviewDecision] = Field(default_factory=list)


class CategoryDecision(BaseModel):
    bvid: str
    categories: list[str] = Field(default_factory=list)


class CategoryPlan(BaseModel):
    items: list[CategoryDecision] = Field(default_factory=list)


class AdapterBackedCrewAILLM(CrewAIBaseLLM):
    def __init__(self, settings: Settings) -> None:
        if BaseLLM is None:
            raise ValueError("CrewAI BaseLLM class is unavailable")
        super().__init__(
            model=settings.effective_llm_model,
            temperature=0.2,
            api_key=settings.effective_llm_api_key,
            base_url=settings.effective_llm_base_url,
            provider=settings.effective_llm_provider,
        )
        self.settings = settings

    def call(
        self,
        messages: str | list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        callbacks: list[Any] | None = None,
        available_functions: dict[str, Any] | None = None,
        from_task: Any | None = None,
        from_agent: Any | None = None,
        response_model: type[BaseModel] | None = None,
    ) -> str | Any:
        del tools, callbacks, available_functions, from_task, from_agent, response_model

        payload_messages: list[dict[str, str]]
        if isinstance(messages, str):
            payload_messages = [{"role": "user", "content": messages}]
        else:
            payload_messages = []
            for message in messages:
                role = str(message.get("role") or "user")
                content = message.get("content")
                if isinstance(content, list):
                    content = "\n".join(str(item.get("text") or item) for item in content)
                payload_messages.append({"role": role, "content": str(content or "")})

        payload = {
            "model": self.settings.effective_llm_model,
            "messages": payload_messages,
            "max_tokens": 1200,
            "temperature": self.temperature or 0.2,
        }

        with httpx.Client(timeout=self.settings.llm_refinement_timeout_seconds) as client:
            response = client.post(
                f"{self.settings.effective_llm_base_url.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.settings.effective_llm_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            body = response.json()

        choices = body.get("choices", [])
        if not choices:
            raise ValueError("adapter-backed CrewAI call returned no choices")
        content = choices[0].get("message", {}).get("content")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("adapter-backed CrewAI call returned empty content")
        return content


class CrewAICurationService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._configure_environment()

    @property
    def available(self) -> bool:
        return bool(
            self.settings.crewai_enabled
            and self.settings.llm_adapter_configured
            and Agent is not None
            and Crew is not None
            and BaseLLM is not None
            and Task is not None
            and Process is not None
        )

    def plan_keywords(self, *, objective: str, extra_requirements: str | None, max_keywords: int) -> list[str]:
        if not self.available:
            return []

        planner = self._build_planner_agent()
        task = Task(
            description=(
                f"Objective: {objective}\n"
                f"Extra requirements: {extra_requirements or ''}\n"
                f"Return at most {max_keywords} short Chinese search keywords for Bilibili."
            ),
            expected_output="A JSON object with a keywords array.",
            agent=planner,
            output_pydantic=KeywordPlan,
        )
        plan = self._run_task(task, KeywordPlan)
        return [keyword.strip() for keyword in plan.keywords if keyword.strip()][:max_keywords]

    def review_candidates(
        self,
        *,
        objective: str,
        extra_requirements: str | None,
        items: list[VideoItem],
    ) -> tuple[dict[str, bool], dict[str, str]]:
        if not self.available or not items:
            return {}, {}

        reviewer = self._build_reviewer_agent()
        task = Task(
            description=(
                f"Objective: {objective}\n"
                f"Extra requirements: {extra_requirements or ''}\n"
                f"Candidates JSON: {self._serialize_items(items)}\n"
                "For each candidate, decide keep true or false and give a short reason."
            ),
            expected_output="A JSON object with decisions array.",
            agent=reviewer,
            output_pydantic=ReviewPlan,
        )
        plan = self._run_task(task, ReviewPlan)
        keep_map = {decision.bvid: decision.keep for decision in plan.decisions}
        reason_map = {decision.bvid: decision.reason for decision in plan.decisions}
        return keep_map, reason_map

    def classify_candidates(
        self,
        *,
        objective: str,
        extra_requirements: str | None,
        items: list[VideoItem],
    ) -> dict[str, list[str]]:
        if not self.available or not items:
            return {}

        classifier = self._build_classifier_agent()
        task = Task(
            description=(
                f"Objective: {objective}\n"
                f"Extra requirements: {extra_requirements or ''}\n"
                f"Candidates JSON: {self._serialize_items(items)}\n"
                "Assign concise category labels to each accepted candidate. Return an empty list for weak matches."
            ),
            expected_output="A JSON object with items array.",
            agent=classifier,
            output_pydantic=CategoryPlan,
        )
        plan = self._run_task(task, CategoryPlan)
        return {entry.bvid: entry.categories for entry in plan.items}

    def _run_task(self, task: Any, model_cls: type[BaseModel]) -> BaseModel:
        crew = Crew(agents=[task.agent], tasks=[task], process=Process.sequential, verbose=False)
        result = crew.kickoff()
        return self._extract_pydantic(result, task, model_cls)

    def _extract_pydantic(self, result: Any, task: Any, model_cls: type[BaseModel]) -> BaseModel:
        result_model = getattr(result, "pydantic", None)
        if isinstance(result_model, model_cls):
            return result_model

        task_output = getattr(task, "output", None)
        task_model = getattr(task_output, "pydantic", None)
        if isinstance(task_model, model_cls):
            return task_model
        if isinstance(task_model, BaseModel):
            return model_cls.model_validate(task_model.model_dump())
        if isinstance(result, dict):
            return model_cls.model_validate(result)

        raw = getattr(result, "raw", None)
        if isinstance(raw, str) and raw.strip():
            return model_cls.model_validate_json(raw)

        raise ValueError("CrewAI result did not contain expected Pydantic output")

    def _build_planner_agent(self) -> Any:
        return Agent(
            role="Bilibili Query Planner",
            goal="Turn a learning objective into short, practical, high-hit Bilibili search phrases.",
            backstory=(
                "You specialize in rewriting vague learning goals into concrete Bilibili-friendly search keywords. "
                "You prefer concise phrases, named topics, concrete stacks, and series-like wording over long prose."
            ),
            verbose=False,
            allow_delegation=False,
            max_iter=1,
            llm=self._build_llm(),
        )

    def _build_reviewer_agent(self) -> Any:
        return Agent(
            role="Bilibili Content Reviewer",
            goal="Strictly reject weak, noisy, clickbait, short-form, or off-target videos before they reach the local library.",
            backstory=(
                "You act like a content quality gate for a personal learning workspace. "
                "You prioritize depth, educational value, topic relevance, and series completeness."
            ),
            verbose=False,
            allow_delegation=False,
            max_iter=1,
            llm=self._build_llm(),
        )

    def _build_classifier_agent(self) -> Any:
        return Agent(
            role="Learning Library Classifier",
            goal="Organize accepted videos into concise learning folders and stable category labels.",
            backstory=(
                "You maintain a structured local learning library. "
                "You prefer compact, reusable category labels over verbose descriptions."
            ),
            verbose=False,
            allow_delegation=False,
            max_iter=1,
            llm=self._build_llm(),
        )

    def _serialize_items(self, items: list[VideoItem]) -> str:
        return json.dumps(
            [
                {
                    "bvid": item.bvid,
                    "title": item.title,
                    "author_name": item.author_name,
                    "duration_seconds": item.duration_seconds,
                    "summary": item.summary,
                    "tags": item.tags,
                }
                for item in items
            ],
            ensure_ascii=False,
        )

    def _configure_environment(self) -> None:
        api_key = self.settings.effective_llm_api_key
        base_url = self.settings.effective_llm_base_url
        model_name = self.settings.effective_llm_model
        storage_dir = (self.settings.database_path.parent / "crewai").resolve()

        storage_dir.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("CREWAI_STORAGE_DIR", str(storage_dir))
        os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")
        os.environ.setdefault("CREWAI_DISABLE_VERSION_CHECK", "true")

        if not api_key:
            return

        # CrewAI commonly reads OpenAI-compatible environment variables through LiteLLM.
        os.environ.setdefault("OPENAI_API_KEY", api_key)
        os.environ.setdefault("OPENAI_API_BASE", base_url)
        os.environ.setdefault("OPENAI_BASE_URL", base_url)
        if model_name:
            os.environ.setdefault("OPENAI_MODEL_NAME", model_name)
            os.environ.setdefault("MODEL", model_name)

    def _build_llm(self) -> Any:
        if BaseLLM is None:
            raise ValueError("CrewAI BaseLLM class is unavailable")
        return AdapterBackedCrewAILLM(self.settings)
