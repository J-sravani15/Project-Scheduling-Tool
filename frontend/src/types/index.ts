export type UserRole = 'student' | 'faculty';

export type ProjectStatus = 'planning' | 'in_progress' | 'submitted' | 'completed' | 'archived';

export type ProjectType = 'capstone' | 'major' | 'minor' | 'research';

export type TeamRole = 'leader' | 'member' | 'researcher' | 'developer' | 'tester' | 'documentation';

export type MilestoneType =
  | 'topic_selection'
  | 'problem_statement'
  | 'literature_review'
  | 'project_proposal'
  | 'requirement_analysis'
  | 'system_design'
  | 'implementation'
  | 'review_1'
  | 'testing'
  | 'review_2'
  | 'documentation'
  | 'final_presentation'
  | 'viva'
  | 'custom';

export type MilestoneStatus = 'pending' | 'in_progress' | 'completed' | 'delayed';

export type TaskPriority = 'low' | 'medium' | 'high' | 'critical';

export type TaskStatus = 'todo' | 'in_progress' | 'blocked' | 'completed';

export type DependencyType = 'finish_to_start';

export type ReviewStatus = 'scheduled' | 'in_progress' | 'completed' | 'cancelled';

export interface UserSummary {
  id: string;
  full_name: string;
  email: string;
  role: UserRole;
  department?: string | null;
}

export interface User extends UserSummary {
  student_roll_number?: string | null;
  faculty_employee_id?: string | null;
  is_active: boolean;
  created_at: string;
}

export interface AcademicProject {
  id: string;
  title: string;
  description?: string | null;
  academic_year: string;
  semester: number;
  department: string;
  project_type: ProjectType;
  status: ProjectStatus;
  start_date: string;
  target_deadline: string;
  actual_completion_date?: string | null;
  owner_id: string;
  faculty_guide_id?: string | null;
  created_at: string;
  updated_at: string;
  owner?: UserSummary | null;
  faculty_guide?: UserSummary | null;
}

export interface AcademicProjectCreate {
  title: string;
  description?: string;
  academic_year: string;
  semester: number;
  department: string;
  project_type?: ProjectType;
  status?: ProjectStatus;
  start_date: string;
  target_deadline: string;
  faculty_guide_id?: string | null;
}

export interface AcademicProjectUpdate {
  title?: string;
  description?: string;
  academic_year?: string;
  semester?: number;
  department?: string;
  project_type?: ProjectType;
  status?: ProjectStatus;
  start_date?: string;
  target_deadline?: string;
  faculty_guide_id?: string | null;
}

export interface ProjectMember {
  id: string;
  project_id: string;
  user_id: string;
  team_role: TeamRole;
  joined_at: string;
  user?: UserSummary | null;
}

export interface AcademicMilestone {
  id: string;
  project_id: string;
  title: string;
  description?: string | null;
  milestone_type: MilestoneType;
  sequence_number: number;
  planned_date: string;
  completed_at?: string | null;
  status: MilestoneStatus;
  is_required: boolean;
  created_at: string;
}

export interface AcademicMilestoneCreate {
  title: string;
  description?: string;
  milestone_type?: MilestoneType;
  sequence_number: number;
  planned_date: string;
  status?: MilestoneStatus;
  is_required?: boolean;
}

export interface TaskAssignment {
  id: string;
  task_id: string;
  user_id: string;
  assigned_at: string;
  assigned_by_id?: string | null;
  user?: UserSummary | null;
}

export interface TaskDependency {
  id: string;
  task_id: string;
  depends_on_task_id: string;
  dependency_type: DependencyType;
  created_at: string;
}

export interface Task {
  id: string;
  project_id: string;
  milestone_id?: string | null;
  title: string;
  description?: string | null;
  status: TaskStatus;
  priority: TaskPriority;
  estimated_duration_hours: number;
  actual_duration_hours?: number | null;
  start_date?: string | null;
  due_date: string;
  completed_at?: string | null;
  created_by_id?: string | null;
  created_at: string;
  updated_at: string;
  assignments?: TaskAssignment[];
  dependencies?: TaskDependency[];
}

export interface TaskCreate {
  title: string;
  description?: string;
  milestone_id?: string | null;
  status?: TaskStatus;
  priority?: TaskPriority;
  estimated_duration_hours: number;
  actual_duration_hours?: number;
  start_date?: string | null;
  due_date: string;
}

export interface TaskUpdate {
  title?: string;
  description?: string;
  milestone_id?: string | null;
  status?: TaskStatus;
  priority?: TaskPriority;
  estimated_duration_hours?: number;
  actual_duration_hours?: number;
  start_date?: string | null;
  due_date?: string;
}

export interface ProjectReview {
  id: string;
  project_id: string;
  faculty_id: string;
  review_number: number;
  scheduled_at: string;
  completed_at?: string | null;
  status: ReviewStatus;
  feedback?: string | null;
  score?: number | null;
  created_at: string;
  faculty?: UserSummary | null;
}

