// API Configuration
export const API_CONFIG = {
  BASE_URL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080',
  ENDPOINTS: {
    AUTH: {
      LOGIN: '/auth/login',
      CALLBACK: '/auth/callback',
      LOGOUT: '/auth/logout',
      ME: '/auth/me',
    },
    REPOSITORIES: {
      LIST: '/repositories',
      DETAIL: '/repositories/:id',
      SYNC: '/repositories/sync',
    },
    CHANGES: {
      LIST: '/changes',
      DETAIL: '/changes/:id',
      CREATE_PR: '/changes/:id/create-pr',
    },
  },
  TIMEOUT: 30000,
};
