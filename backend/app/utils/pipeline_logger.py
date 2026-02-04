"""
Pipeline Logger
Logs all agent processing stages to separate folders for debugging
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional
from app.utils.logger import logger
from app.core.config import settings


class PipelineLogger:
    """Logs all pipeline stages for a specific repository processing session"""
    
    def __init__(self, repo_name: str, base_log_path: str = None):
        """
        Initialize pipeline logger for a repository
        
        Args:
            repo_name: Name of the repository being processed
            base_log_path: Base path for logs (default: from settings or ./logs/pipeline)
        """
        self.repo_name = repo_name
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create log directory structure
        if base_log_path is None:
            base_log_path = settings.PIPELINE_LOG_PATH or "logs/pipeline"
        
        base_log_path = Path(base_log_path)
        
        self.log_dir = base_log_path / repo_name / self.session_id
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories for different stages
        self.stages_dir = self.log_dir / "stages"
        self.llm_dir = self.log_dir / "llm_calls"
        self.tools_dir = self.log_dir / "tool_calls"
        self.errors_dir = self.log_dir / "errors"
        self.api_changes_dir = self.log_dir / "api_changes"
        
        for dir in [self.stages_dir, self.llm_dir, self.tools_dir, self.errors_dir, self.api_changes_dir]:
            dir.mkdir(exist_ok=True)
        
        # Initialize session info
        self.session_info = {
            "repo_name": repo_name,
            "session_id": self.session_id,
            "start_time": datetime.now().isoformat(),
            "log_directory": str(self.log_dir),
            "stages": []
        }
        
        logger.info(f"[PIPELINE] Initialized logging for {repo_name} at {self.log_dir}")
        
    def log_input(self, pom_diff: str, initial_errors: str, repo_path: str, commit_hash: str, api_changes: str = ""):
        """Log initial input data"""
        input_data = {
            "timestamp": datetime.now().isoformat(),
            "repo_path": repo_path,
            "commit_hash": commit_hash,
            "pom_diff": pom_diff,
            "initial_errors": initial_errors,
            "api_changes": api_changes
        }
        
        self._save_json(self.log_dir / "00_input.json", input_data)
        self._save_text(self.log_dir / "00_pom_diff.txt", pom_diff)
        self._save_text(self.log_dir / "00_initial_errors.txt", initial_errors)
        if api_changes:
            self._save_text(self.log_dir / "00_api_changes.txt", api_changes)
        
        self.session_info["stages"].append({
            "stage": "input",
            "timestamp": input_data["timestamp"]
        })
        
        logger.info(f"[PIPELINE] Logged input data")
    
    def log_prompt(self, prompt: str, file_contents: Dict[str, str] = None):
        """Log the prompt sent to the agent"""
        prompt_data = {
            "timestamp": datetime.now().isoformat(),
            "prompt": prompt,
            "file_contents_count": len(file_contents) if file_contents else 0,
            "file_paths": list(file_contents.keys()) if file_contents else []
        }
        
        self._save_json(self.log_dir / "01_prompt.json", prompt_data)
        self._save_text(self.log_dir / "01_prompt.txt", prompt)
        
        if file_contents:
            files_dir = self.log_dir / "01_preread_files"
            files_dir.mkdir(exist_ok=True)
            for file_path, content in file_contents.items():
                safe_name = file_path.replace("/", "_").replace("\\", "_")
                self._save_text(files_dir / f"{safe_name}", content)
        
        self.session_info["stages"].append({
            "stage": "prompt_created",
            "timestamp": prompt_data["timestamp"]
        })
        
        logger.info(f"[PIPELINE] Logged prompt ({len(prompt)} chars)")
    
    def log_llm_call(self, call_number: int, messages: list, response: Any):
        """Log an LLM API call and response"""
        # Extract response content
        response_content = ""
        if hasattr(response, 'content'):
            response_content = str(response.content)
        else:
            response_content = str(response)
        
        call_data = {
            "timestamp": datetime.now().isoformat(),
            "call_number": call_number,
            "messages_count": len(messages),
            "messages": [self._serialize_message(msg) for msg in messages],
            "response": response_content,
            "response_type": response.__class__.__name__ if hasattr(response, '__class__') else "unknown"
        }
        
        filename = f"llm_call_{call_number:03d}.json"
        self._save_json(self.llm_dir / filename, call_data)
        
        # Also save response as text for easy viewing
        response_filename = f"llm_call_{call_number:03d}_response.txt"
        self._save_text(self.llm_dir / response_filename, response_content)
        
        logger.info(f"[PIPELINE] Logged LLM call #{call_number}")
    
    def log_tool_call(self, tool_number: int, tool_name: str, tool_input: Any, tool_output: Any):
        """Log a tool execution"""
        tool_data = {
            "timestamp": datetime.now().isoformat(),
            "tool_number": tool_number,
            "tool_name": tool_name,
            "input": self._serialize_value(tool_input),
            "output": self._serialize_value(tool_output)
        }
        
        filename = f"tool_{tool_number:03d}_{tool_name}.json"
        self._save_json(self.tools_dir / filename, tool_data)
        
        # Also save output as text for easy viewing
        if isinstance(tool_output, str):
            self._save_text(self.tools_dir / f"tool_{tool_number:03d}_{tool_name}_output.txt", tool_output)
        
        logger.info(f"[PIPELINE] Logged tool call: {tool_name}")
    
    def log_stage(self, stage_name: str, data: Dict[str, Any]):
        """Log a pipeline stage"""
        stage_data = {
            "timestamp": datetime.now().isoformat(),
            "stage": stage_name,
            "data": self._serialize_value(data)
        }
        
        # Find stage number
        stage_count = len([s for s in self.session_info["stages"] if s.get("stage") == stage_name])
        filename = f"{stage_name}_{stage_count:02d}.json"
        
        self._save_json(self.stages_dir / filename, stage_data)
        
        self.session_info["stages"].append({
            "stage": stage_name,
            "timestamp": stage_data["timestamp"]
        })
        
        logger.info(f"[PIPELINE] Logged stage: {stage_name}")
    
    def log_error(self, error_type: str, error_message: str, traceback: str = None):
        """Log an error"""
        error_data = {
            "timestamp": datetime.now().isoformat(),
            "error_type": error_type,
            "error_message": error_message,
            "traceback": traceback
        }
        
        error_count = len(list(self.errors_dir.glob("*.json")))
        filename = f"error_{error_count:03d}_{error_type}.json"
        
        self._save_json(self.errors_dir / filename, error_data)
        self._save_text(self.errors_dir / filename.replace(".json", ".txt"), 
                       f"{error_type}: {error_message}\n\n{traceback or 'No traceback'}")
        
        logger.info(f"[PIPELINE] Logged error: {error_type}")
    
    def log_api_tool_raw(self, tool_name: str, artifact: str, version_change: str, output: str):
        """Log raw API analysis tool output (REVAPI/JApiCmp)"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Safe filename from artifact name
        safe_artifact = artifact.replace(":", "_").replace("/", "_")
        safe_version = version_change.replace(" -> ", "_to_").replace(".", "_")
        
        filename = f"{tool_name}_raw_{safe_artifact}_{safe_version}.txt"
        filepath = self.api_changes_dir / filename
        
        content = f"""Tool: {tool_name.upper()}
Artifact: {artifact}
Version Change: {version_change}
Timestamp: {timestamp}
{'=' * 80}

{output}
"""
        
        self._save_text(filepath, content)
        logger.info(f"[PIPELINE] Logged {tool_name} raw output for {artifact}")
    
    def log_api_changes_filtered(self, tool_used: str, artifact: str, version_change: str, filtered_output: str):
        """Log filtered API changes that will be used in the next stage (LLM processing)"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Safe filename from artifact name
        safe_artifact = artifact.replace(":", "_").replace("/", "_")
        safe_version = version_change.replace(" -> ", "_to_").replace(".", "_")
        
        filename = f"api_changes_{safe_artifact}_{safe_version}.txt"
        filepath = self.api_changes_dir / filename
        
        content = f"""Tool(s) Used: {tool_used}
