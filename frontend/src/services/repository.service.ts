import apiClient from './api.client';
import { API_CONFIG } from '../config/api.config';
import { Repository } from '../types';
import { ApiResponse, PaginatedResponse } from '../types/api.types';

export const repositoryService = {
  // Get all repositories
  getRepositories: async (): Promise<ApiResponse<Repository[]>> => {
    const response = await apiClient.get(API_CONFIG.ENDPOINTS.REPOSITORIES.LIST);
    return response.data;
  },

  // Get repository by ID
  getRepositoryById: async (id: string): Promise<ApiResponse<Repository>> => {
    const url = API_CONFIG.ENDPOINTS.REPOSITORIES.DETAIL.replace(':id', id);
    const response = await apiClient.get(url);
    return response.data;
  },

  // Sync repositories from GitHub
  syncRepositories: async (): Promise<ApiResponse<Repository[]>> => {
    const response = await apiClient.post(API_CONFIG.ENDPOINTS.REPOSITORIES.SYNC);
    return response.data;
  },
};
