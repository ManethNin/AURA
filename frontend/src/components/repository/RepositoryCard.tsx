import React from 'react';
import { Repository } from '../../types';
import { Card } from '../common';
import { Link } from 'react-router-dom';

interface RepositoryCardProps {
  repository: Repository;
}

export const RepositoryCard: React.FC<RepositoryCardProps> = ({ repository }) => {
  return (
    <Card>
      <Link to={`/repositories/${repository.id}`} className="repo-link">
        <h3>{repository.name}</h3>
        <p className="repo-full-name">{repository.full_name}</p>
        <div className="repo-meta">
          <span className={`badge ${repository.private ? 'private' : 'public'}`}>
            {repository.private ? 'Private' : 'Public'}
          </span>
          <span className="repo-updated">
            Updated: {new Date(repository.updated_at).toLocaleDateString()}
          </span>
        </div>
      </Link>
    </Card>
  );
};
