import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Badge, PriorityBadge } from '../components/common/Badge';
import { Card } from '../components/common/Card';

describe('Scheduling Algorithm Views & Metrics Rendering', () => {
  it('renders CPM Critical Path calculation results correctly', () => {
    const cpmMock = {
      project_id: 'proj-1',
      total_project_duration_hours: 45.0,
      critical_path_task_ids: ['t1', 't3'],
      tasks: {
        t1: {
          id: 't1',
          title: 'System Architecture Design',
          duration: 15.0,
          early_start: 0.0,
          early_finish: 15.0,
          late_start: 0.0,
          late_finish: 15.0,
          slack: 0.0,
          is_critical: true,
        },
        t2: {
          id: 't2',
          title: 'Preliminary Literature Review',
          duration: 10.0,
          early_start: 0.0,
          early_finish: 10.0,
          late_start: 5.0,
          late_finish: 15.0,
          slack: 5.0,
          is_critical: false,
        },
      },
    };

    render(
      <div>
        <Card title="Critical Path Analysis">
          <div data-testid="total-duration">{cpmMock.total_project_duration_hours}h</div>
          {Object.values(cpmMock.tasks).map((t) => (
            <div key={t.id} data-testid={`task-${t.id}`}>
              <span>{t.title}</span>
              <span>Slack: {t.slack}h</span>
              {t.is_critical && <Badge variant="danger">CRITICAL</Badge>}
            </div>
          ))}
        </Card>
      </div>
    );

    expect(screen.getByText('Critical Path Analysis')).toBeInTheDocument();
    expect(screen.getByTestId('total-duration')).toHaveTextContent('45h');
    expect(screen.getByText('System Architecture Design')).toBeInTheDocument();
    expect(screen.getByText('CRITICAL')).toBeInTheDocument();
    expect(screen.getByText('Preliminary Literature Review')).toBeInTheDocument();
    expect(screen.getByText('Slack: 5h')).toBeInTheDocument();
  });

  it('renders Priority Scheduling dispatch recommendations correctly', () => {
    const priorityMock = {
      project_id: 'proj-1',
      recommended_tasks: [
        {
          id: 't1',
          title: 'Hardware Driver Implementation',
          priority: 'critical' as const,
          total_score: 87.5,
          is_critical: true,
          recommendation_reason: 'High urgency with critical path impact.',
        },
      ],
      blocked_tasks: [
        {
          id: 't2',
          title: 'Hardware-in-the-Loop Testing',
          priority: 'high' as const,
          blocking_prerequisites: ['t1'],
        },
      ],
    };

    render(
      <div>
        <h2>Recommended Eligible Tasks</h2>
        {priorityMock.recommended_tasks.map((task) => (
          <div key={task.id}>
            <span>{task.title}</span>
            <PriorityBadge priority={task.priority} />
            <span>Score: {task.total_score}</span>
            <p>{task.recommendation_reason}</p>
          </div>
        ))}
        <h2>Blocked Tasks</h2>
        {priorityMock.blocked_tasks.map((task) => (
          <div key={task.id}>
            <span>{task.title}</span>
            <span>Blocked by {task.blocking_prerequisites.length} prerequisite(s)</span>
          </div>
        ))}
      </div>
    );

    expect(screen.getByText('Hardware Driver Implementation')).toBeInTheDocument();
    expect(screen.getByText('Critical')).toBeInTheDocument();
    expect(screen.getByText('Score: 87.5')).toBeInTheDocument();
    expect(screen.getByText('High urgency with critical path impact.')).toBeInTheDocument();
    expect(screen.getByText('Hardware-in-the-Loop Testing')).toBeInTheDocument();
    expect(screen.getByText('Blocked by 1 prerequisite(s)')).toBeInTheDocument();
  });

  it('renders PERT Beta distribution expected durations and target probability', () => {
    const pertMock = {
      expected_project_duration_hours: 62.5,
      project_standard_deviation_hours: 4.8,
      probability_within_target: 0.842,
    };

    render(
      <div>
        <div data-testid="pert-expected">{pertMock.expected_project_duration_hours}h</div>
        <div data-testid="pert-sigma">±{pertMock.project_standard_deviation_hours}h</div>
        <div data-testid="pert-prob">{(pertMock.probability_within_target * 100).toFixed(1)}%</div>
      </div>
    );

    expect(screen.getByTestId('pert-expected')).toHaveTextContent('62.5h');
    expect(screen.getByTestId('pert-sigma')).toHaveTextContent('±4.8h');
    expect(screen.getByTestId('pert-prob')).toHaveTextContent('84.2%');
  });

  it('renders CPM parallel tasks with critical and non-critical branches accurately', () => {
    const cpmParallelMock = {
      project_id: 'proj-parallel',
      total_project_duration_hours: 29.0,
      critical_tasks: ['t1', 't2', 't3', 't5', 't6'],
      tasks: {
        t1: {
          id: 't1',
          title: 'Requirement Analysis',
          duration: 4.0,
          early_start: 0.0,
          early_finish: 4.0,
          late_start: 0.0,
          late_finish: 4.0,
          slack: 0.0,
          is_critical: true,
        },
        t2: {
          id: 't2',
          title: 'System Design',
          duration: 6.0,
          early_start: 4.0,
          early_finish: 10.0,
          late_start: 4.0,
          late_finish: 10.0,
          slack: 0.0,
          is_critical: true,
        },
        t3: {
          id: 't3',
          title: 'Backend Implementation',
          duration: 10.0,
          early_start: 10.0,
          early_finish: 20.0,
          late_start: 10.0,
          late_finish: 20.0,
          slack: 0.0,
          is_critical: true,
        },
        t4: {
          id: 't4',
          title: 'Frontend Implementation',
          duration: 8.0,
          early_start: 10.0,
          early_finish: 18.0,
          late_start: 12.0,
          late_finish: 20.0,
          slack: 2.0,
          is_critical: false,
        },
        t5: {
          id: 't5',
          title: 'Integration Testing',
          duration: 4.0,
          early_start: 20.0,
          early_finish: 24.0,
          late_start: 20.0,
          late_finish: 24.0,
          slack: 0.0,
          is_critical: true,
        },
        t6: {
          id: 't6',
          title: 'Documentation and final report',
          duration: 5.0,
          early_start: 24.0,
          early_finish: 29.0,
          late_start: 24.0,
          late_finish: 29.0,
          slack: 0.0,
          is_critical: true,
        },
      },
    };

    render(
      <div>
        <div data-testid="total-duration">{cpmParallelMock.total_project_duration_hours} Hours</div>
        <div data-testid="critical-tasks-count">{cpmParallelMock.critical_tasks.length} Tasks</div>
        <table>
          <tbody>
            {Object.values(cpmParallelMock.tasks).map((t) => (
              <tr key={t.id} data-testid={`cpm-row-${t.id}`}>
                <td>{t.title}</td>
                <td>{t.duration}h</td>
                <td>{t.early_start}h</td>
                <td>{t.early_finish}h</td>
                <td>
                  <span className={t.slack === 0 ? 'text-rose-600' : 'text-emerald-600'}>
                    {t.slack}h
                  </span>
                </td>
                <td>
                  {t.is_critical ? (
                    <Badge variant="danger" size="sm">CRITICAL</Badge>
                  ) : (
                    <Badge variant="neutral" size="sm">Flexible</Badge>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );

    expect(screen.getByTestId('total-duration')).toHaveTextContent('29 Hours');
    expect(screen.getByTestId('critical-tasks-count')).toHaveTextContent('5 Tasks');
    expect(screen.getByText('Backend Implementation')).toBeInTheDocument();
    expect(screen.getByText('Frontend Implementation')).toBeInTheDocument();
    expect(screen.getByText('2h')).toHaveClass('text-emerald-600');
    expect(screen.getByText('Flexible')).toBeInTheDocument();
    expect(screen.getAllByText('CRITICAL').length).toBe(5);
  });
});
