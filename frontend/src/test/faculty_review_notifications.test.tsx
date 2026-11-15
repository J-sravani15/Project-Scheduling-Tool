import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { FacultyDashboardPage } from '../pages/faculty/FacultyDashboardPage';
import { NotificationBell } from '../components/common/NotificationBell';
import { api } from '../api/client';
import {
  AcademicProject,
  FacultyProjectOverview,
  ProjectNotification,
  ProjectReview,
} from '../types';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe('Faculty Review Scheduling & Student Notifications', () => {
  const mockProject: AcademicProject = {
    id: 'proj-academic-101',
    title: 'AI Smart Academic Scheduler',
    description: 'Capstone project for automated academic scheduling and CPM/PERT analysis.',
    department: 'Computer Science',
    academic_year: '2026-2027',
    semester: 8,
    project_type: 'capstone',
    status: 'in_progress',
    owner_id: 'student-owner-1',
    faculty_guide_id: 'faculty-janardhan',
    start_date: '2026-01-10',
    target_deadline: '2026-05-30',
    created_at: '2026-01-10T09:00:00Z',
    updated_at: '2026-01-10T09:00:00Z',
    owner: {
      id: 'student-owner-1',
      full_name: 'Aslesha Student',
      email: 'aslesha@example.edu',
      role: 'student',
      department: 'Computer Science',
    },
  };

  const mockReviews: ProjectReview[] = [
    {
      id: 'rev-001',
      project_id: 'proj-academic-101',
      faculty_id: 'faculty-janardhan',
      review_number: 1,
      scheduled_at: '2026-03-25T10:00:00Z',
      status: 'scheduled',
      feedback: 'Initial progress evaluation on architecture and data models.',
      score: null,
      created_at: '2026-03-01T10:00:00Z',
    },
  ];

  const mockOverview: FacultyProjectOverview = {
    project: mockProject,
    workload: {
      project_id: 'proj-academic-101',
      threshold_hours: 20,
      reference_date: '2026-03-20T00:00:00Z',
      student_workloads: [
        {
          user_id: 'student-owner-1',
          full_name: 'Aslesha Student',
          email: 'aslesha@example.edu',
          team_role: 'lead',
          total_active_hours: 15,
          completed_hours: 10,
          assigned_task_count: 3,
          overdue_task_count: 0,
          upcoming_task_count: 2,
          completed_task_count: 1,
          is_overloaded: false,
          is_underutilized: false,
        },
      ],
      total_team_active_hours: 15,
      average_hours_per_student: 15,
      workload_standard_deviation: 0,
      overloaded_students: [],
      underutilized_students: [],
      recommendations: [],
    },
    readiness: {
      project_id: 'proj-academic-101',
      readiness_score: 85,
      readiness_level: 'High Readiness',
      score_breakdown: {
        milestone_score: 30,
        task_completion_score: 25,
        critical_path_score: 15,
        overdue_score: 10,
        review_timing_score: 5,
        total_score: 85,
      },
      blockers: [],
      actionable_recommendations: [],
    },
    reviews: mockReviews,
  };

  beforeEach(() => {
    vi.restoreAllMocks();
    mockNavigate.mockReset();

    vi.spyOn(api.faculty, 'listProjects').mockResolvedValue([mockProject]);
    vi.spyOn(api.faculty, 'getOverview').mockResolvedValue(mockOverview);
    vi.spyOn(api.faculty, 'scheduleReview').mockImplementation(async (_projId, data) => ({
      id: 'rev-002',
      project_id: 'proj-academic-101',
      faculty_id: 'faculty-janardhan',
      review_number: data.review_number,
      scheduled_at: data.scheduled_at,
      status: data.status || 'scheduled',
      feedback: data.feedback || null,
      score: data.score ?? null,
      created_at: new Date().toISOString(),
    }));
    vi.spyOn(api.faculty, 'updateReview').mockImplementation(async (_projId, reviewId, data) => ({
      ...mockReviews[0],
      id: reviewId,
      scheduled_at: data.scheduled_at || mockReviews[0].scheduled_at,
      status: data.status || mockReviews[0].status,
      feedback: data.feedback !== undefined ? data.feedback : mockReviews[0].feedback,
      score: data.score !== undefined ? data.score : mockReviews[0].score,
    }));
    vi.spyOn(api.faculty, 'cancelReview').mockImplementation(async (_projId, reviewId) => ({
      ...mockReviews[0],
      id: reviewId,
      status: 'cancelled',
    }));
  });

  it('renders faculty dashboard with existing review and action buttons', async () => {
    render(
      <MemoryRouter>
        <FacultyDashboardPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getAllByText('AI Smart Academic Scheduler').length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText('Review 1')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /reschedule \/ edit/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
    });
  });

  it('opens reschedule modal and submits updated review timing', async () => {
    render(
      <MemoryRouter>
        <FacultyDashboardPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Review 1')).toBeInTheDocument();
    });

    const editBtn = screen.getByRole('button', { name: /reschedule \/ edit/i });
    fireEvent.click(editBtn);

    expect(screen.getByText('Reschedule / Edit Review 1')).toBeInTheDocument();

    const submitBtn = screen.getByRole('button', { name: /update review/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(api.faculty.updateReview).toHaveBeenCalledWith(
        'proj-academic-101',
        'rev-001',
        expect.objectContaining({
          status: 'scheduled',
        })
      );
    });
  });

  it('cancels review with user confirmation and notifies students via backend', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true);

    render(
      <MemoryRouter>
        <FacultyDashboardPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Review 1')).toBeInTheDocument();
    });

    const cancelBtn = screen.getByRole('button', { name: /cancel/i });
    fireEvent.click(cancelBtn);

    expect(window.confirm).toHaveBeenCalledWith(
      expect.stringContaining('Are you sure you want to cancel Review 1?')
    );

    await waitFor(() => {
      expect(api.faculty.cancelReview).toHaveBeenCalledWith('proj-academic-101', 'rev-001');
    });
  });

  it('renders student notification bell with review reminder badge and message details', async () => {
    const mockStudentNotif: ProjectNotification = {
      id: 'notif-rev-1',
      recipient_id: 'student-owner-1',
      project_id: 'proj-academic-101',
      task_id: null,
      link_url: '/projects/proj-academic-101',
      notification_type: 'review_reminder',
      title: 'Academic Review Scheduled: AI Smart Academic Scheduler',
      message: 'Dr. Janardhan has scheduled Review 1 on 2026-03-25 10:00 UTC for project "AI Smart Academic Scheduler".',
      read_at: null,
      created_at: new Date(Date.now() - 1000 * 60 * 5).toISOString(),
    };

    vi.spyOn(api.notifications, 'list').mockResolvedValue({
      items: [mockStudentNotif],
      unread_count: 1,
      total_count: 1,
    });
    vi.spyOn(api.notifications, 'markRead').mockResolvedValue({
      ...mockStudentNotif,
      read_at: new Date().toISOString(),
    });

    render(
      <MemoryRouter>
        <NotificationBell />
      </MemoryRouter>
    );

    await waitFor(() => {
      const badge = screen.getByTestId('unread-count-badge');
      expect(badge).toHaveTextContent('1');
    });

    const bellBtn = screen.getByRole('button', { name: /view notifications/i });
    fireEvent.click(bellBtn);

    await waitFor(() => {
      expect(screen.getByText('Academic Review Scheduled: AI Smart Academic Scheduler')).toBeInTheDocument();
      expect(screen.getByText(/Dr\. Janardhan has scheduled Review 1/i)).toBeInTheDocument();
      expect(screen.getByText('Review')).toBeInTheDocument(); // Badge
    });

    // Clicking notification navigates to the project
    const notifItem = screen.getByText('Academic Review Scheduled: AI Smart Academic Scheduler');
    fireEvent.click(notifItem);

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/projects/proj-academic-101');
    });
  });
});
