import { useState, useEffect } from 'react';
import type { Repository } from '../types';
import { API_CONFIG } from '../config/api.config';
import apiClient from '../services/api.client';
import { repositoryService } from '../services';


export const useRepositories = () => {
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchRepositories = async () => {
    try {
      setLoading(true);
      const response = await apiClient.get(API_CONFIG.ENDPOINTS.REPOSITORIES.LIST);

      setRepositories(response.data);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch repositories');
    } finally {
      setLoading(false);
    }
  };

  const deleteRepository = async (id: string) => {
    try {
      await repositoryService.deleteRepository(id);
      // Remove from local state
      setRepositories(prev => prev.filter(repo => repo._id !== id));
      return { success: true };
    } catch (err: any) {
      setError(err.message || 'Failed to delete repository');
      return { success: false, error: err.message };
    }
  };

  useEffect(() => {
    fetchRepositories();
  }, []);

  return { repositories, loading, error, refetch: fetchRepositories, deleteRepository };
};
