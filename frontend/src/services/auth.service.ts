import apiClient from './api.client';
import { API_CONFIG } from '../config/api.config';
import { User } from '../types';
import { ApiResponse } from '../types/api.types';

export const authService = {
  // Redirect to GitHub OAuth
  login: () => {
    window.location.href = `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.AUTH.LOGIN}`;
  },

  // Handle OAuth callback
  handleCallback: async (code: string): Promise<ApiResponse<{ access_token: string; user: User }>> => {
    const response = await apiClient.get(API_CONFIG.ENDPOINTS.AUTH.CALLBACK, {
      params: { code },
    });
    return response.data;
  },

  // Get current user
  getCurrentUser: async (): Promise<ApiResponse<User>> => {
    const response = await apiClient.get(API_CONFIG.ENDPOINTS.AUTH.ME);
    return response.data;
  },

  // Logout
  logout: async (): Promise<void> => {
    await apiClient.post(API_CONFIG.ENDPOINTS.AUTH.LOGOUT);
  },
};
