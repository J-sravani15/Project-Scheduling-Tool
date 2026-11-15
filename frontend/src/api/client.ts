import {
  User,
  UserSummary,
  AcademicProject,
  AcademicProjectCreate,
  AcademicProjectUpdate,
  ProjectMember,
  AcademicMilestone,
  AcademicMilestoneCreate,
  Task,
  TaskCreate,
  TaskUpdate,
  TaskAssignment,
  ProjectReview,
  ProjectReviewCreate,
  ProjectReviewUpdate,
  TeamWorkloadResponse,
  ReviewReadinessResponse,
  CpmCalculationResponse,
  PriorityScheduleResponse,
  PertAnalysisResponse,
  FacultyProjectOverview,
  TaskStatus,
  MilestoneStatus,
  ProjectNotification,
  NotificationListResponse,
} from '../types';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
const TOKEN_KEY = 'scheduler_access_token';

export class ApiError extends Error {
  status: number;
  detail: any;

  constructor(status: number, message: string, detail?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

export const getToken = (): string | null => {
  return localStorage.getItem(TOKEN_KEY);
};

export const setToken = (token: string | null): void => {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
};

let unauthorizedHandler: (() => void) | null = null;
export const onUnauthorized = (callback: () => void) => {
  unauthorizedHandler = callback;
};

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const url = `${BASE_URL}${endpoint}`;
  let response: Response;

  try {
    response = await fetch(url, {
      ...options,
      headers,
    });
  } catch (err: any) {
    throw new ApiError(0, 'Unable to connect to the scheduling backend server. Please verify the backend is running.', err);
  }

  if (response.status === 204) {
    return null as unknown as T;
  }

  let responseData: any = null;
  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    try {
      responseData = await response.json();
    } catch {
      responseData = null;
    }
  }

  if (!response.ok) {
    if (response.status === 401 && unauthorizedHandler) {
      unauthorizedHandler();
    }

    let errorMessage = `HTTP Error ${response.status}`;
    if (responseData && responseData.detail) {
      if (typeof responseData.detail === 'string') {
        errorMessage = responseData.detail;
      } else if (Array.isArray(responseData.detail)) {
        errorMessage = responseData.detail.map((e: any) => `${e.loc?.slice(-1)[0] || 'field'}: ${e.msg}`).join(', ');
      }
    }
    throw new ApiError(response.status, errorMessage, responseData);
  }

  return responseData as T;
}

