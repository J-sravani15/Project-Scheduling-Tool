import React, { useState, useEffect, useRef, useTransition } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Bell,
  Check,
  CheckCheck,
  Clock,
  AlertTriangle,
  UserPlus,
  Compass,
  Award,
  ShieldAlert,
  Inbox,
  ExternalLink,
} from 'lucide-react';
import { api } from '../../api/client';
import { ProjectNotification, NotificationType } from '../../types';
import { LoadingSpinner } from './LoadingSpinner';

const getNotificationIcon = (type: NotificationType) => {
  switch (type) {
    case 'task_assigned':
      return {
        icon: UserPlus,
        bgColor: 'bg-indigo-50 text-indigo-600 border-indigo-100',
        badge: 'Assignment',
      };
    case 'due_date_reminder':
      return {
        icon: Clock,
        bgColor: 'bg-amber-50 text-amber-600 border-amber-100',
        badge: 'Reminder',
      };
    case 'overdue_task':
      return {
        icon: AlertTriangle,
        bgColor: 'bg-rose-50 text-rose-600 border-rose-100',
        badge: 'Overdue',
      };
    case 'milestone_reminder':
      return {
        icon: Compass,
        bgColor: 'bg-violet-50 text-violet-600 border-violet-100',
        badge: 'Milestone',
      };
    case 'review_reminder':
      return {
        icon: Award,
        bgColor: 'bg-emerald-50 text-emerald-600 border-emerald-100',
        badge: 'Review',
      };
    case 'critical_path_alert':
      return {
        icon: ShieldAlert,
        bgColor: 'bg-red-50 text-red-600 border-red-100',
        badge: 'Critical Path',
      };
    default:
      return {
        icon: Bell,
        bgColor: 'bg-slate-50 text-slate-600 border-slate-100',
        badge: 'Notice',
      };
  }
};

const formatTimeAgo = (dateStr: string) => {
  try {
    const date = new Date(dateStr);
    const now = new Date();
    const diffSec = Math.floor((now.getTime() - date.getTime()) / 1000);

    if (diffSec < 60) return 'Just now';
    const diffMin = Math.floor(diffSec / 60);
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHr = Math.floor(diffMin / 60);
    if (diffHr < 24) return `${diffHr}h ago`;
    const diffDays = Math.floor(diffHr / 24);
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  } catch {
    return dateStr;
  }
};

