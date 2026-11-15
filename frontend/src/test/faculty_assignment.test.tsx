import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { ProjectDashboardPage } from '../pages/projects/ProjectDashboardPage';
import { api } from '../api/client';
import * as AuthContextModule from '../context/AuthContext';
import { AcademicProject, UserSummary } from '../types';

describe('Faculty Guide Assignment Feature', () => {
  const mockOwnerUser = {
    id: 'owner-123',
    full_name: 'Student Leader',
    email: 'leader@college.edu',
    role: 'student' as const,
    is_active: true,
    created_at: '2026-01-01',
  };

  const mockOtherUser = {
    id: 'other-999',
    full_name: 'Other Student',
    email: 'other@college.edu',
    role: 'student' as const,
    is_active: true,
    created_at: '2026-01-01',
  };

  const mockProjectWithoutGuide: AcademicProject = {
    id: 'proj-1',
    title: 'Student Project scheduling tool',
    description: 'Capstone project on scheduling algorithms',
    academic_year: '2025-2026',
    semester: 8,
    department: 'CSE',
    project_type: 'capstone',
    status: 'in_progress',
    start_date: '2026-01-01',
    target_deadline: '2026-06-01',
    owner_id: 'owner-123',
    faculty_guide_id: null,
    faculty_guide: null,
    owner: {
      id: 'owner-123',
      full_name: 'Student Leader',
      email: 'leader@college.edu',
      role: 'student',
    },
    created_at: '2026-01-01',
    updated_at: '2026-01-01',
  };

  const mockFacultyList: UserSummary[] = [
    {
      id: 'fac-1',
      full_name: 'Janardhan',
      email: 'janardhan2005@gmail.com',
      role: 'faculty',
      department: 'Computer Science',
    },
    {
      id: 'fac-2',
      full_name: 'Dr. C.V. Raman',
      email: 'raman@college.edu',
      role: 'faculty',
      department: 'Physics',
    },
  ];

  beforeEach(() => {
    vi.restoreAllMocks();

    vi.spyOn(api.projects, 'get').mockResolvedValue(mockProjectWithoutGuide);
    vi.spyOn(api.projects, 'getReadiness').mockResolvedValue({
      project_id: 'proj-1',
      readiness_score: 85,
      readiness_level: 'GOOD',
      score_breakdown: {
        milestone_score: 20,
        task_completion_score: 25,
        critical_path_score: 20,
        overdue_score: 10,
        review_timing_score: 10,
        total_score: 85,
      },
      blockers: [],
      actionable_recommendations: [],
    });
    vi.spyOn(api.projects, 'getWorkload').mockResolvedValue({
      project_id: 'proj-1',
      threshold_hours: 25,
      reference_date: '2026-03-01',
      total_team_active_hours: 40,
      average_hours_per_student: 20,
      workload_standard_deviation: 2,
      student_workloads: [],
      overloaded_students: [],
      underutilized_students: [],
      recommendations: [],
    });
    vi.spyOn(api.projects, 'listMembers').mockResolvedValue([]);
    vi.spyOn(api.tasks, 'list').mockResolvedValue([]);
    vi.spyOn(api.faculty, 'listFacultyMembers').mockResolvedValue(mockFacultyList);
  });

  it('renders "No Guide Assigned Yet" and shows Assign button for project owner', async () => {
    vi.spyOn(AuthContextModule, 'useAuth').mockReturnValue({
      user: mockOwnerUser,
      token: 'tok',
      isLoading: false,
      isAuthenticated: true,
      role: 'student',
      login: vi.fn(),
      register: vi.fn(),
      logout: vi.fn(),
      refreshUser: vi.fn(),
    });

    render(
      <MemoryRouter initialEntries={['/projects/proj-1']}>
        <Routes>
          <Route path="/projects/:projectId" element={<ProjectDashboardPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Student Project scheduling tool')).toBeInTheDocument();
    });

    // Check status display
    expect(screen.getByTestId('faculty-guide-name')).toHaveTextContent('No Guide Assigned Yet');

    // Owner should see the Assign button
    const assignBtn = screen.getByTestId('assign-guide-btn');
    expect(assignBtn).toBeInTheDocument();
    expect(assignBtn).toHaveTextContent('Assign Faculty Guide');
  });

  it('does NOT render Assign button for non-owner student', async () => {
    vi.spyOn(AuthContextModule, 'useAuth').mockReturnValue({
      user: mockOtherUser,
      token: 'tok',
      isLoading: false,
      isAuthenticated: true,
      role: 'student',
      login: vi.fn(),
      register: vi.fn(),
      logout: vi.fn(),
      refreshUser: vi.fn(),
    });

    render(
      <MemoryRouter initialEntries={['/projects/proj-1']}>
        <Routes>
          <Route path="/projects/:projectId" element={<ProjectDashboardPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Student Project scheduling tool')).toBeInTheDocument();
    });

    // Non-owner sees "No Guide Assigned Yet" but NO assign button
    expect(screen.getByTestId('faculty-guide-name')).toHaveTextContent('No Guide Assigned Yet');
    expect(screen.queryByTestId('assign-guide-btn')).not.toBeInTheDocument();
  });

  it('opens modal, lists faculty members, and allows owner to select and assign Janardhan', async () => {
    vi.spyOn(AuthContextModule, 'useAuth').mockReturnValue({
      user: mockOwnerUser,
      token: 'tok',
      isLoading: false,
      isAuthenticated: true,
      role: 'student',
      login: vi.fn(),
      register: vi.fn(),
      logout: vi.fn(),
      refreshUser: vi.fn(),
    });

    const mockProjectWithGuide = {
      ...mockProjectWithoutGuide,
      faculty_guide_id: 'fac-1',
      faculty_guide: mockFacultyList[0],
    };

    const assignSpy = vi.spyOn(api.projects, 'assignFacultyGuide').mockResolvedValue(mockProjectWithGuide);

    vi.spyOn(api.projects, 'get').mockImplementation(async () => {
      return assignSpy.mock.calls.length > 0 ? mockProjectWithGuide : mockProjectWithoutGuide;
    });

    render(
      <MemoryRouter initialEntries={['/projects/proj-1']}>
        <Routes>
          <Route path="/projects/:projectId" element={<ProjectDashboardPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Student Project scheduling tool')).toBeInTheDocument();
    });

    // Click "Assign Faculty Guide"
    fireEvent.click(screen.getByTestId('assign-guide-btn'));

    // Verify modal is open and lists Janardhan
    await waitFor(() => {
      expect(screen.getByText('Janardhan')).toBeInTheDocument();
      expect(screen.getByText('janardhan2005@gmail.com')).toBeInTheDocument();
      expect(screen.getByText('Dr. C.V. Raman')).toBeInTheDocument();
    });

    // Click confirm assignment
    fireEvent.click(screen.getByTestId('confirm-assign-guide-btn'));

    // Verify API was called with project ID and Janardhan's actual UUID
    await waitFor(() => {
      expect(assignSpy).toHaveBeenCalledWith('proj-1', 'fac-1');
    });

    // Verify project overview now displays Janardhan
    await waitFor(() => {
      expect(screen.getByTestId('faculty-guide-name')).toHaveTextContent('Janardhan');
      expect(screen.getByText('janardhan2005@gmail.com')).toBeInTheDocument();
    });
  });

  it('API client sends PUT /projects/:id/faculty-guide and GET /faculty correctly', async () => {
    const mockFetch = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith('/faculty')) {
        return {
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => mockFacultyList,
        } as any;
      }
      if (url.includes('/projects/proj-1/faculty-guide')) {
        return {
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({
            ...mockProjectWithoutGuide,
            faculty_guide_id: 'fac-1',
          }),
        } as any;
      }
      return { ok: false, status: 404 } as any;
    });

    const faculties = await api.faculty.listFacultyMembers();
    expect(faculties).toHaveLength(2);
    expect(faculties[0].full_name).toBe('Janardhan');

    const updated = await api.projects.assignFacultyGuide('proj-1', 'fac-1');
    expect(updated.faculty_guide_id).toBe('fac-1');

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringMatching(/\/projects\/proj-1\/faculty-guide$/),
      expect.objectContaining({
        method: 'PUT',
        body: JSON.stringify({ faculty_guide_id: 'fac-1' }),
      })
    );
  });
});
