import React from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../hooks';
import { Button } from './Button';
import { ROUTES } from '../../config/routes.config';

export const NavBar: React.FC = () => {
  const { isAuthenticated, logout, user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = async () => {
    await logout();
    navigate(ROUTES.LOGIN);
  };

  return (
    <nav className="navbar">
      <div className="navbar-container">
        <Link to={isAuthenticated ? ROUTES.DASHBOARD : ROUTES.LOGIN} className="navbar-brand">
          <span className="brand-name">AURA</span>
        </Link>

        <div className="navbar-menu">
          {isAuthenticated ? (
            <>
              {location.pathname !== ROUTES.DASHBOARD && (
                <Link to={ROUTES.DASHBOARD} className="navbar-link">
                  Dashboard
                </Link>
              )}
              {user && (
                <div className="navbar-user">
                  <img 
                    src={user.avatar_url || `https://ui-avatars.com/api/?name=${user.username}`} 
                    alt={user.username}
                    className="user-avatar"
                  />
                  <span className="user-name">{user.username}</span>
                </div>
              )}
              <Button onClick={handleLogout} variant="secondary" className="logout-btn">
                Logout
              </Button>
            </>
          ) : (
            location.pathname === ROUTES.LOGIN && (
              <a href="#how-it-works" className="navbar-link">
                How It Works
              </a>
            )
          )}
        </div>
      </div>
    </nav>
  );
};
