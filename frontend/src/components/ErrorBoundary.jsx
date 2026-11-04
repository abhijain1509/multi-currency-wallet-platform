import { Component } from "react";

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  render() {
    if (this.state.error) {
      return (
        <div className="container">
          <div className="card">
            <h2>Something went wrong</h2>
            <p className="error">{this.state.error.message}</p>
            <button onClick={() => window.location.assign("/")}>Reload app</button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
