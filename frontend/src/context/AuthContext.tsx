import React, { createContext, useState, useEffect } from 'react';
import type { User } from '../types';
import { authService } from '../services';
import { STORAGE_KEYS } from '../constants';

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: () => void;
  logout: () => void;
  isAuthenticated: boolean;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check if user is logged in on mount
    const initAuth = async () => {
      const token = localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
      if (token) {
        try {
          
          const response = await authService.getCurrentUser();
          setUser(response);
          // console.log(response)
        } catch (error) {
          localStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN);
          localStorage.removeItem(STORAGE_KEYS.USER);
        }
      }
      setLoading(false);
    };

    initAuth();
  }, []);

  const login = () => {
    authService.login();
  };

  const logout = async () => {
    await authService.logout();
    setUser(null);
    window.location.href = '/';
    
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        logout,
        isAuthenticated: !!user,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};
