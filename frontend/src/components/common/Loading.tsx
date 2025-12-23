import React from 'react';

export const Loading: React.FC<{ message?: string }> = ({ message = 'Loading...' }) => {
  return (
    <div className="loading">
      <div className="loading-spinner"></div>
      <p className="loading-message">{message}</p>
    </div>
  );
};
