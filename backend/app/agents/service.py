# agent/service.py
"""
Main service for running the Java migration agent in your web application
"""

import os
import json
import tempfile
import shutil
from pathlib import Path
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from app.common_agents.agent.GitAgent import GitAgent
from .tools import get_tools_for_repo
from .workflow import build_workflow, SYSTEM_PROMPT


class JavaMigrationAgentService:
    """Service to run the agent in your web application"""
    
    def __init__(self, groq_api_key: str):
        self.llm = ChatGroq(
            groq_api_key=groq_api_key,
            model_name="llama-3.3-70b-versatile",
            temperature=0,
            max_retries=3,
            timeout=240
        )
    
    def process_repository(
        self,
        repo_path: str,
        commit_hash: str,
        repo_slug: str,
        pom_diff: str,
        initial_errors: str = ""
    ):
        """
        Run the agent on a repository to fix Java dependency issues
        
        Args:
            repo_path: Path to cloned repository
            commit_hash: Git commit hash
            repo_slug: Repository identifier (owner/repo)
            pom_diff: The pom.xml changes that caused issues
            initial_errors: Compilation errors from Maven (if available)
        
        Returns:
            dict with 'success', 'diff', 'solution' or 'error'
        """
        
        output_path = tempfile.mkdtemp(prefix="agent_out_")
        
        try:
            # Get tools for the repository
            tools = get_tools_for_repo(
                repo_path=Path(repo_path),
                repo_slug=repo_slug,
                commit_hash=commit_hash
            )
            
            # PRE-READ ERROR FILES AND INCLUDE IN PROMPT
            import re
            error_file_matches = re.findall(r'(src/main/java/[\w/]+\.java)', initial_errors)
            unique_files = list(set(error_file_matches))
            
            file_contents = {}
            for file_path in unique_files:
                try:
                    full_path = Path(repo_path) / file_path
                    if full_path.exists():
                        with open(full_path, 'r', encoding='utf-8') as f:
                            file_contents[file_path] = f.read()
                        print(f"[DEBUG] Pre-read file: {file_path} ({len(file_contents[file_path])} chars)")
                except Exception as e:
                    print(f"[WARN] Could not pre-read {file_path}: {e}")
            
            # Build workflow
            app = build_workflow(self.llm, tools, output_path)
            
            # Create prompt for the agent WITH FILE CONTENT
            prompt = self._create_prompt(pom_diff, initial_errors, file_contents)
            
            # Run agent with reduced recursion limit to save tokens
            initial_messages = [
                SYSTEM_PROMPT,
                HumanMessage(content=prompt)
            ]
            
            result = app.invoke(
                {"messages": initial_messages, "proposed_diff": None},
                config={
                    "run_name": commit_hash,
                    "recursion_limit": 30,  # Reduced from 30 to save API tokens
                    "configurable": {"thread_id": commit_hash}
                }
            )
            
            # Get the proposed diff that was validated (stored in state)
            proposed_diff = result.get("proposed_diff", "")
            print(f"[DEBUG] Retrieved proposed_diff from state: {len(proposed_diff) if proposed_diff else 0} chars")
            
            # Get final diff from git as well
            git_agent = GitAgent(Path(repo_path), commit_hash, repo_slug)
            final_diff = git_agent.get_full_diff()
            
            # Use proposed_diff if available, otherwise fall back to git diff
            diff_to_store = proposed_diff if proposed_diff else final_diff
            
            return {
                "success": True,
                "diff": diff_to_store,
                "solution": proposed_diff if proposed_diff else "No diff was generated"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _create_prompt(self, pom_diff: str, initial_errors: str, file_contents: dict = None) -> str:
        """Create the prompt for the agent with actual file content"""
        prompt = f"""You are a Java dependency migration expert. A pom.xml file has been updated with new dependencies, causing compilation errors.

POM.XML CHANGES:
```diff
{pom_diff}
```
"""
        
        if initial_errors:
            prompt += f"""
COMPILATION ERRORS:
```
{initial_errors}
```
"""
        
        # Include actual file content so agent doesn't have to guess
        if file_contents:
            prompt += "\n\n" + "="*80 + "\n"
            prompt += "📄 CURRENT FILE CONTENTS (ACTUAL SOURCE CODE):\n"
            prompt += "="*80 + "\n"
            for file_path, content in file_contents.items():
                prompt += f"\n=== {file_path} ===\n```java\n{content}\n```\n"
            prompt += "\n" + "="*80 + "\n"
            prompt += "⚠️  Your diff MUST match the EXACT lines shown above (including whitespace, blank lines, etc.)\n"
            prompt += "="*80 + "\n\n"
        
        prompt += """
YOUR TASK:
1. Analyze the dependency changes in pom.xml
2. Look at the ACTUAL file content provided above
3. Identify what API changes occurred between the old and new versions
4. Generate a diff that matches the EXACT lines from the actual file content
5. Fix the Java source code to work with the new dependencies
6. Validate your changes compile successfully

⚠️ CRITICAL RULES:
- DO NOT CHANGE versions of existing dependencies in pom.xml
- The version upgrades are intentional and MUST be kept
- You MUST update the Java code to be compatible with the NEW versions
- Reverting dependency versions is FORBIDDEN
- You MAY ADD new dependencies to pom.xml if needed to fix issues (e.g., adding missing transitive dependencies)
- When adding dependencies, only add new <dependency> blocks - do NOT modify existing dependency versions
- Your diff MUST match the exact lines shown in the file content above
- Include proper context lines for the diff to apply correctly

Use the provided tools to:
- Validate diffs before applying them (validate_diffs tool)
- Compile with Maven to check your fixes (compile_maven_stateful tool)
- Reset the repository if needed to try different approaches

Provide unified diff format changes to fix the Java source code AND/OR add new dependencies to pom.xml if needed.
"""
        
        return prompt