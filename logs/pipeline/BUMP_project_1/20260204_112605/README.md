# Pipeline Log: BUMP_project_1

**Session ID:** 20260204_112605
**Start Time:** 2026-02-04T11:26:05.526058
**End Time:** 2026-02-04T11:26:50.538790
**Success:** False

## Directory Structure

```
20260204_112605/
├── README.md                    # This file
├── session_info.json           # Session metadata
├── 00_input.json               # Initial input data
├── 00_pom_diff.txt            # POM.xml changes
├── 00_initial_errors.txt      # Initial compilation errors
├── 01_prompt.json             # Agent prompt metadata
├── 01_prompt.txt              # Full agent prompt
├── 01_preread_files/          # Pre-read source files
├── stages/                    # Pipeline stage logs
├── llm_calls/                 # LLM API call logs
├── tool_calls/                # Tool execution logs
├── api_changes/               # API analysis tool outputs (REVAPI/JApiCmp)
├── errors/                    # Error logs
├── 99_final_result.json       # Final result
├── 99_final_diff.txt          # Final diff (if successful)
└── 99_solution.txt            # Solution text (if available)
```

## Processing Stages

1. **input** - 2026-02-04T11:26:39.702258
2. **build_workflow** - 2026-02-04T11:26:40.567498
3. **prompt_created** - 2026-02-04T11:26:40.571635
4. **agent_start** - 2026-02-04T11:26:40.591819
5. **llm_call_1_start** - 2026-02-04T11:26:40.674668
6. **llm_call_2_start** - 2026-02-04T11:26:42.623584
7. **llm_call_3_start** - 2026-02-04T11:26:50.418283

## Files

- **Input Files:** See `00_*.txt` files
- **LLM Calls:** 2 calls in `llm_calls/`
- **Tool Calls:** 0 calls in `tool_calls/`
- **API Changes:** 2 files in `api_changes/`
- **Errors:** 1 errors in `errors/`
- **Final Result:** See `99_final_*.txt` files
