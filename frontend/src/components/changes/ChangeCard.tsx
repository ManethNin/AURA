import React, { useState } from 'react';
import type { Change } from '../../types';
import { Card, Button } from '../common';
import { Link } from 'react-router-dom';

interface ChangeCardProps {
  change: Change;
  onCreatePR?: (changeId: string) => Promise<{ pr_url: string; pr_number: number; branch: string; files_updated: string[]; message: string }>;
}

export const ChangeCard: React.FC<ChangeCardProps> = ({ change, onCreatePR }) => {
  const [loading, setLoading] = useState(false);

  const handleCreatePR = async () => {
    if (!onCreatePR) return;
    try {
      setLoading(true);
      const result = await onCreatePR(change._id);
      // Open the created PR in a new tab
      window.open(result.pr_url, '_blank');
    } catch (error) {
      console.error('Failed to create PR:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status: Change['status']) => {
    const statusMap: Record<Change['status'], string> = {
      pending: 'badge-warning',
      cloning: 'badge-info',
      preparing: 'badge-info',
      analyzing: 'badge-info',
      fixing: 'badge-info',
      validating: 'badge-info',
      fixed: 'badge-success',
      failed: 'badge-danger',
    };
    return statusMap[status] || 'badge-default';
  };

  return (
    <Card>
      <div className="change-card">
        <div className="change-header">
          <Link to={`/changes/${change._id}`}>
            <h3>{change.commit_message}</h3>
          </Link>
          <span className={`badge ${getStatusBadge(change.status)}`}>{change.status}</span>
        </div>
        <div className="change-meta">
          <span>Commit: {change.commit_sha.substring(0, 7)}</span>
          <span>Date: {new Date(change.created_at).toLocaleDateString()}</span>
        </div>
        {change.breaking_changes && (
          <div className="breaking-changes">
            <strong>Breaking Changes:</strong>
            <pre>{change.breaking_changes}</pre>
          </div>
        )}
        <div className="change-actions">
          {change.status === 'fixed' && !change.pr_url && onCreatePR && (
            <Button onClick={handleCreatePR} loading={loading} variant="primary">
              Create Pull Request
            </Button>
          )}
          {change.pr_url && (
            <a href={change.pr_url} target="_blank" rel="noopener noreferrer">
              <Button variant="secondary">View Pull Request</Button>
            </a>
          )}
        </div>
      </div>
    </Card>
  );
};
