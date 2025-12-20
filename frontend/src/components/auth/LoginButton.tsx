import React from 'react';
import { useAuth } from '../../hooks';
import { Button } from '../common';

export const LoginButton: React.FC = () => {
  const { login, isAuthenticated, user, logout } = useAuth();

  if (isAuthenticated && user) {
    return (
      <div className="user-menu">
        <img src={user.avatar_url} alt={user.username} className="avatar" />
        <span>{user.username}</span>
        <Button onClick={logout} variant="secondary">
          Logout
        </Button>
      </div>
    );
  }

  return (
    <Button onClick={login} variant="primary">
      Login with GitHub
    </Button>
  );
};
