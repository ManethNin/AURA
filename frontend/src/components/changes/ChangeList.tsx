import React from 'react';
import type { Change } from '../../types';
import { ChangeCard } from './ChangeCard';
import { Loading } from '../common';

interface ChangeListProps {
  changes: Change[];
  loading?: boolean;
  onCreatePR?: (changeId: string) => Promise<{ pr_url: string; pr_number: number; branch: string; files_updated: string[]; message: string }>;
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
        <ChangeCard key={change._id} change={change} onCreatePR={onCreatePR} />
      ))}
    </div>
  );
};
