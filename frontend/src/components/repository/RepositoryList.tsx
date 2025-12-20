import React from 'react';
import { Repository } from '../../types';
import { RepositoryCard } from './RepositoryCard';
import { Loading } from '../common';

interface RepositoryListProps {
  repositories: Repository[];
  loading?: boolean;
}

export const RepositoryList: React.FC<RepositoryListProps> = ({ repositories, loading }) => {
  if (loading) {
    return <Loading message="Loading repositories..." />;
  }

  if (repositories.length === 0) {
    return (
      <div className="empty-state">
        <p>No repositories found. Install the AURA GitHub App to get started.</p>
      </div>
    );
  }

  return (
    <div className="repository-list">
      {repositories.map((repo) => (
        <RepositoryCard key={repo.id} repository={repo} />
      ))}
    </div>
  );
};
