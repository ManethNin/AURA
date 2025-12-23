import React, { useState } from 'react';
import type { Repository } from '../../types';
import { Card, Button, Modal } from '../common';
import { Link } from 'react-router-dom';

interface RepositoryCardProps {
  repository: Repository;
  onDelete?: (id: string) => Promise<{ success: boolean; error?: string }>;
}

export const RepositoryCard: React.FC<RepositoryCardProps> = ({ repository, onDelete }) => {
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const handleDelete = async () => {
    if (!onDelete) return;
    
    setDeleting(true);
    const result = await onDelete(repository._id);
    setDeleting(false);
    
    if (result.success) {
      setShowDeleteModal(false);
    } else {
      alert(result.error || 'Failed to delete repository');
    }
  };

  return (
    <>
      <Card>
        <div className="repo-card">
          <Link to={`/repositories/${repository._id}`} className="repo-link">
            <div className="repo-header">
              <h3>{repository.name}</h3>
              <span className={`badge ${repository.is_active ? 'badge-success' : 'badge-inactive'}`}>
                {repository.is_active ? 'Active' : 'Inactive'}
              </span>
            </div>
            <p className="repo-full-name">{repository.full_name}</p>
            <div className="repo-meta">
              <span className="repo-updated">
                Updated: {new Date(repository.updated_at).toLocaleDateString()}
              </span>
            </div>
          </Link>
          
          <div className="repo-actions">
            <Button 
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                setShowDeleteModal(true);
              }}
              variant="secondary"
              className="delete-btn"
            >
              Delete
            </Button>
          </div>
        </div>
      </Card>

      <Modal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        title="Delete Repository"
        onConfirm={handleDelete}
        confirmText="Delete"
        confirmVariant="danger"
        loading={deleting}
      >
        <p>Are you sure you want to delete <strong>{repository.name}</strong>?</p>
        <p className="warning-text">This action cannot be undone. All associated changes will also be removed.</p>
      </Modal>
    </>
  );
};
