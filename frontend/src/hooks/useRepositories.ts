import { useState, useEffect } from 'react';
import { repositoryService } from '../services';
import { Repository } from '../types';
import { STORAGE_KEYS } from '../constants';

export const useRepositories = () => {
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchRepositories = async () => {
    try {
      setLoading(true);
      const response = await repositoryService.getRepositoryById(localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN));
      setRepositories(response.data);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch repositories');
    } finally {
      setLoading(false);
    }
  };

  const syncRepositories = async () => {
    try {
      setLoading(true);
      const response = await repositoryService.syncRepositories();
      setRepositories(response.data);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to sync repositories');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRepositories();
  }, []);

  return { repositories, loading, error, refetch: fetchRepositories, sync: syncRepositories };
};
