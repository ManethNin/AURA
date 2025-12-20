import apiClient from './api.client';
import { API_CONFIG } from '../config/api.config';
import { Change } from '../types';
import { ApiResponse } from '../types/api.types';

export const changeService = {
  // Get all changes
  getChanges: async (repositoryId?: string): Promise<ApiResponse<Change[]>> => {
    const response = await apiClient.get(API_CONFIG.ENDPOINTS.CHANGES.LIST, {
      params: repositoryId ? { repository_id: repositoryId } : {},
    });
    return response.data;
  },

  // Get change by ID
  getChangeById: async (id: string): Promise<ApiResponse<Change>> => {
    const url = API_CONFIG.ENDPOINTS.CHANGES.DETAIL.replace(':id', id);
    const response = await apiClient.get(url);
    return response.data;
  },

  // Create pull request for a change
  createPullRequest: async (id: string): Promise<ApiResponse<{ pr_url: string }>> => {
    const url = API_CONFIG.ENDPOINTS.CHANGES.CREATE_PR.replace(':id', id);
    const response = await apiClient.post(url);
    return response.data;
  },
};
