import React from 'react';

/**
 * ErrorBoundary — lightweight React error boundary for major panels.
 * Prevents total blank pages when a panel crashes.
 */
export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('[ErrorBoundary] Panel crashed:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      const panelName = this.props.panelName || 'This panel';
      return (
        <div style={{
          padding: 24, margin: 16, borderRadius: 12,
          background: '#1a0a0a', border: '1px solid #ff4444',
          color: '#ffaaaa', fontFamily: 'monospace',
        }}>
          <h3 style={{ margin: '0 0 8px', color: '#ff6666' }}>
            {panelName} hit a local rendering error.
          </h3>
          <p style={{ fontSize: 13, margin: '0 0 12px', color: '#cc8888' }}>
            I did not execute anything. No data was lost. Try refreshing the page or navigating to Command Center.
          </p>
          <p style={{ fontSize: 11, margin: '0 0 12px', color: '#886666' }}>
            Error: {this.state.error?.message || 'Unknown error'}
          </p>
          <button
            type="button"
            onClick={() => this.setState({ hasError: false, error: null })}
            style={{
              padding: '6px 14px', borderRadius: 6,
              background: '#331111', border: '1px solid #663333',
              color: '#ffaaaa', cursor: 'pointer', fontSize: 12,
            }}
          >
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
