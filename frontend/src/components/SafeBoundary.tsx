"use client";

import React from "react";
import { ErrorPanel } from "./ErrorPanel";

interface Props {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

interface State {
  caught: boolean;
}

export class SafeBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { caught: false };
  }

  static getDerivedStateFromError(): State {
    return { caught: true };
  }

  componentDidCatch(error: Error): void {
    console.error("[SafeBoundary] component crash:", error.message);
  }

  render() {
    if (this.state.caught) {
      return (
        this.props.fallback ?? (
          <ErrorPanel
            message="This section encountered an error."
            onRetry={() => this.setState({ caught: false })}
          />
        )
      );
    }
    return this.props.children;
  }
}
