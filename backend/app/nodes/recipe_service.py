"""Recipe Agent Service.

Uses LLM to analyze breaking changes and select appropriate OpenRewrite recipes
for automated Java dependency migration using OpenRewrite framework.

This service bridges planning agents and recipe application by leveraging an LLM
to intelligently match breaking changes to applicable recipe transformations.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final, TypedDict

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

from app.config.config import settings
from app.utilities.logger import logger

__all__ = ["RecipeAgentService", "RecipeAnalysisResult", "Recipe"]

# Configuration constants
_DEFAULT_GROQ_MODEL: Final = "mixtral-8x7b-32768"
_DEFAULT_TIMEOUT_SECONDS: Final = 120
_DEFAULT_MAX_RETRIES: Final = 3
_POM_CONTENT_PREVIEW_SIZE: Final = 3000
_RECIPES_FILE_NAME: Final = "recipes.json"


class RecipeNotFoundError(Exception):
    """Raised when recipes.json cannot be found or loaded."""

    pass


class InvalidRecipeError(Exception):
    """Raised when recipe structure is invalid or malformed."""

    pass


class LLMParsingError(Exception):
    """Raised when LLM response cannot be parsed as valid JSON."""

    pass


class RecipeArgumentDict(TypedDict, total=False):
    """OpenRewrite recipe argument map.

    Keys are parameter names (e.g., 'groupId', 'artifactId', 'version'),
    values are strings or nested structures specific to recipe type.
    """

    groupId: str
    artifactId: str
    version: str
    name: str
    packagePattern: str
    newPackageName: str


@dataclass(frozen=True, slots=True)
class Recipe:
    """Immutable OpenRewrite recipe definition.

    Attributes:
        name: Fully qualified recipe class name (e.g., 'org.openrewrite.maven.AddDependency').
        arguments: Mapping of argument names to values for recipe parameterization.
    """

    name: str
    arguments: RecipeArgumentDict

    def __post_init__(self) -> None:
        """Validate recipe structure."""
        if not self.name:
            raise InvalidRecipeError("Recipe name cannot be empty")
        if not isinstance(self.arguments, dict):
            raise InvalidRecipeError("Recipe arguments must be a dictionary")


@dataclass(frozen=True, slots=True)
class RecipeAnalysisResult:
    """Result of breaking change analysis and recipe selection.

    Attributes:
        can_use_recipes: Whether recipes can fix the breaking change.
        reasoning: Detailed explanation of root cause and fix strategy.
        recipe_name: Custom recipe identifier (com.aura.fix.*).
        recipe_display_name: Human-readable recipe name.
        recipe_description: Detailed description of recipe behavior.
        selected_recipes: List of OpenRewrite recipes to apply in order.
    """

    can_use_recipes: bool
    reasoning: str
    selected_recipes: list[Recipe] = field(default_factory=list)
    recipe_name: str = ""
    recipe_display_name: str = ""
    recipe_description: str = ""


class RecipeAgentService:
    """LLM-powered OpenRewrite recipe analyzer and selector.

    Analyzes breaking changes from dependency upgrades and selects applicable
    OpenRewrite recipes to fix them automatically. Recipes are applied before
    the repair agent to prefer declarative transformations over manual repairs.

    Attributes:
        groq_api_key: API key for Groq LLM service.
        llm: Initialized Groq chat model instance.
        _recipes: Cached list of available recipes.
        _recipes_file: Path to recipes.json configuration.
    """

    def __init__(self, groq_api_key: str | None = None) -> None:
        """Initialize the recipe analysis service.

        Args:
            groq_api_key: Groq API key. If None, uses settings.GROQ_API_KEY.

        Raises:
            ValueError: If API key is not provided and settings.GROQ_API_KEY is not set.
        """
        self.groq_api_key = groq_api_key or settings.GROQ_API_KEY
        if not self.groq_api_key:
            raise ValueError(
                "GROQ_API_KEY must be provided as argument or via settings"
            )

        self.llm = ChatGroq(
            groq_api_key=self.groq_api_key,
            model_name=settings.GROQ_MODEL or _DEFAULT_GROQ_MODEL,
            temperature=0,
            max_retries=_DEFAULT_MAX_RETRIES,
            timeout=_DEFAULT_TIMEOUT_SECONDS,
        )
        self._recipes_file = Path(__file__).parent / _RECIPES_FILE_NAME
        self._recipes: list[dict[str, Any]] | None = None
    
    def _ensure_recipes_loaded(self) -> list[dict[str, Any]]:
        """Lazy-load recipes from disk.

        Returns:
            List of recipe definitions loaded from recipes.json.

        Raises:
            RecipeNotFoundError: If recipes.json cannot be found or read.
            json.JSONDecodeError: If recipes.json contains invalid JSON.
        """
        if self._recipes is not None:
            return self._recipes

        if not self._recipes_file.exists():
            raise RecipeNotFoundError(
                f"Recipes file not found: {self._recipes_file.absolute()}"
            )

        try:
            with self._recipes_file.open("r", encoding="utf-8") as f:
                self._recipes = json.load(f)
                logger.debug(
                    f"Loaded {len(self._recipes)} recipes from {self._recipes_file}"
                )
                return self._recipes
        except json.JSONDecodeError as e:
            raise RecipeNotFoundError(
                f"Invalid JSON in recipes file: {self._recipes_file}: {e}"
            ) from e
        except OSError as e:
            raise RecipeNotFoundError(
                f"Cannot read recipes file {self._recipes_file}: {e}"
            ) from e
    
    def analyze_breaking_change(
        self,
        pom_diff: str,
        migration_plan: str = "",
        pom_content: str = "",
    ) -> RecipeAnalysisResult:
        """Analyze breaking change and determine applicable OpenRewrite recipes.

        Sends breaking change details to LLM with available recipes and expects
        a structured JSON response selecting recipes that can fix the issue.

        Args:
            pom_diff: Git diff of pom.xml showing dependency changes.
            migration_plan: Plan produced by planning agent (optional context).
            pom_content: Full pom.xml content for context (optional).

        Returns:
            RecipeAnalysisResult with can_use_recipes flag, selected recipes,
            and reasoning explanation.

        Raises:
            ValueError: If pom_diff is empty or invalid.
            LLMParsingError: If LLM response cannot be parsed.
            RecipeNotFoundError: If recipes cannot be loaded.
        """
        self._validate_inputs(pom_diff, migration_plan, pom_content)

        recipes_context = self._format_recipes_for_prompt()
        system_prompt = self._build_system_prompt(recipes_context)
        user_prompt = self._build_user_prompt(pom_diff, migration_plan, pom_content)

        try:
            response = self.llm.invoke([system_prompt, user_prompt])
            result = self._parse_llm_response(response.content)
            logger.info(
                f"Recipe analysis: can_use_recipes={result['can_use_recipes']}, "
                f"recipes_count={len(result['selected_recipes'])}"
            )
            return self._convert_to_result(result)

        except LLMParsingError as e:
            logger.error(f"LLM parsing failed: {e}")
            return RecipeAnalysisResult(
                can_use_recipes=False,
                reasoning=f"Failed to parse LLM analysis: {e}",
            )
        except Exception as e:
            logger.error(f"Unexpected error during recipe analysis: {type(e).__name__}: {e}")
            return RecipeAnalysisResult(
                can_use_recipes=False,
                reasoning=f"Unexpected error: {type(e).__name__}: {e}",
            )

    @staticmethod
    def _validate_inputs(pom_diff: str, migration_plan: str, pom_content: str) -> None:
        """Validate input parameters.

        Args:
            pom_diff: Must not be empty.
            migration_plan: Can be empty (optional).
            pom_content: Can be empty (optional).

        Raises:
            ValueError: If required parameters are invalid.
        """
        if not pom_diff or not pom_diff.strip():
            raise ValueError("pom_diff cannot be empty")
        if not isinstance(pom_diff, str):
            raise ValueError("pom_diff must be a string")
        if not isinstance(migration_plan, str):
            raise ValueError("migration_plan must be a string")
        if not isinstance(pom_content, str):
            raise ValueError("pom_content must be a string")
    
    def _format_recipes_for_prompt(self) -> str:
        """Format recipes into readable string for LLM prompt.

        Returns:
            Markdown-formatted list of available recipes with details.
        """
        recipes = self._ensure_recipes_loaded()
        lines: list[str] = []

        for recipe in recipes:
            lines.append(f"\n### {recipe.get('name', 'Unknown')}")
            lines.append(f"Description: {recipe.get('description', 'No description')}")

            arguments = recipe.get("arguments", [])
            if arguments:
                lines.append(f"Arguments: {', '.join(arguments)}")

            required = recipe.get("required_arguments", arguments)
            if required:
                lines.append(f"Required: {', '.join(required)}")

            if "example" in recipe:
                lines.append(f"Example: {json.dumps(recipe['example'], indent=2)}")

        return "\n".join(lines)

    @staticmethod
    def _build_system_prompt(recipes_context: str) -> SystemMessage:
        """Build system prompt with recipe guidelines.

        Args:
            recipes_context: Formatted recipes string.

        Returns:
            SystemMessage for LLM initialization.
        """
        return SystemMessage(
            content=_SYSTEM_PROMPT_TEMPLATE.format(recipes_context=recipes_context)
        )

    @staticmethod
    def _build_user_prompt(
        pom_diff: str, migration_plan: str, pom_content: str
    ) -> HumanMessage:
        """Build user query prompt with breaking change details.

        Args:
            pom_diff: Git diff of pom.xml changes.
            migration_plan: Plan context from planning agent.
            pom_content: Full pom.xml content (truncated for preview).

        Returns:
            HumanMessage with analysis request.
        """
        pom_preview = (
            pom_content[:_POM_CONTENT_PREVIEW_SIZE]
            if pom_content
            else "Not provided"
        )
        return HumanMessage(
            content=_USER_PROMPT_TEMPLATE.format(
                pom_diff=pom_diff,
                migration_plan=migration_plan or "Not provided",
                pom_content=pom_preview,
            )
        )

    @staticmethod
    def _parse_llm_response(content: str) -> dict[str, Any]:
        """Extract and parse JSON from LLM response.

        Handles markdown code blocks and extracts valid JSON.
        Raises LLMParsingError if JSON cannot be extracted or parsed.

        Args:
            content: Raw LLM response content.

        Returns:
            Parsed JSON as dictionary.

        Raises:
            LLMParsingError: If response is not valid JSON.
        """
        if not content or not content.strip():
            raise LLMParsingError("Empty response from LLM")

        content = content.strip()

        # Try to extract JSON from markdown code blocks
        if "```json" in content:
            try:
                json_part = content.split("```json")[1].split("```")[0].strip()
            except IndexError as e:
                raise LLMParsingError(
                    "Malformed markdown code block (```json...```)"
                ) from e
        elif "```" in content:
            try:
                json_part = content.split("```")[1].split("```")[0].strip()
            except IndexError as e:
                raise LLMParsingError("Malformed markdown code block (```...```)") from e
        else:
            json_part = content

        try:
            return json.loads(json_part)
        except json.JSONDecodeError as e:
            raise LLMParsingError(
                f"Invalid JSON in LLM response: {e}. Content: {json_part[:200]}"
            ) from e

    @staticmethod
    def _convert_to_result(data: dict[str, Any]) -> RecipeAnalysisResult:
        """Convert parsed LLM response to typed RecipeAnalysisResult.

        Args:
            data: Parsed JSON response from LLM.

        Returns:
            Structured RecipeAnalysisResult.

        Raises:
            InvalidRecipeError: If recipe structure is invalid.
        """
        try:
            can_use_recipes = data.get("can_use_recipes", False)
            reasoning = data.get("reasoning", "No reasoning provided")
            selected_recipes_data = data.get("selected_recipes", [])

            recipes: list[Recipe] = []
            for recipe_data in selected_recipes_data:
                try:
                    recipe = Recipe(
                        name=recipe_data["name"],
                        arguments=recipe_data.get("arguments", {}),
                    )
                    recipes.append(recipe)
                except (KeyError, InvalidRecipeError) as e:
                    logger.warning(
                        f"Skipping invalid recipe in LLM response: {recipe_data}: {e}"
                    )
                    continue

            return RecipeAnalysisResult(
                can_use_recipes=can_use_recipes,
                reasoning=reasoning,
                recipe_name=data.get("recipe_name", ""),
                recipe_display_name=data.get("recipe_display_name", ""),
                recipe_description=data.get("recipe_description", ""),
                selected_recipes=recipes,
            )
        except Exception as e:
            logger.error(f"Error converting LLM response to result: {e}")
            raise InvalidRecipeError(f"Cannot parse LLM response as recipe result: {e}") from e

    def get_available_recipes(self) -> list[dict[str, Any]]:
        """Return list of available OpenRewrite recipes.

        Returns:
            List of recipe definitions with name, arguments, and examples.

        Raises:
            RecipeNotFoundError: If recipes cannot be loaded.
        """
        return self._ensure_recipes_loaded()


# System prompt template for LLM
_SYSTEM_PROMPT_TEMPLATE: Final = """You are an expert Java dependency migration specialist.
Your task is to analyze breaking changes from dependency version upgrades and determine
if OpenRewrite recipes can fix them.

