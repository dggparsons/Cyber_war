import React from 'react'

export class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { hasError: boolean; error: string }
> {
  constructor(props: { children: React.ReactNode }) {
    super(props)
    this.state = { hasError: false, error: '' }
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error: error.message }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-warroom-blue flex items-center justify-center text-red-400 p-8">
          <div className="text-center">
            <h1 className="text-2xl font-pixel mb-4">SYSTEM ERROR</h1>
            <p>{this.state.error}</p>
            <button
              onClick={() => this.setState({ hasError: false, error: '' })}
              className="mt-4 px-4 py-2 bg-warroom-cyan text-black rounded"
            >
              Retry
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
