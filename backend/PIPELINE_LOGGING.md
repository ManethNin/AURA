# Pipeline Logging System

## Overview

The pipeline logging system tracks **every step** of the agent processing workflow, saving detailed logs to organized folders for easy debugging.

## Features

✅ **Comprehensive Tracking**
- All inputs (pom.xml diffs, errors, file contents)
- Every LLM API call and response
- Every tool execution with inputs/outputs
- All pipeline stages
- Final results and diffs
- Complete error traces

✅ **Organized Structure**
- Separate folder per project
- Separate session per run
- Timestamped files
- Easy-to-read README in each session

✅ **Automatic**
- Enabled by default in local mode
- No manual intervention needed

## Log Directory Structure

```
D:/FYP/logs/pipeline/
└── {repo_name}/
    └── {YYYYMMDD_HHMMSS}/
        ├── README.md                  # Navigation guide
        ├── session_info.json         # Session metadata
        ├── 00_input.json             # Initial input data
        ├── 00_pom_diff.txt          # POM changes
        ├── 00_initial_errors.txt    # Compilation errors
        ├── 01_prompt.json           # Prompt metadata
        ├── 01_prompt.txt            # Full prompt
        ├── 01_preread_files/        # Source files
        │   └── *.java               # Pre-read Java files
        ├── stages/                  # Pipeline stages
        │   ├── build_workflow_00.json
        │   ├── agent_start_00.json
        │   └── agent_complete_00.json
        ├── llm_calls/              # LLM interactions
        │   ├── llm_call_001.json
        │   ├── llm_call_002.json
        │   └── ...
        ├── tool_calls/             # Tool executions
        │   ├── tool_001_compile_maven.json
        │   ├── tool_001_compile_maven_output.txt
        │   └── ...
        ├── errors/                 # Error logs
        │   └── error_001_*.json
        ├── 99_final_result.json   # Final result
        ├── 99_final_diff.txt      # Generated diff
        └── 99_solution.txt        # Solution summary
```

## Example Session

### When you run:
```bash
curl -X POST http://localhost:8000/local/process/my-project
```

### Logs created at:
```
D:/FYP/logs/pipeline/my-project/20260202_205217/
```

### What's logged:

1. **Input Phase**
   - `00_input.json` - Request details
   - `00_pom_diff.txt` - What changed in pom.xml
   - `00_initial_errors.txt` - Maven errors

2. **Preparation**
   - `01_prompt.txt` - Full prompt sent to LLM
   - `01_preread_files/` - Source code the agent sees

3. **Agent Execution**
   - `llm_calls/llm_call_001.json` - First LLM call
   - `tool_calls/tool_001_compile_maven.json` - Maven compile
   - `tool_calls/tool_002_validate_diffs.json` - Diff validation
   - (continues for each iteration)

4. **Result**
   - `99_final_result.json` - Success/failure status
   - `99_final_diff.txt` - The fix generated

## Usage

### View Logs After Processing

The API response includes the log directory path:

```json
{
  "success": true,
  "log_directory": "D:\\FYP\\logs\\pipeline\\my-project\\20260202_205217"
}
```

### Navigate the Logs

1. Open the log directory
2. Read `README.md` for session overview
3. Check `00_*.txt` files for inputs
4. Review `llm_calls/` to see agent thinking
5. Check `tool_calls/` to see what was executed
6. View `99_final_*.txt` for results

### Debug a Failed Run

1. Check `errors/` folder for error details
2. Look at the last LLM call in `llm_calls/`
3. Check tool outputs in `tool_calls/`
4. Review `session_info.json` for timeline

## Configuration

In `.env`:
```env
PIPELINE_LOG_PATH=D:/FYP/logs/pipeline
```

Default: `./logs/pipeline` (relative to backend/)

## Retention

Logs are **never automatically deleted**. You can:
- Keep them for analysis
- Delete old sessions manually
- Archive by project/date

## Tips

### Finding Recent Logs
Sort folders by date - newest session is last alphabetically.

### Comparing Runs
Keep logs from different attempts to compare approaches.

### Sharing Logs
Logs are self-contained - just zip the session folder.

### Privacy
Logs contain:
- Source code snippets
- LLM API calls (no API keys)
- Error messages
- File paths

Don't share publicly if code is proprietary!

## Example Log Files

### session_info.json
```json
{
  "repo_name": "my-project",
  "session_id": "20260202_205217",
  "start_time": "2026-02-02T20:52:17.123456",
  "end_time": "2026-02-02T20:53:45.789012",
  "success": true,
  "stages": [
    {"stage": "input", "timestamp": "..."},
    {"stage": "prompt_created", "timestamp": "..."},
    {"stage": "agent_start", "timestamp": "..."},
    {"stage": "agent_complete", "timestamp": "..."}
  ]
}
```

### tool_001_compile_maven.json
```json
{
  "timestamp": "2026-02-02T20:52:30.123456",
  "tool_number": 1,
  "tool_name": "compile_maven",
  "input": {"diff": "..."},
  "output": {
    "success": false,
    "errors": "..."
  }
}
```

## Troubleshooting

### Logs not created?
- Check `PIPELINE_LOG_PATH` in `.env`
- Ensure directory is writable
- Check backend logs for permission errors

### Too many log files?
- Each LLM call creates a file
- Normal for complex fixes (10-20 calls)
- Check `session_info.json` for summary

### Can't find a session?
- Check `log_directory` in API response
- Look in `PIPELINE_LOG_PATH/{repo_name}/`
- Sessions are timestamped: `YYYYMMDD_HHMMSS`