You have access to these OpenRewrite recipes:
{recipes_context}

## CRITICAL CONTEXT:

The pipeline that runs your selected recipes automatically handles:
1. Reverting pom.xml to the last working version before running Java recipes
2. Appending UpgradeDependencyVersion to the recipe list after your selections
3. Re-applying the version bump after source fixes are complete

Therefore:
- DO NOT include UpgradeDependencyVersion in your selected_recipes
- DO NOT disqualify Java recipes because the project currently does not compile
- The project WILL be compilable when your recipes run

## RECIPE SELECTION GUIDELINES:

### Maven Recipes (pom.xml only):
- **AddDependency**: A transitive dependency was removed
- **RemoveDependency**: A dependency is no longer needed
- **ChangeDependencyGroupIdAndArtifactId**: A library was renamed/relocated

### Java Recipes (source files — pipeline handles compilability):
- **ChangeType**: A specific class moved to a different package
- **ChangePackage**: An entire package was renamed
- **ChangeMethodName**: A method was renamed

## DECISION RULE:

If the migration plan already provides an old → new class or package mapping,
ChangeType or ChangePackage CAN fix it. Do not second-guess mappings 
already identified by the migration plan.

## RECIPE ORDERING:

Always order selected_recipes as:
ChangeType → ChangePackage → ChangeMethodName → Maven recipes

