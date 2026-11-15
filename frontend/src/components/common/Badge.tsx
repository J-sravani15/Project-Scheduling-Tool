import React from 'react';

type BadgeVariant =
  | 'default'
  | 'primary'
  | 'success'
  | 'warning'
  | 'danger'
  | 'info'
  | 'neutral';

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  size?: 'sm' | 'md';
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'default',
  size = 'md',
  className = '',
}) => {
  const variantStyles: Record<BadgeVariant, string> = {
    default: 'bg-slate-100 text-slate-800 border-slate-200',
    primary: 'bg-indigo-50 text-indigo-700 border-indigo-200',
    success: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    warning: 'bg-amber-50 text-amber-700 border-amber-200',
    danger: 'bg-rose-50 text-rose-700 border-rose-200',
    info: 'bg-sky-50 text-sky-700 border-sky-200',
    neutral: 'bg-gray-100 text-gray-700 border-gray-200',
  };

  const sizeStyles = {
    sm: 'text-xs px-2 py-0.5 font-medium',
    md: 'text-xs px-2.5 py-1 font-semibold tracking-wide',
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}
    >
      {children}
    </span>
  );
};

export const PriorityBadge: React.FC<{ priority: string }> = ({ priority }) => {
  switch (priority.toLowerCase()) {
    case 'critical':
      return <Badge variant="danger">Critical</Badge>;
    case 'high':
      return <Badge variant="warning">High</Badge>;
    case 'medium':
      return <Badge variant="primary">Medium</Badge>;
    case 'low':
      return <Badge variant="neutral">Low</Badge>;
    default:
      return <Badge variant="default">{priority}</Badge>;
  }
};

export const StatusBadge: React.FC<{ status?: string | null }> = ({ status }) => {
  if (!status) return <Badge variant="neutral">Pending</Badge>;
  switch (status.toLowerCase()) {
    case 'completed':
      return <Badge variant="success">Completed</Badge>;
    case 'in_progress':
      return <Badge variant="info">In Progress</Badge>;
    case 'todo':
    case 'pending':
      return <Badge variant="neutral">Pending</Badge>;
    case 'blocked':
    case 'delayed':
      return <Badge variant="danger">Blocked</Badge>;
    case 'planning':
      return <Badge variant="primary">Planning</Badge>;
    case 'archived':
      return <Badge variant="neutral">Archived</Badge>;
    default:
      return <Badge variant="default">{status.replace('_', ' ')}</Badge>;
  }
};
