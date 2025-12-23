import React from 'react';
import type { Repository } from '../../types';
import { RepositoryCard } from './RepositoryCard';
import { Loading } from '../common';

interface RepositoryListProps {
  repositories: Repository[];
  loading?: boolean;
  onDelete?: (id: string) => Promise<{ success: boolean; error?: string }>;
}

export const RepositoryList: React.FC<RepositoryListProps> = ({ repositories, loading, onDelete }) => {
  if (loading) {
    return <Loading message="Loading repositories..." />;
  }

  if (repositories.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-icon">📦</div>
        <p className="empty-title">No repositories found</p>
        <p className="empty-description">Install the AURA GitHub App to get started.</p>
      </div>
    );
  }

  return (
    <div className="repository-list">
      {repositories.map((repo) => (
        <RepositoryCard key={repo.github_repo_id} repository={repo} onDelete={onDelete} />
      ))}
    </div>
  );
};
