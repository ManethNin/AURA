import { useState, useEffect } from 'react';
import { repositoryService, changeService } from '../services';
import type { Change } from '../types';

export const useChanges = (repositoryId: string) => {
  const [changes, setChanges] = useState<Change[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchChanges = async () => {
    try {
      setLoading(true);
      const data = await repositoryService.getChangesByRepository(repositoryId);
      setChanges(data);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch changes');
    } finally {
      setLoading(false);
    }
  };

  const createPR = async (changeId: string) => {
    try {
      const response = await changeService.createPullRequest(changeId);
      await fetchChanges(); // Refresh changes
      return response;
    } catch (err: any) {
      throw new Error(err.message || 'Failed to create pull request');
    }
  };

  useEffect(() => {
    fetchChanges();
  }, [repositoryId]);

  return { changes, loading, error, refetch: fetchChanges, createPR };
};