Artifact: {artifact}
Version Change: {version_change}
Timestamp: {timestamp}
Purpose: Filtered output for LLM processing
{'=' * 80}

{filtered_output}
"""
        
        self._save_text(filepath, content)
        logger.info(f"[PIPELINE] Logged filtered API changes for {artifact} (will be used in next stage)")
    
    def log_recipe_analysis(self, analysis_result: Dict[str, Any]):
        """Log recipe agent LLM analysis result"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        analysis_data = {
            "timestamp": timestamp,
            "can_use_recipes": analysis_result.get("can_use_recipes", False),
            "selected_recipes": analysis_result.get("selected_recipes", []),
            "recipe_name": analysis_result.get("recipe_name", ""),
            "reasoning": analysis_result.get("reasoning", ""),
            "analysis": self._serialize_value(analysis_result)
        }
        
        filepath = self.stages_dir / "recipe_analysis.json"
        self._save_json(filepath, analysis_data)
        
        # Also save as text for easy reading
        text_content = f"""Recipe Analysis Result
Timestamp: {timestamp}
Can Use Recipes: {analysis_result.get('can_use_recipes', False)}
Reasoning: {analysis_result.get('reasoning', '')}

Selected Recipes ({len(analysis_result.get('selected_recipes', []))}):
"""
        for i, recipe in enumerate(analysis_result.get("selected_recipes", []), 1):
            text_content += f"\n{i}. {recipe.get('name', 'Unknown')}"
            if recipe.get('arguments'):
                text_content += f"\n   Arguments: {recipe.get('arguments')}"
        
        self._save_text(self.stages_dir / "recipe_analysis.txt", text_content)
        logger.info(f"[PIPELINE] Logged recipe analysis (can_use_recipes={analysis_result.get('can_use_recipes')})")
    
    def log_recipe_execution(self, execution_type: str, success: bool, output: str, error: str = ""):
        """Log recipe execution steps (rewrite.yaml generation, mvn rewrite:run, compilation)"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        execution_data = {
            "timestamp": timestamp,
            "execution_type": execution_type,
            "success": success,
            "output": output,
            "error": error
        }
        
        # Save to recipe_execution subdirectory
        recipe_exec_dir = self.stages_dir / "recipe_execution"
        recipe_exec_dir.mkdir(exist_ok=True)
        
        filename = f"{execution_type}_{timestamp}.json"
        self._save_json(recipe_exec_dir / filename, execution_data)
        
        # Also save output as text
        text_filename = f"{execution_type}_{timestamp}.txt"
        text_content = f"""Recipe Execution: {execution_type}
