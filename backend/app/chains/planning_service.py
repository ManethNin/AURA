"""
Planning Agent Service.

Analyzes dependency migration problems and creates a structured migration plan
before the recipe agent or LLM repair agent executes the changes.
"""

import re
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict, Union

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from groq import Groq

from app.config.config import settings
from app.utilities.logger import logger

__all__ = ["PlanningAgentService", "PlanResult"]


class PlanResult(TypedDict):
    """Type definition for the result returned by create_plan."""
    success: bool
    plan: str
    error: Optional[str]


PLANNING_SYSTEM_PROMPT = """You are an expert Java dependency migration planner.

Your ONLY job is to analyze the problem and produce a clear, actionable, step-by-step migration plan.
You do NOT fix code. You do NOT produce diffs. You ONLY plan.

Given:
- The pom.xml dependency changes (what was upgraded)
- Compilation errors caused by the upgrade
- API changes between the old and new dependency versions (if available)
- The actual source code of affected files

Your global plan will be utilized by a dual-executor system: 
1. A Recipe Agent (which attempts to apply automated, deterministic AST-level transformation recipes).
2. An LLM Repair Agent (which acts as a fallback to handle complex, custom logic rewrites if recipes fail).

## Expected Output Format
You must produce a structured plan in a numbered list format, starting with '## Step 1' and incrementing for each subsequent step. 

Each step MUST exactly follow this format:
## Step N
Reasoning: [Your detailed thought process]
Step: [The concrete, high-level directive for the Executors]
Classification: [Standard API Migration | Complex Logic Rewrite | Dependency Management]

## Detailed Guidelines:
1. **Initial State Grounding**: In the 'Reasoning' section of '## Step 1', you MUST provide an observation of the initial state. Analyze the provided pom.xml changes and summarize the root cause of the compilation errors based on the provided API changes.
2. **Chain of Thought**: For every step, use the 'Reasoning' block to explain *why* this step is logically necessary before stating the step itself.
3. **Cluster Related Actions**: Group logically related changes together to minimize the number of steps. For example, if multiple files require the same import update, combine them into a single step like "Update servlet imports across X, Y, and Z files". 
4. **Be Specific (WHAT, not HOW)**: Focus on describing WHAT needs to be accomplished rather than outputting exact diffs. Use actual class names, old signature → new signature mappings, and specific file targets. Do not use vague phrasing.
5. **Action Classification**: Use the 'Classification' field to help route the task. 
   - Use 'Standard API Migration' for import swaps, method renames, or deprecated class replacements (ideal for the Recipe Agent).
   - Use 'Complex Logic Rewrite' for structural changes, rewriting test frameworks, or migrating entirely removed APIs without direct replacements (ideal for the LLM Repair Agent).
   - Use 'Dependency Management' for pom.xml updates.
6. **Suggested Order**: Structure your steps in the exact, safest execution order. Fix shared utilities, interfaces, or base classes before updating the concrete implementations that depend on them.
7. **Risk Flagging**: If a step carries runtime behavior risks beyond just fixing the compilation error, explicitly state this in the 'Reasoning' block of that step.

## Repair Strategy Guidelines
When multiple possible fixes exist, prefer the **least invasive change that restores compilation**.

Follow this priority order when planning fixes:
1. Update imports or package names if classes were relocated.
2. Add missing dependencies that contain the relocated classes.
3. Update method signatures or API usage if the API changed.
4. Replace deprecated classes with recommended alternatives.
5. Perform structural refactors (e.g., switching runners, rewriting tests, migrating frameworks) **ONLY if the previous options cannot resolve the compilation errors.**

Avoid introducing new architectural patterns or test frameworks unless the original API is completely removed and no compatibility layer exists.

## Consistency Requirement
If a missing class appears to have been **relocated to another package or artifact**, prefer restoring the same class via import or dependency updates rather than replacing it with a different mechanism.

IMPORTANT RULES:
- DO NOT produce any code diffs or patches.
- DO NOT suggest reverting dependency versions — the upgrades are intentional.
- You MAY create a step to add NEW dependencies to pom.xml if required to bridge the API gap.
"""


