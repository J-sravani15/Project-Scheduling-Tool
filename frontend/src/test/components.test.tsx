import React from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { EmptyState } from '../components/common/EmptyState';
import { Badge, PriorityBadge, StatusBadge } from '../components/common/Badge';
import { Alert } from '../components/common/Alert';
import { Card } from '../components/common/Card';

describe('Common UI Components', () => {
  it('renders LoadingSpinner with accessible status', () => {
    render(<LoadingSpinner label="Evaluating critical path..." />);
    expect(screen.getByRole('status')).toBeInTheDocument();
    expect(screen.getByText('Evaluating critical path...')).toBeInTheDocument();
  });

  it('renders EmptyState with custom title, message, and action', () => {
    render(
      <EmptyState
        title="No Project Milestones"
        description="Please define your departmental milestones."
        action={<button>Add First Milestone</button>}
      />
    );
    expect(screen.getByText('No Project Milestones')).toBeInTheDocument();
    expect(screen.getByText('Please define your departmental milestones.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /add first milestone/i })).toBeInTheDocument();
  });

  it('renders Badges with correct variant text and styling', () => {
    const { rerender } = render(<Badge variant="success">Completed</Badge>);
    expect(screen.getByText('Completed')).toBeInTheDocument();

    rerender(<PriorityBadge priority="critical" />);
    expect(screen.getByText('Critical')).toBeInTheDocument();

    rerender(<PriorityBadge priority="high" />);
    expect(screen.getByText('High')).toBeInTheDocument();

    rerender(<StatusBadge status="completed" />);
    expect(screen.getByText('Completed')).toBeInTheDocument();

    rerender(<StatusBadge status="in_progress" />);
    expect(screen.getByText('In Progress')).toBeInTheDocument();

    rerender(<StatusBadge status="blocked" />);
    expect(screen.getByText('Blocked')).toBeInTheDocument();
  });

  it('renders Alert component with error and success types', () => {
    const { rerender } = render(
      <Alert type="error" title="Critical Dependency Cycle">
        Circular prerequisite detected.
      </Alert>
    );
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText('Critical Dependency Cycle')).toBeInTheDocument();
    expect(screen.getByText('Circular prerequisite detected.')).toBeInTheDocument();

    rerender(
      <Alert type="success" title="Schedule Optimized">
        All tasks successfully scheduled.
      </Alert>
    );
    expect(screen.getByText('Schedule Optimized')).toBeInTheDocument();
  });

  it('renders Card component with title, subtitle, and body', () => {
    render(
      <Card title="Team Effort" subtitle="Hours breakdown">
        <div>35 active hours total</div>
      </Card>
    );
    expect(screen.getByText('Team Effort')).toBeInTheDocument();
    expect(screen.getByText('Hours breakdown')).toBeInTheDocument();
    expect(screen.getByText('35 active hours total')).toBeInTheDocument();
  });
});
