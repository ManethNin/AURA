import apiClient from './api.client';
import { API_CONFIG } from '../config/api.config';
import type { User } from '../types';
import { STORAGE_KEYS } from '../constants';

export const authService = {
  // Redirect to GitHub OAuth
  login: () => {
    window.location.href = `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.AUTH.LOGIN}`;
  },

  // Get current user
  getCurrentUser: async (): Promise<User> => {
    const response = await apiClient.get(API_CONFIG.ENDPOINTS.USERS.ME);
    return response.data;
  },

  // Logout
  logout: async (): Promise<void> => {
    localStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN);
    localStorage.removeItem(STORAGE_KEYS.USER);
    // await apiClient.post(API_CONFIG.ENDPOINTS.AUTH.LOGOUT);
  },
};
