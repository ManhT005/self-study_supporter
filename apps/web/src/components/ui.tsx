"use client";
import type { ButtonHTMLAttributes, ReactNode } from "react";
import { BookOpen, LoaderCircle } from "lucide-react";

export function Button({
  pending,
  children,
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { pending?: boolean }) {
  return (
    <button
      {...props}
      disabled={props.disabled || pending}
      aria-busy={pending}
      className={`button ${className}`}
    >
      {pending && <LoaderCircle size={18} aria-hidden="true" />}
      {children}
    </button>
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
    <div className="card empty">
      <div className="empty-icon">
        <BookOpen size={28} aria-hidden="true" />
      </div>
      <h2>{title}</h2>
      <p className="muted">{children}</p>
      {action}
    </div>
  );
}
export function ErrorState({
  message,
  retry,
}: {
  message: string;
  retry?: () => void;
}) {
  return (
    <div className="error" role="alert">
      <p>{message}</p>
      {retry && (
        <Button className="secondary" onClick={retry}>
          Thử lại
        </Button>
      )}
    </div>
  );
}
export function LoadingState() {
  return (
    <div role="status" className="stack">
      <span className="muted">Đang tải nội dung…</span>
      <div className="skeleton" aria-hidden="true" />
    </div>
  );
}
export function PageHeading({
  eyebrow,
  title,
  children,
}: {
  eyebrow?: string;
  title: string;
  children?: ReactNode;
}) {
  return (
    <div className="page-heading">
      {eyebrow && <p className="eyebrow">{eyebrow}</p>}
      <h1>{title}</h1>
      {children && <p className="muted">{children}</p>}
    </div>
  );
}
