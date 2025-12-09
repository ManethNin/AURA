# AURA Backend

## 📁 Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── core/
│   │   └── config.py        # Configuration management (Settings class)
│   ├── api/
│   │   └── routes/
│   │       ├── webhook.py   # GitHub webhook endpoint
│   │       ├── auth.py      # Authentication endpoints (OAuth)
│   │       ├── repositories.py  # Repo management & PR creation
│   │       └── users.py     # User profile endpoints
│   ├── agents/              # LangGraph multi-agent system
│   │   ├── state.py         # Shared state definition
│   │   ├── analyzer.py      # Dependency analysis node
│   │   ├── repairer.py      # Code repair node
│   │   ├── workflow.py      # LangGraph workflow orchestration
│   │   └── llm_client.py    # LLM API client wrapper
│   ├── services/
│   │   ├── github_service.py    # GitHub API interactions
│   │   └── repair_service.py    # Repair workflow orchestration
│   ├── database/
│   │   └── mongodb.py       # MongoDB connection manager
│   ├── models/              # MongoDB document models
│   │   ├── user.py
│   │   ├── repository.py
│   │   └── change.py
│   ├── schemas/             # Pydantic schemas for validation
│   │   └── schemas.py
│   ├── auth/
│   │   ├── github_oauth.py  # GitHub OAuth flow
│   │   └── jwt.py           # JWT token utilities
│   └── utils/
│       ├── logger.py        # Logging configuration
│       └── helpers.py       # Common utilities
├── requirements.txt         # Python dependencies
├── .env.example            # Environment variables template
└── .gitignore
```



#### Phase 1: Core Infrastructure
1. **Database Connection** (`database/mongodb.py`)
   - Setup Motor async MongoDB client
   - Create connection pooling
   - Add health check function

2. **Models** (`models/*.py`)
   - Define MongoDB document schemas
   - Add validation and helper methods

3. **Configuration** (`core/config.py`)
   - Already set up, just verify settings

#### Phase 2: Authentication
4. **GitHub OAuth** (`auth/github_oauth.py`)
   - Implement OAuth flow
   - Token exchange
   - User info retrieval

5. **JWT Tokens** (`auth/jwt.py`)
   - Create/verify tokens
   - Add authentication dependency

6. **Auth Routes** (`api/routes/auth.py`)
   - Login endpoint
   - Callback handler
   - Logout

#### Phase 3: GitHub Integration
7. **GitHub Service** (`services/github_service.py`)
   - Webhook verification
   - Fetch file content
   - Create pull requests
   - List repositories

8. **Webhook Handler** (`api/routes/webhook.py`)
   - Receive webhook events
   - Verify signatures
   - Detect pom.xml changes
   - Trigger repair workflow

#### Phase 4: LangGraph Agent System
9. **LLM Client** (`agents/llm_client.py`)
   - Initialize LLM client
   - Create analysis prompt
   - Create repair prompt
   - Handle retries

10. **Agent State** (`agents/state.py`)
    - Define shared state structure
    - Already set up, adjust as needed

11. **Analyzer Node** (`agents/analyzer.py`)
    - Parse pom.xml
    - Call LLM for analysis
    - Identify breaking changes

12. **Repairer Node** (`agents/repairer.py`)
    - Call LLM for fix generation
    - Validate suggested fix
    - Handle retry logic

13. **Workflow** (`agents/workflow.py`)
    - Create LangGraph StateGraph
    - Add nodes and edges
    - Define conditional routing
    - Compile and export

#### Phase 5: Business Logic
14. **Repair Service** (`services/repair_service.py`)
    - Trigger workflow
    - Save results to DB
    - Update change status

15. **Repository Routes** (`api/routes/repositories.py`)
    - List user repos
    - Get changes/suggestions
    - Trigger repair
    - Create PR

16. **User Routes** (`api/routes/users.py`)
    - Get profile
    - Update settings

#### Phase 6: Polish
17. **Schemas** (`schemas/schemas.py`)
    - Add all request/response models

18. **Logging** (`utils/logger.py`)
    - Setup structured logging

19. **Main App** (`main.py`)
    - Wire up all routes
    - Add database lifecycle
    - Configure CORS

## 🔄 LangGraph Workflow Architecture

### Flow Diagram
```
START
  ↓
analyzer (analyze_dependencies)
  ↓
[Issues found?] → No → END (no action needed)
  ↓ Yes
repairer (repair_code)
  ↓
[Success?] → Yes → END (save fix)
  ↓ No
[Retries left?] → Yes → repairer (retry)
  ↓ No
END (mark as failed)
```

### State Flow
1. **Input**: commit_sha, repo_name, pom_content, breaking_code
2. **Analyzer**: Detects dependency issues
3. **Repairer**: Generates fix (with retries)
4. **Output**: suggested_fix or error_message

## 📝 Key Implementation Notes

### MongoDB Collections
- **users**: User accounts and GitHub tokens
- **repositories**: Tracked repositories
- **changes**: Detected issues and suggested fixes

### LLM Integration
- Two main prompts: analysis and repair
- Retry mechanism for failed fixes
- Structured output parsing

### GitHub App Flow
1. User installs GitHub App → webhook registration
2. Push to repo → webhook triggered
3. pom.xml detected → analysis started
4. Fix generated → shown to user on website
5. User approves → PR created

### Authentication Flow
1. User clicks "Login with GitHub"
2. Redirect to GitHub OAuth
3. Callback with code
4. Exchange for access token
5. Create JWT for session
6. Store user in MongoDB

## 🧪 Testing

