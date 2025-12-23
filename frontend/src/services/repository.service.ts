import apiClient from './api.client';
import { API_CONFIG } from '../config/api.config';
import type { Repository, Change } from '../types';

export const repositoryService = {
  // Get all repositories
  getRepositories: async (): Promise<Repository[]> => {
    const response = await apiClient.get(API_CONFIG.ENDPOINTS.REPOSITORIES.LIST);
    return response.data;
  },

  // Get repository by ID
  getRepositoryById: async (id: string): Promise<Repository> => {
    const url = API_CONFIG.ENDPOINTS.REPOSITORIES.DETAIL.replace(':id', id);
    const response = await apiClient.get(url);
    return response.data;
  },

  // Get changes for a specific repository
  getChangesByRepository: async (id: string): Promise<Change[]> => {
    console.log(id)
    const url = API_CONFIG.ENDPOINTS.REPOSITORIES.CHANGES.replace(':id', id);
    const response = await apiClient.get(url);
    return response.data;
  },

  // Delete repository
  deleteRepository: async (id: string): Promise<{ id: string; message: string }> => {
    const url = API_CONFIG.ENDPOINTS.REPOSITORIES.DETAIL.replace(':id', id);
    const response = await apiClient.delete(url);
    return response.data;
  }
};
