# Pipeline Log: guice

**Session ID:** 20260204_194422
**Start Time:** 2026-02-04T19:44:22.861384
**End Time:** 2026-02-04T19:49:09.682988
**Success:** False

## Directory Structure

```
20260204_194422/
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

1. **input** - 2026-02-04T19:46:00.389574
2. **build_workflow** - 2026-02-04T19:46:01.440256
3. **prompt_created** - 2026-02-04T19:46:01.446306
4. **agent_start** - 2026-02-04T19:46:01.453665
5. **llm_call_1_start** - 2026-02-04T19:46:01.458694
6. **llm_call_2_start** - 2026-02-04T19:49:09.523230

## Files

- **Input Files:** See `00_*.txt` files
- **Recipe Agent:** Analysis logged
- **LLM Calls:** 1 calls in `llm_calls/`
- **Tool Calls:** 0 calls in `tool_calls/`
- **API Changes:** 2 files in `api_changes/`
- **Errors:** 1 errors in `errors/`
- **Final Result:** See `99_final_*.txt` files
