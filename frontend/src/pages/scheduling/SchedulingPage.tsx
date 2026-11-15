import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import {
  Clock,
  Plus,
  Play,
  Flame,
  CheckCircle2,
  AlertTriangle,
  Layers,
  ArrowRight,
  SlidersHorizontal,
  Info,
  Calendar,
  Sparkles,
  Link as LinkIcon,
  Trash2,
  Edit2,
  UserPlus,
  Users,
  X,
} from 'lucide-react';
import { api } from '../../api/client';
import {
  Task,
  TaskCreate,
  TaskUpdate,
  AcademicMilestone,
  ProjectMember,
  PriorityScheduleResponse,
  CpmCalculationResponse,
  PertAnalysisResponse,
  TaskPriority,
  TaskStatus,
  TeamWorkloadResponse,
  TaskAssignment,
} from '../../types';
import { Card } from '../../components/common/Card';
import { Badge, PriorityBadge, StatusBadge } from '../../components/common/Badge';
import { Modal } from '../../components/common/Modal';
import { Alert } from '../../components/common/Alert';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { EmptyState } from '../../components/common/EmptyState';

type ActiveTab = 'tasks' | 'priority' | 'cpm' | 'pert';

export const SchedulingPage: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();

  const [activeTab, setActiveTab] = useState<ActiveTab>('tasks');
  const [tasks, setTasks] = useState<Task[]>([]);
  const [milestones, setMilestones] = useState<AcademicMilestone[]>([]);
  const [members, setMembers] = useState<ProjectMember[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Algorithm Results
  const [priorityResult, setPriorityResult] = useState<PriorityScheduleResponse | null>(null);
  const [cpmResult, setCpmResult] = useState<CpmCalculationResponse | null>(null);
  const [pertResult, setPertResult] = useState<PertAnalysisResponse | null>(null);
  const [isAlgorithmLoading, setIsAlgorithmLoading] = useState(false);
  const [algorithmError, setAlgorithmError] = useState<string | null>(null);

  // Task Creation / Editing Modal
  const [isTaskModalOpen, setIsTaskModalOpen] = useState(false);
  const [editingTask, setEditingTask] = useState<Task | null>(null);
  const [taskTitle, setTaskTitle] = useState('');
  const [taskDesc, setTaskDesc] = useState('');
  const [taskMilestone, setTaskMilestone] = useState('');
  const [taskPriority, setTaskPriority] = useState<TaskPriority>('medium');
  const [taskStatus, setTaskStatus] = useState<TaskStatus>('todo');
  const [taskDuration, setTaskDuration] = useState(10);
  const [taskDueDate, setTaskDueDate] = useState(
    new Date(Date.now() + 14 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
  );
  const [isSubmittingTask, setIsSubmittingTask] = useState(false);

  // Assignment Modal
  const [assigningTask, setAssigningTask] = useState<Task | null>(null);
  const [selectedMemberId, setSelectedMemberId] = useState('');
  const [isAssigning, setIsAssigning] = useState(false);
  const [assignError, setAssignError] = useState<string | null>(null);
  const [assignSuccess, setAssignSuccess] = useState<string | null>(null);
  const [confirmingUnassignUserId, setConfirmingUnassignUserId] = useState<string | null>(null);
  const [workloadData, setWorkloadData] = useState<TeamWorkloadResponse | null>(null);

  // Dependency Modal
  const [dependencyTask, setDependencyTask] = useState<Task | null>(null);
  const [selectedPrereqId, setSelectedPrereqId] = useState('');
  const [depError, setDepError] = useState<string | null>(null);

  // PERT Inputs State: task_id -> { optimistic, most_likely, pessimistic }
  const [pertEstimates, setPertEstimates] = useState<
    Record<string, { optimistic: number; most_likely: number; pessimistic: number }>
  >({});
  const [pertTargetDeadlineHours, setPertTargetDeadlineHours] = useState<number | undefined>(undefined);

  const getInitials = (name?: string | null) => {
    if (!name) return '??';
    const parts = name.trim().split(/\s+/);
    if (parts.length === 1) return parts[0].substring(0, 2).toUpperCase();
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  };

  const getAvatarBg = (name?: string | null) => {
    if (!name) return 'bg-slate-100 text-slate-700 border-slate-200';
    const styles = [
      'bg-indigo-50 text-indigo-700 border-indigo-200',
      'bg-emerald-50 text-emerald-700 border-emerald-200',
      'bg-amber-50 text-amber-700 border-amber-200',
      'bg-sky-50 text-sky-700 border-sky-200',
      'bg-purple-50 text-purple-700 border-purple-200',
      'bg-rose-50 text-rose-700 border-rose-200',
    ];
    let hash = 0;
    for (let i = 0; i < name.length; i++) {
      hash = name.charCodeAt(i) + ((hash << 5) - hash);
    }
    return styles[Math.abs(hash) % styles.length];
  };

  const getStudentWorkload = (userId: string) => {
    if (workloadData?.student_workloads) {
      const found = workloadData.student_workloads.find((sw) => sw.user_id === userId);
      if (found) return found;
    }
    const activeTasks = tasks.filter(
      (t) =>
        t.status !== 'completed' &&
        t.assignments?.some((a) => a.user_id === userId)
    );
    const activeHours = activeTasks.reduce((sum, t) => sum + (t.estimated_duration_hours || 0), 0);
    return {
      user_id: userId,
      full_name: '',
      email: '',
      team_role: '',
      total_active_hours: activeHours,
      completed_hours: 0,
      assigned_task_count: activeTasks.length,
      overdue_task_count: 0,
      upcoming_task_count: 0,
      completed_task_count: 0,
      is_overloaded: activeHours > 25.0,
      is_underutilized: activeHours < 5.0,
    };
  };

  const openAssignModal = (task: Task) => {
    const freshTask = tasks.find((t) => t.id === task.id) || task;
    setAssigningTask(freshTask);
    setSelectedMemberId('');
    setAssignError(null);
    setAssignSuccess(null);
    setConfirmingUnassignUserId(null);
  };

  const fetchData = async () => {
    if (!projectId) return;
    setIsLoading(true);
    setError(null);
    try {
      const [taskData, milestoneData, memberData, workloadRes] = await Promise.all([
        api.tasks.list(projectId),
        api.milestones.list(projectId),
        api.projects.listMembers(projectId),
        api.projects.getWorkload(projectId).catch(() => null),
      ]);
      setTasks(taskData);
      setMilestones(milestoneData);
      setMembers(memberData);
      if (workloadRes) {
        setWorkloadData(workloadRes);
      }

      // Initialize PERT estimates default
      const initialEstimates: Record<string, { optimistic: number; most_likely: number; pessimistic: number }> = {};
      taskData.forEach((t) => {
        const est = t.estimated_duration_hours || 10;
        initialEstimates[t.id] = {
          optimistic: Math.max(1, Math.round(est * 0.7)),
          most_likely: Math.round(est),
          pessimistic: Math.round(est * 1.5),
        };
      });
      setPertEstimates(initialEstimates);
    } catch (err: any) {
      setError(err.message || 'Failed to load scheduling workspace.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [projectId]);

  // Handle Tab Switch & Computation
  const handleTabChange = async (tab: ActiveTab) => {
    setActiveTab(tab);
    setAlgorithmError(null);
    if (!projectId) return;

    if (tab === 'priority') {
      setIsAlgorithmLoading(true);
      try {
        const res = await api.scheduling.calculatePriority(projectId);
        setPriorityResult(res);
      } catch (err: any) {
        setAlgorithmError(err.message || 'Priority Scheduling calculation failed.');
      } finally {
        setIsAlgorithmLoading(false);
      }
    } else if (tab === 'cpm') {
      setIsAlgorithmLoading(true);
      try {
        const res = await api.scheduling.calculateCpm(projectId);
        setCpmResult(res);
      } catch (err: any) {
        setAlgorithmError(err.message || 'Critical Path Method (CPM) calculation failed.');
      } finally {
        setIsAlgorithmLoading(false);
      }
    }
  };

  const handleRunPert = async () => {
    if (!projectId) return;
    setIsAlgorithmLoading(true);
    setAlgorithmError(null);

    const payload = tasks.map((t) => {
      const est = pertEstimates[t.id] || {
        optimistic: t.estimated_duration_hours * 0.7,
        most_likely: t.estimated_duration_hours,
        pessimistic: t.estimated_duration_hours * 1.5,
      };
      return {
        task_id: t.id,
        optimistic_hours: Number(est.optimistic),
        most_likely_hours: Number(est.most_likely),
        pessimistic_hours: Number(est.pessimistic),
      };
    });

    try {
      const res = await api.scheduling.calculatePert(projectId, payload, pertTargetDeadlineHours);
      setPertResult(res);
    } catch (err: any) {
      setAlgorithmError(err.message || 'PERT calculation failed.');
    } finally {
      setIsAlgorithmLoading(false);
    }
  };

  const openCreateTaskModal = () => {
    setEditingTask(null);
    setTaskTitle('');
    setTaskDesc('');
    setTaskMilestone('');
    setTaskPriority('medium');
    setTaskStatus('todo');
    setTaskDuration(10);
    setTaskDueDate(
      new Date(Date.now() + 14 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
    );
    setIsTaskModalOpen(true);
  };

  const openEditTaskModal = (task: Task) => {
    setEditingTask(task);
    setTaskTitle(task.title);
    setTaskDesc(task.description || '');
    setTaskMilestone(task.milestone_id || '');
    setTaskPriority(task.priority);
    setTaskStatus(task.status);
    setTaskDuration(task.estimated_duration_hours);
    setTaskDueDate(
      task.due_date ? task.due_date.split('T')[0] : new Date().toISOString().split('T')[0]
    );
    setIsTaskModalOpen(true);
  };

  const handleSubmitTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!projectId) return;
    setIsSubmittingTask(true);
    setError(null);

    try {
      if (editingTask) {
        const payload: TaskUpdate = {
          title: taskTitle,
          description: taskDesc || undefined,
          milestone_id: taskMilestone || undefined,
          priority: taskPriority,
          status: taskStatus,
          estimated_duration_hours: Number(taskDuration),
          due_date: taskDueDate,
        };
        await api.tasks.update(editingTask.id, payload);
      } else {
        const payload: TaskCreate = {
          title: taskTitle,
          description: taskDesc || undefined,
          milestone_id: taskMilestone || undefined,
          priority: taskPriority,
          estimated_duration_hours: Number(taskDuration),
          due_date: taskDueDate,
        };
        await api.tasks.create(projectId, payload);
      }
      setIsTaskModalOpen(false);
      setEditingTask(null);
      setTaskTitle('');
      setTaskDesc('');
      await fetchData();
      if (activeTab === 'priority') {
        handleTabChange('priority');
      } else if (activeTab === 'cpm') {
        handleTabChange('cpm');
      }
    } catch (err: any) {
      setError(err.message || (editingTask ? 'Failed to update task.' : 'Failed to create task.'));
    } finally {
      setIsSubmittingTask(false);
    }
  };

  const handleDeleteTask = async (task: Task) => {
    let confirmMsg = `Are you sure you want to delete task "${task.title}"?`;
    if (task.assignments && task.assignments.length > 0) {
      confirmMsg += `\nWarning: This task has ${task.assignments.length} assigned member(s).`;
    }
    confirmMsg += '\nAny dependency relationships and scheduling allocations for this task will also be deleted.';

    if (!window.confirm(confirmMsg)) {
      return;
    }

    try {
      await api.tasks.delete(task.id);
      await fetchData();
      if (activeTab === 'priority') {
        handleTabChange('priority');
      } else if (activeTab === 'cpm') {
        handleTabChange('cpm');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to delete task.');
    }
  };

  const handleStatusChange = async (taskId: string, newStatus: TaskStatus) => {
    try {
      await api.tasks.updateStatus(taskId, newStatus);
      fetchData();
    } catch (err: any) {
      setError(err.message || 'Failed to update task status.');
    }
  };

  const handleAssignMember = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!assigningTask || !selectedMemberId) return;

    setIsAssigning(true);
    setAssignError(null);
    setAssignSuccess(null);

    try {
      const newAssignment = await api.tasks.assign(assigningTask.id, selectedMemberId);
      const memberObj = members.find((m) => m.user_id === selectedMemberId);
      const enrichedAssignment: TaskAssignment = {
        ...newAssignment,
        user: newAssignment.user || memberObj?.user || null,
      };

      setTasks((prevTasks) =>
        prevTasks.map((t) => {
          if (t.id === assigningTask.id) {
            const currentAssigns = t.assignments || [];
            return {
              ...t,
              assignments: [...currentAssigns, enrichedAssignment],
            };
          }
          return t;
        })
      );

      setAssigningTask((prev) => {
        if (!prev) return null;
        return {
          ...prev,
          assignments: [...(prev.assignments || []), enrichedAssignment],
        };
      });

      setSelectedMemberId('');
      setAssignSuccess(`Assigned ${memberObj?.user?.full_name || 'member'} to this task.`);

      if (projectId) {
        api.projects.getWorkload(projectId).then(setWorkloadData).catch(() => {});
      }
    } catch (err: any) {
      setAssignError(err.message || 'Failed to assign team member.');
    } finally {
      setIsAssigning(false);
    }
  };

  const handleUnassignMember = async (userId: string, memberName: string) => {
    if (!assigningTask) return;

    setIsAssigning(true);
    setAssignError(null);
    setAssignSuccess(null);

    try {
      await api.tasks.unassign(assigningTask.id, userId);

      setTasks((prevTasks) =>
        prevTasks.map((t) => {
          if (t.id === assigningTask.id) {
            return {
              ...t,
              assignments: (t.assignments || []).filter((a) => a.user_id !== userId),
            };
          }
          return t;
        })
      );

      setAssigningTask((prev) => {
        if (!prev) return null;
        return {
          ...prev,
          assignments: (prev.assignments || []).filter((a) => a.user_id !== userId),
        };
      });

      setConfirmingUnassignUserId(null);
      setAssignSuccess(`Removed ${memberName} from this task.`);

      if (projectId) {
        api.projects.getWorkload(projectId).then(setWorkloadData).catch(() => {});
      }
    } catch (err: any) {
      setAssignError(err.message || 'Failed to remove team member.');
    } finally {
      setIsAssigning(false);
    }
  };

  const handleAddDependency = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!dependencyTask || !selectedPrereqId) return;
    setDepError(null);

    try {
      await api.tasks.addDependency(dependencyTask.id, selectedPrereqId);
      setDependencyTask(null);
      setSelectedPrereqId('');
      fetchData();
    } catch (err: any) {
      setDepError(err.message || 'Failed to add task dependency.');
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Scheduling Workspace</h1>
          <p className="text-xs text-slate-500 mt-1">
            Work breakdown structure, Priority Dispatching, Critical Path Method (CPM), and PERT estimation.
          </p>
        </div>
        <button
          onClick={openCreateTaskModal}
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold shadow-xs transition-colors cursor-pointer shrink-0"
        >
          <Plus className="w-4 h-4" />
          <span>New Work Task</span>
        </button>
      </div>

      {error && <Alert type="error">{error}</Alert>}

      {/* Tabs Bar */}
      <div className="flex items-center border-b border-slate-200 overflow-x-auto space-x-1 sm:space-x-2">
        <button
          onClick={() => handleTabChange('tasks')}
          className={`py-3 px-4 text-xs font-semibold border-b-2 flex items-center gap-2 transition-colors cursor-pointer whitespace-nowrap ${
            activeTab === 'tasks'
              ? 'border-indigo-600 text-indigo-700 bg-indigo-50/40 rounded-t-lg'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Layers className="w-4 h-4" />
          <span>Task Breakdown ({tasks.length})</span>
        </button>

        <button
          onClick={() => handleTabChange('priority')}
          className={`py-3 px-4 text-xs font-semibold border-b-2 flex items-center gap-2 transition-colors cursor-pointer whitespace-nowrap ${
            activeTab === 'priority'
              ? 'border-indigo-600 text-indigo-700 bg-indigo-50/40 rounded-t-lg'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Sparkles className="w-4 h-4 text-indigo-600" />
          <span>Priority Scheduling</span>
        </button>

        <button
          onClick={() => handleTabChange('cpm')}
          className={`py-3 px-4 text-xs font-semibold border-b-2 flex items-center gap-2 transition-colors cursor-pointer whitespace-nowrap ${
            activeTab === 'cpm'
              ? 'border-indigo-600 text-indigo-700 bg-indigo-50/40 rounded-t-lg'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Flame className="w-4 h-4 text-rose-500" />
          <span>Critical Path (CPM)</span>
        </button>

        <button
          onClick={() => handleTabChange('pert')}
          className={`py-3 px-4 text-xs font-semibold border-b-2 flex items-center gap-2 transition-colors cursor-pointer whitespace-nowrap ${
            activeTab === 'pert'
              ? 'border-indigo-600 text-indigo-700 bg-indigo-50/40 rounded-t-lg'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <SlidersHorizontal className="w-4 h-4 text-amber-500" />
          <span>PERT 3-Point Estimation</span>
        </button>
      </div>

      {isLoading ? (
        <div className="py-20">
          <LoadingSpinner size="lg" label="Loading tasks and schedule models..." />
        </div>
      ) : (
        <>
          {/* TAB 1: TASK BREAKDOWN */}
          {activeTab === 'tasks' && (
            <div className="space-y-4">
              {tasks.length === 0 ? (
                <EmptyState
                  title="No Tasks Defined Yet"
                  description="Break down your project into specific academic tasks, assign estimated effort hours, and set due dates to enable scheduling algorithms."
                  action={
                    <button
                      onClick={openCreateTaskModal}
                      className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 text-white text-xs font-semibold hover:bg-indigo-700 cursor-pointer"
                    >
                      <Plus className="w-4 h-4" />
                      <span>Add First Task</span>
                    </button>
                  }
                />
              ) : (
                <div className="bg-white rounded-2xl border border-slate-200/80 shadow-2xs overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider">
                        <tr>
                          <th className="py-3 px-4">Task Details</th>
                          <th className="py-3 px-4">Priority</th>
                          <th className="py-3 px-4">Status</th>
                          <th className="py-3 px-4">Duration</th>
                          <th className="py-3 px-4">Due Date</th>
                          <th className="py-3 px-4">Assigned Team Members</th>
                          <th className="py-3 px-4 text-right">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 text-slate-700">
                        {tasks.map((task) => (
                          <tr key={task.id} className="hover:bg-slate-50/50 transition-colors">
                            <td className="py-3.5 px-4 max-w-xs">
                              <span className="font-semibold text-slate-900 block leading-tight">
                                {task.title}
                              </span>
                              {task.description && (
                                <span className="text-[11px] text-slate-400 truncate block mt-0.5">
                                  {task.description}
                                </span>
                              )}
                            </td>
                            <td className="py-3.5 px-4">
                              <PriorityBadge priority={task.priority} />
                            </td>
                            <td className="py-3.5 px-4">
                              <select
                                value={task.status}
                                onChange={(e) => handleStatusChange(task.id, e.target.value as TaskStatus)}
                                className="bg-slate-50 border border-slate-200 text-slate-700 text-xs rounded-lg px-2 py-1 font-medium focus:ring-1 focus:ring-indigo-500"
                              >
                                <option value="todo">Todo</option>
                                <option value="in_progress">In Progress</option>
                                <option value="blocked">Blocked</option>
                                <option value="completed">Completed</option>
                              </select>
                            </td>
                            <td className="py-3.5 px-4 font-medium text-slate-600">
                              {task.estimated_duration_hours}h
                            </td>
                            <td className="py-3.5 px-4 text-slate-600">
                              {task.due_date}
                            </td>
                            <td className="py-3.5 px-4 min-w-[200px]">
                              {task.assignments && task.assignments.length > 0 ? (
                                <div className="flex flex-wrap items-center gap-1.5" data-testid={`task-assignees-${task.id}`}>
                                  {task.assignments.map((assignment) => {
                                    const memberInfo = members.find((m) => m.user_id === assignment.user_id);
                                    const name = assignment.user?.full_name || memberInfo?.user?.full_name || 'Member';
                                    const role = memberInfo?.team_role;
                                    return (
                                      <span
                                        key={assignment.id || assignment.user_id}
                                        title={`${name} (${role || 'Member'})`}
                                        className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-medium border bg-white shadow-2xs text-slate-700 border-slate-200"
                                      >
                                        <span
                                          className={`w-4 h-4 rounded-full flex items-center justify-center text-[9px] font-bold border shrink-0 ${getAvatarBg(
                                            name
                                          )}`}
                                        >
                                          {getInitials(name)}
                                        </span>
                                        <span className="truncate max-w-[110px]">{name}</span>
                                        {role && (
                                          <span className="text-[9px] uppercase px-1 py-0.2 bg-slate-100 text-slate-500 rounded font-semibold shrink-0">
                                            {role}
                                          </span>
                                        )}
                                      </span>
                                    );
                                  })}
                                </div>
                              ) : (
                                <div className="flex items-center gap-2">
                                  <span className="text-[11px] text-slate-400 italic">Unassigned</span>
                                  <button
                                    onClick={() => openAssignModal(task)}
                                    className="inline-flex items-center gap-1 text-[11px] font-medium text-indigo-600 hover:text-indigo-800 bg-indigo-50 hover:bg-indigo-100 px-1.5 py-0.5 rounded transition-colors cursor-pointer"
                                  >
                                    <UserPlus className="w-3 h-3" />
                                    <span>Assign</span>
                                  </button>
                                </div>
                              )}
                            </td>
                            <td className="py-3.5 px-4 text-right space-x-1.5 whitespace-nowrap">
                              <button
                                onClick={() => openEditTaskModal(task)}
                                className="inline-flex items-center gap-1 text-[11px] font-medium text-slate-700 hover:text-indigo-600 bg-slate-100 hover:bg-indigo-50 px-2 py-1 rounded-md transition-colors cursor-pointer"
                                title="Edit Task"
                              >
                                <Edit2 className="w-3 h-3" />
                                <span>Edit</span>
                              </button>
                              <button
                                onClick={() => openAssignModal(task)}
                                className="inline-flex items-center gap-1 text-[11px] font-medium text-indigo-600 hover:text-indigo-800 bg-indigo-50 hover:bg-indigo-100 px-2 py-1 rounded-md transition-colors cursor-pointer"
                              >
                                <UserPlus className="w-3 h-3" />
                                <span>Assign {task.assignments && task.assignments.length > 0 ? `(${task.assignments.length})` : ''}</span>
                              </button>
                              <button
                                onClick={() => setDependencyTask(task)}
                                className="inline-flex items-center gap-1 text-[11px] font-medium text-slate-600 hover:text-slate-800 bg-slate-100 hover:bg-slate-200 px-2 py-1 rounded-md transition-colors cursor-pointer"
                              >
                                <LinkIcon className="w-3 h-3" />
                                <span>Prereq</span>
                              </button>
                              <button
                                onClick={() => handleDeleteTask(task)}
                                className="inline-flex items-center gap-1 text-[11px] font-medium text-rose-600 hover:text-rose-800 bg-rose-50 hover:bg-rose-100 px-2 py-1 rounded-md transition-colors cursor-pointer"
                                title="Delete Task"
                              >
                                <Trash2 className="w-3 h-3" />
                                <span>Delete</span>
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 2: PRIORITY SCHEDULING */}
          {activeTab === 'priority' && (
            <div className="space-y-6">
              {isAlgorithmLoading ? (
                <div className="py-16">
                  <LoadingSpinner size="md" label="Calculating priority ranking and bottleneck heuristics..." />
                </div>
              ) : algorithmError ? (
                <Alert type="error" title="Priority Scheduling Error">
                  {algorithmError}
                </Alert>
              ) : !priorityResult ? (
                <EmptyState
                  title="Priority Analysis Ready"
                  description="Run priority dispatching to dynamically rank tasks based on priority weights, deadline urgency, critical path inclusion, and downstream dependents count."
                  action={
                    <button
                      onClick={() => handleTabChange('priority')}
                      className="px-4 py-2 bg-indigo-600 text-white rounded-xl text-xs font-semibold"
                    >
                      Compute Priority Schedule
                    </button>
                  }
                />
              ) : (
                <div className="space-y-6">
                  {/* Recommended Eligible Tasks */}
                  <Card
                    title="Recommended Next Tasks (Eligible for Immediate Execution)"
                    subtitle="Tasks whose prerequisite dependencies have been completely resolved, prioritized by composite urgency & critical path bonus."
                  >
                    {priorityResult.recommended_tasks.length === 0 ? (
                      <p className="text-xs text-slate-400 italic">No eligible tasks remaining.</p>
                    ) : (
                      <div className="divide-y divide-slate-100">
                        {priorityResult.recommended_tasks.map((task, idx) => (
                          <div key={task.id} className="py-3.5 flex items-start justify-between gap-4">
                            <div className="flex items-start gap-3">
                              <span className="w-6 h-6 rounded-full bg-indigo-600 text-white flex items-center justify-center font-bold text-xs shrink-0 mt-0.5">
                                {idx + 1}
                              </span>
                              <div>
                                <div className="flex items-center gap-2">
                                  <span className="font-semibold text-slate-800 text-sm">{task.title}</span>
                                  {task.is_critical && (
                                    <span className="bg-rose-50 text-rose-700 border border-rose-200 text-[10px] font-bold uppercase px-1.5 py-0.5 rounded-sm">
                                      Critical Path
                                    </span>
                                  )}
                                  <PriorityBadge priority={task.priority} />
                                </div>
                                <p className="text-xs text-indigo-700 mt-1 font-medium bg-indigo-50/60 p-1.5 rounded-md inline-block">
                                  💡 {task.recommendation_reason}
                                </p>
                              </div>
                            </div>
                            <div className="text-right shrink-0">
                              <span className="text-xs font-bold text-indigo-700 block">
                                Score: {task.total_score}
                              </span>
                              <span className="text-[11px] text-slate-400 block mt-0.5">
                                Due: {task.due_date}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </Card>

                  {/* Blocked Tasks */}
                  {priorityResult.blocked_tasks.length > 0 && (
                    <Card
                      title={`Blocked Tasks (${priorityResult.blocked_tasks.length})`}
                      subtitle="Tasks currently waiting on unfinished prerequisite dependencies."
                      className="border-amber-100 bg-amber-50/10"
                    >
                      <div className="divide-y divide-slate-100">
                        {priorityResult.blocked_tasks.map((task) => (
                          <div key={task.id} className="py-3 flex items-center justify-between gap-4">
                            <div>
                              <span className="font-medium text-slate-800 text-xs block">{task.title}</span>
                              <span className="text-[11px] text-amber-700 mt-0.5 block">
                                Blocked by {task.blocking_prerequisites.length} prerequisite task(s)
                              </span>
                            </div>
                            <Badge variant="warning" size="sm">
                              Blocked
                            </Badge>
                          </div>
                        ))}
                      </div>
                    </Card>
                  )}
                </div>
              )}
            </div>
          )}

          {/* TAB 3: CRITICAL PATH METHOD (CPM) */}
          {activeTab === 'cpm' && (
            <div className="space-y-6">
              {isAlgorithmLoading ? (
                <div className="py-16">
                  <LoadingSpinner size="md" label="Calculating forward/backward pass and slack hours..." />
                </div>
              ) : algorithmError ? (
                <Alert type="error" title="CPM Calculation Error">
                  {algorithmError}
                </Alert>
              ) : !cpmResult ? (
                <EmptyState
                  title="CPM Analysis"
                  description="Run CPM to determine project completion duration, early/late schedules, and zero-slack bottleneck tasks."
                />
              ) : (
                <div className="space-y-6">
                  {/* Summary Metric Box */}
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    <div className="p-4 rounded-xl bg-white border border-slate-200/80 shadow-2xs">
                      <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">
                        Total Project Duration
                      </span>
                      <div className="text-2xl font-bold text-slate-900 mt-1">
                        {cpmResult.total_project_duration_hours} Hours
                      </div>
                      <span className="text-[11px] text-slate-500 mt-0.5 block">
                        Estimated academic work hours
                      </span>
                    </div>

                    <div className="p-4 rounded-xl bg-rose-50 border border-rose-200/80 shadow-2xs">
                      <span className="text-xs font-semibold text-rose-700 uppercase tracking-wider block">
                        Critical Tasks (Zero Slack)
                      </span>
                      <div className="text-2xl font-bold text-rose-800 mt-1">
                        {(cpmResult.critical_tasks || cpmResult.critical_path_task_ids || []).length} Tasks
                      </div>
                      <span className="text-[11px] text-rose-600 mt-0.5 block">
                        Any delay here delays the final viva!
                      </span>
                    </div>

                    <div className="p-4 rounded-xl bg-white border border-slate-200/80 shadow-2xs">
                      <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">
                        Total Tasks Modeled
                      </span>
                      <div className="text-2xl font-bold text-slate-900 mt-1">
                        {Object.keys(cpmResult.tasks).length} Tasks
                      </div>
                      <span className="text-[11px] text-slate-500 mt-0.5 block">
                        Network graph nodes
                      </span>
                    </div>
                  </div>

                  {/* CPM Table */}
                  <Card title="Critical Path Schedule & Slack Analysis">
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs">
                        <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider">
                          <tr>
                            <th className="py-3 px-4">Task Name</th>
                            <th className="py-3 px-4">Duration</th>
                            <th className="py-3 px-4">Early Start (ES)</th>
                            <th className="py-3 px-4">Early Finish (EF)</th>
                            <th className="py-3 px-4">Late Start (LS)</th>
                            <th className="py-3 px-4">Late Finish (LF)</th>
                            <th className="py-3 px-4">Slack (LS-ES)</th>
                            <th className="py-3 px-4">Critical?</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 text-slate-700">
                          {Object.values(cpmResult.tasks).map((t) => (
                            <tr
                              key={t.id}
                              className={t.is_critical ? 'bg-rose-50/50 font-medium' : 'hover:bg-slate-50/50'}
                            >
                              <td className="py-3 px-4 font-semibold text-slate-800">
                                {t.title}
                              </td>
                              <td className="py-3 px-4">{t.duration}h</td>
                              <td className="py-3 px-4 text-slate-500">{t.early_start}h</td>
                              <td className="py-3 px-4 text-slate-500">{t.early_finish}h</td>
                              <td className="py-3 px-4 text-slate-500">{t.late_start}h</td>
                              <td className="py-3 px-4 text-slate-500">{t.late_finish}h</td>
                              <td className="py-3 px-4">
                                <span
                                  className={`font-bold ${
                                    t.slack === 0 ? 'text-rose-600' : 'text-emerald-600'
                                  }`}
                                >
                                  {t.slack}h
                                </span>
                              </td>
                              <td className="py-3 px-4">
                                {t.is_critical ? (
                                  <Badge variant="danger" size="sm">
                                    CRITICAL
                                  </Badge>
                                ) : (
                                  <Badge variant="neutral" size="sm">
                                    Flexible
                                  </Badge>
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </Card>
                </div>
              )}
            </div>
          )}

          {/* TAB 4: PERT PROBABILISTIC ANALYSIS */}
          {activeTab === 'pert' && (
            <div className="space-y-6">
              <div className="bg-amber-50/70 border border-amber-200 rounded-xl p-4 flex items-start gap-3 text-xs text-amber-800">
                <Info className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-bold">Three-Point Academic Estimations</h4>
                  <p className="mt-0.5 leading-relaxed">
                    Provide Optimistic (a), Most Likely (m), and Pessimistic (b) work duration estimates.
                    The algorithm computes expected duration via Beta distribution [t_e = (a + 4m + b)/6]
                    and variance [v = ((b-a)/6)^2]. Note: Probabilistic estimates are planning models, not guarantees.
                  </p>
                </div>
              </div>

              {/* Estimate Inputs Table */}
              <Card
                title="Task Duration Estimates (Hours)"
                action={
                  <div className="flex items-center gap-3">
                    <div className="flex items-center gap-1.5 text-xs text-slate-600">
                      <span>Target (h):</span>
                      <input
                        type="number"
                        min={1}
                        placeholder="Optional"
                        value={pertTargetDeadlineHours || ''}
                        onChange={(e) => setPertTargetDeadlineHours(e.target.value ? Number(e.target.value) : undefined)}
                        className="w-20 px-2 py-1 bg-slate-50 border border-slate-200 rounded text-xs"
                      />
                    </div>
                    <button
                      onClick={handleRunPert}
                      disabled={isAlgorithmLoading}
                      className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-semibold shadow-xs disabled:opacity-50 cursor-pointer"
                    >
                      <Play className="w-3.5 h-3.5" />
                      <span>Run PERT Simulation</span>
                    </button>
                  </div>
                }
              >
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider">
                      <tr>
                        <th className="py-3 px-3">Task Name</th>
                        <th className="py-3 px-3">Optimistic (a)</th>
                        <th className="py-3 px-3">Most Likely (m)</th>
                        <th className="py-3 px-3">Pessimistic (b)</th>
                        <th className="py-3 px-3">Expected (te)</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {tasks.map((task) => {
                        const current = pertEstimates[task.id] || {
                          optimistic: 5,
                          most_likely: 10,
                          pessimistic: 15,
                        };
                        const te = (current.optimistic + 4 * current.most_likely + current.pessimistic) / 6;

                        return (
                          <tr key={task.id}>
                            <td className="py-2.5 px-3 font-semibold text-slate-800">
                              {task.title}
                            </td>
                            <td className="py-2.5 px-3">
                              <input
                                type="number"
                                min={0.5}
                                step={0.5}
                                value={current.optimistic}
                                onChange={(e) =>
                                  setPertEstimates({
                                    ...pertEstimates,
                                    [task.id]: {
                                      ...current,
                                      optimistic: Number(e.target.value),
                                    },
                                  })
                                }
                                className="w-20 px-2 py-1 bg-slate-50 border border-slate-200 rounded text-xs"
                              />
                            </td>
                            <td className="py-2.5 px-3">
                              <input
                                type="number"
                                min={0.5}
                                step={0.5}
                                value={current.most_likely}
                                onChange={(e) =>
                                  setPertEstimates({
                                    ...pertEstimates,
                                    [task.id]: {
                                      ...current,
                                      most_likely: Number(e.target.value),
                                    },
                                  })
                                }
                                className="w-20 px-2 py-1 bg-slate-50 border border-slate-200 rounded text-xs"
                              />
                            </td>
                            <td className="py-2.5 px-3">
                              <input
                                type="number"
                                min={0.5}
                                step={0.5}
                                value={current.pessimistic}
                                onChange={(e) =>
                                  setPertEstimates({
                                    ...pertEstimates,
                                    [task.id]: {
                                      ...current,
                                      pessimistic: Number(e.target.value),
                                    },
                                  })
                                }
                                className="w-20 px-2 py-1 bg-slate-50 border border-slate-200 rounded text-xs"
                              />
                            </td>
                            <td className="py-2.5 px-3 font-semibold text-indigo-700">
                              {te.toFixed(1)}h
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </Card>

              {/* PERT Output Results */}
              {isAlgorithmLoading ? (
                <div className="py-12">
                  <LoadingSpinner size="md" label="Simulating critical path variance and normal distribution..." />
                </div>
              ) : algorithmError ? (
                <Alert type="error">{algorithmError}</Alert>
              ) : pertResult && (
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-2xs">
                    <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">
                      Expected Project Duration
                    </span>
                    <div className="text-2xl font-bold text-indigo-700 mt-1">
                      {((pertResult.critical_path_expected_duration_hours ?? pertResult.expected_project_duration_hours) ?? 0).toFixed(1)}h
                    </div>
                  </div>

                  <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-2xs">
                    <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">
                      Project Standard Deviation (σ)
                    </span>
                    <div className="text-2xl font-bold text-slate-800 mt-1">
                      ±{((pertResult.critical_path_std_dev ?? pertResult.project_standard_deviation_hours) ?? 0).toFixed(1)}h
                    </div>
                  </div>

                  <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 shadow-2xs">
                    <span className="text-xs font-semibold text-emerald-700 uppercase tracking-wider block">
                      Deadline Completion Probability
                    </span>
                    <div className="text-2xl font-bold text-emerald-800 mt-1">
                      {(() => {
                        const prob = pertResult.probability_of_meeting_deadline ?? pertResult.probability_within_target;
                        return prob !== null && prob !== undefined
                          ? `${(prob * 100).toFixed(1)}%`
                          : 'N/A';
                      })()}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </>
      )}

      {/* Task Creation / Editing Modal */}
      <Modal
        isOpen={isTaskModalOpen}
        onClose={() => setIsTaskModalOpen(false)}
        title={editingTask ? 'Edit Academic Task' : 'Create Academic Task'}
        subtitle={
          editingTask
            ? 'Update work task details, priority, status, duration, and milestone link.'
            : 'Add a work task with estimated effort and milestone link.'
        }
        maxWidth="md"
      >
        <form onSubmit={handleSubmitTask} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Task Title *
            </label>
            <input
              type="text"
              required
              value={taskTitle}
              onChange={(e) => setTaskTitle(e.target.value)}
              placeholder="e.g. Implement Kalman Filter for state estimation"
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Description
            </label>
            <textarea
              rows={2}
              value={taskDesc}
              onChange={(e) => setTaskDesc(e.target.value)}
              placeholder="Detailed description of task requirements..."
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Priority
              </label>
              <select
                value={taskPriority}
                onChange={(e) => setTaskPriority(e.target.value as TaskPriority)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm"
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Estimated Hours *
              </label>
              <input
                type="number"
                min={0.5}
                step={0.5}
                required
                value={taskDuration}
                onChange={(e) => setTaskDuration(Number(e.target.value))}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Academic Milestone
              </label>
              <select
                value={taskMilestone}
                onChange={(e) => setTaskMilestone(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm"
              >
                <option value="">No Milestone Link</option>
                {milestones.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.sequence_number}. {m.title}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Due Date *
              </label>
              <input
                type="date"
                required
                value={taskDueDate}
                onChange={(e) => setTaskDueDate(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm"
              />
            </div>
          </div>

          {editingTask && (
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Task Status
              </label>
              <select
                value={taskStatus}
                onChange={(e) => setTaskStatus(e.target.value as TaskStatus)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm"
              >
                <option value="todo">To Do</option>
                <option value="in_progress">In Progress</option>
                <option value="completed">Completed</option>
                <option value="blocked">Blocked</option>
              </select>
            </div>
          )}

          <div className="pt-3 border-t border-slate-100 flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={() => setIsTaskModalOpen(false)}
              className="px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmittingTask}
              className="px-4 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl shadow-xs cursor-pointer"
            >
              {isSubmittingTask ? 'Saving...' : editingTask ? 'Update Task' : 'Create Task'}
            </button>
          </div>
        </form>
      </Modal>

      {/* Member Assignment Modal */}
      <Modal
        isOpen={!!assigningTask}
        onClose={() => setAssigningTask(null)}
        title="Manage Task Assignments"
        subtitle={`Assign or manage student team members for "${assigningTask?.title}".`}
        maxWidth="md"
      >
        <div className="space-y-6">
          {assignSuccess && (
            <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-800 text-xs flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>{assignSuccess}</span>
              </div>
              <button
                onClick={() => setAssignSuccess(null)}
                className="text-emerald-600 hover:text-emerald-800 cursor-pointer"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          )}

          {assignError && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-800 text-xs flex items-center justify-between">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
                <span>{assignError}</span>
              </div>
              <button
                onClick={() => setAssignError(null)}
                className="text-rose-600 hover:text-rose-800 cursor-pointer"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          )}

          {/* Section 1: Current Assignees */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                <Users className="w-3.5 h-3.5 text-indigo-600" />
                <span>Currently Assigned ({assigningTask?.assignments?.length || 0})</span>
              </h4>
              <span className="text-[11px] text-slate-400">
                Multiple students can be assigned concurrently
              </span>
            </div>

            {!assigningTask?.assignments || assigningTask.assignments.length === 0 ? (
              <div className="p-4 bg-slate-50 border border-dashed border-slate-200 rounded-xl text-center">
                <p className="text-xs text-slate-500 font-medium">No team members assigned yet</p>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Select an eligible member below to assign them to this task.
                </p>
              </div>
            ) : (
              <div className="space-y-2">
                {assigningTask.assignments.map((assignment) => {
                  const memberInfo = members.find((m) => m.user_id === assignment.user_id);
                  const name = assignment.user?.full_name || memberInfo?.user?.full_name || 'Member';
                  const email = assignment.user?.email || memberInfo?.user?.email;
                  const role = memberInfo?.team_role || 'member';
                  const workload = getStudentWorkload(assignment.user_id);
                  const isConfirming = confirmingUnassignUserId === assignment.user_id;

                  return (
                    <div
                      key={assignment.id || assignment.user_id}
                      className="p-3 bg-white border border-slate-200 rounded-xl flex items-center justify-between gap-3 shadow-2xs hover:border-slate-300 transition-colors"
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <span
                          className={`w-9 h-9 rounded-full flex items-center justify-center text-xs font-bold border shrink-0 ${getAvatarBg(
                            name
                          )}`}
                        >
                          {getInitials(name)}
                        </span>
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-sm text-slate-900 truncate">
                              {name}
                            </span>
                            <span className="text-[10px] uppercase px-1.5 py-0.5 bg-slate-100 text-slate-600 rounded font-semibold shrink-0">
                              {role}
                            </span>
                          </div>
                          <div className="flex items-center gap-2 text-[11px] text-slate-500 mt-0.5 truncate">
                            {email && <span>{email}</span>}
                            <span>•</span>
                            <span className="font-medium text-slate-700">
                              {workload.assigned_task_count} active {workload.assigned_task_count === 1 ? 'task' : 'tasks'} ({workload.total_active_hours}h)
                            </span>
                            {workload.is_overloaded && (
                              <span className="text-[10px] font-semibold text-rose-600 bg-rose-50 px-1.5 py-0.2 rounded border border-rose-200">
                                Overloaded
                              </span>
                            )}
                          </div>
                        </div>
                      </div>

                      <div className="shrink-0 flex items-center gap-2">
                        {isConfirming ? (
                          <div className="flex items-center gap-1.5 bg-rose-50 border border-rose-200 p-1 rounded-lg">
                            <span className="text-[11px] text-rose-700 font-medium px-1">Remove?</span>
                            <button
                              type="button"
                              disabled={isAssigning}
                              onClick={() => handleUnassignMember(assignment.user_id, name)}
                              className="px-2 py-0.5 text-[11px] font-bold text-white bg-rose-600 hover:bg-rose-700 rounded transition-colors cursor-pointer"
                            >
                              Yes
                            </button>
                            <button
                              type="button"
                              onClick={() => setConfirmingUnassignUserId(null)}
                              className="px-2 py-0.5 text-[11px] font-medium text-slate-600 hover:bg-slate-200 rounded transition-colors cursor-pointer"
                            >
                              No
                            </button>
                          </div>
                        ) : (
                          <button
                            type="button"
                            disabled={isAssigning}
                            onClick={() => setConfirmingUnassignUserId(assignment.user_id)}
                            className="inline-flex items-center gap-1 text-xs text-rose-600 hover:text-rose-800 hover:bg-rose-50 px-2 py-1 rounded-lg transition-colors cursor-pointer"
                            title="Remove member from task"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                            <span>Remove</span>
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Section 2: Add Team Member */}
          <div className="pt-4 border-t border-slate-100">
            <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <UserPlus className="w-3.5 h-3.5 text-indigo-600" />
              <span>Add Team Member</span>
            </h4>

            {(() => {
              const assignedUserIds = new Set(
                (assigningTask?.assignments || []).map((a) => a.user_id)
              );
              const availableMembers = members.filter((m) => !assignedUserIds.has(m.user_id));

              if (members.length === 0) {
                return (
                  <p className="text-xs text-slate-400 italic">
                    No members are in this project team yet. Add team members from the Project Overview page first.
                  </p>
                );
              }

              if (availableMembers.length === 0) {
                return (
                  <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-center">
                    <p className="text-xs text-slate-600 font-medium">
                      All team members are already assigned to this task.
                    </p>
                  </div>
                );
              }

              return (
                <form onSubmit={handleAssignMember} className="space-y-3">
                  <div>
                    <label
                      htmlFor="assign-student-select"
                      className="block text-[11px] font-semibold text-slate-600 uppercase tracking-wider mb-1"
                    >
                      Select Available Student
                    </label>
                    <select
                      id="assign-student-select"
                      value={selectedMemberId}
                      onChange={(e) => setSelectedMemberId(e.target.value)}
                      required
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-medium text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
                    >
                      <option value="">Choose an eligible student...</option>
                      {availableMembers.map((m) => {
                        const workload = getStudentWorkload(m.user_id);
                        const overloadNotice = workload.is_overloaded ? ' ⚠️ Overloaded' : '';
                        return (
                          <option key={m.user_id} value={m.user_id}>
                            {m.user?.full_name} ({m.team_role}) — {workload.assigned_task_count} active tasks ({workload.total_active_hours}h){overloadNotice}
                          </option>
                        );
                      })}
                    </select>
                  </div>

                  {/* Workload Preview for Selected Member */}
                  {selectedMemberId && (() => {
                    const selectedMember = members.find((m) => m.user_id === selectedMemberId);
                    const workload = getStudentWorkload(selectedMemberId);
                    return (
                      <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs flex items-center justify-between">
                        <div>
                          <span className="font-semibold text-slate-800">{selectedMember?.user?.full_name}</span>
                          <span className="text-slate-500 ml-1.5">({selectedMember?.team_role})</span>
                          <div className="text-[11px] text-slate-500 mt-0.5">
                            Currently has {workload.assigned_task_count} active tasks totaling {workload.total_active_hours}h effort
                          </div>
                        </div>
                        {workload.is_overloaded ? (
                          <span className="text-[10px] font-semibold text-rose-700 bg-rose-100 px-2 py-0.5 rounded-full shrink-0">
                            High Workload
                          </span>
                        ) : (
                          <span className="text-[10px] font-semibold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded-full shrink-0">
                            Available Capacity
                          </span>
                        )}
                      </div>
                    );
                  })()}

                  <div className="flex items-center justify-end gap-2 pt-1">
                    <button
                      type="submit"
                      disabled={isAssigning || !selectedMemberId}
                      className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-xl shadow-xs transition-colors cursor-pointer"
                    >
                      <UserPlus className="w-3.5 h-3.5" />
                      <span>{isAssigning ? 'Assigning...' : 'Assign Team Member'}</span>
                    </button>
                  </div>
                </form>
              );
            })()}
          </div>

          <div className="pt-3 border-t border-slate-100 flex justify-end">
            <button
              type="button"
              onClick={() => setAssigningTask(null)}
              className="px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100 rounded-xl transition-colors cursor-pointer"
            >
              Done
            </button>
          </div>
        </div>
      </Modal>

      {/* Dependency Modal */}
      <Modal
        isOpen={!!dependencyTask}
        onClose={() => {
          setDependencyTask(null);
          setDepError(null);
        }}
        title="Add Prerequisite Dependency"
        subtitle={`Select which task must be finished before "${dependencyTask?.title}" can start.`}
        maxWidth="md"
      >
        {depError && <Alert type="error" className="mb-4">{depError}</Alert>}
        <form onSubmit={handleAddDependency} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Prerequisite Task
            </label>
            <select
              value={selectedPrereqId}
              onChange={(e) => setSelectedPrereqId(e.target.value)}
              required
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm"
            >
              <option value="">Select prerequisite...</option>
              {tasks
                .filter((t) => t.id !== dependencyTask?.id)
                .map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.title} ({t.estimated_duration_hours}h)
                  </option>
                ))}
            </select>
            <p className="text-[11px] text-slate-400 mt-1">
              Dependency cycle detection (Kahn's algorithm) will prevent circular prerequisites.
            </p>
          </div>
          <div className="pt-3 border-t border-slate-100 flex justify-end gap-2">
            <button
              type="button"
              onClick={() => {
                setDependencyTask(null);
                setDepError(null);
              }}
              className="px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl shadow-xs"
            >
              Add Dependency
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
