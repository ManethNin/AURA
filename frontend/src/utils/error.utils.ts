// Error handling utilities
import { AxiosError } from 'axios';
import type { ApiError } from '../types/api.types';

export const getErrorMessage = (error: unknown): string => {
  if (error instanceof AxiosError) {
    const apiError = error.response?.data as ApiError;
    return apiError?.message || error.message || 'An unexpected error occurred';
  }
  
  if (error instanceof Error) {
    return error.message;
  }
  
  return 'An unexpected error occurred';
};

export const handleApiError = (error: unknown): void => {
  const message = getErrorMessage(error);
  console.error('API Error:', message);
  // You can add toast notification here
};
