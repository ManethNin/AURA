# agents/planning_service.py
"""
Planning agent service - analyzes the problem and creates a migration plan
before the recipe agent or LLM repair agent runs.
"""

import re
import traceback
from pathlib import Path
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from app.core.config import settings
from app.utils.logger import logger


PLANNING_SYSTEM_PROMPT = """You are an expert Java dependency migration planner.

Your ONLY job is to analyze the problem and produce a clear, actionable migration plan.
You do NOT fix code. You do NOT produce diffs. You ONLY plan.

Given:
- The pom.xml dependency changes (what was upgraded)
- Compilation errors caused by the upgrade
- API changes between the old and new dependency versions (if available)
- The actual source code of affected files

You must produce a structured migration plan that covers:

1. **Root Cause Analysis**: What dependency was upgraded and why it causes breakage.
2. **Breaking Changes Summary**: List each breaking API change that affects this project.
3. **Affected Files**: Which source files need changes and why.
4. **Migration Steps**: For each affected file, describe the exact changes needed:
   - Which imports need updating
   - Which method calls need to change (old signature → new signature)
   - Which classes/interfaces were renamed or moved
   - Any new dependencies that need to be added to pom.xml
5. **Risk Assessment**: Flag any changes that might affect runtime behavior beyond compilation.
6. **Suggested Order**: The recommended order to apply fixes (e.g., fix shared utilities first).

IMPORTANT RULES:
- DO NOT produce any code diffs or patches
- DO NOT suggest reverting dependency versions — the upgrades are intentional
- You MAY suggest adding NEW dependencies to pom.xml if needed
- Be specific: use actual class names, method signatures, and line references
- If API changes are provided, cross-reference them with the compilation errors
- Keep the plan concise but thorough
"""


class PlanningAgentService:
    """Service that analyzes the migration problem and produces an actionable plan."""

    def __init__(self, provider: str = None, api_key: str = None, model: str = None):
        """Initialize with configurable LLM provider.

        Args:
            provider: "groq" or "gemini" (defaults to settings.LLM_PROVIDER)
            api_key: API key (defaults to appropriate key from settings)
            model: Model name (defaults to appropriate model from settings)
        """
        provider = provider or settings.LLM_PROVIDER

        if provider == "gemini":
            api_key = api_key or settings.GOOGLE_API_KEY
            model = model or settings.GEMINI_MODEL
            self.llm = ChatGoogleGenerativeAI(
                model=model,
                temperature=0.0,
                google_api_key=api_key,
                max_retries=3,
                timeout=240,
            )
            self.provider = "gemini"
        else:
            api_key = api_key or settings.GROQ_API_KEY
            model = model or settings.GROQ_MODEL
            self.llm = ChatGroq(
                groq_api_key=api_key,
                model_name=model,
                temperature=0.0,
                max_retries=3,
                timeout=240,
            )
            self.provider = "groq"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_plan(
        self,
        repo_path: str,
        commit_hash: str,
        repo_slug: str,
        pom_diff: str,
        initial_errors: str = "",
        api_changes_text: str = "",
        pipeline_logger=None,
    ) -> dict:
        """Analyze the migration problem and return a structured plan.

        Returns:
            dict with keys:
                - success (bool)
                - plan (str): the full plan text
                - error (str | None): error message if failed
        """
        logger.info(f"[PlanningAgent] Creating migration plan for {repo_slug}")

        if pipeline_logger:
            pipeline_logger.log_stage("planning_agent_start", {
                "repo_slug": repo_slug,
                "commit_hash": commit_hash,
                "provider": self.provider,
            })

        try:
            # Pre-read files referenced in compilation errors
            file_contents = self._read_error_files(repo_path, initial_errors)

            # Build the prompt
            prompt = self._build_prompt(
                pom_diff=pom_diff,
                initial_errors=initial_errors,
                api_changes_text=api_changes_text,
                file_contents=file_contents,
            )

            if pipeline_logger:
                pipeline_logger.log_stage("planning_agent_prompt", {
                    "prompt_length": len(prompt),
                    "files_included": list(file_contents.keys()),
                })

            # Call the LLM
            messages = [
                {"role": "system", "content": PLANNING_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]

            response = self.llm.invoke(messages)
            plan_text = response.content.strip() if hasattr(response, "content") else str(response)

            logger.info(f"[PlanningAgent] Plan generated ({len(plan_text)} chars)")

            if pipeline_logger:
                pipeline_logger.log_stage("planning_agent_complete", {
                    "plan_length": len(plan_text),
                })
                # Save the plan to a dedicated file in the log directory
                try:
                    plan_file = pipeline_logger.log_dir / "migration_plan.md"
                    plan_file.write_text(plan_text, encoding="utf-8")
                    logger.info(f"[PlanningAgent] Plan saved to {plan_file}")
                except Exception as e:
                    logger.warning(f"[PlanningAgent] Could not save plan file: {e}")

            return {
                "success": True,
                "plan": plan_text,
                "error": None,
            }

        except Exception as e:
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

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _read_error_files(repo_path: str, initial_errors: str) -> dict:
        """Pre-read Java source files mentioned in compilation errors."""
        file_contents: dict[str, str] = {}
        if not initial_errors:
            return file_contents

        error_file_matches = re.findall(r"(src/main/java/[\w/]+\.java)", initial_errors)
        unique_files = list(set(error_file_matches))

        for file_path in unique_files:
            try:
                full_path = Path(repo_path) / file_path
                if full_path.exists():
                    file_contents[file_path] = full_path.read_text(encoding="utf-8")
                    logger.debug(f"[PlanningAgent] Pre-read {file_path} ({len(file_contents[file_path])} chars)")
            except Exception as e:
                logger.warning(f"[PlanningAgent] Could not read {file_path}: {e}")

        return file_contents

    def _build_prompt(
        self,
        pom_diff: str,
        initial_errors: str,
        api_changes_text: str,
        file_contents: dict,
    ) -> str:
        """Assemble the user prompt sent to the planning LLM."""
        sections: list[str] = []

        # 1. POM diff
        sections.append("## POM.XML DEPENDENCY CHANGES\n```diff\n" + (pom_diff or "(no diff provided)") + "\n```")

        # 2. API changes
        if api_changes_text:
            sections.append("## API CHANGES BETWEEN OLD AND NEW DEPENDENCY VERSIONS\n```\n" + api_changes_text + "\n```")

        # 3. Compilation errors
        if initial_errors:
            sections.append("## COMPILATION ERRORS\n```\n" + initial_errors + "\n```")

        # 4. Source files
        if file_contents:
            file_section = "## AFFECTED SOURCE FILES\n"
            for path, content in file_contents.items():
                file_section += f"\n### {path}\n```java\n{content}\n```\n"
            sections.append(file_section)

        sections.append(
            "Based on the information above, produce a detailed migration plan. "
            "Do NOT produce code diffs — only describe what needs to change and why."
        )

        return "\n\n".join(sections)
