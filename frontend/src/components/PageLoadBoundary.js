import React from "react";

// A failed page download should leave navigation available and offer recovery.
export class PageLoadBoundary extends React.Component {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <div role="alert" className="mx-auto flex min-h-[50vh] max-w-xl flex-col items-center justify-center gap-4 px-6 text-center">
        <h1 className="text-xl font-semibold">This page could not load</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">Check your connection and reload to try again.</p>
        <button type="button" onClick={() => window.location.reload()} className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2">Reload page</button>
      </div>
    );
  }
}
