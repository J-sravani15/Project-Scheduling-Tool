import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { NotificationBell } from '../components/common/NotificationBell';
import { api } from '../api/client';
import { ProjectNotification } from '../types';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe('NotificationBell & Notification Center', () => {
  const mockNotifications: ProjectNotification[] = [
    {
      id: 'notif-1',
      recipient_id: 'user-123',
      project_id: 'proj-123',
      task_id: 'task-101',
      link_url: '/projects/proj-123?taskId=task-101',
      notification_type: 'task_assigned',
      title: 'Task Assigned: Implement Core Model',
      message: 'You have been assigned to task "Implement Core Model" by Dr. Janardhan. Due: 2026-03-25.',
      read_at: null,
      created_at: new Date(Date.now() - 1000 * 60 * 15).toISOString(), // 15 mins ago
    },
    {
      id: 'notif-2',
      recipient_id: 'user-123',
      project_id: 'proj-123',
      task_id: 'task-102',
      link_url: '/projects/proj-123?taskId=task-102',
      notification_type: 'due_date_reminder',
      title: 'Reminder: Task Due in 24 Hours',
      message: 'Task "Literature Review" is due tomorrow (2026-03-26).',
      read_at: null,
      created_at: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(), // 2 hours ago
    },
    {
      id: 'notif-3',
      recipient_id: 'user-123',
      project_id: 'proj-123',
      task_id: 'task-103',
      link_url: '/projects/proj-123?taskId=task-103',
      notification_type: 'overdue_task',
      title: 'OVERDUE: Task "System Design"',
      message: 'Task was due yesterday and is currently overdue.',
      read_at: '2026-03-20T10:00:00Z', // already read
      created_at: new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString(), // 1 day ago
    },
  ];

  beforeEach(() => {
    vi.restoreAllMocks();
    mockNavigate.mockReset();

    vi.spyOn(api.notifications, 'list').mockResolvedValue({
      items: mockNotifications,
      unread_count: 2,
      total_count: 3,
    });

    vi.spyOn(api.notifications, 'markRead').mockImplementation(async (id: string) => {
      const found = mockNotifications.find((n) => n.id === id);
      return {
        ...(found || mockNotifications[0]),
        read_at: new Date().toISOString(),
      };
    });

    vi.spyOn(api.notifications, 'markAllRead').mockResolvedValue({
      updated_count: 2,
      message: '2 notifications marked as read.',
    });
  });

  const renderComponent = () => {
    return render(
      <MemoryRouter>
        <NotificationBell />
      </MemoryRouter>
    );
  };

  it('renders notification bell with unread count badge', async () => {
    renderComponent();

    const bellBtn = screen.getByRole('button', { name: /view notifications/i });
    expect(bellBtn).toBeInTheDocument();

    await waitFor(() => {
      const badge = screen.getByTestId('unread-count-badge');
      expect(badge).toHaveTextContent('2');
    });
  });

  it('opens notification dropdown on click and displays notification items', async () => {
    renderComponent();

    const bellBtn = screen.getByRole('button', { name: /view notifications/i });
    fireEvent.click(bellBtn);

    await waitFor(() => {
      expect(screen.getByTestId('notification-dropdown')).toBeInTheDocument();
      expect(screen.getByText('Notifications')).toBeInTheDocument();
      expect(screen.getByText(/2 unread/i)).toBeInTheDocument();
      expect(screen.getByText('Task Assigned: Implement Core Model')).toBeInTheDocument();
      expect(screen.getByText('Reminder: Task Due in 24 Hours')).toBeInTheDocument();
      expect(screen.getByText('OVERDUE: Task "System Design"')).toBeInTheDocument();
    });
  });

  it('filters notifications between All and Unread', async () => {
    renderComponent();

    fireEvent.click(screen.getByRole('button', { name: /view notifications/i }));

    await waitFor(() => {
      expect(screen.getByText('Task Assigned: Implement Core Model')).toBeInTheDocument();
    });

    // Switch to Unread tab
    const unreadTab = screen.getByRole('button', { name: /unread \(2\)/i });
    fireEvent.click(unreadTab);

    // Overdue task (which is already read) should be filtered out
    expect(screen.getByText('Task Assigned: Implement Core Model')).toBeInTheDocument();
    expect(screen.getByText('Reminder: Task Due in 24 Hours')).toBeInTheDocument();
    expect(screen.queryByText('OVERDUE: Task "System Design"')).not.toBeInTheDocument();

    // Switch back to All tab
    const allTab = screen.getByRole('button', { name: /all \(3\)/i });
    fireEvent.click(allTab);
    expect(screen.getByText('OVERDUE: Task "System Design"')).toBeInTheDocument();
  });

  it('marks all notifications as read when clicking "Mark all read"', async () => {
    renderComponent();

    fireEvent.click(screen.getByRole('button', { name: /view notifications/i }));

    await waitFor(() => {
      expect(screen.getByText(/mark all read/i)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText(/mark all read/i));

    await waitFor(() => {
      expect(api.notifications.markAllRead).toHaveBeenCalled();
      // Badge should disappear or count should become 0
      expect(screen.queryByTestId('unread-count-badge')).not.toBeInTheDocument();
    });
  });

  it('clicking an unread notification marks it as read and navigates to target link', async () => {
    renderComponent();

    fireEvent.click(screen.getByRole('button', { name: /view notifications/i }));

    await waitFor(() => {
      expect(screen.getByText('Task Assigned: Implement Core Model')).toBeInTheDocument();
    });

    const item = screen.getByText('Task Assigned: Implement Core Model').closest('div[class*="cursor-pointer"]');
    expect(item).not.toBeNull();
    fireEvent.click(item!);

    await waitFor(() => {
      expect(api.notifications.markRead).toHaveBeenCalledWith('notif-1');
      expect(mockNavigate).toHaveBeenCalledWith('/projects/proj-123?taskId=task-101');
    });
  });

  it('displays friendly empty state when there are no unread notifications', async () => {
    vi.spyOn(api.notifications, 'list').mockResolvedValue({
      items: [mockNotifications[2]], // only read notification
      unread_count: 0,
      total_count: 1,
    });

    renderComponent();

    fireEvent.click(screen.getByRole('button', { name: /view notifications/i }));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /unread \(0\)/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /unread \(0\)/i }));

    expect(screen.getByText("You're all caught up!")).toBeInTheDocument();
    expect(screen.getByText(/there are no unread deadline reminders or alerts/i)).toBeInTheDocument();
  });
});
