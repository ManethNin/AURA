import React from 'react';
import { useParams } from 'react-router-dom';
import { useChanges } from '../hooks';
import { ChangeList } from '../components/changes';
import { Loading } from '../components/common';

export const RepositoryDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { changes, loading, createPR } = useChanges(id);

  if (loading) {
    return <Loading message="Loading repository details..." />;
  }

  return (
    <div className="repository-detail">
      <header>
        <h1>Repository Changes</h1>
      </header>

      <section>
        <h2>Detected Changes</h2>
        <ChangeList changes={changes} onCreatePR={createPR} />
      </section>
    </div>
  );
};
