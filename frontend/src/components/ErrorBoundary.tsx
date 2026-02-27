import { Component, type ReactNode } from 'react'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null })
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center p-12 text-center">
          <h2 className="text-lg font-semibold text-red-700">
            Etwas ist schiefgelaufen
          </h2>
          <p className="mt-2 text-sm text-gray-600">
            {this.state.error?.message || 'Unbekannter Fehler'}
          </p>
          <button
            onClick={this.handleReset}
            className="mt-4 rounded-md bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700"
          >
            Erneut versuchen
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