Timestamp: {timestamp}
Success: {success}
{'=' * 80}

OUTPUT:
{output}
"""
        if error:
            text_content += f"\n{'=' * 80}\nERROR:\n{error}"
        
        self._save_text(recipe_exec_dir / text_filename, text_content)
        logger.info(f"[PIPELINE] Logged recipe execution: {execution_type} (success={success})")
    
    def log_recipe_result(self, result: Dict[str, Any]):
        """Log final recipe agent result"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        result_data = {
            "timestamp": timestamp,
            "success": result.get("success", False),
            "used_recipes": result.get("used_recipes", False),
            "recipes_applied": result.get("recipes_applied", []),
            "message": result.get("message", ""),
            "result": self._serialize_value(result)
        }
        
        filepath = self.stages_dir / "recipe_result.json"
        self._save_json(filepath, result_data)
        
        # Save diff if present
        if result.get("diff"):
            self._save_text(self.stages_dir / "recipe_diff.txt", result["diff"])
        
        text_content = f"""Recipe Agent Result
Timestamp: {timestamp}
Success: {result.get('success', False)}
Used Recipes: {result.get('used_recipes', False)}
Message: {result.get('message', '')}

Recipes Applied: {result.get('recipes_applied', [])}
"""
        
        self._save_text(self.stages_dir / "recipe_result.txt", text_content)
        logger.info(f"[PIPELINE] Logged recipe result (success={result.get('success')})")
    
    def log_final_result(self, success: bool, result: Dict[str, Any]):
        """Log the final result"""
        final_data = {
            "timestamp": datetime.now().isoformat(),
            "success": success,
            "result": self._serialize_value(result)
        }
        
        self._save_json(self.log_dir / "99_final_result.json", final_data)
        
        # Save diff if present
        if "diff" in result:
            self._save_text(self.log_dir / "99_final_diff.txt", result["diff"])
        
        # Save solution if present
        if "solution" in result:
            self._save_text(self.log_dir / "99_solution.txt", result["solution"])
        
        self.session_info["end_time"] = datetime.now().isoformat()
        self.session_info["success"] = success
        
        logger.info(f"[PIPELINE] Logged final result (success={success})")
    
    def finalize(self):
        """Finalize logging and save session summary"""
        self.session_info["end_time"] = self.session_info.get("end_time", datetime.now().isoformat())
        self._save_json(self.log_dir / "session_info.json", self.session_info)
        
        # Create a README for easy navigation
        readme = self._generate_readme()
        self._save_text(self.log_dir / "README.md", readme)
        
        logger.info(f"[PIPELINE] Finalized logging session at {self.log_dir}")
    
    def _generate_readme(self) -> str:
        """Generate a README for the log directory"""
        readme = f"""# Pipeline Log: {self.repo_name}

**Session ID:** {self.session_id}
**Start Time:** {self.session_info.get('start_time')}
**End Time:** {self.session_info.get('end_time', 'In progress')}
**Success:** {self.session_info.get('success', 'Unknown')}

## Directory Structure

```
{self.log_dir.name}/
├── README.md                    # This file
├── session_info.json           # Session metadata
├── 00_input.json               # Initial input data
├── 00_pom_diff.txt            # POM.xml changes
├── 00_initial_errors.txt      # Initial compilation errors
├── 01_prompt.json             # Agent prompt metadata
├── 01_prompt.txt              # Full agent prompt
├── 01_preread_files/          # Pre-read source files
├── stages/                    # Pipeline stage logs
│   ├── recipe_analysis.json   # Recipe agent LLM analysis (if used)
│   ├── recipe_result.json     # Recipe agent final result (if used)
│   └── recipe_execution/      # Recipe execution logs (if used)
├── llm_calls/                 # LLM API call logs
├── tool_calls/                # Tool execution logs
├── api_changes/               # API analysis tool outputs (REVAPI/JApiCmp)
├── errors/                    # Error logs
├── 99_final_result.json       # Final result
├── 99_final_diff.txt          # Final diff (if successful)
└── 99_solution.txt            # Solution text (if available)
```

## Processing Stages

"""
        for i, stage in enumerate(self.session_info.get("stages", []), 1):
            readme += f"{i}. **{stage['stage']}** - {stage['timestamp']}\n"
        
        readme += f"\n## Files\n\n"
        readme += f"- **Input Files:** See `00_*.txt` files\n"
        
        # Check for recipe logs
        recipe_analysis = (self.stages_dir / "recipe_analysis.json").exists()
        recipe_execution_dir = self.stages_dir / "recipe_execution"
        recipe_executions = len(list(recipe_execution_dir.glob('*.json'))) if recipe_execution_dir.exists() else 0
        
        if recipe_analysis or recipe_executions > 0:
            readme += f"- **Recipe Agent:** "
            if recipe_analysis:
                readme += f"Analysis logged"
            if recipe_executions > 0:
                readme += f", {recipe_executions} execution steps in `stages/recipe_execution/`"
            readme += "\n"
        
        readme += f"- **LLM Calls:** {len(list(self.llm_dir.glob('*.json')))} calls in `llm_calls/`\n"
        readme += f"- **Tool Calls:** {len(list(self.tools_dir.glob('*.json')))} calls in `tool_calls/`\n"
        readme += f"- **API Changes:** {len(list(self.api_changes_dir.glob('*.txt')))} files in `api_changes/`\n"
        readme += f"- **Errors:** {len(list(self.errors_dir.glob('*.json')))} errors in `errors/`\n"
        readme += f"- **Final Result:** See `99_final_*.txt` files\n"
        
        return readme
    
    def _save_json(self, filepath: Path, data: Any):
        """Save data as JSON"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _save_text(self, filepath: Path, text: str):
        """Save text to file"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(text)
    
    def _serialize_message(self, msg) -> Dict:
        """Serialize a LangChain message"""
        try:
            return {
                "type": msg.__class__.__name__,
                "content": str(msg.content) if hasattr(msg, 'content') else str(msg)
            }
        except:
            return {"type": "unknown", "content": str(msg)}
    
    def _serialize_value(self, value: Any) -> Any:
        """Serialize a value for JSON storage"""
        if isinstance(value, (str, int, float, bool, type(None))):
            return value
        elif isinstance(value, dict):
            return {k: self._serialize_value(v) for k, v in value.items()}
        elif isinstance(value, (list, tuple)):
            return [self._serialize_value(v) for v in value]
        elif isinstance(value, Path):
            return str(value)
        elif isinstance(value, datetime):
            return value.isoformat()
        else:
            return str(value)
