import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { MilestonesWorkloadPage } from '../pages/milestones/MilestonesWorkloadPage';
import { SchedulingPage } from '../pages/scheduling/SchedulingPage';
import { ProjectDashboardPage } from '../pages/projects/ProjectDashboardPage';
import { api } from '../api/client';
import * as AuthContextModule from '../context/AuthContext';
import {
  AcademicMilestone,
  AcademicProject,
  ProjectMember,
  Task,
  TeamWorkloadResponse,
  ReviewReadinessResponse,
} from '../types';

describe('General Edit and Delete Frontend Functionality', () => {
  const mockUser = {
    id: 'user-lead-1',
    full_name: 'Lead Student',
    email: 'lead@test.edu',
    role: 'student' as const,
    is_active: true,
    created_at: '2026-01-01',
  };

  const mockProject: AcademicProject = {
    id: 'proj-1',
    title: 'Autonomous Drone Navigation',
    description: 'Path planning with obstacle avoidance',
    academic_year: '2025-2026',
    semester: 7,
    department: 'Computer Science',
    project_type: 'capstone',
    status: 'in_progress',
    start_date: '2026-01-10',
    target_deadline: '2026-05-30',
    owner_id: 'user-lead-1',
    faculty_guide_id: 'fac-1',
    faculty_guide: {
      id: 'fac-1',
      full_name: 'Dr. Alan Turing',
      email: 'alan@test.edu',
      role: 'faculty',
    },
    owner: {
      id: 'user-lead-1',
      full_name: 'Lead Student',
      email: 'lead@test.edu',
      role: 'student',
    },
    created_at: '2026-01-01',
    updated_at: '2026-01-01',
  };

  const mockMilestones: AcademicMilestone[] = [
    {
      id: 'm-1',
      project_id: 'proj-1',
      title: 'Literature Review & Architecture',
      description: 'Survey existing literature',
      milestone_type: 'literature_review',
      sequence_number: 1,
      planned_date: '2026-02-15',
      completed_at: null,
      status: 'pending',
      is_required: true,
      created_at: '2026-01-01',
    },
    {
      id: 'm-2',
      project_id: 'proj-1',
      title: 'Optional Field Testing',
      description: 'Extended outdoors experiment',
      milestone_type: 'testing',
      sequence_number: 2,
      planned_date: '2026-04-10',
      completed_at: null,
      status: 'pending',
      is_required: false,
      created_at: '2026-01-01',
    },
  ];

  const mockMembers: ProjectMember[] = [
    {
      id: 'pm-1',
      project_id: 'proj-1',
      user_id: 'user-lead-1',
      team_role: 'leader',
      joined_at: '2026-01-01',
      user: {
        id: 'user-lead-1',
        full_name: 'Lead Student',
        email: 'lead@test.edu',
        role: 'student',
      },
    },
    {
      id: 'pm-2',
      project_id: 'proj-1',
      user_id: 'user-student-2',
      team_role: 'developer',
      joined_at: '2026-01-02',
      user: {
        id: 'user-student-2',
        full_name: 'Aslesha Developer',
        email: 'aslesha@test.edu',
        role: 'student',
      },
    },
  ];

  const mockTasks: Task[] = [
    {
      id: 'task-1',
      project_id: 'proj-1',
      milestone_id: 'm-1',
      title: 'Implement A* Algorithm',
      description: 'Write grid-based pathfinding code',
      priority: 'high',
      status: 'in_progress',
      estimated_duration_hours: 15,
      actual_duration_hours: null,
      due_date: '2026-02-28',
      created_at: '2026-01-01',
      updated_at: '2026-01-01',
      assignments: [
        {
          id: 'asg-1',
          task_id: 'task-1',
          user_id: 'user-student-2',
          assigned_at: '2026-01-02',
          user: {
            id: 'user-student-2',
            full_name: 'Aslesha Developer',
            email: 'aslesha@test.edu',
            role: 'student',
          },
        },
      ],
      dependencies: [],
    },
  ];

  const mockWorkload: TeamWorkloadResponse = {
    project_id: 'proj-1',
    threshold_hours: 20,
    reference_date: '2026-01-15',
    total_team_active_hours: 15,
    average_hours_per_student: 7.5,
    workload_standard_deviation: 7.5,
    overloaded_students: ['user-student-2'],
    underutilized_students: [],
    recommendations: ['Balance effort between developers'],
    student_workloads: [
      {
        user_id: 'user-lead-1',
        full_name: 'Lead Student',
        email: 'lead@test.edu',
        team_role: 'leader',
        total_active_hours: 0,
        completed_hours: 0,
        assigned_task_count: 0,
        overdue_task_count: 0,
        upcoming_task_count: 0,
        completed_task_count: 0,
        is_overloaded: false,
        is_underutilized: false,
      },
      {
        user_id: 'user-student-2',
        full_name: 'Aslesha Developer',
        email: 'aslesha@test.edu',
        team_role: 'developer',
        total_active_hours: 15,
        completed_hours: 0,
        assigned_task_count: 1,
        overdue_task_count: 0,
        upcoming_task_count: 1,
        completed_task_count: 0,
        is_overloaded: true,
        is_underutilized: false,
      },
    ],
  };

  const mockReadiness: ReviewReadinessResponse = {
    project_id: 'proj-1',
    readiness_score: 75,
    readiness_level: 'GOOD READINESS',
    score_breakdown: {
      milestone_score: 30,
      task_completion_score: 10,
      critical_path_score: 15,
      overdue_score: 10,
      review_timing_score: 10,
      total_score: 75,
    },
    blockers: [],
    actionable_recommendations: [],
    next_review_scheduled_at: null,
  };

  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(AuthContextModule, 'useAuth').mockReturnValue({
      user: mockUser,
      token: 'fake-jwt',
      role: 'student',
      login: vi.fn(),
      register: vi.fn(),
      logout: vi.fn(),
      refreshUser: vi.fn(),
      isLoading: false,
      isAuthenticated: true,
    });
  });

  describe('MilestonesWorkloadPage Edit/Delete', () => {
    beforeEach(() => {
      vi.spyOn(api.milestones, 'list').mockResolvedValue(mockMilestones);
      vi.spyOn(api.projects, 'getWorkload').mockResolvedValue(mockWorkload);
      vi.spyOn(api.projects, 'getReadiness').mockResolvedValue(mockReadiness);
      vi.spyOn(api.projects, 'listMembers').mockResolvedValue(mockMembers);
    });

    it('renders Required vs Optional badges and Edit/Delete buttons on milestones', async () => {
      render(
        <MemoryRouter initialEntries={['/projects/proj-1/milestones']}>
          <Routes>
            <Route path="/projects/:projectId/milestones" element={<MilestonesWorkloadPage />} />
          </Routes>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('Literature Review & Architecture')).toBeInTheDocument();
      });

      expect(screen.getByText('Required')).toBeInTheDocument();
      expect(screen.getByText('Optional')).toBeInTheDocument();

      const editButtons = screen.getAllByRole('button', { name: /edit/i });
      const deleteButtons = screen.getAllByRole('button', { name: /delete/i });
      expect(editButtons.length).toBeGreaterThanOrEqual(2);
      expect(deleteButtons.length).toBeGreaterThanOrEqual(2);
    });

    it('opens prefilled edit modal and submits milestone update', async () => {
      const updateSpy = vi.spyOn(api.milestones, 'update').mockResolvedValue({
        ...mockMilestones[0],
        title: 'Updated Literature Review',
      });

      render(
        <MemoryRouter initialEntries={['/projects/proj-1/milestones']}>
          <Routes>
            <Route path="/projects/:projectId/milestones" element={<MilestonesWorkloadPage />} />
          </Routes>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('Literature Review & Architecture')).toBeInTheDocument();
      });

      const editButtons = screen.getAllByRole('button', { name: /edit/i });
      fireEvent.click(editButtons[0]);

      expect(screen.getByText('Edit Academic Milestone')).toBeInTheDocument();
      const titleInput = screen.getByDisplayValue('Literature Review & Architecture');
      fireEvent.change(titleInput, { target: { value: 'Updated Literature Review' } });

      const saveButton = screen.getByRole('button', { name: /update milestone/i });
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(updateSpy).toHaveBeenCalledWith(
          'm-1',
          expect.objectContaining({
            title: 'Updated Literature Review',
            is_required: true,
          })
        );
      });
    });

    it('calls delete milestone on confirmation', async () => {
      const deleteSpy = vi.spyOn(api.milestones, 'delete').mockResolvedValue(undefined);
      vi.spyOn(window, 'confirm').mockReturnValue(true);

      render(
        <MemoryRouter initialEntries={['/projects/proj-1/milestones']}>
          <Routes>
            <Route path="/projects/:projectId/milestones" element={<MilestonesWorkloadPage />} />
          </Routes>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('Optional Field Testing')).toBeInTheDocument();
      });

      const deleteButtons = screen.getAllByRole('button', { name: /delete/i });
      fireEvent.click(deleteButtons[1]);

      expect(window.confirm).toHaveBeenCalledWith(
        expect.stringContaining('Optional Field Testing')
      );
      await waitFor(() => {
        expect(deleteSpy).toHaveBeenCalledWith('m-2');
      });
    });
  });

  describe('SchedulingPage Task Edit/Delete', () => {
    beforeEach(() => {
      vi.spyOn(api.tasks, 'list').mockResolvedValue(mockTasks);
      vi.spyOn(api.milestones, 'list').mockResolvedValue(mockMilestones);
      vi.spyOn(api.projects, 'listMembers').mockResolvedValue(mockMembers);
      vi.spyOn(api.projects, 'getWorkload').mockResolvedValue(mockWorkload);
    });

    it('displays Edit and Delete actions in task breakdown table', async () => {
      render(
        <MemoryRouter initialEntries={['/projects/proj-1/scheduling']}>
          <Routes>
            <Route path="/projects/:projectId/scheduling" element={<SchedulingPage />} />
          </Routes>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('Implement A* Algorithm')).toBeInTheDocument();
      });

      expect(screen.getByRole('button', { name: /edit/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /delete/i })).toBeInTheDocument();
    });

    it('opens prefilled task modal and submits task update', async () => {
      const updateTaskSpy = vi.spyOn(api.tasks, 'update').mockResolvedValue({
        ...mockTasks[0],
        title: 'Optimized A* Algorithm',
        priority: 'critical',
      });

      render(
        <MemoryRouter initialEntries={['/projects/proj-1/scheduling']}>
          <Routes>
            <Route path="/projects/:projectId/scheduling" element={<SchedulingPage />} />
          </Routes>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('Implement A* Algorithm')).toBeInTheDocument();
      });

      const editBtn = screen.getByRole('button', { name: /edit/i });
      fireEvent.click(editBtn);

      expect(screen.getByText('Edit Academic Task')).toBeInTheDocument();
      const titleInput = screen.getByDisplayValue('Implement A* Algorithm');
      fireEvent.change(titleInput, { target: { value: 'Optimized A* Algorithm' } });

      const updateBtn = screen.getByRole('button', { name: /update task/i });
      fireEvent.click(updateBtn);

      await waitFor(() => {
        expect(updateTaskSpy).toHaveBeenCalledWith(
          'task-1',
          expect.objectContaining({
            title: 'Optimized A* Algorithm',
          })
        );
      });
    });

    it('confirms and calls delete task, warning about assigned members', async () => {
      const deleteTaskSpy = vi.spyOn(api.tasks, 'delete').mockResolvedValue(undefined);
      vi.spyOn(window, 'confirm').mockReturnValue(true);

      render(
        <MemoryRouter initialEntries={['/projects/proj-1/scheduling']}>
          <Routes>
            <Route path="/projects/:projectId/scheduling" element={<SchedulingPage />} />
          </Routes>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('Implement A* Algorithm')).toBeInTheDocument();
      });

      const deleteBtn = screen.getByRole('button', { name: /delete/i });
      fireEvent.click(deleteBtn);

      expect(window.confirm).toHaveBeenCalledWith(
        expect.stringContaining('Warning: This task has 1 assigned member(s)')
      );

      await waitFor(() => {
        expect(deleteTaskSpy).toHaveBeenCalledWith('task-1');
      });
    });
  });

  describe('ProjectDashboardPage Project Edit & Member Management', () => {
    beforeEach(() => {
      vi.spyOn(api.projects, 'get').mockResolvedValue(mockProject);
      vi.spyOn(api.projects, 'getReadiness').mockResolvedValue(mockReadiness);
      vi.spyOn(api.projects, 'getWorkload').mockResolvedValue(mockWorkload);
      vi.spyOn(api.projects, 'listMembers').mockResolvedValue(mockMembers);
      vi.spyOn(api.tasks, 'list').mockResolvedValue(mockTasks);
    });

    it('displays Edit Project button for owner and updates project details', async () => {
      const updateProjectSpy = vi.spyOn(api.projects, 'update').mockResolvedValue({
        ...mockProject,
        title: 'Autonomous Drone Navigation (Final Phase)',
      });

      render(
        <MemoryRouter initialEntries={['/projects/proj-1']}>
          <Routes>
            <Route path="/projects/:projectId" element={<ProjectDashboardPage />} />
          </Routes>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('Autonomous Drone Navigation')).toBeInTheDocument();
      });

      const editProjBtn = screen.getByRole('button', { name: /edit project/i });
      fireEvent.click(editProjBtn);

      expect(screen.getByText('Edit Project Details')).toBeInTheDocument();
      const titleInput = screen.getByDisplayValue('Autonomous Drone Navigation');
      fireEvent.change(titleInput, { target: { value: 'Autonomous Drone Navigation (Final Phase)' } });

      const saveChangesBtn = screen.getByRole('button', { name: /save changes/i });
      fireEvent.click(saveChangesBtn);

      await waitFor(() => {
        expect(updateProjectSpy).toHaveBeenCalledWith(
          'proj-1',
          expect.objectContaining({
            title: 'Autonomous Drone Navigation (Final Phase)',
          })
        );
      });
    });

    it('allows changing role for non-owner member', async () => {
      const updateRoleSpy = vi.spyOn(api.projects, 'updateMemberRole').mockResolvedValue({
        ...mockMembers[1],
        team_role: 'tester',
      });

      render(
        <MemoryRouter initialEntries={['/projects/proj-1']}>
          <Routes>
            <Route path="/projects/:projectId" element={<ProjectDashboardPage />} />
          </Routes>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('Aslesha Developer')).toBeInTheDocument();
      });

      const roleSelect = screen.getByTitle('Change team role');
      fireEvent.change(roleSelect, { target: { value: 'tester' } });

      await waitFor(() => {
        expect(updateRoleSpy).toHaveBeenCalledWith('proj-1', 'user-student-2', 'tester');
      });
    });

    it('allows removing a non-owner team member with confirmation', async () => {
      const removeMemberSpy = vi.spyOn(api.projects, 'removeMember').mockResolvedValue(undefined);
      vi.spyOn(window, 'confirm').mockReturnValue(true);

      render(
        <MemoryRouter initialEntries={['/projects/proj-1']}>
          <Routes>
            <Route path="/projects/:projectId" element={<ProjectDashboardPage />} />
          </Routes>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('Aslesha Developer')).toBeInTheDocument();
      });

      const removeBtn = screen.getByTitle('Remove Aslesha Developer from team');
      fireEvent.click(removeBtn);

      expect(window.confirm).toHaveBeenCalledWith(
        expect.stringContaining('Aslesha Developer')
      );

      await waitFor(() => {
        expect(removeMemberSpy).toHaveBeenCalledWith('proj-1', 'user-student-2');
      });
    });
  });
});
