import React, { useState, useEffect, useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  Compass,
  Calendar,
  Clock,
  CheckCircle2,
  AlertTriangle,
  Users,
  Award,
  ArrowRight,
  UserPlus,
  ShieldAlert,
  Flame,
  Check,
  GraduationCap,
  Search,
  X,
  Edit2,
  Trash2,
} from 'lucide-react';
import { api } from '../../api/client';
import { useAuth } from '../../context/AuthContext';
import {
  AcademicProject,
  AcademicProjectUpdate,
  ProjectStatus,
  ProjectType,
  ReviewReadinessResponse,
  TeamWorkloadResponse,
  ProjectMember,
  Task,
  TeamRole,
  UserSummary,
} from '../../types';
import { Card } from '../../components/common/Card';
import { Badge, StatusBadge } from '../../components/common/Badge';
import { Alert } from '../../components/common/Alert';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { Modal } from '../../components/common/Modal';
import { EmptyState } from '../../components/common/EmptyState';

export const ProjectDashboardPage: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const { user } = useAuth();

  const [project, setProject] = useState<AcademicProject | null>(null);
  const [readiness, setReadiness] = useState<ReviewReadinessResponse | null>(null);
  const [workload, setWorkload] = useState<TeamWorkloadResponse | null>(null);
  const [members, setMembers] = useState<ProjectMember[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Add Member Modal State
  const [isMemberModalOpen, setIsMemberModalOpen] = useState(false);
  const [availableStudents, setAvailableStudents] = useState<UserSummary[]>([]);
  const [isLoadingStudents, setIsLoadingStudents] = useState(false);
  const [studentSearchTerm, setStudentSearchTerm] = useState('');
  const [targetUserId, setTargetUserId] = useState('');
  const [memberRole, setMemberRole] = useState<TeamRole>('developer');
  const [memberError, setMemberError] = useState<string | null>(null);
  const [isAddingMember, setIsAddingMember] = useState(false);

  // Faculty Guide Assignment State
  const [isGuideModalOpen, setIsGuideModalOpen] = useState(false);
  const [facultyList, setFacultyList] = useState<UserSummary[]>([]);
  const [isLoadingFaculty, setIsLoadingFaculty] = useState(false);
  const [selectedGuideId, setSelectedGuideId] = useState<string>('');
  const [guideError, setGuideError] = useState<string | null>(null);
  const [guideSuccess, setGuideSuccess] = useState<string | null>(null);
  const [isSubmittingGuide, setIsSubmittingGuide] = useState(false);

  // Edit Project State
  const [isEditProjectModalOpen, setIsEditProjectModalOpen] = useState(false);
  const [editTitle, setEditTitle] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [editProjectType, setEditProjectType] = useState<ProjectType>('capstone');
  const [editDepartment, setEditDepartment] = useState('');
  const [editAcademicYear, setEditAcademicYear] = useState('');
  const [editSemester, setEditSemester] = useState(7);
  const [editStartDate, setEditStartDate] = useState('');
  const [editTargetDeadline, setEditTargetDeadline] = useState('');
  const [editStatus, setEditStatus] = useState<ProjectStatus>('in_progress');
  const [isSubmittingProjectEdit, setIsSubmittingProjectEdit] = useState(false);
  const [projectEditError, setProjectEditError] = useState<string | null>(null);

  const fetchProjectData = async () => {
    if (!projectId) return;
    setIsLoading(true);
    setError(null);

    try {
      const [projData, readData, wlData, memData, taskData] = await Promise.all([
        api.projects.get(projectId),
        api.projects.getReadiness(projectId),
        api.projects.getWorkload(projectId),
        api.projects.listMembers(projectId),
        api.tasks.list(projectId),
      ]);
      setProject(projData);
      setReadiness(readData);
      setWorkload(wlData);
      setMembers(memData);
      setTasks(taskData);
    } catch (err: any) {
      setError(err.message || 'Failed to load project dashboard.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchProjectData();
  }, [projectId]);

  const handleOpenMemberModal = async () => {
    setIsMemberModalOpen(true);
    setMemberError(null);
    setTargetUserId('');
    setStudentSearchTerm('');
    if (!projectId) return;

    setIsLoadingStudents(true);
    try {
      const data = await api.projects.listAvailableStudents(projectId);
      setAvailableStudents(data);
      if (data.length > 0) {
        setTargetUserId(data[0].id);
      }
    } catch (err: any) {
      setMemberError(err.message || 'Failed to load available students.');
    } finally {
      setIsLoadingStudents(false);
    }
  };

  const filteredStudents = useMemo(() => {
    if (!studentSearchTerm.trim()) return availableStudents;
    const term = studentSearchTerm.toLowerCase().trim();
    return availableStudents.filter(
      (s) =>
        s.full_name.toLowerCase().includes(term) ||
        s.email.toLowerCase().includes(term) ||
        (s.department && s.department.toLowerCase().includes(term))
    );
  }, [availableStudents, studentSearchTerm]);

  const handleAddMember = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!projectId) return;
    if (!targetUserId) {
      setMemberError('Please select a student from the list.');
      return;
    }
    setMemberError(null);
    setIsAddingMember(true);

    try {
      await api.projects.addMember(projectId, {
        user_id: targetUserId.trim(),
        team_role: memberRole,
      });
      setIsMemberModalOpen(false);
      setTargetUserId('');
      setStudentSearchTerm('');
      fetchProjectData();
    } catch (err: any) {
      setMemberError(err.message || 'Failed to add team member.');
    } finally {
      setIsAddingMember(false);
    }
  };

  const isOwner = Boolean(user && project && project.owner_id === user.id);

  const handleOpenGuideModal = async () => {
    setIsGuideModalOpen(true);
    setGuideError(null);
    setGuideSuccess(null);
    setSelectedGuideId(project?.faculty_guide_id || '');
    setIsLoadingFaculty(true);
    try {
      const data = await api.faculty.listFacultyMembers();
      setFacultyList(data);
      if (!project?.faculty_guide_id && data.length > 0) {
        setSelectedGuideId(data[0].id);
      }
    } catch (err: any) {
      setGuideError(err.message || 'Failed to load registered faculty supervisors.');
    } finally {
      setIsLoadingFaculty(false);
    }
  };

  const handleAssignGuide = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!projectId || !selectedGuideId) return;
    setIsSubmittingGuide(true);
    setGuideError(null);
    setGuideSuccess(null);

    try {
      const updated = await api.projects.assignFacultyGuide(projectId, selectedGuideId);
      setProject(updated);
      setGuideSuccess('Faculty supervisor successfully assigned!');
      await fetchProjectData();
      setTimeout(() => {
        setIsGuideModalOpen(false);
        setGuideSuccess(null);
      }, 700);
    } catch (err: any) {
      setGuideError(err.message || 'Failed to assign faculty guide.');
    } finally {
      setIsSubmittingGuide(false);
    }
  };

  const handleOpenEditProjectModal = () => {
    if (!project) return;
    setEditTitle(project.title);
    setEditDescription(project.description || '');
    setEditProjectType(project.project_type);
    setEditDepartment(project.department);
    setEditAcademicYear(project.academic_year);
    setEditSemester(project.semester);
    setEditStartDate(project.start_date || '');
    setEditTargetDeadline(project.target_deadline || '');
    setEditStatus(project.status);
    setProjectEditError(null);
    setIsEditProjectModalOpen(true);
  };

  const handleSaveProjectEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!projectId) return;
    setIsSubmittingProjectEdit(true);
    setProjectEditError(null);

    const payload: AcademicProjectUpdate = {
      title: editTitle,
      description: editDescription || undefined,
      project_type: editProjectType,
      department: editDepartment,
      academic_year: editAcademicYear,
      semester: Number(editSemester),
      start_date: editStartDate,
      target_deadline: editTargetDeadline,
      status: editStatus,
    };

    try {
      const updated = await api.projects.update(projectId, payload);
      setProject(updated);
      setIsEditProjectModalOpen(false);
      await fetchProjectData();
    } catch (err: any) {
      setProjectEditError(err.message || 'Failed to update project.');
    } finally {
      setIsSubmittingProjectEdit(false);
    }
  };

  const handleUpdateMemberRole = async (userId: string, newRole: string) => {
    if (!projectId) return;
    try {
      await api.projects.updateMemberRole(projectId, userId, newRole);
      await fetchProjectData();
    } catch (err: any) {
      setError(err.message || 'Failed to update team member role.');
    }
  };

  const handleRemoveMember = async (member: ProjectMember) => {
    if (!projectId) return;
    const memberName = member.user?.full_name || 'this student';
    if (
      !window.confirm(
        `Are you sure you want to remove ${memberName} from the project team?\nAny tasks assigned to them will be unassigned.`
      )
    ) {
      return;
    }

    try {
      await api.projects.removeMember(projectId, member.user_id);
      await fetchProjectData();
    } catch (err: any) {
      setError(err.message || 'Failed to remove team member.');
    }
  };

  if (isLoading) {
    return (
      <div className="py-20">
        <LoadingSpinner size="lg" label="Loading project dashboard and readiness scorecard..." />
      </div>
    );
  }

  if (error || !project) {
    return (
      <Alert type="error" title="Failed to Load Project">
        {error || 'Project not found or you do not have permission to view it.'}
      </Alert>
    );
  }

  const completedTasks = tasks.filter((t) => t.status === 'completed');
  const activeTasks = tasks.filter((t) => t.status !== 'completed');
  const overdueTasks = activeTasks.filter(
    (t) => t.due_date && new Date(t.due_date) < new Date(new Date().toDateString())
  );

  const getReadinessBadgeVariant = (level?: string | null) => {
    if (!level) return 'neutral';
    if (level.includes('EXCELLENT')) return 'success';
    if (level.includes('GOOD')) return 'info';
    if (level.includes('NEEDS')) return 'warning';
    if (level.includes('CRITICAL')) return 'danger';
    return 'neutral';
  };

  return (
    <div className="space-y-6">
      {/* Project Overview Header */}
      <div className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-2xs">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5 flex-wrap mb-2">
              <span className="text-xs font-bold uppercase tracking-wider text-indigo-700 bg-indigo-50 border border-indigo-100 px-2.5 py-0.5 rounded-md">
                {project.project_type}
              </span>
              <StatusBadge status={project.status} />
              <span className="text-xs text-slate-500 font-medium">
                Semester {project.semester} • {project.academic_year} • {project.department}
              </span>
            </div>
            <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
              {project.title}
            </h1>
            {project.description && (
              <p className="text-xs text-slate-600 mt-1 max-w-3xl leading-relaxed">
                {project.description}
              </p>
            )}
          </div>

          <div className="flex items-center gap-2.5 shrink-0">
            {isOwner && (
              <button
                onClick={handleOpenEditProjectModal}
                className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold transition-colors cursor-pointer"
                title="Edit Project Details"
              >
                <Edit2 className="w-4 h-4" />
                <span>Edit Project</span>
              </button>
            )}
            <Link
              to={`/projects/${project.id}/scheduling`}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold shadow-xs transition-colors"
            >
              <Clock className="w-4 h-4" />
              <span>Scheduling Workspace</span>
            </Link>
            <Link
              to={`/projects/${project.id}/milestones`}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold transition-colors"
            >
              <CheckCircle2 className="w-4 h-4" />
              <span>Milestones</span>
            </Link>
          </div>
        </div>

        {/* Target Deadline & Guide Info */}
        <div className="mt-5 pt-4 border-t border-slate-100 grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
          <div>
            <span className="text-slate-400 block">Target Viva / Submission Deadline</span>
            <span className="font-semibold text-slate-800 text-sm mt-0.5 block">
              {project.target_deadline}
            </span>
          </div>
          <div>
            <div className="flex items-center justify-between gap-2">
              <span className="text-slate-400 block">Faculty Supervisor</span>
              {isOwner && (
                <button
                  type="button"
                  onClick={handleOpenGuideModal}
                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-indigo-50 hover:bg-indigo-100 text-indigo-700 font-semibold text-[11px] transition-colors cursor-pointer"
                  data-testid="assign-guide-btn"
                >
                  <GraduationCap className="w-3.5 h-3.5" />
                  <span>{project.faculty_guide ? 'Change' : 'Assign Faculty Guide'}</span>
                </button>
              )}
            </div>
            <span
              className="font-semibold text-indigo-700 text-sm mt-0.5 block"
              data-testid="faculty-guide-name"
            >
              {project.faculty_guide ? project.faculty_guide.full_name : 'No Guide Assigned Yet'}
            </span>
            {project.faculty_guide?.email && (
              <span className="text-[11px] text-slate-500 block truncate">
                {project.faculty_guide.email}
              </span>
            )}
          </div>
          <div>
            <span className="text-slate-400 block">Project Team Leader</span>
            <span className="font-semibold text-slate-800 text-sm mt-0.5 block">
              {project.owner ? project.owner.full_name : 'Student Owner'}
            </span>
          </div>
        </div>
      </div>

      {/* Review Readiness Scorecard */}
      {readiness && (
        <Card
          title="Academic Review Readiness Scorecard"
          subtitle="Transparent 100-point viva readiness index based on milestone completion, task progress, critical path health, and deadline adherence."
          className="border-indigo-100 bg-gradient-to-br from-white to-indigo-50/20"
        >
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
            {/* Score Ring / Pill */}
            <div className="lg:col-span-4 flex flex-col items-center justify-center p-6 bg-white rounded-2xl border border-indigo-100/80 shadow-xs text-center">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
                Readiness Score
              </span>
              <div className="text-5xl font-extrabold text-indigo-700 tracking-tight">
                {readiness.readiness_score}
                <span className="text-2xl font-normal text-slate-400">/100</span>
              </div>
              <div className="mt-3">
                <Badge variant={getReadinessBadgeVariant(readiness.readiness_level)} size="md">
                  {readiness.readiness_level}
                </Badge>
              </div>
              {readiness.next_review_scheduled_at && (
                <div className="mt-4 text-[11px] text-slate-500 bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-100">
                  Next Review:{' '}
                  <span className="font-semibold text-slate-700">
                    {new Date(readiness.next_review_scheduled_at).toLocaleDateString()}
                  </span>
                </div>
              )}
            </div>

            {/* Score Breakdown Bars */}
            <div className="lg:col-span-8 space-y-3.5">
              <div>
                <div className="flex justify-between text-xs font-medium text-slate-700 mb-1">
                  <span>Milestone Completion (Max 40 pts)</span>
                  <span className="font-semibold text-indigo-600">
                    {readiness.score_breakdown.milestone_score} / 40.0
                  </span>
                </div>
                <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                  <div
                    className="bg-indigo-600 h-2 rounded-full transition-all duration-500"
                    style={{ width: `${(readiness.score_breakdown.milestone_score / 40.0) * 100}%` }}
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs font-medium text-slate-700 mb-1">
                  <span>Work Breakdown Task Completion (Max 15 pts)</span>
                  <span className="font-semibold text-indigo-600">
                    {readiness.score_breakdown.task_completion_score} / 15.0
                  </span>
                </div>
                <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                  <div
                    className="bg-indigo-600 h-2 rounded-full transition-all duration-500"
                    style={{ width: `${(readiness.score_breakdown.task_completion_score / 15.0) * 100}%` }}
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs font-medium text-slate-700 mb-1">
                  <span>CPM Critical Path Health (Max 15 pts)</span>
                  <span className="font-semibold text-indigo-600">
                    {readiness.score_breakdown.critical_path_score} / 15.0
                  </span>
                </div>
                <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                  <div
                    className="bg-indigo-600 h-2 rounded-full transition-all duration-500"
                    style={{ width: `${(readiness.score_breakdown.critical_path_score / 15.0) * 100}%` }}
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs font-medium text-slate-700 mb-1">
                  <span>Overdue Tasks Penalty (Max 20 pts, -5 pts per overdue)</span>
                  <span className="font-semibold text-indigo-600">
                    {readiness.score_breakdown.overdue_score} / 20.0
                  </span>
                </div>
                <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                  <div
                    className="bg-indigo-600 h-2 rounded-full transition-all duration-500"
                    style={{ width: `${(readiness.score_breakdown.overdue_score / 20.0) * 100}%` }}
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs font-medium text-slate-700 mb-1">
                  <span>Upcoming Review Proximity Score (Max 10 pts)</span>
                  <span className="font-semibold text-indigo-600">
                    {readiness.score_breakdown.review_timing_score} / 10.0
                  </span>
                </div>
                <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                  <div
                    className="bg-indigo-600 h-2 rounded-full transition-all duration-500"
                    style={{ width: `${(readiness.score_breakdown.review_timing_score / 10.0) * 100}%` }}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Blockers & Recommendations */}
          {(readiness.blockers.length > 0 || readiness.actionable_recommendations.length > 0) && (
            <div className="mt-6 pt-5 border-t border-slate-100 grid grid-cols-1 md:grid-cols-2 gap-4">
              {readiness.blockers.length > 0 && (
                <div className="bg-rose-50 border border-rose-200 rounded-xl p-4">
                  <div className="flex items-center gap-2 text-rose-800 text-xs font-bold uppercase tracking-wider mb-2">
                    <ShieldAlert className="w-4 h-4 text-rose-600" />
                    <span>Active Viva Blockers ({readiness.blockers.length})</span>
                  </div>
                  <ul className="space-y-1.5 text-xs text-rose-700">
                    {readiness.blockers.map((b, i) => (
                      <li key={i} className="flex items-start gap-1.5">
                        <span className="font-bold">•</span>
                        <span>{b}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {readiness.actionable_recommendations.length > 0 && (
                <div className="bg-indigo-50/70 border border-indigo-100 rounded-xl p-4">
                  <div className="flex items-center gap-2 text-indigo-900 text-xs font-bold uppercase tracking-wider mb-2">
                    <Flame className="w-4 h-4 text-indigo-600" />
                    <span>Actionable Recommendations</span>
                  </div>
                  <ul className="space-y-1.5 text-xs text-indigo-800">
                    {readiness.actionable_recommendations.map((rec, i) => (
                      <li key={i} className="flex items-start gap-1.5">
                        <Check className="w-3.5 h-3.5 text-indigo-600 shrink-0 mt-0.5" />
                        <span>{rec}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </Card>
      )}

      {/* Quick Metrics Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-2xs">
          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
            Total Tasks
          </span>
          <div className="text-2xl font-bold text-slate-800 mt-1">
            {tasks.length}
          </div>
          <span className="text-[11px] text-slate-500 mt-0.5 block">
            {completedTasks.length} done • {activeTasks.length} active
          </span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-2xs">
          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
            Overdue Tasks
          </span>
          <div className={`text-2xl font-bold mt-1 ${overdueTasks.length > 0 ? 'text-rose-600' : 'text-slate-800'}`}>
            {overdueTasks.length}
          </div>
          <span className="text-[11px] text-slate-500 mt-0.5 block">
            Past target due date
          </span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-2xs">
          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
            Active Team Workload
          </span>
          <div className="text-2xl font-bold text-indigo-600 mt-1">
            {workload?.total_team_active_hours || 0}h
          </div>
          <span className="text-[11px] text-slate-500 mt-0.5 block">
            Avg: {workload?.average_hours_per_student || 0}h / member
          </span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-2xs">
          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
            Workload StdDev
          </span>
          <div className="text-2xl font-bold text-slate-800 mt-1">
            {workload?.workload_standard_deviation || 0}h
          </div>
          <span className="text-[11px] text-slate-500 mt-0.5 block">
            Effort balance metric
          </span>
        </div>
      </div>

      {/* Team Members Section */}
      <Card
        title="Student Project Team"
        subtitle="Registered student contributors and their assigned roles for this project."
        action={
          isOwner ? (
            <button
              onClick={handleOpenMemberModal}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-50 text-indigo-700 hover:bg-indigo-100 text-xs font-semibold transition-colors cursor-pointer"
            >
              <UserPlus className="w-3.5 h-3.5" />
              <span>Add Member</span>
            </button>
          ) : undefined
        }
      >
        <div className="divide-y divide-slate-100">
          {members.map((m) => (
            <div key={m.id} className="py-3 flex items-center justify-between first:pt-0 last:pb-0">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-slate-100 text-slate-600 flex items-center justify-center font-bold text-xs uppercase">
                  {m.user?.full_name ? m.user.full_name.slice(0, 2) : 'ST'}
                </div>
                <div>
                  <span className="text-sm font-semibold text-slate-800 block">
                    {m.user?.full_name}
                  </span>
                  <span className="text-xs text-slate-400">
                    {m.user?.email}
                  </span>
                </div>
              </div>
              {isOwner && m.user_id !== project.owner_id ? (
                <div className="flex items-center gap-2">
                  <select
                    value={m.team_role}
                    onChange={(e) => handleUpdateMemberRole(m.user_id, e.target.value)}
                    className="text-xs bg-slate-50 border border-slate-200 rounded-lg px-2 py-1 text-slate-700 font-medium cursor-pointer"
                    title="Change team role"
                  >
                    <option value="leader">Leader</option>
                    <option value="member">Member</option>
                    <option value="developer">Developer</option>
                    <option value="researcher">Researcher</option>
                    <option value="tester">Tester</option>
                    <option value="documentation">Documentation</option>
                  </select>
                  <button
                    onClick={() => handleRemoveMember(m)}
                    className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors cursor-pointer"
                    title={`Remove ${m.user?.full_name || 'member'} from team`}
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ) : (
                <Badge variant="primary" size="sm">
                  {m.team_role}
                </Badge>
              )}
            </div>
          ))}
        </div>
      </Card>

      {/* Add Member Modal */}
      <Modal
        isOpen={isMemberModalOpen}
        onClose={() => setIsMemberModalOpen(false)}
        title="Add Team Member"
        subtitle="Select a registered student to add to this academic project team."
        maxWidth="md"
      >
        {memberError && (
          <Alert type="error" className="mb-4">
            {memberError}
          </Alert>
        )}

        <form onSubmit={handleAddMember} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">
              Select Student *
            </label>

            {isLoadingStudents ? (
              <div className="py-8">
                <LoadingSpinner size="md" label="Loading eligible student accounts..." />
              </div>
            ) : availableStudents.length === 0 ? (
              <EmptyState
                title="No Available Students"
                description="All registered students are already members of this project, or no other active student accounts exist."
              />
            ) : (
              <div className="space-y-2">
                <div className="relative">
                  <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                  <input
                    type="text"
                    value={studentSearchTerm}
                    onChange={(e) => setStudentSearchTerm(e.target.value)}
                    placeholder="Search by student name or email..."
                    className="w-full pl-9 pr-8 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-hidden focus:ring-2 focus:ring-indigo-600 focus:bg-white text-slate-800"
                  />
                  {studentSearchTerm && (
                    <button
                      type="button"
                      onClick={() => setStudentSearchTerm('')}
                      className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 p-0.5"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>

                <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                  {filteredStudents.length === 0 ? (
                    <p className="text-xs text-slate-500 py-4 text-center">
                      No students matching "{studentSearchTerm}" found.
                    </p>
                  ) : (
                    filteredStudents.map((stud) => {
                      const isSelected = targetUserId === stud.id;
                      return (
                        <label
                          key={stud.id}
                          className={`flex items-start gap-3 p-3 rounded-xl border transition-all cursor-pointer ${
                            isSelected
                              ? 'border-indigo-600 bg-indigo-50/50 shadow-2xs'
                              : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'
                          }`}
                        >
                          <input
                            type="radio"
                            name="student_member_selection"
                            value={stud.id}
                            checked={isSelected}
                            onChange={() => setTargetUserId(stud.id)}
                            className="mt-1 text-indigo-600 focus:ring-indigo-500"
                          />
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center justify-between gap-2">
                              <span className="text-sm font-semibold text-slate-900 truncate">
                                {stud.full_name}
                              </span>
                              <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-700 bg-emerald-50 border border-emerald-100 px-1.5 py-0.5 rounded">
                                Student
                              </span>
                            </div>
                            <span className="text-xs text-slate-500 block truncate mt-0.5">
                              {stud.email}
                            </span>
                            {stud.department && (
                              <span className="text-[11px] text-slate-400 block mt-0.5">
                                {stud.department}
                              </span>
                            )}
                          </div>
                        </label>
                      );
                    })
                  )}
                </div>
              </div>
            )}
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Assigned Team Role *
            </label>
            <select
              value={memberRole}
              onChange={(e) => setMemberRole(e.target.value as TeamRole)}
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-hidden focus:ring-2 focus:ring-indigo-600 focus:bg-white text-slate-800"
            >
              <option value="developer">Developer</option>
              <option value="researcher">Researcher</option>
              <option value="tester">Tester</option>
              <option value="documentation">Documentation</option>
              <option value="member">General Member</option>
            </select>
          </div>

          <div className="pt-3 border-t border-slate-100 flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={() => setIsMemberModalOpen(false)}
              className="px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isAddingMember || !targetUserId || availableStudents.length === 0}
              className="px-3.5 py-1.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-2xs disabled:opacity-50 cursor-pointer"
            >
              {isAddingMember ? 'Adding...' : 'Add Student'}
            </button>
          </div>
        </form>
      </Modal>

      {/* Assign Faculty Guide Modal */}
      <Modal
        isOpen={isGuideModalOpen}
        onClose={() => setIsGuideModalOpen(false)}
        title={project.faculty_guide ? 'Change Faculty Supervisor' : 'Assign Faculty Guide'}
        subtitle="Select an approved faculty supervisor to monitor project milestones, review readiness, and conduct academic reviews."
        maxWidth="md"
      >
        <form onSubmit={handleAssignGuide} className="space-y-4">
          {guideError && (
            <Alert type="error" title="Assignment Error">
              {guideError}
            </Alert>
          )}

          {guideSuccess && (
            <Alert type="success" title="Success">
              {guideSuccess}
            </Alert>
          )}

          {isLoadingFaculty ? (
            <div className="py-8">
              <LoadingSpinner size="md" label="Loading registered faculty members..." />
            </div>
          ) : facultyList.length === 0 ? (
            <EmptyState
              title="No Faculty Supervisors Found"
              description="There are currently no active faculty members registered in the system."
            />
          ) : (
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">
                Select Faculty Supervisor *
              </label>
              <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
                {facultyList.map((fac) => {
                  const isSelected = selectedGuideId === fac.id;
                  return (
                    <label
                      key={fac.id}
                      className={`flex items-start gap-3 p-3 rounded-xl border transition-all cursor-pointer ${
                        isSelected
                          ? 'border-indigo-600 bg-indigo-50/50 shadow-2xs'
                          : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'
                      }`}
                    >
                      <input
                        type="radio"
                        name="faculty_guide_selection"
                        value={fac.id}
                        checked={isSelected}
                        onChange={() => setSelectedGuideId(fac.id)}
                        className="mt-1 text-indigo-600 focus:ring-indigo-500"
                      />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-sm font-semibold text-slate-900 truncate">
                            {fac.full_name}
                          </span>
                          <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-700 bg-indigo-50 border border-indigo-100 px-1.5 py-0.5 rounded">
                            Faculty
                          </span>
                        </div>
                        <span className="text-xs text-slate-500 block truncate mt-0.5">
                          {fac.email}
                        </span>
                        {fac.department && (
                          <span className="text-[11px] text-slate-400 block mt-0.5">
                            {fac.department}
                          </span>
                        )}
                      </div>
                    </label>
                  );
                })}
              </div>
            </div>
          )}

          <div className="pt-3 border-t border-slate-100 flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={() => setIsGuideModalOpen(false)}
              className="px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmittingGuide || isLoadingFaculty || !selectedGuideId || facultyList.length === 0}
              className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-2xs disabled:opacity-50 cursor-pointer"
              data-testid="confirm-assign-guide-btn"
            >
              {isSubmittingGuide ? (
                <>
                  <LoadingSpinner size="sm" />
                  <span>Assigning...</span>
                </>
              ) : (
                <>
                  <Check className="w-3.5 h-3.5" />
                  <span>Confirm Assignment</span>
                </>
              )}
            </button>
          </div>
        </form>
      </Modal>

      {/* Edit Project Modal */}
      <Modal
        isOpen={isEditProjectModalOpen}
        onClose={() => setIsEditProjectModalOpen(false)}
        title="Edit Project Details"
        subtitle="Update academic project settings, milestones baseline, and target deadline."
        maxWidth="lg"
      >
        {projectEditError && (
          <Alert type="error" className="mb-4">
            {projectEditError}
          </Alert>
        )}

        <form onSubmit={handleSaveProjectEdit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Project Title *
            </label>
            <input
              type="text"
              required
              value={editTitle}
              onChange={(e) => setEditTitle(e.target.value)}
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Description
            </label>
            <textarea
              rows={3}
              value={editDescription}
              onChange={(e) => setEditDescription(e.target.value)}
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Project Type *
              </label>
              <select
                value={editProjectType}
                onChange={(e) => setEditProjectType(e.target.value as ProjectType)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm"
              >
                <option value="capstone">Capstone</option>
                <option value="major">Major Project</option>
                <option value="minor">Minor Project</option>
                <option value="research">Research Paper</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Department *
              </label>
              <input
                type="text"
                required
                value={editDepartment}
                onChange={(e) => setEditDepartment(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Academic Year *
              </label>
              <input
                type="text"
                required
                placeholder="2024-2025"
                value={editAcademicYear}
                onChange={(e) => setEditAcademicYear(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Semester *
              </label>
              <input
                type="number"
                min={1}
                max={12}
                required
                value={editSemester}
                onChange={(e) => setEditSemester(Number(e.target.value))}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Start Date *
              </label>
              <input
                type="date"
                required
                value={editStartDate}
                onChange={(e) => setEditStartDate(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Target Deadline *
              </label>
              <input
                type="date"
                required
                value={editTargetDeadline}
                onChange={(e) => setEditTargetDeadline(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Project Status *
            </label>
            <select
              value={editStatus}
              onChange={(e) => setEditStatus(e.target.value as ProjectStatus)}
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm capitalize"
            >
              <option value="planning">Planning</option>
              <option value="in_progress">In Progress</option>
              <option value="submitted">Submitted</option>
              <option value="completed">Completed</option>
              <option value="archived">Archived</option>
            </select>
          </div>

          <div className="pt-3 border-t border-slate-100 flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={() => setIsEditProjectModalOpen(false)}
              className="px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmittingProjectEdit}
              className="px-4 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl shadow-xs cursor-pointer"
            >
              {isSubmittingProjectEdit ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
