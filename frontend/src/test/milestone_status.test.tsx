import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { MilestonesWorkloadPage } from '../pages/milestones/MilestonesWorkloadPage';
import { api } from '../api/client';
import * as AuthContextModule from '../context/AuthContext';
import {
  AcademicMilestone,
  TeamWorkloadResponse,
  ReviewReadinessResponse,
} from '../types';

describe('Academic Milestone Status Feature (Pending vs Completed)', () => {
  const mockUser = {
    id: 'user-lead-1',
    full_name: 'Lead Student',
    email: 'lead@test.edu',
    role: 'student' as const,
    is_active: true,
    created_at: '2026-01-01',
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
      title: 'Implementation Progress Review',
      description: 'Core modules working',
      milestone_type: 'implementation',
      sequence_number: 2,
      planned_date: '2026-03-30',
      completed_at: '2026-03-28T10:00:00Z',
      status: 'completed',
      is_required: true,
      created_at: '2026-01-01',
    },
    {
      id: 'm-3',
      project_id: 'proj-1',
      title: 'Legacy Milestone Without Stored Status',
      description: 'Old record test',
      milestone_type: 'system_design',
      sequence_number: 3,
      planned_date: '2026-04-15',
      completed_at: null,
      // @ts-expect-error testing missing status
      status: undefined,
      is_required: true,
      created_at: '2026-01-01',
    },
  ];

  const mockWorkload: TeamWorkloadResponse = {
    project_id: 'proj-1',
    threshold_hours: 20,
    reference_date: '2026-01-15',
    total_team_active_hours: 15,
    average_hours_per_student: 7.5,
    workload_standard_deviation: 7.5,
    overloaded_students: [],
    underutilized_students: [],
    recommendations: [],
    student_workloads: [],
  };

  const mockReadiness: ReviewReadinessResponse = {
    project_id: 'proj-1',
    readiness_score: 55,
    readiness_level: 'NEEDS ATTENTION',
    score_breakdown: {
      milestone_score: 13.3, // 1 of 3 required milestones completed -> (1/3)*40 = 13.3
      task_completion_score: 15,
      critical_path_score: 15,
      overdue_score: 7,
      review_timing_score: 5,
      total_score: 55,
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
    vi.spyOn(api.milestones, 'list').mockResolvedValue(mockMilestones);
    vi.spyOn(api.projects, 'getWorkload').mockResolvedValue(mockWorkload);
    vi.spyOn(api.projects, 'getReadiness').mockResolvedValue(mockReadiness);
  });

  it('renders Pending and Completed badges on milestone cards, defaulting missing status to Pending', async () => {
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

    // Milestone 1 (pending) and Milestone 3 (undefined status) should both show Pending badge
    const pendingBadges = screen.getAllByText('Pending');
    expect(pendingBadges.length).toBeGreaterThanOrEqual(2);

    // Milestone 2 should show Completed badge
    const completedElements = screen.getAllByText('Completed');
    expect(completedElements.length).toBeGreaterThanOrEqual(1);
  });

  it('provides exactly two options (Pending and Completed) in the Status dropdown and loads current status', async () => {
    render(
      <MemoryRouter initialEntries={['/projects/proj-1/milestones']}>
        <Routes>
          <Route path="/projects/:projectId/milestones" element={<MilestonesWorkloadPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Implementation Progress Review')).toBeInTheDocument();
    });

    // Click Edit on Milestone 2 (which is 'completed')
    const editButtons = screen.getAllByRole('button', { name: /edit/i });
    fireEvent.click(editButtons[1]);

    expect(screen.getByText('Edit Academic Milestone')).toBeInTheDocument();

    const statusSelect = screen.getByTestId('milestone-status-select') as HTMLSelectElement;
    expect(statusSelect).toBeInTheDocument();

    // Verify exactly two options: Pending and Completed
    const options = Array.from(statusSelect.options).map((opt) => opt.value);
    expect(options).toEqual(['pending', 'completed']);
    expect(options.length).toBe(2);

    // Verify it loaded the milestone's current status ('completed')
    expect(statusSelect.value).toBe('completed');
  });

  it('allows changing status from Pending to Completed and saves via api.milestones.update', async () => {
    const updateSpy = vi.spyOn(api.milestones, 'update').mockResolvedValue({
      ...mockMilestones[0],
      status: 'completed',
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

    // Click Edit on Milestone 1 (which is 'pending')
    const editButtons = screen.getAllByRole('button', { name: /edit/i });
    fireEvent.click(editButtons[0]);

    const statusSelect = screen.getByTestId('milestone-status-select') as HTMLSelectElement;
    expect(statusSelect.value).toBe('pending');

    // Change status to completed
    fireEvent.change(statusSelect, { target: { value: 'completed' } });
    expect(statusSelect.value).toBe('completed');

    // Submit the form
    const saveButton = screen.getByRole('button', { name: /update milestone/i });
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(updateSpy).toHaveBeenCalledWith(
        'm-1',
        expect.objectContaining({
          status: 'completed',
        })
      );
    });
  });

  it('allows changing status from Completed back to Pending and saves via api.milestones.update', async () => {
    const updateSpy = vi.spyOn(api.milestones, 'update').mockResolvedValue({
      ...mockMilestones[1],
      status: 'pending',
    });

    render(
      <MemoryRouter initialEntries={['/projects/proj-1/milestones']}>
        <Routes>
          <Route path="/projects/:projectId/milestones" element={<MilestonesWorkloadPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Implementation Progress Review')).toBeInTheDocument();
    });

    // Click Edit on Milestone 2 (which is 'completed')
    const editButtons = screen.getAllByRole('button', { name: /edit/i });
    fireEvent.click(editButtons[1]);

    const statusSelect = screen.getByTestId('milestone-status-select') as HTMLSelectElement;
    expect(statusSelect.value).toBe('completed');

    // Change status back to pending
    fireEvent.change(statusSelect, { target: { value: 'pending' } });
    expect(statusSelect.value).toBe('pending');

    // Submit form
    const saveButton = screen.getByRole('button', { name: /update milestone/i });
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(updateSpy).toHaveBeenCalledWith(
        'm-2',
        expect.objectContaining({
          status: 'pending',
        })
      );
    });
  });

  it('displays Academic Review Readiness Scorecard with milestone score breakdown', async () => {
    render(
      <MemoryRouter initialEntries={['/projects/proj-1/milestones']}>
        <Routes>
          <Route path="/projects/:projectId/milestones" element={<MilestonesWorkloadPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Academic Review Readiness Scorecard')).toBeInTheDocument();
    });

    expect(screen.getByText('55')).toBeInTheDocument();
    expect(screen.getByText('/100')).toBeInTheDocument();
    expect(screen.getByText('Milestone Completion (Max 40 pts)')).toBeInTheDocument();
    expect(screen.getByText('13.3 / 40.0')).toBeInTheDocument();
  });
});
