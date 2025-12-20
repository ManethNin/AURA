import React from 'react';
import { useAuth } from '../hooks';
import { Button } from '../components/common';
import { Navigate } from 'react-router-dom';
import { ROUTES } from '../config/routes.config';

export const Login: React.FC = () => {
  const { login, isAuthenticated } = useAuth();

  if (isAuthenticated) {
    return <Navigate to={ROUTES.DASHBOARD} replace />;
  }

  return (
    <div className="login-page">
      <div className="login-container">
        <h1>AURA</h1>
        <p>Automated Multi-Agent Repair System for Java Dependencies</p>
        <Button onClick={login} variant="primary">
          Login with GitHub
        </Button>
      </div>
    </div>
  );
};
