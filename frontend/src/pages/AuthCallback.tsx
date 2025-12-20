import React, { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { authService } from '../services';
import { STORAGE_KEYS } from '../constants';
import { Loading } from '../components/common';
import { ROUTES } from '../config/routes.config';

export const AuthCallback: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  useEffect(() => {
    const handleCallback = async () => {
      const code = searchParams.get('code');
      
      if (!code) {
        navigate(ROUTES.LOGIN);
        return;
      }

      try {
        const response = await authService.handleCallback(code);
        localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, response.data.access_token);
        localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(response.data.user));
        navigate(ROUTES.DASHBOARD);
      } catch (error) {
        console.error('Auth callback error:', error);
        navigate(ROUTES.LOGIN);
      }
    };

    handleCallback();
  }, [searchParams, navigate]);

  return <Loading message="Completing authentication..." />;
};
