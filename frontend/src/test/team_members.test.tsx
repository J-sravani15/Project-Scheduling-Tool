import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { ProjectDashboardPage } from '../pages/projects/ProjectDashboardPage';
import { api } from '../api/client';
import * as AuthContextModule from '../context/AuthContext';
import { AcademicProject, UserSummary, ProjectMember } from '../types';

describe('Add Team Member Feature', () => {
  const mockOwner = {
    id: 'owner-uuid-123',
    full_name: 'Sravani Project Lead',
    email: 'sravani@college.edu',
    role: 'student' as const,
    is_active: true,
    created_at: '2026-01-01',
  };

  const mockNonOwner = {
    id: 'other-student-uuid',
    full_name: 'Other Student',
    email: 'other@college.edu',
    role: 'student' as const,
    is_active: true,
    created_at: '2026-01-01',
  };

  const mockProject: AcademicProject = {
    id: 'proj-123',
    title: 'Student Project scheduling tool',
    description: 'Capstone project on scheduling algorithms',
    academic_year: '2025-2026',
    semester: 8,
    department: 'Computer Science',
    project_type: 'capstone',
    status: 'in_progress',
    start_date: '2026-01-01',
    target_deadline: '2026-06-01',
    owner_id: 'owner-uuid-123',
    faculty_guide_id: null,
    faculty_guide: null,
    owner: {
      id: 'owner-uuid-123',
      full_name: 'Sravani Project Lead',
      email: 'sravani@college.edu',
      role: 'student',
    },
    created_at: '2026-01-01',
    updated_at: '2026-01-01',
  };

  const mockExistingMembers: ProjectMember[] = [
    {
      id: 'mem-1',
      project_id: 'proj-123',
      user_id: 'owner-uuid-123',
      team_role: 'leader',
      joined_at: '2026-01-01',
      user: {
        id: 'owner-uuid-123',
        full_name: 'Sravani Project Lead',
        email: 'sravani@college.edu',
        role: 'student',
      },
    },
  ];

  const mockAvailableStudents: UserSummary[] = [
    {
      id: 'student-aslesha-uuid',
      full_name: 'Aslesha',
      email: 'aslesha1@gmail.com',
      role: 'student',
      department: 'Computer Science',
    },
    {
      id: 'student-rohit-uuid',
      full_name: 'Rohit Sharma',
      email: 'rohit@college.edu',
      role: 'student',
      department: 'Information Technology',
    },
  ];

  beforeEach(() => {
    vi.restoreAllMocks();

    vi.spyOn(api.projects, 'get').mockResolvedValue(mockProject);
    vi.spyOn(api.projects, 'getReadiness').mockResolvedValue({
      project_id: 'proj-123',
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
    } as any);
    vi.spyOn(api.projects, 'getWorkload').mockResolvedValue({
      project_id: 'proj-123',
      threshold_hours: 25,
      reference_date: '2026-03-01',
      total_team_active_hours: 40,
      average_hours_per_student: 20,
      workload_standard_deviation: 2,
      is_balanced: true,
      overloaded_students: [],
      student_workloads: [],
    } as any);
    vi.spyOn(api.projects, 'listMembers').mockResolvedValue(mockExistingMembers);
    vi.spyOn(api.tasks, 'list').mockResolvedValue([]);
    vi.spyOn(api.projects, 'listAvailableStudents').mockResolvedValue(mockAvailableStudents);
    vi.spyOn(api.projects, 'addMember').mockResolvedValue({
      id: 'mem-new',
      project_id: 'proj-123',
      user_id: 'student-aslesha-uuid',
      team_role: 'developer',
      joined_at: '2026-01-02',
      user: mockAvailableStudents[0],
    } as any);
  });

  const renderDashboard = (currentUser = mockOwner) => {
    vi.spyOn(AuthContextModule, 'useAuth').mockReturnValue({
      user: currentUser,
      token: 'fake-jwt-token',
      role: currentUser.role,
      login: vi.fn(),
      register: vi.fn(),
      logout: vi.fn(),
      refreshUser: vi.fn(),
      isLoading: false,
      isAuthenticated: true,
    });

    return render(
      <MemoryRouter initialEntries={['/projects/proj-123']}>
        <Routes>
          <Route path="/projects/:projectId" element={<ProjectDashboardPage />} />
        </Routes>
      </MemoryRouter>
    );
  };

  it('renders Add Member button for project owner and opens modal with selectable students', async () => {
    renderDashboard(mockOwner);

    // Wait for project dashboard to load
    await waitFor(() => {
      expect(screen.getByText('Student Project Team')).toBeInTheDocument();
    });

    const addMemberBtn = screen.getByRole('button', { name: /add member/i });
    expect(addMemberBtn).toBeInTheDocument();

    fireEvent.click(addMemberBtn);

    // Verify modal title and loading
    expect(screen.getByText('Select a registered student to add to this academic project team.')).toBeInTheDocument();

    // Verify available students are loaded and rendered
    await waitFor(() => {
      expect(screen.getByText('Aslesha')).toBeInTheDocument();
      expect(screen.getByText('aslesha1@gmail.com')).toBeInTheDocument();
      expect(screen.getByText('Rohit Sharma')).toBeInTheDocument();
      expect(screen.getByText('rohit@college.edu')).toBeInTheDocument();
    });
  });

  it('filters available students by search term (name or email)', async () => {
    renderDashboard(mockOwner);

    await waitFor(() => {
      expect(screen.getByText('Student Project Team')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /add member/i }));

    await waitFor(() => {
      expect(screen.getByText('Aslesha')).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/search by student name or email/i);
    fireEvent.change(searchInput, { target: { value: 'aslesha' } });

    // Aslesha should remain visible, Rohit should be filtered out
    expect(screen.getByText('Aslesha')).toBeInTheDocument();
    expect(screen.queryByText('Rohit Sharma')).not.toBeInTheDocument();

    // Clear search
    fireEvent.change(searchInput, { target: { value: 'nonexistent-student' } });
    expect(screen.getByText(/no students matching "nonexistent-student" found/i)).toBeInTheDocument();
  });

  it('submits student selection with UUID and chosen role to backend', async () => {
    renderDashboard(mockOwner);

    await waitFor(() => {
      expect(screen.getByText('Student Project Team')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /add member/i }));

    await waitFor(() => {
      expect(screen.getByText('Aslesha')).toBeInTheDocument();
    });

    // Select Aslesha
    const asleshaRadio = screen.getByDisplayValue('student-aslesha-uuid');
    fireEvent.click(asleshaRadio);

    // Choose role Researcher
    const roleSelect = screen.getByRole('combobox');
    fireEvent.change(roleSelect, { target: { value: 'researcher' } });

    // Submit form
    const submitBtn = screen.getByRole('button', { name: /add student/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(api.projects.addMember).toHaveBeenCalledWith('proj-123', {
        user_id: 'student-aslesha-uuid',
        team_role: 'researcher',
      });
    });
  });

  it('does not display Add Member button for non-owners', async () => {
    renderDashboard(mockNonOwner);

    await waitFor(() => {
      expect(screen.getByText('Student Project Team')).toBeInTheDocument();
    });

    expect(screen.queryByRole('button', { name: /add member/i })).not.toBeInTheDocument();
  });

  it('displays empty state when no students are available', async () => {
    vi.spyOn(api.projects, 'listAvailableStudents').mockResolvedValue([]);
    renderDashboard(mockOwner);

    await waitFor(() => {
      expect(screen.getByText('Student Project Team')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /add member/i }));

    await waitFor(() => {
      expect(screen.getByText('No Available Students')).toBeInTheDocument();
    });
  });
});