## RESPONSE FORMAT:

Respond ONLY with valid JSON:
{{
    "can_use_recipes": true,
    "reasoning": "Reference the specific mapping from the migration plan",
    "recipe_name": "com.aura.fix.DescriptiveName",
    "recipe_display_name": "Fix XYZ Breaking Changes",
    "recipe_description": "What this recipe fixes",
    "selected_recipes": [
        {{
            "name": "org.openrewrite.java.ChangeType",
            "arguments": {{
                "oldFullyQualifiedTypeName": "...",
                "newFullyQualifiedTypeName": "..."
            }}
        }}
    ]
}}

If the migration plan contains NO clear type or package mapping and the fix
requires custom logic changes, return:
{{
    "can_use_recipes": false,
    "reasoning": "Explanation of why no recipe mapping exists",
    "selected_recipes": []
}}
"""

# User prompt template for breaking change analysis
_USER_PROMPT_TEMPLATE: Final = """Analyze this breaking change and determine if OpenRewrite recipes can fix it.

## POM.XML CHANGES (Git Diff):
```diff
{pom_diff}
```

## MIGRATION PLAN (from Planning Agent - follow this plan):
```
{migration_plan}
```

## CURRENT POM.XML CONTENT:
```xml
{pom_content}
```

Analyze the errors and determine:
1. What dependency version changed?
2. What is the root cause of the errors?
3. Can any of the available OpenRewrite recipes fix this?

Respond with JSON only."""
