# AURA Local Mode Setup Guide

## Overview

AURA now supports **Local Mode**, allowing you to work with Java projects on your local filesystem instead of requiring a GitHub App setup. This is ideal for development and testing.

## Quick Start

### 1. Configure Environment

Copy the example environment file:
```bash
cp .env.local.example .env
```

Edit `.env` and set:
```env
LOCAL_MODE=true
LOCAL_WORKSPACE_PATH=D:/FYP/workspace  # Your workspace path
GROQ_API_KEY=your_groq_api_key
MONGODB_URL=mongodb://localhost:27017
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Start MongoDB

Make sure MongoDB is running locally:
```bash
# Windows (if MongoDB is installed as a service)
net start MongoDB

# Or using Docker
docker run -d -p 27017:27017 --name mongodb mongo:latest
```

### 4. Run the Backend

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

## API Endpoints (Local Mode)

### List Local Repositories
```bash
GET /local/list
```

Returns all Java (Maven) projects in your workspace directory.

### Clone a Repository from GitHub
```bash
POST /local/clone
Content-Type: application/json

{
  "git_url": "https://github.com/owner/repo.git",
  "target_name": "my-project"  // optional
}
```

This clones a GitHub repository to your local workspace.

### Process a Repository with the Agent
```bash
POST /local/process/{repo_name}
Content-Type: application/json

{
  "pom_diff": "",  // optional: specific pom.xml changes
  "initial_errors": ""  // optional: Maven compilation errors
}
```

Runs the Java migration agent on a local repository to fix dependency issues.

### Get Repository Info
```bash
GET /local/info/{repo_name}
```

Returns detailed information about a local repository.

## Workflow Example

### 1. Clone a Java Project

```bash
curl -X POST http://localhost:8000/local/clone \
  -H "Content-Type: application/json" \
  -d '{
    "git_url": "https://github.com/apache/commons-lang.git"
  }'
```

### 2. List Your Projects

```bash
curl http://localhost:8000/local/list
```

### 3. Process a Project

```bash
curl -X POST http://localhost:8000/local/process/commons-lang \
  -H "Content-Type: application/json" \
  -d '{
    "initial_errors": "Compilation errors here..."
  }'
```

## Directory Structure

```
LOCAL_WORKSPACE_PATH/
├── project1/
│   ├── pom.xml
│   ├── src/
│   └── ...
├── project2/
│   ├── pom.xml
│   ├── src/
│   └── ...
└── ...
```

## Features in Local Mode

✅ **Enabled:**
- Clone repositories from GitHub
- List local Java projects
- Process repositories with the agent
- View repository information
- All agent functionality works locally

❌ **Disabled:**
- GitHub webhooks
- GitHub OAuth authentication
- Automatic PR creation (agent still generates diffs)

## Switching Back to GitHub App Mode

To use AURA as a GitHub App:

1. Set `LOCAL_MODE=false` in `.env`
2. Configure all GitHub App settings:
   - GITHUB_APP_ID
   - GITHUB_PRIVATE_KEY
   - GITHUB_WEBHOOK_SECRET
   - GITHUB_CLIENT_ID
   - GITHUB_CLIENT_SECRET
3. Restart the application

## Testing

### Test the Setup

```bash
# Check API is running
curl http://localhost:8000/

# List repositories (should be empty initially)
curl http://localhost:8000/local/list

# Clone a test project
curl -X POST http://localhost:8000/local/clone \
  -H "Content-Type: application/json" \
  -d '{"git_url": "https://github.com/your-test-repo.git"}'
```

## Troubleshooting

### "LOCAL_WORKSPACE_PATH not configured"
- Make sure `LOCAL_WORKSPACE_PATH` is set in your `.env` file
- Use an absolute path
- Ensure the directory exists or the app will create it

### "Repository not found"
- Check that the repository name matches the directory name
- Use `GET /local/list` to see available repositories

### Agent Processing Fails
- Ensure MongoDB is running
- Check that GROQ_API_KEY is valid
- Verify the project has a valid pom.xml file
- Check logs for detailed error messages

## Development Notes

The agent service (`app.agents.service.JavaMigrationAgentService`) works identically in both modes. The main differences are:

- **Local Mode**: Repositories are read from filesystem
- **GitHub Mode**: Repositories are cloned temporarily from GitHub webhooks

All agent logic, LLM integration, and repair mechanisms remain the same.
