import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../../hooks';
import { Loading } from '../common';
import { ROUTES } from '../../config/routes.config';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return <Loading message="Checking authentication..." />;
  }

  if (!isAuthenticated) {
    console.log("Hiii")
    return <Navigate to={ROUTES.LOGIN} replace />;
  }

  return <>{children}</>;
};
