import React from 'react';
import { Change } from '../../types';
import { ChangeCard } from './ChangeCard';
import { Loading } from '../common';

interface ChangeListProps {
  changes: Change[];
  loading?: boolean;
  onCreatePR?: (changeId: string) => Promise<void>;
}

export const ChangeList: React.FC<ChangeListProps> = ({ changes, loading, onCreatePR }) => {
  if (loading) {
    return <Loading message="Loading changes..." />;
  }

  if (changes.length === 0) {
    return (
      <div className="empty-state">
        <p>No changes detected yet. Push commits to your repository to see automated fixes.</p>
      </div>
    );
  }

  return (
    <div className="change-list">
      {changes.map((change) => (
        <ChangeCard key={change.id} change={change} onCreatePR={onCreatePR} />
      ))}
    </div>
  );
};
