import React from 'react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger';
  loading?: boolean;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  loading = false,
  disabled,
  className = '',
  ...props
}) => {
  return (
    <button
      data-variant={variant}
      className={className}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? (
        <>
          <span className="loading-spinner" style={{ width: '16px', height: '16px', borderWidth: '2px' }}></span>
          Loading...
        </>
      ) : children}
    </button>
  );
};
