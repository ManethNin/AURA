import React, { useState } from 'react';
import { Change } from '../../types';
import { Card, Button } from '../common';
import { Link } from 'react-router-dom';

interface ChangeCardProps {
  change: Change;
  onCreatePR?: (changeId: string) => Promise<void>;
}

export const ChangeCard: React.FC<ChangeCardProps> = ({ change, onCreatePR }) => {
  const [loading, setLoading] = useState(false);

  const handleCreatePR = async () => {
    if (!onCreatePR) return;
    try {
      setLoading(true);
      await onCreatePR(change.id);
    } catch (error) {
      console.error('Failed to create PR:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status: Change['status']) => {
    const statusMap = {
      pending: 'badge-warning',
      analyzed: 'badge-info',
      fixed: 'badge-success',
      pr_created: 'badge-success',
      failed: 'badge-danger',
    };
    return statusMap[status] || 'badge-default';
  };

  return (
    <Card>
      <div className="change-card">
        <div className="change-header">
          <Link to={`/changes/${change.id}`}>
            <h3>{change.commit_message}</h3>
          </Link>
          <span className={`badge ${getStatusBadge(change.status)}`}>{change.status}</span>
        </div>
        <div className="change-meta">
          <span>Author: {change.author}</span>
          <span>Commit: {change.commit_sha.substring(0, 7)}</span>
          <span>Date: {new Date(change.created_at).toLocaleDateString()}</span>
        </div>
        {change.breaking_changes && change.breaking_changes.length > 0 && (
          <div className="breaking-changes">
            <strong>Breaking Changes:</strong>
            <ul>
              {change.breaking_changes.map((bc, idx) => (
                <li key={idx}>
                  {bc.dependency}: {bc.old_version} → {bc.new_version}
                </li>
              ))}
            </ul>
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
