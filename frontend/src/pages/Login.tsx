import React from 'react';
import { useAuth } from '../hooks';
import { Button, NavBar } from '../components/common';
import { Navigate } from 'react-router-dom';
import { ROUTES } from '../config/routes.config';

export const Login: React.FC = () => {
  const { login, isAuthenticated } = useAuth();

  if (isAuthenticated) {
    return <Navigate to={ROUTES.DASHBOARD} replace />;
  }

  return (
    <div className="login-page">
      <NavBar />
      
      <div className="login-hero">
        <div className="hero-content">
          <h1 className="hero-title">AURA</h1>
          <p className="hero-subtitle">
            Automated Multi-Agent Repair System for Java Dependencies
          </p>
          <p className="hero-description">
            Automatically detect and fix breaking changes in your Java projects with AI-powered agents
          </p>
          <Button onClick={login} variant="primary" className="hero-login-btn">
            <svg className="github-icon" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
            </svg>
            Login with GitHub
          </Button>
        </div>
      </div>

      <div className="how-it-works" id="how-it-works">
        <div className="how-it-works-container">
          <h2 className="section-title">How AURA Works</h2>
          <p className="section-subtitle">
            Get started in minutes and let AI agents handle your dependency updates
          </p>

          <div className="steps-grid">
            <div className="step-card">
              <div className="step-number">1</div>
              <div className="step-icon">🔐</div>
              <h3 className="step-title">Connect GitHub</h3>
              <p className="step-description">
                Click the "Login with GitHub" button above to authenticate. We'll need access to your repositories to monitor changes.
              </p>
            </div>

            <div className="step-card">
              <div className="step-number">2</div>
              <div className="step-icon">📦</div>
              <h3 className="step-title">Install AURA App</h3>
              <p className="step-description">
                Install the AURA GitHub App on your repositories. You can choose specific repos or install it organization-wide.
              </p>
            </div>

            <div className="step-card">
              <div className="step-number">3</div>
              <div className="step-icon">🔍</div>
              <h3 className="step-title">Push Your Code</h3>
              <p className="step-description">
                When you push commits to your Java projects, AURA automatically detects dependency changes and breaking changes.
              </p>
            </div>

            <div className="step-card">
              <div className="step-number">4</div>
              <div className="step-icon">🤖</div>
              <h3 className="step-title">AI Agents Analyze</h3>
              <p className="step-description">
                Our multi-agent system analyzes the breaking changes, explores your codebase, and generates fix suggestions.
              </p>
            </div>

            <div className="step-card">
              <div className="step-number">5</div>
              <div className="step-icon">🔧</div>
              <h3 className="step-title">Automated Fixes</h3>
              <p className="step-description">
                AURA applies the fixes, validates them with Maven, and creates a branch with the updated code.
              </p>
            </div>

            <div className="step-card">
              <div className="step-number">6</div>
              <div className="step-icon">✅</div>
              <h3 className="step-title">Review & Merge</h3>
              <p className="step-description">
                Review the auto-generated pull request with all the fixes, then merge when you're ready. It's that simple!
              </p>
            </div>
          </div>

          <div className="features-section">
            <h3 className="features-title">Key Features</h3>
            <div className="features-grid">
              <div className="feature-item">
                <span className="feature-icon">⚡</span>
                <span className="feature-text">Real-time change detection</span>
              </div>
              <div className="feature-item">
                <span className="feature-icon">🎯</span>
                <span className="feature-text">Intelligent break analysis</span>
              </div>
              <div className="feature-item">
                <span className="feature-icon">🛠️</span>
                <span className="feature-text">Automated code repair</span>
              </div>
              <div className="feature-item">
                <span className="feature-icon">✓</span>
                <span className="feature-text">Maven validation</span>
              </div>
              <div className="feature-item">
                <span className="feature-icon">🔄</span>
                <span className="feature-text">Pull request creation</span>
              </div>
              <div className="feature-item">
                <span className="feature-icon">📊</span>
                <span className="feature-text">Dashboard monitoring</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <footer className="login-footer">
        <p>Powered by AI • Built for Java Developers</p>
      </footer>
    </div>
  );
};
