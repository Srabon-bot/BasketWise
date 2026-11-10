import type { ReactNode } from "react";

export function LoadingState({ label }: { label: string }) {
  return (
    <div className="state" role="status" aria-live="polite">
      <h2>{label}</h2>
      <p>Reading the exported JSON. This only takes a moment.</p>
      <div className="loading-lines" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
    </div>
  );
}

export function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
    <div className="state state--error" role="alert">
      <h2>The data did not load.</h2>
      <p>{message}</p>
      <button type="button" className="btn" onClick={onRetry}>
        Try again
      </button>
    </div>
  );
}

export function EmptyState({
  title,
  children,
  action,
}: {
  title: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="state">
      <h2>{title}</h2>
      <p>{children}</p>
      {action}
    </div>
  );
}
