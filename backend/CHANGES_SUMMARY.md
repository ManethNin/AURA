# AURA Local Mode - Changes Summary

## Changes Made

### 1. Configuration ([config.py](backend/app/core/config.py))
- Added `LOCAL_MODE` flag (default: `true`)
- Added `LOCAL_WORKSPACE_PATH` setting for local repository storage
- Made all GitHub settings optional (only required when `LOCAL_MODE=false`)

### 2. New Service ([local_repository_service.py](backend/app/services/local_repository_service.py))
Created a comprehensive service for local filesystem operations:
- `list_local_repositories()` - List all Maven projects in workspace
- `clone_repository()` - Clone from GitHub to local workspace
- `read_file()` / `write_file()` - File operations
- `get_repository_path()` - Path resolution
- `_get_git_info()` - Extract git metadata from local repos

### 3. New API Routes ([local_repos.py](backend/app/api/routes/local_repos.py))
Added endpoints for local repository management:
- `GET /local/list` - List local repositories
- `POST /local/clone` - Clone repository from GitHub
- `POST /local/process/{repo_name}` - Run agent on local repo
- `GET /local/info/{repo_name}` - Get repository details

### 4. Main Application ([main.py](backend/app/main.py))
- Conditionally load routes based on `LOCAL_MODE`
- GitHub webhooks/auth only enabled in GitHub mode
- Local routes only enabled in local mode

### 5. GitHub Service ([github_service.py](backend/app/services/github_service.py))
- Made initialization conditional on `LOCAL_MODE`
- Webhook verification returns `true` in local mode

### 6. Documentation
- Created [LOCAL_MODE_GUIDE.md](backend/LOCAL_MODE_GUIDE.md) - Complete setup guide
- Created [.env.local.example](backend/.env.local.example) - Example configuration

## How It Works

### GitHub App Mode (Original)
```
GitHub Webhook → API → Clone temporarily → Agent → Create PR
```

### Local Mode (New)
```
Local Filesystem → API → Read directly → Agent → Generate diff
```

## Key Benefits

✅ **No GitHub App Setup Required** - Just set `LOCAL_MODE=true`  
✅ **Work Offline** - Process local Java projects without internet  
✅ **Faster Development** - No webhook delays or OAuth flows  
✅ **Same Agent Logic** - All repair functionality unchanged  
✅ **Easy Testing** - Test on local projects before GitHub integration  

## Migration Path

The changes are **backwards compatible**:
- Set `LOCAL_MODE=false` to use as GitHub App (original behavior)
- Set `LOCAL_MODE=true` to use with local filesystem (new behavior)

## Next Steps

To use local mode:

1. Copy `.env.local.example` to `.env`
2. Set `LOCAL_MODE=true`
3. Set `LOCAL_WORKSPACE_PATH` to your workspace directory
4. Start the backend: `uvicorn app.main:app --reload`
5. Use the `/local/*` endpoints to manage repositories

See [LOCAL_MODE_GUIDE.md](backend/LOCAL_MODE_GUIDE.md) for detailed instructions.
