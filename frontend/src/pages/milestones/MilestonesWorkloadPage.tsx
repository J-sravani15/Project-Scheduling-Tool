import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import {
  CheckCircle2,
  Calendar,
  AlertTriangle,
  Plus,
  Users,
  Flame,
  ArrowRight,
  TrendingUp,
  Clock,
  Sparkles,
  Edit2,
  Trash2,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Legend,
} from 'recharts';
import { api } from '../../api/client';
import {
  AcademicMilestone,
  AcademicMilestoneCreate,
  TeamWorkloadResponse,
  ReviewReadinessResponse,
  MilestoneStatus,
  MilestoneType,
} from '../../types';
import { Card } from '../../components/common/Card';
import { Badge, StatusBadge } from '../../components/common/Badge';
import { Modal } from '../../components/common/Modal';
import { Alert } from '../../components/common/Alert';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';

export const MilestonesWorkloadPage: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();

  const [milestones, setMilestones] = useState<AcademicMilestone[]>([]);
  const [workload, setWorkload] = useState<TeamWorkloadResponse | null>(null);
  const [readiness, setReadiness] = useState<ReviewReadinessResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Milestone Modal State (Create / Edit)
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingMilestone, setEditingMilestone] = useState<AcademicMilestone | null>(null);
  const [mTitle, setMTitle] = useState('');
  const [mDesc, setMDesc] = useState('');
  const [mType, setMType] = useState<MilestoneType>('review_1');
  const [mSeq, setMSeq] = useState(1);
  const [mDate, setMDate] = useState(
    new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
  );
  const [mStatus, setMStatus] = useState<'pending' | 'completed'>('pending');
  const [mRequired, setMRequired] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchData = async () => {
    if (!projectId) return;
    setIsLoading(true);
    setError(null);
    try {
      const [mList, wl, rd] = await Promise.all([
        api.milestones.list(projectId),
        api.projects.getWorkload(projectId),
        api.projects.getReadiness(projectId),
      ]);
      setMilestones(mList);
      setWorkload(wl);
      setReadiness(rd);
      setMSeq(mList.length + 1);
    } catch (err: any) {
      setError(err.message || 'Failed to load milestones and workload.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [projectId]);

  const handleOpenCreateModal = () => {
    setEditingMilestone(null);
    setMTitle('');
    setMDesc('');
    setMType('review_1');
    setMSeq(milestones.length + 1);
    setMDate(new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]);
    setMStatus('pending');
    setMRequired(true);
    setIsModalOpen(true);
  };

  const handleOpenEditModal = (m: AcademicMilestone) => {
    setEditingMilestone(m);
    setMTitle(m.title);
    setMDesc(m.description || '');
    setMType(m.milestone_type);
    setMSeq(m.sequence_number);
    setMDate(m.planned_date);
    setMRequired(m.is_required);
    setMStatus(m.status === 'completed' ? 'completed' : 'pending');
    setIsModalOpen(true);
  };

  const handleSubmitMilestone = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!projectId) return;
    setIsSubmitting(true);
    setError(null);

    const payload = {
      title: mTitle.trim(),
      description: mDesc.trim() || undefined,
      milestone_type: mType,
      sequence_number: Number(mSeq),
      planned_date: mDate,
      status: mStatus,
      is_required: mRequired,
    };

    try {
      if (editingMilestone) {
        await api.milestones.update(editingMilestone.id, payload);
      } else {
        await api.milestones.create(projectId, payload as AcademicMilestoneCreate);
      }
      setIsModalOpen(false);
      setEditingMilestone(null);
      setMTitle('');
      setMDesc('');
      await fetchData();
    } catch (err: any) {
      setError(err.message || 'Failed to save academic milestone.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteMilestone = async (m: AcademicMilestone) => {
    const confirmed = window.confirm(
      `Are you sure you want to delete milestone "${m.title}"? Any tasks linked to this milestone will remain but have their milestone detached.`
    );
    if (!confirmed) return;

    try {
      await api.milestones.delete(m.id);
      await fetchData();
    } catch (err: any) {
      setError(err.message || 'Failed to delete academic milestone.');
    }
  };

  const handleToggleMilestone = async (m: AcademicMilestone) => {
    const nextStatus: MilestoneStatus = m.status === 'completed' ? 'pending' : 'completed';
    try {
      await api.milestones.updateStatus(m.id, nextStatus);
      await fetchData();
    } catch (err: any) {
      setError(err.message || 'Failed to update milestone status.');
    }
  };

  const getReadinessBadgeVariant = (level?: string | null) => {
    if (!level) return 'neutral';
    if (level.includes('EXCELLENT')) return 'success';
    if (level.includes('GOOD')) return 'info';
    if (level.includes('NEEDS')) return 'warning';
    if (level.includes('CRITICAL')) return 'danger';
    return 'neutral';
  };

  if (isLoading) {
    return (
      <div className="py-20">
        <LoadingSpinner size="lg" label="Loading academic milestones and workload analytics..." />
      </div>
    );
  }

  // Prepare chart data from student workloads
  const chartData = workload?.student_workloads.map((s) => ({
    name: s.full_name.split(' ')[0] || s.full_name,
    active: s.total_active_hours,
    completed: s.completed_hours,
  })) || [];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Milestones & Team Workload</h1>
          <p className="text-xs text-slate-500 mt-1">
            Academic evaluation checkpoints and capacity-balanced effort distribution.
          </p>
        </div>
        <button
          onClick={handleOpenCreateModal}
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold shadow-xs transition-colors cursor-pointer shrink-0"
        >
          <Plus className="w-4 h-4" />
          <span>New Academic Milestone</span>
        </button>
      </div>

      {error && <Alert type="error">{error}</Alert>}

      {/* Academic Review Readiness Scorecard */}
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
                    {readiness.score_breakdown?.milestone_score ?? 0} / 40.0
                  </span>
                </div>
                <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                  <div
                    className="bg-indigo-600 h-2 rounded-full transition-all duration-500"
                    style={{ width: `${((readiness.score_breakdown?.milestone_score ?? 0) / 40.0) * 100}%` }}
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs font-medium text-slate-700 mb-1">
                  <span>Work Breakdown Task Completion (Max 15 pts)</span>
                  <span className="font-semibold text-indigo-600">
                    {readiness.score_breakdown?.task_completion_score ?? 0} / 15.0
                  </span>
                </div>
                <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                  <div
                    className="bg-indigo-600 h-2 rounded-full transition-all duration-500"
                    style={{ width: `${((readiness.score_breakdown?.task_completion_score ?? 0) / 15.0) * 100}%` }}
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs font-medium text-slate-700 mb-1">
                  <span>Critical Path CPM Health (Max 15 pts)</span>
                  <span className="font-semibold text-indigo-600">
                    {readiness.score_breakdown?.critical_path_score ?? 0} / 15.0
                  </span>
                </div>
                <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                  <div
                    className="bg-indigo-600 h-2 rounded-full transition-all duration-500"
                    style={{ width: `${((readiness.score_breakdown?.critical_path_score ?? 0) / 15.0) * 100}%` }}
                  />
                </div>
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* SECTION 1: ACADEMIC MILESTONES */}
      <Card
        title="Academic Checkpoint Milestones"
        subtitle="Key departmental checkpoints required for semester viva and progress evaluation."
      >
        {milestones.length === 0 ? (
          <p className="text-xs text-slate-400 italic">No milestones defined yet.</p>
        ) : (
          <div className="relative border-l-2 border-indigo-200 ml-4 pl-6 space-y-6 my-2">
            {milestones.map((m) => {
              const isCompleted = m.status === 'completed';
              const currentStatus = isCompleted ? 'completed' : 'pending';

              return (
                <div key={m.id} className="relative group">
                  {/* Dot on timeline */}
                  <div
                    onClick={() => handleToggleMilestone(m)}
                    className={`absolute -left-[31px] top-0.5 w-6 h-6 rounded-full flex items-center justify-center cursor-pointer transition-transform group-hover:scale-110 shadow-xs ${
                      isCompleted
                        ? 'bg-emerald-600 text-white'
                        : 'bg-white border-2 border-indigo-600 text-indigo-600'
                    }`}
                    title={isCompleted ? 'Mark as pending' : 'Mark as completed'}
                  >
                    {isCompleted ? <CheckCircle2 className="w-4 h-4" /> : <span className="text-[10px] font-bold">{m.sequence_number}</span>}
                  </div>

                  <div className="bg-slate-50/70 hover:bg-slate-50 p-4 rounded-xl border border-slate-200/80 transition-colors">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-xs font-bold text-slate-900">{m.title}</span>
                          <span className="text-[10px] uppercase font-bold text-slate-500 bg-slate-200/60 px-1.5 py-0.5 rounded">
                            {m.milestone_type.replace('_', ' ')}
                          </span>
                          {m.is_required ? (
                            <Badge variant="primary" size="sm">
                              Required
                            </Badge>
                          ) : (
                            <Badge variant="neutral" size="sm">
                              Optional
                            </Badge>
                          )}
                          <StatusBadge status={currentStatus} />
                        </div>
                        {m.description && (
                          <p className="text-xs text-slate-500 mt-1 leading-relaxed">
                            {m.description}
                          </p>
                        )}
                      </div>

                      <div className="flex flex-col items-end gap-2 shrink-0">
                        <div className="text-right">
                          <span className="text-xs font-semibold text-slate-700 block">
                            Planned: {m.planned_date}
                          </span>
                          {m.completed_at && (
                            <span className="text-[10px] text-emerald-600 font-medium block mt-0.5">
                              Done on {new Date(m.completed_at).toLocaleDateString()}
                            </span>
                          )}
                        </div>

                        {/* Action buttons: Edit & Delete */}
                        <div className="flex items-center gap-1.5 mt-1">
                          <button
                            type="button"
                            onClick={() => handleOpenEditModal(m)}
                            className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-medium text-indigo-700 bg-indigo-50 hover:bg-indigo-100 rounded-lg border border-indigo-200/60 transition-colors cursor-pointer"
                            title="Edit milestone details"
                          >
                            <Edit2 className="w-3 h-3" />
                            <span>Edit</span>
                          </button>
                          <button
                            type="button"
                            onClick={() => handleDeleteMilestone(m)}
                            className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-medium text-rose-700 bg-rose-50 hover:bg-rose-100 border border-rose-200/60 rounded-lg transition-colors cursor-pointer"
                            title="Delete this milestone"
                          >
                            <Trash2 className="w-3 h-3" />
                            <span>Delete</span>
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </Card>

      {/* SECTION 2: TEAM WORKLOAD BALANCING */}
      {workload && (
        <div className="space-y-6">
          <Card
            title="Team Workload Distribution & Balance Analytics"
            subtitle={`Effort allocation compared against semester capacity threshold of ${workload.threshold_hours}h.`}
          >
            {/* Workload Stats Bar */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
              <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200/80 text-center">
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                  Total Active Hours
                </span>
                <span className="text-xl font-bold text-indigo-700 mt-1 block">
                  {workload.total_team_active_hours}h
                </span>
              </div>

              <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200/80 text-center">
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                  Average per Student
                </span>
                <span className="text-xl font-bold text-slate-800 mt-1 block">
                  {workload.average_hours_per_student}h
                </span>
              </div>

              <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200/80 text-center">
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                  Capacity Threshold
                </span>
                <span className="text-xl font-bold text-slate-800 mt-1 block">
                  {workload.threshold_hours}h
                </span>
              </div>

              <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200/80 text-center">
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                  Workload StdDev
                </span>
                <span className="text-xl font-bold text-indigo-600 mt-1 block">
                  {workload.workload_standard_deviation}h
                </span>
              </div>
            </div>

            {/* Recharts Workload Bar Chart */}
            {chartData.length > 0 && (
              <div className="mt-6 mb-6">
                <h4 className="text-xs font-semibold text-slate-700 uppercase tracking-wider mb-4">
                  Student Effort Allocation vs Capacity Threshold ({workload.threshold_hours}h)
                </h4>
                <div className="h-64 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                      <XAxis dataKey="name" tick={{ fontSize: 12, fill: '#64748b' }} />
                      <YAxis tick={{ fontSize: 12, fill: '#64748b' }} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#ffffff',
                          borderRadius: '12px',
                          border: '1px solid #e2e8f0',
                          fontSize: '12px',
                        }}
                      />
                      <Legend />
                      <ReferenceLine
                        y={workload.threshold_hours}
                        stroke="#e11d48"
                        strokeDasharray="4 4"
                        label={{
                          value: `Capacity Threshold (${workload.threshold_hours}h)`,
                          fill: '#e11d48',
                          fontSize: 11,
                        }}
                      />
                      <Bar dataKey="active" name="Active Hours" fill="#6366f1" radius={[6, 6, 0, 0]} />
                      <Bar dataKey="completed" name="Completed Hours" fill="#10b981" radius={[6, 6, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}

            {/* Student Breakdown Table */}
            <div className="overflow-x-auto mt-4">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider">
                  <tr>
                    <th className="py-2.5 px-3">Student Name</th>
                    <th className="py-2.5 px-3">Role</th>
                    <th className="py-2.5 px-3">Active Hours</th>
                    <th className="py-2.5 px-3">Completed</th>
                    <th className="py-2.5 px-3">Overdue</th>
                    <th className="py-2.5 px-3">Load Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-slate-700">
                  {workload.student_workloads.map((s) => (
                    <tr key={s.user_id}>
                      <td className="py-3 px-3">
                        <span className="font-semibold text-slate-900 block">{s.full_name}</span>
                        <span className="text-[11px] text-slate-400 block">{s.email}</span>
                      </td>
                      <td className="py-3 px-3 capitalize">{s.team_role}</td>
                      <td className="py-3 px-3 font-semibold text-indigo-700">{s.total_active_hours}h</td>
                      <td className="py-3 px-3 text-emerald-600 font-medium">{s.completed_hours}h</td>
                      <td className="py-3 px-3">
                        {s.overdue_task_count > 0 ? (
                          <span className="text-rose-600 font-bold">{s.overdue_task_count} overdue</span>
                        ) : (
                          <span className="text-slate-400">0</span>
                        )}
                      </td>
                      <td className="py-3 px-3">
                        {s.is_overloaded ? (
                          <Badge variant="danger" size="sm">
                            Overloaded (&gt;{workload.threshold_hours}h)
                          </Badge>
                        ) : s.is_underutilized ? (
                          <Badge variant="info" size="sm">
                            Available Capacity
                          </Badge>
                        ) : (
                          <Badge variant="success" size="sm">
                            Optimal Load
                          </Badge>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Advisory Rebalancing Suggestions */}
            {workload.recommendations && workload.recommendations.length > 0 && (
              <div className="mt-6 p-4 rounded-xl bg-amber-50/70 border border-amber-200 text-xs">
                <div className="flex items-center gap-2 font-bold text-amber-900 mb-2">
                  <Sparkles className="w-4 h-4 text-amber-600" />
                  <span>Advisory Workload Rebalancing Recommendations</span>
                </div>
                <ul className="space-y-1.5 text-amber-800">
                  {workload.recommendations.map((rec, i) => (
                    <li key={i} className="flex items-start gap-1.5 leading-relaxed">
                      <span>•</span>
                      <span>{rec}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </Card>
        </div>
      )}

      {/* Milestone Modal (Add / Edit) */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false);
          setEditingMilestone(null);
        }}
        title={editingMilestone ? "Edit Academic Milestone" : "Add Academic Milestone"}
        subtitle={
          editingMilestone
            ? "Update milestone checkpoint title, planned date, sequence number, or required status."
            : "Configure an academic checkpoint with target planned date and required/optional setting."
        }
        maxWidth="md"
      >
        <form onSubmit={handleSubmitMilestone} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Milestone Title *
            </label>
            <input
              type="text"
              required
              value={mTitle}
              onChange={(e) => setMTitle(e.target.value)}
              placeholder="e.g. Design Presentation & Review 1"
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Description
            </label>
            <textarea
              rows={2}
              value={mDesc}
              onChange={(e) => setMDesc(e.target.value)}
              placeholder="Deliverables required for this milestone..."
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Milestone Type
              </label>
              <select
                value={mType}
                onChange={(e) => setMType(e.target.value as MilestoneType)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm"
              >
                <option value="topic_selection">Topic Selection</option>
                <option value="problem_statement">Problem Statement</option>
                <option value="literature_review">Literature Review</option>
                <option value="project_proposal">Project Proposal</option>
                <option value="requirement_analysis">Requirement Analysis</option>
                <option value="system_design">System Design</option>
                <option value="implementation">Implementation</option>
                <option value="review_1">Review 1</option>
                <option value="testing">Testing</option>
                <option value="review_2">Review 2</option>
                <option value="documentation">Documentation</option>
                <option value="final_presentation">Final Presentation</option>
                <option value="viva">Viva Defense</option>
                <option value="custom">Custom</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Sequence Number
              </label>
              <input
                type="number"
                min={1}
                required
                value={mSeq}
                onChange={(e) => setMSeq(Number(e.target.value))}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Planned Date *
              </label>
              <input
                type="date"
                required
                value={mDate}
                onChange={(e) => setMDate(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Status
              </label>
              <select
                value={mStatus}
                onChange={(e) => setMStatus(e.target.value as 'pending' | 'completed')}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm"
                data-testid="milestone-status-select"
              >
                <option value="pending">Pending</option>
                <option value="completed">Completed</option>
              </select>
            </div>
          </div>

          <div className="flex items-center pt-2">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={mRequired}
                onChange={(e) => setMRequired(e.target.checked)}
                className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500 w-4 h-4"
              />
              <span className="text-xs font-medium text-slate-700">Required Milestone</span>
            </label>
          </div>

          <div className="pt-3 border-t border-slate-100 flex justify-end gap-2">
            <button
              type="button"
              onClick={() => {
                setIsModalOpen(false);
                setEditingMilestone(null);
              }}
              className="px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl shadow-xs disabled:opacity-50 cursor-pointer"
            >
              {isSubmitting ? 'Saving...' : editingMilestone ? 'Update Milestone' : 'Add Milestone'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
