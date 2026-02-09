"""
Recipe Agent Service
Uses LLM to analyze breaking changes and select appropriate OpenRewrite recipes.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from app.core.config import settings
from app.utils.logger import logger


class RecipeAgentService:
    """
    Service that uses LLM to analyze breaking changes and select OpenRewrite recipes.
    This runs BEFORE the existing repair agent to attempt recipe-based fixes first.
    """
    
    def __init__(self, groq_api_key: str = None):
        self.groq_api_key = groq_api_key or settings.GROQ_API_KEY
        self.llm = ChatGroq(
            groq_api_key=self.groq_api_key,
            model_name=settings.LLM_MODEL,
            temperature=0,
            max_retries=3,
            timeout=120
        )
        self.recipes = self._load_recipes()
    
    def _load_recipes(self) -> List[Dict]:
        """Load available OpenRewrite recipes from JSON file."""
        recipes_path = Path(__file__).parent / "recipes.json"
        try:
            with open(recipes_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load recipes: {e}")
            return []
    
    def analyze_breaking_change(
        self,
        pom_diff: str,
        compilation_errors: str,
        pom_content: str = ""
    ) -> Dict[str, Any]:
        """
        Analyze the breaking change and determine if OpenRewrite recipes can fix it.
        
        Args:
            pom_diff: The git diff of pom.xml showing dependency changes
            compilation_errors: Maven compilation errors
            pom_content: Full pom.xml content for context
            
        Returns:
            Dict with:
                - can_use_recipes: bool - whether recipes can handle this
                - selected_recipes: List[Dict] - recipes to apply with their arguments
                - recipe_name: str - name for the custom recipe
                - reasoning: str - explanation of the decision
        """
        
        recipes_context = self._format_recipes_for_prompt()
        
        system_prompt = SystemMessage(content="""You are an expert Java dependency migration specialist.
Your task is to analyze breaking changes from dependency version upgrades and determine if OpenRewrite recipes can fix them.

You have access to these OpenRewrite recipes:
""" + recipes_context + """

## RECIPE SELECTION GUIDELINES:

### Maven Recipes (work on broken projects):
These recipes only modify pom.xml and work even when the project doesn't compile:
- **AddDependency**: Use when a transitive dependency is removed (missing package/class errors)
- **RemoveDependency**: Use when a dependency causes conflicts or is no longer needed
- **UpgradeDependency**: Use when you need to change a dependency version
- **ChangeDependencyGroupIdAndArtifactId**: Use when a library has been renamed/relocated
- **AddPlugin**: Use when a Maven plugin is required

### Java Recipes (require compilable code):
These recipes modify Java source files. Note: They may not work on broken projects:
- **ChangeType**: Use when a class moved to a different package (e.g., javax → jakarta)
- **ChangePackage**: Use when an entire package was renamed
- **ChangeMethodName**: Use when a method was renamed in a library

## CRITICAL RULES:

1. **Prefer Maven recipes** for broken projects - they're more reliable
2. **Version strings must be EXACT** - Maven Central requires exact, fully-qualified version strings:
   - ✅ "1.16.1", "2.15.1", "3.14.0" (exact patch versions that exist on Maven Central)
   - ❌ "1.16", "2.15", "3.14" (incomplete versions that may not exist!)
   - Always use the full X.Y.Z (or equivalent) version as published on Maven Central
   - When unsure about the exact version, prefer the latest stable release
   
3. **Identify the root cause** by analyzing:
   - What dependency version changed in the pom.xml diff
   - What packages/classes are missing according to the compilation errors
   - Whether a transitive dependency was removed, a library was relocated, or an API changed
   
4. **For AddDependency**: Do NOT use 'onlyIfUsing' parameter
5. **Multiple recipes**: You can select multiple recipes if needed to fix the issue
6. **Be general**: These recipes should work for ANY dependency issue - not just specific libraries

## RESPONSE FORMAT:

Respond ONLY with valid JSON:
{
    "can_use_recipes": true/false,
    "reasoning": "Detailed explanation of the root cause and fix strategy",
    "recipe_name": "com.aura.fix.DescriptiveName",
    "recipe_display_name": "Fix XYZ Breaking Changes", 
    "recipe_description": "Description of what this recipe does",
    "selected_recipes": [
        {
            "name": "org.openrewrite.maven.AddDependency",
            "arguments": {
                "groupId": "...",
                "artifactId": "...",
                "version": "..."
            }
        }
    ]
}

If recipes CANNOT fix the issue (e.g., requires complex logic changes), return:
{
    "can_use_recipes": false,
    "reasoning": "Explanation of why recipes cannot fix this",
    "selected_recipes": []
}
""")

        user_prompt = HumanMessage(content=f"""Analyze this breaking change and determine if OpenRewrite recipes can fix it.

## POM.XML CHANGES (Git Diff):
```diff
{pom_diff}
```

## COMPILATION ERRORS:
```
{compilation_errors}
```

## CURRENT POM.XML CONTENT:
```xml
{pom_content[:3000] if pom_content else "Not provided"}
```

Analyze the errors and determine:
1. What dependency version changed?
2. What is the root cause of the errors?
3. Can any of the available OpenRewrite recipes fix this?

Respond with JSON only.""")

        try:
            response = self.llm.invoke([system_prompt, user_prompt])
            content = response.content.strip()
            
            # Extract JSON from response (handle markdown code blocks)
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            result = json.loads(content)
            logger.info(f"Recipe analysis result: can_use_recipes={result.get('can_use_recipes')}")
            logger.info(f"Reasoning: {result.get('reasoning', 'No reasoning provided')}")
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"Raw response: {content}")
            return {
                "can_use_recipes": False,
                "reasoning": f"Failed to parse LLM response: {e}",
                "selected_recipes": []
            }
        except Exception as e:
            logger.error(f"Error analyzing breaking change: {e}")
            return {
                "can_use_recipes": False,
                "reasoning": f"Error during analysis: {e}",
                "selected_recipes": []
            }
    
    def _format_recipes_for_prompt(self) -> str:
        """Format recipes into a readable string for the LLM prompt."""
        lines = []
        for recipe in self.recipes:
            lines.append(f"\n### {recipe['name']}")
            lines.append(f"Description: {recipe['description']}")
            lines.append(f"Arguments: {', '.join(recipe['arguments'])}")
            lines.append(f"Required: {', '.join(recipe.get('required_arguments', recipe['arguments']))}")
            if 'example' in recipe:
                lines.append(f"Example: {json.dumps(recipe['example'], indent=2)}")
        return "\n".join(lines)
    
    def get_available_recipes(self) -> List[Dict]:
        """Return list of available recipes."""
        return self.recipes
