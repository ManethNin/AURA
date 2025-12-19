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
from app.masterthesis.agent.GitAgent import GitAgent
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
            
            # Build workflow
            app = build_workflow(self.llm, tools, output_path)
            
            # Create prompt for the agent
            prompt = self._create_prompt(pom_diff, initial_errors)
            
            # Run agent
            initial_messages = [
                SYSTEM_PROMPT,
                HumanMessage(content=prompt)
            ]
            
            result = app.invoke(
                {"messages": initial_messages, "proposed_diff": None},
                config={
                    "run_name": commit_hash,
                    "recursion_limit": 30,
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
    
    def _create_prompt(self, pom_diff: str, initial_errors: str) -> str:
        """Create the prompt for the agent"""
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
        
        prompt += """
YOUR TASK:
1. Analyze the dependency changes in pom.xml
2. Identify what API changes occurred between the old and new versions
3. Fix the Java source code to work with the new dependencies
4. Validate your changes compile successfully

⚠️ CRITICAL RULES:
- DO NOT modify pom.xml or any Maven/Gradle build files
- The version upgrade is intentional and MUST be kept
- You MUST update the Java code to be compatible with the NEW versions
- Reverting dependency versions is FORBIDDEN

Use the provided tools to:
- Read files to understand the codebase
- Validate diffs before applying them
- Compile with Maven to check your fixes
- Reset the repository if needed to try different approaches

Provide unified diff format changes to fix the JAVA SOURCE CODE ONLY.
"""
        
        return prompt