export const api = {
  auth: {
    register: (data: {
      email: string;
      password: string;
      full_name: string;
      role: string;
      department?: string;
      student_roll_number?: string;
      faculty_employee_id?: string;
    }) => request<User>('/auth/register', { method: 'POST', body: JSON.stringify(data) }),

    login: async (email: string, password: string): Promise<{ access_token: string; token_type: string }> => {
      const res = await request<{ access_token: string; token_type: string }>('/auth/login/json', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      });
      setToken(res.access_token);
      return res;
    },

    me: () => request<User>('/auth/me'),

    logout: () => {
      setToken(null);
    },
  },

  projects: {
    list: () => request<AcademicProject[]>('/projects'),

    get: (id: string) => request<AcademicProject>(`/projects/${id}`),

    create: (data: AcademicProjectCreate) =>
      request<AcademicProject>('/projects', { method: 'POST', body: JSON.stringify(data) }),

    update: (id: string, data: AcademicProjectUpdate) =>
      request<AcademicProject>(`/projects/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

    assignFacultyGuide: (projectId: string, facultyGuideId: string) =>
      request<AcademicProject>(`/projects/${projectId}/faculty-guide`, {
        method: 'PUT',
        body: JSON.stringify({ faculty_guide_id: facultyGuideId }),
      }),

    archive: (id: string) =>
      request<AcademicProject>(`/projects/${id}/archive`, { method: 'POST' }),

    delete: (id: string) =>
      request<void>(`/projects/${id}`, { method: 'DELETE' }),

    addMember: (projectId: string, data: { user_id: string; team_role: string }) =>
      request<ProjectMember>(`/projects/${projectId}/members`, { method: 'POST', body: JSON.stringify(data) }),

    updateMemberRole: (projectId: string, userId: string, role: string) =>
      request<ProjectMember>(`/projects/${projectId}/members/${userId}`, {
        method: 'PUT',
        body: JSON.stringify({ team_role: role }),
      }),

    removeMember: (projectId: string, userId: string) =>
      request<void>(`/projects/${projectId}/members/${userId}`, { method: 'DELETE' }),

    listMembers: (projectId: string) =>
      request<ProjectMember[]>(`/projects/${projectId}/members`),

    listAvailableStudents: (projectId: string, search?: string) => {
      const q = search ? `?search=${encodeURIComponent(search)}` : '';
      return request<UserSummary[]>(`/projects/${projectId}/available-students${q}`);
    },

    getWorkload: (projectId: string, thresholdHours: number = 25.0, referenceDate?: string) => {
      let query = `?threshold_hours=${thresholdHours}`;
      if (referenceDate) query += `&reference_date=${referenceDate}`;
      return request<TeamWorkloadResponse>(`/projects/${projectId}/workload${query}`);
    },

    getReadiness: (projectId: string, referenceDate?: string) => {
      const query = referenceDate ? `?reference_date=${referenceDate}` : '';
      return request<ReviewReadinessResponse>(`/projects/${projectId}/review-readiness${query}`);
    },
  },

  milestones: {
    list: (projectId: string) =>
      request<AcademicMilestone[]>(`/projects/${projectId}/milestones`),

    create: (projectId: string, data: AcademicMilestoneCreate) =>
      request<AcademicMilestone>(`/projects/${projectId}/milestones`, { method: 'POST', body: JSON.stringify(data) }),

    update: (id: string, data: Partial<AcademicMilestoneCreate>) =>
      request<AcademicMilestone>(`/milestones/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

    updateStatus: (id: string, status: MilestoneStatus) =>
      request<AcademicMilestone>(`/milestones/${id}/status?status_value=${status}`, { method: 'PATCH' }),

    delete: (id: string) =>
      request<void>(`/milestones/${id}`, { method: 'DELETE' }),
  },

  tasks: {
    list: (
      projectId: string,
      filters?: {
        status?: TaskStatus;
        milestone_id?: string;
        priority?: string;
        assigned_user_id?: string;
      }
    ) => {
      const params = new URLSearchParams();
      if (filters?.status) params.append('status', filters.status);
      if (filters?.milestone_id) params.append('milestone_id', filters.milestone_id);
      if (filters?.priority) params.append('priority', filters.priority);
      if (filters?.assigned_user_id) params.append('assigned_user_id', filters.assigned_user_id);
      const q = params.toString() ? `?${params.toString()}` : '';
      return request<Task[]>(`/projects/${projectId}/tasks${q}`);
    },

    get: (id: string) => request<Task>(`/tasks/${id}`),

    create: (projectId: string, data: TaskCreate) =>
      request<Task>(`/projects/${projectId}/tasks`, { method: 'POST', body: JSON.stringify(data) }),

    update: (id: string, data: TaskUpdate) =>
      request<Task>(`/tasks/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

    updateStatus: (id: string, status: TaskStatus) =>
      request<Task>(`/tasks/${id}/status?status_value=${status}`, { method: 'PATCH' }),

    delete: (id: string) =>
      request<void>(`/tasks/${id}`, { method: 'DELETE' }),

    assign: (taskId: string, userId: string) =>
      request<TaskAssignment>(`/tasks/${taskId}/assignments`, { method: 'POST', body: JSON.stringify({ user_id: userId }) }),

    unassign: (taskId: string, userId: string) =>
      request<void>(`/tasks/${taskId}/assignments/${userId}`, { method: 'DELETE' }),

    getAssignments: (taskId: string) =>
      request<TaskAssignment[]>(`/tasks/${taskId}/assignments`),

    addDependency: (taskId: string, dependsOnTaskId: string, dependencyType: string = 'finish_to_start') =>
      request(`/tasks/${taskId}/dependencies`, {
        method: 'POST',
        body: JSON.stringify({ depends_on_task_id: dependsOnTaskId, dependency_type: dependencyType }),
      }),

    removeDependency: (taskId: string, dependsOnTaskId: string) =>
      request(`/tasks/${taskId}/dependencies/${dependsOnTaskId}`, { method: 'DELETE' }),
  },

  faculty: {
    listFacultyMembers: () => request<UserSummary[]>('/faculty'),

    listProjects: () => request<AcademicProject[]>('/faculty/projects'),

    getOverview: (projectId: string) =>
      request<FacultyProjectOverview>(`/faculty/projects/${projectId}/overview`),

    scheduleReview: (projectId: string, data: ProjectReviewCreate) =>
      request<ProjectReview>(`/faculty/projects/${projectId}/reviews`, { method: 'POST', body: JSON.stringify(data) }),

    updateReview: (projectId: string, reviewId: string, data: ProjectReviewUpdate) =>
      request<ProjectReview>(`/faculty/projects/${projectId}/reviews/${reviewId}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      }),

    cancelReview: (projectId: string, reviewId: string) =>
      request<ProjectReview>(`/faculty/projects/${projectId}/reviews/${reviewId}`, {
        method: 'DELETE',
      }),
  },

  students: {
    list: (search?: string) => {
      const q = search ? `?search=${encodeURIComponent(search)}` : '';
      return request<UserSummary[]>(`/students${q}`);
    },
  },

  notifications: {
    list: (unreadOnly: boolean = false, skip: number = 0, limit: number = 50) => {
      const q = `?unread_only=${unreadOnly}&skip=${skip}&limit=${limit}`;
      return request<NotificationListResponse>(`/notifications${q}`);
    },

    markRead: (id: string) =>
      request<ProjectNotification>(`/notifications/${id}/read`, { method: 'PATCH' }),

    markAllRead: () =>
      request<{ updated_count: number; message: string }>('/notifications/mark-all-read', { method: 'POST' }),

    triggerReminders: () =>
      request<{ status: string; deadline_reminders: any; academic_alerts: any }>('/notifications/trigger-reminders', {
        method: 'POST',
      }),
  },

  scheduling: {
    calculateCpm: (projectId: string) =>
      request<CpmCalculationResponse>(`/projects/${projectId}/schedule/cpm`, { method: 'GET' }),

    calculatePriority: (
      projectId: string,
      weights?: {
        weight_priority: number;
        weight_urgency: number;
        weight_critical: number;
        weight_downstream: number;
        weight_effort: number;
      },
      referenceDate?: string
    ) => {
      let query = '';
      if (referenceDate) query += `?reference_date=${encodeURIComponent(referenceDate)}`;
      return request<PriorityScheduleResponse>(`/projects/${projectId}/schedule/priority${query}`, {
        method: 'GET',
      });
    },

    calculatePert: (
      projectId: string,
      estimates: Array<{
        task_id: string;
        optimistic_hours: number;
        most_likely_hours: number;
        pessimistic_hours: number;
      }>,
      targetDeadlineHours?: number
    ) => {
      return request<PertAnalysisResponse>(`/projects/${projectId}/schedule/pert`, {
        method: 'POST',
        body: JSON.stringify({
          estimates,
          target_deadline_hours: targetDeadlineHours,
        }),
      });
    },
  },
};