class PlanningAgentService:
    """Service that analyzes the migration problem and produces an actionable plan."""

    # Provider Constants
    PROVIDER_GEMINI = "gemini"
    PROVIDER_GROQ_NATIVE = "gpt-oss-120"
    PROVIDER_GROQ_LANGCHAIN = "groq"

    # LLM Configuration Constants
    DEFAULT_TEMPERATURE = 0.0
    NATIVE_GROQ_TEMPERATURE = 1.0
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_TIMEOUT = 240
    MAX_COMPLETION_TOKENS = 8192
    DEFAULT_TOP_P = 1.0
    DEFAULT_REASONING_EFFORT = "medium"

    # Regex compilation for performance
    JAVA_FILE_PATTERN = re.compile(r"(src/main/java/[\w/]+\.java)")

    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        """Initialize the planning service with a configurable LLM provider.

        Args:
            provider: LLM provider identifier (defaults to settings.LLM_PROVIDER).
                Valid options: "groq", "gpt-oss-120", or "gemini".
            api_key: Provider API key (defaults to appropriate key from settings).
            model: Target model name (defaults to appropriate model from settings).
        """
        self.provider = provider or settings.LLM_PROVIDER
        self.client: Optional[Groq] = None
        self.llm: Optional[Union[ChatGoogleGenerativeAI, ChatGroq]] = None
        self.model: Optional[str] = None

        self._initialize_provider(api_key, model)

    def _initialize_provider(self, api_key: Optional[str], model: Optional[str]) -> None:
        """Set up the appropriate LLM client based on the selected provider.

        Args:
            api_key: The API key for the selected provider.
            model: The model name to be used.
        """
        if self.provider == self.PROVIDER_GEMINI:
            self._setup_gemini(api_key, model)
        elif self.provider == self.PROVIDER_GROQ_NATIVE:
            self._setup_groq_native(api_key, model)
        else:
            self._setup_groq_langchain(api_key, model)
            self.provider = self.PROVIDER_GROQ_LANGCHAIN

    def _setup_gemini(self, api_key: Optional[str], model: Optional[str]) -> None:
        """Initialize the Gemini client via LangChain."""
        key = api_key or settings.GOOGLE_API_KEY
        self.model = model or settings.GEMINI_MODEL
        self.llm = ChatGoogleGenerativeAI(
            model=self.model,
            temperature=self.DEFAULT_TEMPERATURE,
            google_api_key=key,
            max_retries=self.DEFAULT_MAX_RETRIES,
            timeout=self.DEFAULT_TIMEOUT,
        )

    def _setup_groq_native(self, api_key: Optional[str], model: Optional[str]) -> None:
        """Initialize the native Groq client for specific reasoning models."""
        key = api_key or settings.GROQ_API_KEY
        self.model = model or settings.GROQ_PLANNING_MODEL
        self.client = Groq(api_key=key)

    def _setup_groq_langchain(self, api_key: Optional[str], model: Optional[str]) -> None:
        """Initialize the standard Groq client via LangChain."""
        key = api_key or settings.GROQ_API_KEY
        self.model = model or settings.GROQ_MODEL
        self.llm = ChatGroq(
            groq_api_key=key,
            model_name=self.model,
            temperature=self.DEFAULT_TEMPERATURE,
            max_retries=self.DEFAULT_MAX_RETRIES,
            timeout=self.DEFAULT_TIMEOUT,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_plan(
        self,
        repo_path: Union[str, Path],
        commit_hash: str,
        repo_slug: str,
        pom_diff: str,
        initial_errors: str = "",
        api_changes_text: str = "",
        pipeline_logger: Optional[Any] = None,
    ) -> PlanResult:
        """Analyze the migration problem and return a structured plan.

        Args:
            repo_path: Path to the local repository.
            commit_hash: The current commit hash being processed.
            repo_slug: The repository identifier (e.g., 'owner/repo').
            pom_diff: The git diff of the pom.xml file.
            initial_errors: Captured compilation errors to analyze.
            api_changes_text: Known API changes between library versions.
            pipeline_logger: Optional logger object for pipeline tracking.

        Returns:
            A dictionary containing success status, the plan text, and any errors.
        """
        logger.info(f"[PlanningAgent] Creating migration plan for {repo_slug}")
        repo_path_obj = Path(repo_path)

        if pipeline_logger:
            pipeline_logger.log_stage(
                "planning_agent_start",
                {
                    "repo_slug": repo_slug,
                    "commit_hash": commit_hash,
                    "provider": self.provider,
                },
            )

        try:
            file_contents = self._read_error_files(repo_path_obj, initial_errors)
            prompt = self._build_prompt(
                pom_diff=pom_diff,
                initial_errors=initial_errors,
                api_changes_text=api_changes_text,
                file_contents=file_contents,
            )

            if pipeline_logger:
                pipeline_logger.log_stage(
                    "planning_agent_prompt",
                    {
                        "prompt_length": len(prompt),
                        "files_included": list(file_contents.keys()),
                    },
                )

            plan_text = self._invoke_llm(prompt)

            logger.info(f"[PlanningAgent] Plan generated ({len(plan_text)} chars)")

            if pipeline_logger:
                pipeline_logger.log_stage(
                    "planning_agent_complete", {"plan_length": len(plan_text)}
                )
                self._save_plan_to_disk(plan_text, pipeline_logger)

            return {
                "success": True,
                "plan": plan_text,
                "error": None,
            }

        except Exception as e:
            return self._handle_error(e, pipeline_logger)

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _invoke_llm(self, prompt: str) -> str:
        """Send the prompt to the configured LLM and retrieve the response.

        Args:
            prompt: The assembled user prompt.

        Returns:
            The raw text response from the LLM.
        """
        messages = [
            {"role": "system", "content": PLANNING_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        if self.provider == self.PROVIDER_GROQ_NATIVE and self.client:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.NATIVE_GROQ_TEMPERATURE,
                max_completion_tokens=self.MAX_COMPLETION_TOKENS,
                top_p=self.DEFAULT_TOP_P,
                reasoning_effort=self.DEFAULT_REASONING_EFFORT,
                stream=False,
            )
            return completion.choices[0].message.content.strip()

        if self.llm:
            response = self.llm.invoke(messages)
            return (
                response.content.strip()
                if hasattr(response, "content")
                else str(response).strip()
            )

        raise RuntimeError("No LLM client was properly initialized.")

    @classmethod
    def _read_error_files(cls, repo_path: Path, initial_errors: str) -> Dict[str, str]:
        """Pre-read Java source files mentioned in compilation errors.

        Args:
            repo_path: The root path of the repository.
            initial_errors: The raw compilation error output.

        Returns:
            A dictionary mapping file paths (relative) to their textual content.
        """
        file_contents: Dict[str, str] = {}
        if not initial_errors:
            return file_contents

        unique_files = list(set(cls.JAVA_FILE_PATTERN.findall(initial_errors)))

        for file_path in unique_files:
            try:
                full_path = repo_path / file_path
                if full_path.exists():
                    content = full_path.read_text(encoding="utf-8")
                    file_contents[file_path] = content
                    logger.debug(
                        f"[PlanningAgent] Pre-read {file_path} ({len(content)} chars)"
                    )
            except OSError as e:
                logger.warning(f"[PlanningAgent] Could not read {file_path}: {e}")

        return file_contents

    @staticmethod
    def _build_prompt(
        pom_diff: str,
        initial_errors: str,
        api_changes_text: str,
        file_contents: Dict[str, str],
    ) -> str:
        """Assemble the user prompt sent to the planning LLM.

        Args:
            pom_diff: Git diff of the pom.xml file.
            initial_errors: Compilation errors text.
            api_changes_text: API changes text.
            file_contents: Dictionary of file contents related to errors.

        Returns:
            The fully assembled prompt string.
        """
        sections: List[str] = [
            f"## POM.XML DEPENDENCY CHANGES\n```diff\n{pom_diff or '(no diff provided)'}\n```"
        ]

        if api_changes_text:
            sections.append(
                f"## API CHANGES BETWEEN OLD AND NEW DEPENDENCY VERSIONS\n```\n{api_changes_text}\n```"
            )

        if initial_errors:
            sections.append(f"## COMPILATION ERRORS\n```\n{initial_errors}\n```")

        if file_contents:
            file_section = ["## AFFECTED SOURCE FILES"]
            for path, content in file_contents.items():
                file_section.append(f"\n### {path}\n```java\n{content}\n```")
            sections.append("\n".join(file_section))

        sections.append(
            "Based on the information above, produce a detailed migration plan. "
            "Do NOT produce code diffs — only describe what needs to change and why."
        )

        return "\n\n".join(sections)

    @staticmethod
    def _save_plan_to_disk(plan_text: str, pipeline_logger: Any) -> None:
        """Save the generated plan to the logger's directory.

        Args:
            plan_text: The final generated plan string.
            pipeline_logger: The pipeline logger containing the log directory.
        """
        try:
            log_dir = Path(pipeline_logger.log_dir)
            log_dir.mkdir(parents=True, exist_ok=True)
            plan_file = log_dir / "migration_plan.md"
            plan_file.write_text(plan_text, encoding="utf-8")
            logger.info(f"[PlanningAgent] Plan saved to {plan_file}")
        except OSError as e:
            logger.warning(f"[PlanningAgent] Could not save plan file: {e}")

    @staticmethod
    def _handle_error(e: Exception, pipeline_logger: Optional[Any]) -> PlanResult:
        """Handle exceptions during the planning phase, log them, and format the return.

        Args:
            e: The caught exception.
            pipeline_logger: Optional logger for pipeline error tracking.

        Returns:
            A PlanResult dictionary indicating failure.
        """
        error_trace = traceback.format_exc()
        logger.error(f"[PlanningAgent] Failed to create plan: {e}")

        if pipeline_logger:
            pipeline_logger.log_error(
                error_type="planning_agent_error",
                error_message=str(e),
                traceback=error_trace,
            )

        return {
            "success": False,
            "plan": "",
            "error": str(e),
        }