export const NotificationBell: React.FC = () => {
  const navigate = useNavigate();
  const [isOpen, setIsOpen] = useState(false);
  const [notifications, setNotifications] = useState<ProjectNotification[]>([]);
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | 'unread'>('all');
  const [, startTransition] = useTransition();

  const containerRef = useRef<HTMLDivElement>(null);

  const fetchNotifications = async (showLoading = false) => {
    if (showLoading) setIsLoading(true);
    setError(null);
    try {
      const res = await api.notifications.list(false, 0, 50);
      setNotifications(res.items);
      setUnreadCount(res.unread_count);
      setTotalCount(res.total_count);
    } catch (err: any) {
      setError(err.message || 'Failed to load notifications.');
    } finally {
      if (showLoading) setIsLoading(false);
    }
  };

  // Initial load and periodic poll every 30 seconds
  useEffect(() => {
    fetchNotifications(true);
    const interval = setInterval(() => {
      fetchNotifications(false);
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  // Close on outside click
  useEffect(() => {
    const handleOutsideClick = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleOutsideClick);
    }
    return () => document.removeEventListener('mousedown', handleOutsideClick);
  }, [isOpen]);

  const handleToggle = () => {
    const nextState = !isOpen;
    setIsOpen(nextState);
    if (nextState) {
      fetchNotifications(true);
    }
  };

  const handleMarkAsRead = async (e: React.MouseEvent, notif: ProjectNotification) => {
    e.stopPropagation();
    if (notif.read_at) return;
    try {
      const updated = await api.notifications.markRead(notif.id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === notif.id ? updated : n))
      );
      setUnreadCount((c) => Math.max(0, c - 1));
    } catch (err) {
      console.error('Failed to mark notification as read:', err);
    }
  };

  const handleMarkAllAsRead = async () => {
    try {
      await api.notifications.markAllRead();
      const nowIso = new Date().toISOString();
      setNotifications((prev) =>
        prev.map((n) => ({ ...n, read_at: n.read_at || nowIso }))
      );
      setUnreadCount(0);
    } catch (err) {
      console.error('Failed to mark all as read:', err);
    }
  };

  const handleNotificationClick = async (notif: ProjectNotification) => {
    if (!notif.read_at) {
      try {
        await api.notifications.markRead(notif.id);
        setNotifications((prev) =>
          prev.map((n) => (n.id === notif.id ? { ...n, read_at: new Date().toISOString() } : n))
        );
        setUnreadCount((c) => Math.max(0, c - 1));
      } catch (err) {
        console.error('Failed to mark read on click:', err);
      }
    }
    setIsOpen(false);

    // Navigate to link_url or project
    if (notif.link_url) {
      startTransition(() => {
        navigate(notif.link_url!);
      });
    } else if (notif.project_id) {
      startTransition(() => {
        navigate(`/projects/${notif.project_id}`);
      });
    }
  };

  const displayedNotifications =
    filter === 'unread' ? notifications.filter((n) => !n.read_at) : notifications;

  return (
    <div className="relative" ref={containerRef}>
      {/* Bell Button */}
      <button
        onClick={handleToggle}
        aria-label="View notifications"
        aria-expanded={isOpen}
        className={`relative p-2 rounded-xl transition-all cursor-pointer ${
          isOpen
            ? 'bg-indigo-50 text-indigo-700 shadow-2xs'
            : 'text-slate-500 hover:text-slate-800 hover:bg-slate-100'
        }`}
      >
        <Bell className="w-5 h-5" />
        {unreadCount > 0 && (
          <span
            data-testid="unread-count-badge"
            className="absolute -top-0.5 -right-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-rose-600 px-1 text-[10px] font-bold text-white shadow-2xs ring-2 ring-white animate-in zoom-in"
          >
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown Panel */}
      {isOpen && (
        <div
          data-testid="notification-dropdown"
          className="absolute right-0 mt-2 w-80 sm:w-96 rounded-2xl bg-white shadow-xl border border-slate-200/90 z-50 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-150"
        >
          {/* Header */}
          <div className="p-4 border-b border-slate-100 bg-slate-50/70">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-slate-800 text-sm">Notifications</h3>
                {unreadCount > 0 && (
                  <span className="text-[11px] font-semibold bg-rose-50 text-rose-700 border border-rose-100 px-2 py-0.5 rounded-full">
                    {unreadCount} unread
                  </span>
                )}
              </div>

              {unreadCount > 0 && (
                <button
                  onClick={handleMarkAllAsRead}
                  className="inline-flex items-center gap-1 text-[11px] font-semibold text-indigo-600 hover:text-indigo-800 transition-colors cursor-pointer"
                >
                  <CheckCheck className="w-3.5 h-3.5" />
                  <span>Mark all read</span>
                </button>
              )}
            </div>

            {/* Filter Tabs */}
            <div className="flex gap-2 mt-3">
              <button
                onClick={() => setFilter('all')}
                className={`text-xs px-2.5 py-1 rounded-lg font-medium transition-colors cursor-pointer ${
                  filter === 'all'
                    ? 'bg-indigo-600 text-white shadow-2xs font-semibold'
                    : 'text-slate-600 hover:bg-slate-200/60'
                }`}
              >
                All ({totalCount})
              </button>
              <button
                onClick={() => setFilter('unread')}
                className={`text-xs px-2.5 py-1 rounded-lg font-medium transition-colors cursor-pointer ${
                  filter === 'unread'
                    ? 'bg-indigo-600 text-white shadow-2xs font-semibold'
                    : 'text-slate-600 hover:bg-slate-200/60'
                }`}
              >
                Unread ({unreadCount})
              </button>
            </div>
          </div>

          {/* Notification List Container */}
          <div className="max-h-[380px] overflow-y-auto divide-y divide-slate-100">
            {isLoading ? (
              <div className="py-12 flex justify-center">
                <LoadingSpinner size="md" label="Loading alerts..." />
              </div>
            ) : error ? (
              <div className="p-6 text-center">
                <p className="text-xs text-rose-600 mb-2">{error}</p>
                <button
                  onClick={() => fetchNotifications(true)}
                  className="text-xs font-semibold text-indigo-600 hover:underline cursor-pointer"
                >
                  Try again
                </button>
              </div>
            ) : displayedNotifications.length === 0 ? (
              <div className="py-12 px-6 text-center">
                <div className="w-10 h-10 rounded-full bg-slate-100 text-slate-400 mx-auto flex items-center justify-center mb-2">
                  <Inbox className="w-5 h-5" />
                </div>
                <p className="text-sm font-semibold text-slate-700">
                  {filter === 'unread' ? "You're all caught up!" : 'No notifications yet'}
                </p>
                <p className="text-xs text-slate-400 mt-0.5">
                  {filter === 'unread'
                    ? 'There are no unread deadline reminders or alerts.'
                    : 'Task assignments and academic alerts will appear here.'}
                </p>
              </div>
            ) : (
              displayedNotifications.map((notif) => {
                const { icon: Icon, bgColor, badge } = getNotificationIcon(notif.notification_type);
                const isUnread = !notif.read_at;

                return (
                  <div
                    key={notif.id}
                    onClick={() => handleNotificationClick(notif)}
                    className={`p-3.5 flex items-start gap-3 transition-colors cursor-pointer group ${
                      isUnread
                        ? 'bg-indigo-50/40 hover:bg-indigo-50/70'
                        : 'bg-white hover:bg-slate-50'
                    }`}
                  >
                    {/* Notification Type Icon */}
                    <div
                      className={`w-8 h-8 rounded-xl border flex items-center justify-center shrink-0 mt-0.5 ${bgColor}`}
                    >
                      <Icon className="w-4 h-4" />
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-1.5 mb-0.5">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                          {badge}
                        </span>
                        <span className="text-[11px] text-slate-400 shrink-0">
                          {formatTimeAgo(notif.created_at)}
                        </span>
                      </div>

                      <h4
                        className={`text-xs leading-snug line-clamp-1 ${
                          isUnread ? 'font-bold text-slate-900' : 'font-medium text-slate-700'
                        }`}
                      >
                        {notif.title}
                      </h4>

                      <p className="text-[11px] text-slate-500 line-clamp-2 mt-0.5 leading-relaxed">
                        {notif.message}
                      </p>

                      {notif.link_url && (
                        <span className="inline-flex items-center gap-1 text-[10px] text-indigo-600 font-semibold mt-1 group-hover:underline">
                          <span>View details</span>
                          <ExternalLink className="w-2.5 h-2.5" />
                        </span>
                      )}
                    </div>

                    {/* Read Action / Indicator */}
                    <div className="flex items-center gap-1 shrink-0 self-center">
                      {isUnread && (
                        <>
                          <span
                            title="Unread notification"
                            className="w-2 h-2 rounded-full bg-indigo-600 shrink-0 group-hover:hidden"
                          />
                          <button
                            type="button"
                            onClick={(e) => handleMarkAsRead(e, notif)}
                            title="Mark as read"
                            className="hidden group-hover:inline-flex p-1 rounded-md text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 transition-colors"
                          >
                            <Check className="w-3.5 h-3.5" />
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
};
