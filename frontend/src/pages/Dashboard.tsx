import React from 'react';
import { useRepositories } from '../hooks';
import { RepositoryList } from '../components/repository';
import { NavBar } from '../components/common';

export const Dashboard: React.FC = () => {
  const { repositories, loading: reposLoading, deleteRepository } = useRepositories();

  return (
    <div className="dashboard">
      <NavBar />
      
      <div className="dashboard-container">
        <header className="dashboard-header">
          <h1>Dashboard</h1>
          <p className="dashboard-subtitle">Manage your repositories and monitor automated fixes</p>
        </header>

        <section className="dashboard-section">
          <div className="section-header">
            <h2>Your Repositories</h2>
            <span className="repo-count">{repositories.length} {repositories.length === 1 ? 'repository' : 'repositories'}</span>
          </div>
          <RepositoryList 
            repositories={repositories} 
            loading={reposLoading} 
            onDelete={deleteRepository}
          />
        </section>
      </div>
    </div>
  );
};
