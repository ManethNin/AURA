# AURA Frontend - Environment Setup

## Quick Start

1. **Create `.env` file** in the `frontend` directory:
```env
VITE_API_BASE_URL=http://localhost:8000
```

2. **Install dependencies**:
```bash
cd frontend
npm install react-router-dom axios
```

3. **Start development server**:
```bash
npm run dev
```

## What's Already Set Up

✅ **Complete folder structure**  
✅ **TypeScript type definitions**  
✅ **API service layer with axios**  
✅ **Authentication context and hooks**  
✅ **React Router configuration**  
✅ **All page components**  
✅ **All feature components**  
✅ **Utility functions**

## What You Need to Code

### 1. Styling (CSS)
All components are structured but need styling:
- `src/App.css` - Global styles
- Add component-specific CSS files as needed
- Style common components: Button, Card, Loading
- Style page layouts: Login, Dashboard, etc.

### 2. Component Implementation Details
Components are scaffolded but may need:
- Additional props and customization
- More detailed UI elements
- Loading and error states refinement
- Accessibility improvements

### 3. Environment Configuration
- Set up `.env` file with your API URL
- Configure CORS in your backend

## Folder Structure Overview

```
src/
├── components/
│   ├── auth/           # Login, ProtectedRoute
│   ├── changes/        # ChangeCard, ChangeList
│   ├── common/         # Button, Card, Loading
│   └── repository/     # RepositoryCard, RepositoryList
├── config/             # API and route configs
├── context/            # AuthContext
├── hooks/              # useAuth, useRepositories, useChanges
├── pages/              # All page components
├── router/             # Router setup
├── services/           # API client and services
├── types/              # TypeScript definitions
└── utils/              # Helper functions
```

## Key Files to Review

1. **`src/App.tsx`** - Main app component with router
2. **`src/router/index.tsx`** - Route definitions
3. **`src/services/api.client.ts`** - API client configuration
4. **`src/context/AuthContext.tsx`** - Authentication state
5. **`src/config/api.config.ts`** - API endpoint definitions

## Development Workflow

1. Start backend server (port 8000)
2. Start frontend dev server: `npm run dev`
3. Navigate to `http://localhost:5173`
4. Test GitHub OAuth flow
5. View repositories and changes
6. Test PR creation

## Backend API Requirements

Your backend should expose these endpoints:
- `GET /auth/login` - GitHub OAuth redirect
- `GET /auth/callback` - OAuth callback handler
- `GET /auth/me` - Get current user
- `GET /repositories` - List repositories
- `GET /repositories/:id` - Repository details
- `GET /changes` - List changes
- `POST /changes/:id/create-pr` - Create pull request

## Tips

- Use browser DevTools to debug API calls
- Check localStorage for auth token
- Add console.logs to track data flow
- Start with styling the Login page first
- Test authentication flow early
