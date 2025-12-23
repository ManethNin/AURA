// API Configuration
export const API_CONFIG = {
  BASE_URL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080',
  ENDPOINTS: {
    USERS :{
      USERS : '/users',
      ME : '/users/me',
    },
    AUTH: {
      LOGIN: '/auth/github/login'
    },
    REPOSITORIES: {
      LIST: '/repositories',
      DETAIL: '/repositories/:id',
      DELETE: '/repositories/:id',
      CHANGES: '/repositories/:id/changes'
    },
    CHANGES: {
      DETAIL: '/changes/:id',
      STATUS: '/changes/:id/status',           
      CREATE_PR: '/changes/:id/pull-request'  
    },
    ADMIN: {
      USERS: '/admin/users',
      REPOSITORIES: '/admin/repositories',
      CHANGES: '/admin/changes'
    }
  },
  TIMEOUT: 30000,
};
