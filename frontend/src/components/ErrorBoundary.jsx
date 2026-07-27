import React from 'react'

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null, errorInfo: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    console.error('Unhandled React Error:', error, errorInfo)
    this.setState({ errorInfo })
  }

  handleReload = () => {
    window.location.reload()
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justify: 'center',
          padding: '24px',
          backgroundColor: '#0f172a',
          color: '#f8fafc',
          textAlign: 'center',
          fontFamily: 'system-ui, -apple-system, sans-serif'
        }}>
          <div style={{
            maxWidth: '500px',
            backgroundColor: '#1e293b',
            border: '1px solid #334155',
            borderRadius: '16px',
            padding: '32px',
            boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.5)'
          }}>
            <h2 style={{ color: '#ef4444', marginTop: 0, fontSize: '1.5rem' }}>Something went wrong</h2>
            <p style={{ color: '#94a3b8', fontSize: '0.95rem', marginBottom: '20px' }}>
              The application encountered an unexpected visual error.
            </p>
            {this.state.error && (
              <pre style={{
                backgroundColor: '#090d16',
                color: '#f87171',
                padding: '12px',
                borderRadius: '8px',
                fontSize: '0.8rem',
                overflowX: 'auto',
                textAlign: 'left',
                marginBottom: '24px',
                border: '1px solid #273549'
              }}>
                {this.state.error.toString()}
              </pre>
            )}
            <button
              onClick={this.handleReload}
              style={{
                backgroundColor: '#3b82f6',
                color: '#ffffff',
                border: 'none',
                padding: '12px 24px',
                borderRadius: '8px',
                fontWeight: 600,
                fontSize: '0.95rem',
                cursor: 'pointer',
                transition: 'background-color 0.2s'
              }}
            >
              Reload Page
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
