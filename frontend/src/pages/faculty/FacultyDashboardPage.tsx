import React, { useState, useEffect } from 'react';
import {
  GraduationCap,
  Calendar,
  Clock,
  CheckCircle2,
  AlertTriangle,
  Award,
  Users,
  ShieldAlert,
  ArrowRight,
  Plus,
  Flame,
  FileText,
  CalendarClock,
  CalendarX,
  Edit2,
} from 'lucide-react';
import { api } from '../../api/client';
import {
  AcademicProject,
  FacultyProjectOverview,
  ProjectReviewCreate,
  ProjectReviewUpdate,
  ProjectReview,
  ReviewStatus,
} from '../../types';
import { Card } from '../../components/common/Card';
import { Badge, StatusBadge } from '../../components/common/Badge';
import { Modal } from '../../components/common/Modal';
import { Alert } from '../../components/common/Alert';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { EmptyState } from '../../components/common/EmptyState';

export const FacultyDashboardPage: React.FC = () => {
  const [projects, setProjects] = useState<AcademicProject[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [overview, setOverview] = useState<FacultyProjectOverview | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isOverviewLoading, setIsOverviewLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Review Modal State
  const [isReviewModalOpen, setIsReviewModalOpen] = useState(false);
  const [editingReview, setEditingReview] = useState<ProjectReview | null>(null);
  const [reviewNumber, setReviewNumber] = useState(1);
  const [scheduledAt, setScheduledAt] = useState(
    new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().slice(0, 16)
  );
  const [reviewStatus, setReviewStatus] = useState<ReviewStatus>('scheduled');
  const [feedback, setFeedback] = useState('');
  const [score, setScore] = useState<number | undefined>(undefined);
  const [reviewError, setReviewError] = useState<string | null>(null);
  const [isSubmittingReview, setIsSubmittingReview] = useState(false);

  const fetchProjects = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.faculty.listProjects();
      setProjects(data);
      if (data.length > 0 && !selectedProjectId) {
        setSelectedProjectId(data[0].id);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load supervised projects.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  const fetchOverview = async (projId: string) => {
    setIsOverviewLoading(true);
    setReviewError(null);
    try {
      const data = await api.faculty.getOverview(projId);
      setOverview(data);
      setReviewNumber(data.reviews.length + 1);
    } catch (err: any) {
      setError(err.message || 'Failed to load project monitoring overview.');
    } finally {
      setIsOverviewLoading(false);
    }
  };

  useEffect(() => {
    if (selectedProjectId) {
      fetchOverview(selectedProjectId);
    }
  }, [selectedProjectId]);

  const handleOpenCreateModal = () => {
    setEditingReview(null);
    setReviewNumber(overview ? overview.reviews.length + 1 : 1);
    const d = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000);
    const offset = d.getTimezoneOffset() * 60000;
    setScheduledAt(new Date(d.getTime() - offset).toISOString().slice(0, 16));
    setReviewStatus('scheduled');
    setFeedback('');
    setScore(undefined);
    setReviewError(null);
    setIsReviewModalOpen(true);
  };

  const handleOpenEditModal = (review: ProjectReview) => {
    setEditingReview(review);
    setReviewNumber(review.review_number);
    try {
      const d = new Date(review.scheduled_at);
      const offset = d.getTimezoneOffset() * 60000;
      setScheduledAt(new Date(d.getTime() - offset).toISOString().slice(0, 16));
    } catch {
      setScheduledAt(review.scheduled_at.slice(0, 16));
    }
    setReviewStatus(review.status);
    setFeedback(review.feedback || '');
    setScore(review.score !== null && review.score !== undefined ? review.score : undefined);
    setReviewError(null);
    setIsReviewModalOpen(true);
  };

  const handleCancelReview = async (review: ProjectReview) => {
    if (!selectedProjectId) return;
    const confirmCancel = window.confirm(
      `Are you sure you want to cancel Review ${review.review_number}? All enrolled team members will be notified of this cancellation.`
    );
    if (!confirmCancel) return;

    try {
      await api.faculty.cancelReview(selectedProjectId, review.id);
      await fetchOverview(selectedProjectId);
    } catch (err: any) {
      setError(err.message || 'Failed to cancel academic review.');
    }
  };

  const handleSubmitReview = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProjectId) return;
    setIsSubmittingReview(true);
    setReviewError(null);

    try {
      if (editingReview) {
        const payload: ProjectReviewUpdate = {
          scheduled_at: new Date(scheduledAt).toISOString(),
          status: reviewStatus,
          feedback: feedback || undefined,
          score: score !== undefined && score !== null ? Number(score) : undefined,
        };
        await api.faculty.updateReview(selectedProjectId, editingReview.id, payload);
      } else {
        const payload: ProjectReviewCreate = {
          review_number: Number(reviewNumber),
          scheduled_at: new Date(scheduledAt).toISOString(),
          status: reviewStatus,
          feedback: feedback || undefined,
          score: score !== undefined && score !== null ? Number(score) : undefined,
        };
        await api.faculty.scheduleReview(selectedProjectId, payload);
      }
      setIsReviewModalOpen(false);
      setEditingReview(null);
      setFeedback('');
      setScore(undefined);
      await fetchOverview(selectedProjectId);
    } catch (err: any) {
      setReviewError(err.message || 'Failed to save academic review.');
    } finally {
      setIsSubmittingReview(false);
    }
  };

  if (isLoading) {
    return (
      <div className="py-20">
        <LoadingSpinner size="lg" label="Loading supervised academic projects..." />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-2xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <Badge variant="warning" size="md">Faculty Supervisor Portal</Badge>
              <span className="text-xs text-slate-500 font-medium">Academic Capstone Monitoring</span>
            </div>
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Supervised Student Projects</h1>
            <p className="text-xs text-slate-500 mt-1">
              Review readiness evaluation, milestone completion verification, student workload monitoring, and viva grading.
            </p>
          </div>
        </div>
      </div>

      {error && <Alert type="error">{error}</Alert>}

      {projects.length === 0 ? (
        <EmptyState
          title="No Projects Assigned"
          description="You are currently not listed as the faculty supervisor for any student projects. When students specify your account as their faculty guide during project creation, they will appear here."
        />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Projects Selection List */}
          <div className="lg:col-span-4 space-y-3">
            <h2 className="text-xs font-bold text-slate-500 uppercase tracking-wider px-1">
              Assigned Projects ({projects.length})
            </h2>
            <div className="space-y-2">
              {projects.map((p) => {
                const isSelected = p.id === selectedProjectId;
                return (
                  <div
                    key={p.id}
                    onClick={() => setSelectedProjectId(p.id)}
                    className={`p-4 rounded-xl border transition-all cursor-pointer ${
                      isSelected
                        ? 'bg-indigo-50/70 border-indigo-400 shadow-xs'
                        : 'bg-white border-slate-200/80 hover:bg-slate-50'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-700 bg-white border border-indigo-100 px-2 py-0.5 rounded">
                        {p.project_type}
                      </span>
                      <StatusBadge status={p.status} />
                    </div>
                    <h3 className="text-sm font-semibold text-slate-900 line-clamp-1">{p.title}</h3>
                    <div className="mt-2 text-xs text-slate-500 flex items-center justify-between">
                      <span>Owner: {p.owner?.full_name || 'Student'}</span>
                      <span className="font-medium text-slate-700">Sem {p.semester}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Project Detailed Overview Panel */}
          <div className="lg:col-span-8 space-y-6">
            {isOverviewLoading ? (
              <div className="py-20 bg-white rounded-2xl border border-slate-200/80">
                <LoadingSpinner size="md" label="Loading monitoring metrics and reviews..." />
              </div>
            ) : overview ? (
              <>
                {/* Active Project Card */}
                <div className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-2xs space-y-4">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <h2 className="text-lg font-bold text-slate-900">{overview.project.title}</h2>
                      <p className="text-xs text-slate-500 mt-0.5">
                        {overview.project.department} • Semester {overview.project.semester} • {overview.project.academic_year}
                      </p>
                    </div>
                    <button
                      onClick={handleOpenCreateModal}
                      className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-semibold shadow-xs transition-colors cursor-pointer shrink-0"
                    >
                      <Plus className="w-4 h-4" />
                      <span>Conduct / Schedule Review</span>
                    </button>
                  </div>

                  {/* Readiness Metrics */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-3 border-t border-slate-100">
                    <div className="p-3 bg-indigo-50/50 rounded-xl border border-indigo-100">
                      <span className="text-[10px] uppercase font-bold text-slate-400 block">Readiness Score</span>
                      <span className="text-2xl font-black text-indigo-700 mt-1 block">
                        {overview.readiness.readiness_score}/100
                      </span>
                    </div>

                    <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                      <span className="text-[10px] uppercase font-bold text-slate-400 block">Status Level</span>
                      <span className="text-xs font-bold text-slate-800 mt-2 block">
                        {overview.readiness.readiness_level}
                      </span>
                    </div>

                    <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                      <span className="text-[10px] uppercase font-bold text-slate-400 block">Active Team Load</span>
                      <span className="text-2xl font-bold text-slate-800 mt-1 block">
                        {overview.workload.total_team_active_hours}h
                      </span>
                    </div>

                    <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                      <span className="text-[10px] uppercase font-bold text-slate-400 block">Target Deadline</span>
                      <span className="text-xs font-semibold text-slate-700 mt-2 block">
                        {overview.project.target_deadline}
                      </span>
                    </div>
                  </div>

                  {/* Blockers Alert if any */}
                  {overview.readiness.blockers.length > 0 && (
                    <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-700">
                      <div className="flex items-center gap-1.5 font-bold text-rose-900 mb-1">
                        <ShieldAlert className="w-4 h-4 text-rose-600" />
                        <span>Active Viva Blockers Detected:</span>
                      </div>
                      <ul className="list-disc list-inside space-y-0.5">
                        {overview.readiness.blockers.map((b, i) => (
                          <li key={i}>{b}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>

                {/* Reviews History */}
                <Card
                  title="Academic Reviews & Viva History"
                  subtitle="Formal project milestones evaluated by the faculty guide."
                >
                  {overview.reviews.length === 0 ? (
                    <p className="text-xs text-slate-400 italic">
                      No reviews scheduled or scored yet. Click "Conduct / Schedule Review" to record viva feedback.
                    </p>
                  ) : (
                    <div className="divide-y divide-slate-100">
                      {overview.reviews.map((r) => (
                        <div key={r.id} className="py-3.5 flex items-start justify-between gap-4">
                          <div className="flex-1">
                            <div className="flex items-center gap-2">
                              <span className="font-bold text-slate-900 text-sm">
                                Review {r.review_number}
                              </span>
                              <StatusBadge status={r.status} />
                              {r.score !== null && r.score !== undefined && (
                                <Badge variant="success" size="sm">
                                  Score: {r.score}/100
                                </Badge>
                              )}
                            </div>
                            <span className="text-xs text-slate-400 block mt-0.5">
                              Scheduled: {new Date(r.scheduled_at).toLocaleString()}
                            </span>
                            {r.feedback && (
                              <p className="text-xs text-slate-600 bg-slate-50 p-2.5 rounded-lg border border-slate-100 mt-2 leading-relaxed">
                                💬 <strong>Faculty Feedback:</strong> {r.feedback}
                              </p>
                            )}
                          </div>
                          <div className="flex items-center gap-2 shrink-0">
                            <button
                              type="button"
                              onClick={() => handleOpenEditModal(r)}
                              className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200/60 rounded-lg transition-colors cursor-pointer"
                              title="Reschedule or edit review"
                            >
                              <Edit2 className="w-3 h-3" />
                              <span>Reschedule / Edit</span>
                            </button>
                            {r.status !== 'cancelled' && (
                              <button
                                type="button"
                                onClick={() => handleCancelReview(r)}
                                className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-rose-700 bg-rose-50 hover:bg-rose-100 border border-rose-200/60 rounded-lg transition-colors cursor-pointer"
                                title="Cancel this scheduled review"
                              >
                                <CalendarX className="w-3 h-3" />
                                <span>Cancel</span>
                              </button>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </Card>

                {/* Team Effort Monitoring */}
                <Card
                  title="Student Contributor Effort Allocation"
                  subtitle="Monitored effort distribution across enrolled student team members."
                >
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-50 text-slate-500 font-semibold uppercase tracking-wider">
                        <tr>
                          <th className="py-2 px-3">Student Name</th>
                          <th className="py-2 px-3">Role</th>
                          <th className="py-2 px-3">Active Hours</th>
                          <th className="py-2 px-3">Overdue Tasks</th>
                          <th className="py-2 px-3">Capacity Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 text-slate-700">
                        {overview.workload.student_workloads.map((s) => (
                          <tr key={s.user_id}>
                            <td className="py-2.5 px-3 font-semibold text-slate-900">{s.full_name}</td>
                            <td className="py-2.5 px-3 capitalize">{s.team_role}</td>
                            <td className="py-2.5 px-3 font-semibold text-indigo-700">{s.total_active_hours}h</td>
                            <td className="py-2.5 px-3">
                              {s.overdue_task_count > 0 ? (
                                <span className="text-rose-600 font-bold">{s.overdue_task_count}</span>
                              ) : (
                                <span className="text-slate-400">0</span>
                              )}
                            </td>
                            <td className="py-2.5 px-3">
                              {s.is_overloaded ? (
                                <Badge variant="danger" size="sm">Overloaded</Badge>
                              ) : (
                                <Badge variant="success" size="sm">Normal</Badge>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </Card>
              </>
            ) : null}
          </div>
        </div>
      )}

      {/* Review Scheduling & Scoring Modal */}
      <Modal
        isOpen={isReviewModalOpen}
        onClose={() => setIsReviewModalOpen(false)}
        title={editingReview ? `Reschedule / Edit Review ${editingReview.review_number}` : 'Schedule / Evaluate Academic Review'}
        subtitle={
          editingReview
            ? 'Update review timing, grading, or status. Enrolled students will be notified of schedule changes.'
            : 'Record formal review scores, scheduled viva dates, and evaluation feedback.'
        }
        maxWidth="md"
      >
        {reviewError && <Alert type="error" className="mb-4">{reviewError}</Alert>}

        <form onSubmit={handleSubmitReview} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Review Number
              </label>
              <input
                type="number"
                min={1}
                required
                disabled={!!editingReview}
                value={reviewNumber}
                onChange={(e) => setReviewNumber(Number(e.target.value))}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm disabled:opacity-60 disabled:bg-slate-100"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Review Status
              </label>
              <select
                value={reviewStatus}
                onChange={(e) => setReviewStatus(e.target.value as ReviewStatus)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm"
              >
                <option value="scheduled">Scheduled</option>
                <option value="in_progress">In Progress</option>
                <option value="completed">Completed / Scored</option>
                <option value="cancelled">Cancelled</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Date & Time *
            </label>
            <input
              type="datetime-local"
              required
              value={scheduledAt}
              onChange={(e) => setScheduledAt(e.target.value)}
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Evaluation Score (0 - 100)
            </label>
            <input
              type="number"
              min={0}
              max={100}
              step={0.5}
              value={score !== undefined ? score : ''}
              onChange={(e) => setScore(e.target.value ? Number(e.target.value) : undefined)}
              placeholder="Leave blank if not yet graded"
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Faculty Feedback & Viva Comments
            </label>
            <textarea
              rows={3}
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              placeholder="Comments on methodology, presentation quality, progress bottlenecks..."
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm"
            />
          </div>

          <div className="pt-3 border-t border-slate-100 flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setIsReviewModalOpen(false)}
              className="px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmittingReview}
              className="px-4 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl shadow-xs disabled:opacity-50 cursor-pointer"
            >
              {isSubmittingReview ? 'Saving...' : editingReview ? 'Update Review' : 'Schedule Review'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
