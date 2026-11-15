from enum import Enum


class UserRole(str, Enum):
    STUDENT = "student"
    FACULTY = "faculty"


class ProjectStatus(str, Enum):
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ProjectType(str, Enum):
    CAPSTONE = "capstone"
    MAJOR = "major"
    MINOR = "minor"
    RESEARCH = "research"


class TeamRole(str, Enum):
    LEADER = "leader"
    MEMBER = "member"
    RESEARCHER = "researcher"
    DEVELOPER = "developer"
    TESTER = "tester"
    DOCUMENTATION = "documentation"


class MilestoneType(str, Enum):
    TOPIC_SELECTION = "topic_selection"
    PROBLEM_STATEMENT = "problem_statement"
    LITERATURE_REVIEW = "literature_review"
    PROJECT_PROPOSAL = "project_proposal"
    REQUIREMENT_ANALYSIS = "requirement_analysis"
    SYSTEM_DESIGN = "system_design"
    IMPLEMENTATION = "implementation"
    REVIEW_1 = "review_1"
    TESTING = "testing"
    REVIEW_2 = "review_2"
    DOCUMENTATION = "documentation"
    FINAL_PRESENTATION = "final_presentation"
    VIVA = "viva"
    CUSTOM = "custom"


class MilestoneStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DELAYED = "delayed"


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"


class DependencyType(str, Enum):
    FINISH_TO_START = "finish_to_start"


class ReviewStatus(str, Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class NotificationType(str, Enum):
    DUE_DATE_REMINDER = "due_date_reminder"
    MILESTONE_REMINDER = "milestone_reminder"
    OVERDUE_TASK = "overdue_task"
    REVIEW_REMINDER = "review_reminder"
    TASK_ASSIGNED = "task_assigned"
    CRITICAL_PATH_ALERT = "critical_path_alert"
    GENERAL = "general"
