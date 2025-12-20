# AURA Frontend

Automated Multi-Agent Repair System for Java Dependencies - Frontend Application

## Overview

AURA is a web application that helps developers automatically fix breaking dependency updates in Java codebases. Users can connect their GitHub repositories through a GitHub App, and AURA will monitor for changes, analyze breaking updates, and suggest fixes that can be applied via pull requests.

## Project Structure

```
src/
├── components/          # Reusable UI components
│   ├── auth/           # Authentication-related components
│   ├── changes/        # Change/fix display components
│   ├── common/         # Shared UI components (Button, Card, Loading)
│   └── repository/     # Repository display components
├── config/             # Configuration files
│   ├── api.config.ts   # API endpoints and settings
│   └── routes.config.ts # Route definitions
├── context/            # React context providers
│   └── AuthContext.tsx # Authentication state management
├── hooks/              # Custom React hooks
│   ├── useAuth.ts      # Authentication hook
│   ├── useChanges.ts   # Changes data hook
│   └── useRepositories.ts # Repositories data hook
├── pages/              # Page components
│   ├── AuthCallback.tsx # OAuth callback handler
│   ├── Dashboard.tsx   # Main dashboard
│   ├── Login.tsx       # Login page
│   └── RepositoryDetail.tsx # Repository detail view
├── router/             # Routing configuration
│   └── index.tsx       # Route definitions
├── services/           # API services
│   ├── api.client.ts   # Axios instance with interceptors
│   ├── auth.service.ts # Authentication API calls
│   ├── change.service.ts # Changes API calls
│   └── repository.service.ts # Repositories API calls
├── types/              # TypeScript type definitions
│   ├── api.types.ts    # API response types
│   └── index.ts        # Domain types (User, Repository, Change)
├── utils/              # Utility functions
│   ├── date.utils.ts   # Date formatting
│   ├── error.utils.ts  # Error handling
│   └── storage.utils.ts # LocalStorage wrapper
├── App.tsx             # Root component
└── main.tsx            # Application entry point
```

## Getting Started

### Prerequisites

- Node.js (v18 or higher)
- npm or yarn
- Backend API running (default: http://localhost:8000)

### Installation

1. Install dependencies:
```bash
npm install
```

2. Create a `.env` file in the frontend root directory:
```env
VITE_API_BASE_URL=http://localhost:8000
```

3. Start the development server:
```bash
npm run dev
```

### Required Dependencies

Add these to your `package.json`:

```bash
npm install react-router-dom axios
npm install -D @types/node
```

## Key Features

### 1. GitHub OAuth Authentication
- Users log in via GitHub OAuth
- Tokens stored in localStorage
- Automatic token refresh on API calls

### 2. Repository Management
- View all connected repositories
- Sync repositories from GitHub
- View repository-specific changes

### 3. Change Detection & Fixes
- View detected breaking changes
- See suggested fixes by the AI system
- Create pull requests with one click
- Track PR status

## Development Guidelines

### Component Structure
- Keep components small and focused
- Use functional components with hooks
- Export components from index.ts files

### State Management
- Use React Context for global state (auth)
- Use custom hooks for data fetching
- Keep component state local when possible

### API Integration
- All API calls go through services
- Use the api.client for authenticated requests
- Handle errors consistently with error.utils

### Styling
- Add your own CSS in component-specific files or global styles
- Use CSS classes with BEM naming convention
- Keep styling minimal and clean

## Environment Variables

- `VITE_API_BASE_URL`: Backend API base URL (default: http://localhost:8000)

## Building for Production

```bash
npm run build
```

The built files will be in the `dist/` directory.

## Next Steps for Development

1. **Implement styling**: Add CSS for all components in their respective files or in a global styles file
2. **Add error boundaries**: Implement React error boundaries for better error handling
3. **Add loading states**: Improve loading indicators and skeleton screens
4. **Add notifications**: Implement toast notifications for user feedback
5. **Add tests**: Write unit tests for components and integration tests
6. **Add pagination**: Implement pagination for repositories and changes lists
7. **Add search/filter**: Add search and filter functionality for lists
8. **Improve accessibility**: Add ARIA labels and keyboard navigation
9. **Add dark mode**: Implement dark mode support
10. **Optimize performance**: Add code splitting and lazy loading

## API Endpoints Reference

### Authentication
- `GET /auth/login` - Redirect to GitHub OAuth
- `GET /auth/callback?code=...` - Handle OAuth callback
- `GET /auth/me` - Get current user
- `POST /auth/logout` - Logout user

### Repositories
- `GET /repositories` - Get all repositories
- `GET /repositories/:id` - Get repository details
- `POST /repositories/sync` - Sync repositories from GitHub

### Changes
- `GET /changes?repository_id=...` - Get changes (optionally filtered)
- `GET /changes/:id` - Get change details
- `POST /changes/:id/create-pr` - Create pull request for a change

## License

[Your License]
