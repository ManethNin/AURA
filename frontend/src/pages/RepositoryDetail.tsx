import React from 'react';
import { useParams, Navigate, Link } from 'react-router-dom';
import { useChanges } from '../hooks';
import { ChangeList } from '../components/changes';
import { Loading, NavBar } from '../components/common';
import { ROUTES } from '../config/routes.config';

export const RepositoryDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  if (!id) {
    return <Navigate to="/" replace />;
  }
  
  const { changes, loading, createPR } = useChanges(id);

  if (loading) {
    return (
      <>
        <NavBar />
        <Loading message="Loading repository details..." />
      </>
    );
  }

  return (
    <div className="repository-detail">
      <NavBar />
      
      <div className="repository-detail-container">
        <header className="page-header">
          <div className="breadcrumb">
            <Link to={ROUTES.DASHBOARD} className="breadcrumb-link">Dashboard</Link>
            <span className="breadcrumb-separator">/</span>
            <span className="breadcrumb-current">Repository Changes</span>
          </div>
          <h1>Repository Changes</h1>
          <p className="page-subtitle">View and manage automated fixes for this repository</p>
        </header>

        <section className="changes-section">
          <div className="section-header">
            <h2>Detected Changes</h2>
            <span className="change-count">{changes.length} {changes.length === 1 ? 'change' : 'changes'}</span>
          </div>
          <ChangeList changes={changes} onCreatePR={createPR} />
        </section>
      </div>
    </div>
  );
};
