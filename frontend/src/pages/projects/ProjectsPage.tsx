import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Plus,
  Compass,
  Calendar,
  Clock,
  CheckCircle2,
  AlertCircle,
  GraduationCap,
  Building,
  User,
  ArrowRight,
} from 'lucide-react';
import { api } from '../../api/client';
import { AcademicProject, AcademicProjectCreate, ProjectType, UserSummary } from '../../types';
import { Card } from '../../components/common/Card';
import { Badge, StatusBadge } from '../../components/common/Badge';
import { Modal } from '../../components/common/Modal';
import { Alert } from '../../components/common/Alert';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { EmptyState } from '../../components/common/EmptyState';

export const ProjectsPage: React.FC = () => {
  const [projects, setProjects] = useState<AcademicProject[]>([]);
  const [facultyList, setFacultyList] = useState<UserSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Form State
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [academicYear, setAcademicYear] = useState('2025-2026');
  const [semester, setSemester] = useState(8);
  const [department, setDepartment] = useState('Computer Science & Engineering');
  const [projectType, setProjectType] = useState<ProjectType>('capstone');
  const [startDate, setStartDate] = useState(new Date().toISOString().split('T')[0]);
  const [targetDeadline, setTargetDeadline] = useState(
    new Date(Date.now() + 90 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
  );
  const [facultyGuideId, setFacultyGuideId] = useState('');
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchProjects = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [data, facData] = await Promise.all([
        api.projects.list(),
        api.faculty.listFacultyMembers().catch(() => []),
      ]);
      setProjects(data);
      setFacultyList(facData);
    } catch (err: any) {
      setError(err.message || 'Failed to load projects.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setIsSubmitting(true);

    const payload: AcademicProjectCreate = {
      title,
      description: description || undefined,
      academic_year: academicYear,
      semester: Number(semester),
      department,
      project_type: projectType,
      start_date: startDate,
      target_deadline: targetDeadline,
      faculty_guide_id: facultyGuideId ? facultyGuideId : undefined,
    };

    try {
      await api.projects.create(payload);
      setIsModalOpen(false);
      // Reset form
      setTitle('');
      setDescription('');
      setFacultyGuideId('');
      fetchProjects();
    } catch (err: any) {
      setFormError(err.message || 'Failed to create academic project.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const getDaysRemaining = (deadline: string) => {
    const target = new Date(deadline);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const diffTime = target.getTime() - today.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays;
  };

  return (
    <div className="space-y-6">
      {/* Top Action Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Academic Projects</h1>
          <p className="text-xs text-slate-500 mt-1">
            Manage capstone, major, and research scheduling with Priority, CPM & PERT algorithms.
          </p>
        </div>
        <button
          onClick={() => setIsModalOpen(true)}
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold shadow-xs hover:shadow-md transition-all cursor-pointer shrink-0"
        >
          <Plus className="w-4 h-4" />
          <span>New Academic Project</span>
        </button>
      </div>

      {error && (
        <Alert type="error" title="Error Loading Projects">
          {error}
        </Alert>
      )}

      {isLoading ? (
        <div className="py-16">
          <LoadingSpinner size="lg" label="Loading your academic projects..." />
        </div>
      ) : projects.length === 0 ? (
        <EmptyState
          title="No Academic Projects Yet"
          description="You are not enrolled in or managing any academic projects yet. Create your first capstone or research project to start planning milestones, tasks, and scheduling."
          action={
            <button
              onClick={() => setIsModalOpen(true)}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 text-white text-xs font-semibold hover:bg-indigo-700 transition-colors shadow-2xs cursor-pointer"
            >
              <Plus className="w-4 h-4" />
              <span>Create First Project</span>
            </button>
          }
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          {projects.map((proj) => {
            const daysLeft = getDaysRemaining(proj.target_deadline);
            const isOverdue = daysLeft < 0;

            return (
              <Card
                key={proj.id}
                className="flex flex-col justify-between hover:border-indigo-300 transition-colors"
                headerClassName="bg-slate-50/50"
              >
                <div>
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-md border border-indigo-100">
                      {proj.project_type}
                    </span>
                    <StatusBadge status={proj.status} />
                  </div>

                  <Link
                    to={`/projects/${proj.id}`}
                    className="block group"
                  >
                    <h2 className="text-base font-semibold text-slate-900 group-hover:text-indigo-600 transition-colors line-clamp-1">
                      {proj.title}
                    </h2>
                  </Link>

                  {proj.description && (
                    <p className="text-xs text-slate-500 mt-1.5 line-clamp-2 leading-relaxed">
                      {proj.description}
                    </p>
                  )}

                  <div className="mt-4 pt-3 border-t border-slate-100 space-y-2 text-xs text-slate-600">
                    <div className="flex items-center gap-2">
                      <GraduationCap className="w-3.5 h-3.5 text-slate-400" />
                      <span>Semester {proj.semester} • {proj.academic_year}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Building className="w-3.5 h-3.5 text-slate-400" />
                      <span className="truncate">{proj.department}</span>
                    </div>
                    {proj.faculty_guide && (
                      <div className="flex items-center gap-2 text-indigo-700 bg-indigo-50/50 px-2 py-1 rounded-md">
                        <User className="w-3.5 h-3.5 text-indigo-500" />
                        <span className="truncate">Guide: {proj.faculty_guide.full_name}</span>
                      </div>
                    )}
                  </div>
                </div>

                <div className="mt-6 pt-4 border-t border-slate-100">
                  <div className="flex items-center justify-between text-xs mb-3">
                    <span className="text-slate-400 flex items-center gap-1">
                      <Calendar className="w-3.5 h-3.5" />
                      <span>Deadline</span>
                    </span>
                    <span
                      className={`font-semibold ${
                        isOverdue ? 'text-rose-600 font-bold' : daysLeft <= 14 ? 'text-amber-600' : 'text-slate-700'
                      }`}
                    >
                      {proj.target_deadline} {isOverdue ? `(${Math.abs(daysLeft)}d overdue)` : `(${daysLeft}d left)`}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <Link
                      to={`/projects/${proj.id}`}
                      className="flex items-center justify-center gap-1.5 py-2 px-3 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 rounded-xl text-xs font-semibold transition-colors"
                    >
                      <Compass className="w-3.5 h-3.5" />
                      <span>Dashboard</span>
                    </Link>
                    <Link
                      to={`/projects/${proj.id}/scheduling`}
                      className="flex items-center justify-center gap-1.5 py-2 px-3 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-semibold transition-colors"
                    >
                      <Clock className="w-3.5 h-3.5" />
                      <span>Schedule</span>
                    </Link>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {/* Create Project Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Create Academic Project"
        subtitle="Set up your semester project with academic metadata and target deadlines."
        maxWidth="lg"
      >
        {formError && (
          <Alert type="error" className="mb-4">
            {formError}
          </Alert>
        )}

        <form onSubmit={handleCreateProject} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Project Title *
            </label>
            <input
              type="text"
              required
              minLength={3}
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Autonomous Robotic Navigation using CPM & PERT"
              className="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-hidden focus:ring-2 focus:ring-indigo-600 focus:bg-white text-slate-800"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Project Description
            </label>
            <textarea
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Brief summary of objectives, methodology, and deliverables..."
              className="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-hidden focus:ring-2 focus:ring-indigo-600 focus:bg-white text-slate-800"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Project Type
              </label>
              <select
                value={projectType}
                onChange={(e) => setProjectType(e.target.value as ProjectType)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-hidden focus:ring-2 focus:ring-indigo-600 focus:bg-white text-slate-800"
              >
                <option value="capstone">Capstone Project</option>
                <option value="major">Major Project</option>
                <option value="minor">Minor Project</option>
                <option value="research">Research Project</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Semester (1-12)
              </label>
              <input
                type="number"
                min={1}
                max={12}
                required
                value={semester}
                onChange={(e) => setSemester(Number(e.target.value))}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-hidden focus:ring-2 focus:ring-indigo-600 focus:bg-white text-slate-800"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Academic Year
              </label>
              <input
                type="text"
                required
                pattern="^\d{4}(-\d{4})?$"
                value={academicYear}
                onChange={(e) => setAcademicYear(e.target.value)}
                placeholder="2025-2026"
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-hidden focus:ring-2 focus:ring-indigo-600 focus:bg-white text-slate-800"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Department
              </label>
              <input
                type="text"
                required
                value={department}
                onChange={(e) => setDepartment(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-hidden focus:ring-2 focus:ring-indigo-600 focus:bg-white text-slate-800"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Start Date
              </label>
              <input
                type="date"
                required
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-hidden focus:ring-2 focus:ring-indigo-600 focus:bg-white text-slate-800"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Target Deadline
              </label>
              <input
                type="date"
                required
                value={targetDeadline}
                onChange={(e) => setTargetDeadline(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-hidden focus:ring-2 focus:ring-indigo-600 focus:bg-white text-slate-800"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Faculty Supervisor (Optional)
            </label>
            <select
              value={facultyGuideId}
              onChange={(e) => setFacultyGuideId(e.target.value)}
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-hidden focus:ring-2 focus:ring-indigo-600 focus:bg-white text-slate-800"
            >
              <option value="">No Guide Assigned Yet</option>
              {facultyList.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.full_name} ({f.email})
                </option>
              ))}
            </select>
            <p className="text-[11px] text-slate-400 mt-1">
              You can also assign or change your faculty supervisor later from the project overview.
            </p>
          </div>

          <div className="pt-4 border-t border-slate-100 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={() => setIsModalOpen(false)}
              className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-xl transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl transition-colors shadow-2xs disabled:opacity-50 cursor-pointer"
            >
              {isSubmitting ? 'Creating...' : 'Create Project'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
