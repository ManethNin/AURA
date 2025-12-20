import React from 'react';
import { useRepositories, useChanges } from '../hooks';
import { RepositoryList } from '../components/repository';
import { ChangeList } from '../components/changes';
import { Button } from '../components/common';

export const Dashboard: React.FC = () => {
  const { repositories, loading: reposLoading, sync } = useRepositories();
  const { changes, loading: changesLoading, createPR } = useChanges();

  const handleSync = async () => {
    await sync();
  };

  const handleCreatePR = async (changeId: string) => {
    await createPR(changeId);
  };

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>Dashboard</h1>
        <Button onClick={handleSync} variant="secondary">
          Sync Repositories
        </Button>
      </header>

      <section className="dashboard-section">
        <h2>Your Repositories</h2>
        <RepositoryList repositories={repositories} loading={reposLoading} />
      </section>

      <section className="dashboard-section">
        <h2>Recent Changes</h2>
        <ChangeList changes={changes} loading={changesLoading} onCreatePR={handleCreatePR} />
      </section>
    </div>
  );
};