export interface ProjectReviewCreate {
  review_number: number;
  scheduled_at: string;
  status?: ReviewStatus;
  feedback?: string;
  score?: number;
  faculty_id?: string;
}

export interface ProjectReviewUpdate {
  scheduled_at?: string;
  completed_at?: string | null;
  status?: ReviewStatus;
  feedback?: string | null;
  score?: number | null;
}

// Workload Analytics
export interface StudentWorkloadSummary {
  user_id: string;
  full_name: string;
  email: string;
  team_role: string;
  total_active_hours: number;
  completed_hours: number;
  assigned_task_count: number;
  overdue_task_count: number;
  upcoming_task_count: number;
  completed_task_count: number;
  is_overloaded: boolean;
  is_underutilized: boolean;
}

export interface TeamWorkloadResponse {
  project_id: string;
  threshold_hours: number;
  reference_date: string;
  total_team_active_hours: number;
  average_hours_per_student: number;
  workload_standard_deviation: number;
  student_workloads: StudentWorkloadSummary[];
  overloaded_students: string[];
  underutilized_students: string[];
  recommendations: string[];
}

// Review Readiness
export interface ReadinessBreakdown {
  milestone_score: number;
  task_completion_score: number;
  critical_path_score: number;
  overdue_score: number;
  review_timing_score: number;
  total_score: number;
}

export interface ReviewReadinessResponse {
  project_id: string;
  readiness_score: number;
  readiness_level: string;
  score_breakdown: ReadinessBreakdown;
  blockers: string[];
  actionable_recommendations: string[];
  next_review_scheduled_at?: string | null;
}

// Scheduling Algorithms Output
export interface CpmTaskOutput {
  id: string;
  title: string;
  duration: number;
  early_start: number;
  early_finish: number;
  late_start: number;
  late_finish: number;
  slack: number;
  is_critical: boolean;
}

export interface CpmCalculationResponse {
  project_id: string;
  critical_tasks: string[];
  critical_paths?: string[][];
  total_project_duration_hours: number;
  tasks: Record<string, CpmTaskOutput>;
  warnings?: string[];
  // Backwards-compatible alias:
  critical_path_task_ids?: string[];
}

export interface ScoreBreakdown {
  priority_norm: number;
  urgency_norm: number;
  critical_norm: number;
  downstream_norm: number;
  effort_norm: number;
  weighted_total: number;
}

export interface PriorityTaskOutput {
  id: string;
  title: string;
  priority: TaskPriority;
  status: TaskStatus;
  due_date: string;
  estimated_duration_hours?: number | null;
  is_eligible: boolean;
  blocking_prerequisites: string[];
  is_critical: boolean;
  downstream_dependents_count: number;
  total_score: number;
  score_breakdown: ScoreBreakdown;
  recommendation_reason: string;
}

export interface PriorityScheduleResponse {
  project_id: string;
  recommended_tasks: PriorityTaskOutput[];
  blocked_tasks: PriorityTaskOutput[];
  completed_tasks: PriorityTaskOutput[];
  weights: Record<string, number>;
}

export interface PertTaskMetrics {
  task_id: string;
  optimistic_hours?: number;
  most_likely_hours?: number;
  pessimistic_hours?: number;
  expected_duration_hours?: number;
  expected_duration?: number;
  variance: number;
  standard_deviation: number;
  is_critical?: boolean;
}

export interface PertAnalysisResponse {
  project_id: string;
  critical_path_expected_duration_hours: number;
  critical_path_variance: number;
  critical_path_std_dev: number;
  target_deadline_hours?: number | null;
  z_score?: number | null;
  probability_of_meeting_deadline?: number | null;
  confidence_percentage?: number | null;
  tasks?: Record<string, PertTaskMetrics>;
  assumptions?: string[];
  // Backwards-compatible aliases:
  expected_project_duration_hours?: number;
  project_standard_deviation_hours?: number;
  probability_within_target?: number | null;
  critical_path_task_ids?: string[];
  task_metrics?: PertTaskMetrics[];
}

export interface FacultyProjectOverview {
  project: AcademicProject;
  workload: TeamWorkloadResponse;
  readiness: ReviewReadinessResponse;
  reviews: ProjectReview[];
}

export type NotificationType =
  | 'due_date_reminder'
  | 'milestone_reminder'
  | 'overdue_task'
  | 'review_reminder'
  | 'task_assigned'
  | 'critical_path_alert'
  | 'general';

export interface ProjectNotification {
  id: string;
  project_id?: string | null;
  recipient_id: string;
  notification_type: NotificationType;
  title: string;
  message: string;
  task_id?: string | null;
  link_url?: string | null;
  scheduled_at?: string | null;
  sent_at?: string | null;
  read_at?: string | null;
  created_at: string;
}

export interface NotificationListResponse {
  items: ProjectNotification[];
  unread_count: number;
  total_count: number;
}
