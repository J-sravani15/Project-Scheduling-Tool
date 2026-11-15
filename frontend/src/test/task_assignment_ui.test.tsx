import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { SchedulingPage } from '../pages/scheduling/SchedulingPage';
import { api } from '../api/client';
import { Task, ProjectMember, AcademicMilestone, TeamWorkloadResponse } from '../types';

vi.mock('../api/client', () => ({
  api: {
    tasks: {
      list: vi.fn(),
      get: vi.fn(),
      create: vi.fn(),
      update: vi.fn(),
      updateStatus: vi.fn(),
      assign: vi.fn(),
      unassign: vi.fn(),
      getAssignments: vi.fn(),
      addDependency: vi.fn(),
      removeDependency: vi.fn(),
    },
    milestones: {
      list: vi.fn(),
    },
    projects: {
      listMembers: vi.fn(),
      getWorkload: vi.fn(),
    },
    scheduling: {
      calculatePriority: vi.fn(),
      calculateCpm: vi.fn(),
      calculatePert: vi.fn(),
    },
  },
}));

describe('Scheduling Workspace Task Assignment UI', () => {
  const mockTasks: Task[] = [
    {
      id: 'task-req-1',
      project_id: 'proj-123',
      title: 'Requirements Engineering',
      description: 'Collect student scheduling constraints',
      status: 'in_progress',
      priority: 'high',
      estimated_duration_hours: 12.0,
      due_date: '2026-04-10',
      created_at: '2026-01-01',
      updated_at: '2026-01-01',
      assignments: [
        {
          id: 'assign-1',
          task_id: 'task-req-1',
          user_id: 'user-aslesha',
          assigned_at: '2026-02-01',
          user: {
            id: 'user-aslesha',
            full_name: 'Aslesha Student',
            email: 'aslesha@college.edu',
            role: 'student',
          },
        },
      ],
    },
    {
      id: 'task-arch-2',
      project_id: 'proj-123',
      title: 'Architecture Blueprint',
      description: 'Design CPM and PERT engine',
      status: 'todo',
      priority: 'critical',
      estimated_duration_hours: 18.0,
      due_date: '2026-04-20',
      created_at: '2026-01-01',
      updated_at: '2026-01-01',
      assignments: [],
    },
  ];

  const mockMembers: ProjectMember[] = [
    {
      id: 'mem-1',
      project_id: 'proj-123',
      user_id: 'user-aslesha',
      team_role: 'developer',
      joined_at: '2026-01-01',
      user: {
        id: 'user-aslesha',
        full_name: 'Aslesha Student',
        email: 'aslesha@college.edu',
        role: 'student',
      },
    },
    {
      id: 'mem-2',
      project_id: 'proj-123',
      user_id: 'user-sravani',
      team_role: 'leader',
      joined_at: '2026-01-01',
      user: {
        id: 'user-sravani',
        full_name: 'Sravani Leader',
        email: 'sravani@college.edu',
        role: 'student',
      },
    },
  ];

  const mockWorkload: TeamWorkloadResponse = {
    project_id: 'proj-123',
    threshold_hours: 25.0,
    reference_date: '2026-03-01',
    total_team_active_hours: 30.0,
    average_hours_per_student: 15.0,
    workload_standard_deviation: 3.0,
    student_workloads: [
      {
        user_id: 'user-aslesha',
        full_name: 'Aslesha Student',
        email: 'aslesha@college.edu',
        team_role: 'developer',
        total_active_hours: 12.0,
        completed_hours: 0,
        assigned_task_count: 1,
        overdue_task_count: 0,
        upcoming_task_count: 1,
        completed_task_count: 0,
        is_overloaded: false,
        is_underutilized: false,
      },
      {
        user_id: 'user-sravani',
        full_name: 'Sravani Leader',
        email: 'sravani@college.edu',
        team_role: 'leader',
        total_active_hours: 18.0,
        completed_hours: 0,
        assigned_task_count: 1,
        overdue_task_count: 0,
        upcoming_task_count: 1,
        completed_task_count: 0,
        is_overloaded: false,
        is_underutilized: false,
      },
    ],
    overloaded_students: [],
    underutilized_students: [],
    recommendations: [],
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.tasks.list).mockResolvedValue([...mockTasks]);
    vi.mocked(api.milestones.list).mockResolvedValue([]);
    vi.mocked(api.projects.listMembers).mockResolvedValue([...mockMembers]);
    vi.mocked(api.projects.getWorkload).mockResolvedValue(mockWorkload);
  });

  const renderComponent = () =>
    render(
      <MemoryRouter initialEntries={['/projects/proj-123/scheduling']}>
        <Routes>
          <Route path="/projects/:projectId/scheduling" element={<SchedulingPage />} />
        </Routes>
      </MemoryRouter>
    );

  it('renders Assigned Team Members column, showing assignee chips and unassigned indicators', async () => {
    renderComponent();

    // Verify column header
    await waitFor(() => {
      expect(screen.getByText('Assigned Team Members')).toBeInTheDocument();
    });

    // Verify task 1 has assignee chip for Aslesha
    expect(screen.getByTestId('task-assignees-task-req-1')).toHaveTextContent('Aslesha Student');
    expect(screen.getByTestId('task-assignees-task-req-1')).toHaveTextContent('developer');

    // Verify task 2 has "Unassigned" indicator
    expect(screen.getByText('Unassigned')).toBeInTheDocument();
  });

  it('opens assignment modal displaying existing assignee with workload stats and allows adding a second member without overwrite', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Requirements Engineering')).toBeInTheDocument();
    });

    // Click assign on task-req-1 (which already has Aslesha assigned)
    const assignButtons = screen.getAllByRole('button', { name: /Assign/i });
    fireEvent.click(assignButtons[0]);

    // Modal opens
    await waitFor(() => {
      expect(screen.getByText('Manage Task Assignments')).toBeInTheDocument();
      expect(screen.getByText(/Currently Assigned \(1\)/i)).toBeInTheDocument();
    });

    // Verify existing assignee Aslesha is listed at top in the modal (and also in table)
    expect(screen.getAllByText('Aslesha Student').length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText(/1 active task/i).length).toBeGreaterThanOrEqual(1);

    // Verify available members dropdown contains Sravani (unassigned) and NOT Aslesha
    const select = screen.getByLabelText(/Select Available Student/i) as HTMLSelectElement;
    const optionTexts = Array.from(select.options).map((o) => o.text);
    expect(optionTexts.some((t) => t.includes('Sravani Leader'))).toBe(true);
    expect(optionTexts.some((t) => t.includes('Aslesha Student'))).toBe(false);

    // Mock successful assignment of Sravani
    vi.mocked(api.tasks.assign).mockResolvedValueOnce({
      id: 'assign-2',
      task_id: 'task-req-1',
      user_id: 'user-sravani',
      assigned_at: '2026-03-01',
      user: {
        id: 'user-sravani',
        full_name: 'Sravani Leader',
        email: 'sravani@college.edu',
        role: 'student',
      },
    });

    // Select Sravani Leader
    fireEvent.change(select, { target: { value: 'user-sravani' } });

    // Submit assignment
    const assignSubmitBtn = screen.getByRole('button', { name: /Assign Team Member/i });
    fireEvent.click(assignSubmitBtn);

    await waitFor(() => {
      expect(api.tasks.assign).toHaveBeenCalledWith('task-req-1', 'user-sravani');
    });

    // Verify BOTH Aslesha and Sravani are now displayed in the modal
    await waitFor(() => {
      expect(screen.getByText(/Currently Assigned \(2\)/i)).toBeInTheDocument();
      expect(screen.getByText('Assigned Sravani Leader to this task.')).toBeInTheDocument();
    });

    // Click Done to close modal
    fireEvent.click(screen.getByRole('button', { name: /Done/i }));

    // Verify table now displays BOTH assignees in task-req-1 row
    const taskAssigneesCell = screen.getByTestId('task-assignees-task-req-1');
    expect(taskAssigneesCell).toHaveTextContent('Aslesha Student');
    expect(taskAssigneesCell).toHaveTextContent('Sravani Leader');
  });

  it('allows unassigning a team member with confirmation prompt and reflects immediately', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Requirements Engineering')).toBeInTheDocument();
    });

    // Click assign on task-req-1
    const assignButtons = screen.getAllByRole('button', { name: /Assign/i });
    fireEvent.click(assignButtons[0]);

    await waitFor(() => {
      expect(screen.getByText('Manage Task Assignments')).toBeInTheDocument();
    });

    // Click Remove on Aslesha
    const removeBtn = screen.getByRole('button', { name: /Remove/i });
    fireEvent.click(removeBtn);

    // Verify confirmation prompt appeared
    expect(screen.getByText('Remove?')).toBeInTheDocument();
    const yesBtn = screen.getByRole('button', { name: 'Yes' });

    vi.mocked(api.tasks.unassign).mockResolvedValueOnce(undefined as any);

    // Confirm removal
    fireEvent.click(yesBtn);

    await waitFor(() => {
      expect(api.tasks.unassign).toHaveBeenCalledWith('task-req-1', 'user-aslesha');
      expect(screen.getByText('Removed Aslesha Student from this task.')).toBeInTheDocument();
      expect(screen.getByText(/Currently Assigned \(0\)/i)).toBeInTheDocument();
      expect(screen.getByText('No team members assigned yet')).toBeInTheDocument();
    });
  });
});
