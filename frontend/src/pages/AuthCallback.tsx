import React, { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { authService } from '../services';
import { STORAGE_KEYS } from '../constants';
import { Loading, NavBar } from '../components/common';
import { ROUTES } from '../config/routes.config';

export const AuthCallback: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  useEffect(() => {
    const handleCallback = async () => {
      const token = searchParams.get('token');
      
      if (!token) {
        navigate(ROUTES.LOGIN);
        return;
      }

      try {
        localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, token);

        const response = await authService.getCurrentUser()

        localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(response));
        navigate(ROUTES.DASHBOARD);

      } catch (error) {
        console.error('Auth callback error:', error);
        navigate(ROUTES.LOGIN);
      }
    };

    handleCallback();
  }, [searchParams, navigate]);

  return (
    <>
      <NavBar />
      <Loading message="Completing authentication..." />
    </>
  );
};
