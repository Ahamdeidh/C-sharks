import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Interface Error Caught by Boundary:', error, errorInfo);
  }

  handleReload = () => {
    this.setState({ hasError: false, error: null });
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen w-screen bg-[#03060c] text-slate-100 flex items-center justify-center p-6">
          <div className="max-w-xl w-full bg-[#0a1020] border border-rose-600/50 rounded-2xl p-6 shadow-2xl space-y-4">
            <div className="flex items-center space-x-3 text-rose-400">
              <AlertTriangle className="h-6 w-6" aria-hidden="true" />
              <h1 className="text-base font-bold uppercase tracking-wider font-orbitron">
                Flight Telemetry Interface Error
              </h1>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed font-sans">
              An unexpected render error occurred in this view. The application intercepted the fault to prevent a total crash.
            </p>
            {this.state.error?.message && (
              <div className="p-3 bg-black/60 rounded-lg border border-slate-800 text-[11px] font-mono text-rose-300 break-words">
                {this.state.error.message}
              </div>
            )}
            <div className="pt-2 flex justify-end">
              <button
                type="button"
                onClick={this.handleReload}
                className="px-4 py-2 bg-cyan-500 hover:bg-cyan-400 text-black font-bold text-xs uppercase tracking-wider rounded-xl flex items-center space-x-2 transition shadow-lg"
              >
                <RefreshCw className="h-4 w-4" />
                <span>Reload Interface</span>
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
