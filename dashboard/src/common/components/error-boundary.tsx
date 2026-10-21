import { Component, ErrorInfo, ReactNode } from "react";
import { ErrorBoundaryFallback } from "./error-boundary-fallback";

interface Props {
  children: ReactNode;
  /** Custom fallback UI; when omitted the localized default panel is shown */
  fallback?: ReactNode;
  /**
   * Recovery to run before Try Again re-renders the children, e.g. rerunning
   * the route loader whose failure was caught here. Without it, Try Again
   * only clears this boundary, which cannot recover a failed loader (w4/264).
   */
  onRetry?: () => unknown;
  /** A change (e.g. the location) clears a caught error. */
  resetKey?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

/**
 * Error boundary that degrades a single panel instead of blanking the app.
 * Logs the full error for debugging; the localized fallback keeps the same
 * details behind a disclosure the reader can copy to support.
 */
export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("[ErrorBoundary] React error caught:", {
      error: {
        message: error.message,
        name: error.name,
        stack: error.stack,
      },
      errorInfo: {
        componentStack: errorInfo.componentStack,
      },
      location: typeof window !== "undefined" ? window.location.href : "ssr",
      timestamp: new Date().toISOString(),
    });

    this.setState({ errorInfo });
  }

  componentDidUpdate(previous: Props) {
    if (this.state.hasError && previous.resetKey !== this.props.resetKey) {
      this.setState({ hasError: false, error: null, errorInfo: null });
    }
  }

  handleRetry = async () => {
    const clear = () =>
      this.setState({ hasError: false, error: null, errorInfo: null });
    // A plain panel retry stays immediate; only a recovery is awaited.
    if (!this.props.onRetry) return clear();
    try {
      await this.props.onRetry();
    } finally {
      clear();
    }
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <ErrorBoundaryFallback
          error={this.state.error}
          errorInfo={this.state.errorInfo}
          onRetry={() => void this.handleRetry()}
        />
      );
    }

    return this.props.children;
  }
}
