import apiClient from './api.client';
import { API_CONFIG } from '../config/api.config';
import type { Change } from '../types';

export const changeService = {
  // Get all changes
  // getChanges: async (repositoryId?: string): Promise<Change[]> => {
  //   const response = await apiClient.get(API_CONFIG.ENDPOINTS.CHANGES.LIST, {
  //     params: repositoryId ? { repository_id: repositoryId } : {},
  //   });
  //   return response.data;
  // },

  // Get change by ID
  getChangeById: async (id: string): Promise<Change> => {
    const url = API_CONFIG.ENDPOINTS.CHANGES.DETAIL.replace(':id', id);
    const response = await apiClient.get(url);
    return response.data;
  },

  // Create pull request for a change
  createPullRequest: async (id: string): Promise<{ 
    success: boolean;
    pr_url: string;
    pr_number: number;
    branch: string;
    files_updated: string[];
    message: string;
  }> => {
    const url = API_CONFIG.ENDPOINTS.CHANGES.CREATE_PR.replace(':id', id);
    const response = await apiClient.post(url);
    return response.data;
  },
};
