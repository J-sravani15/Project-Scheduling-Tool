import React, { useState } from 'react';
import { Link, NavLink, Outlet, useNavigate, useParams, useLocation } from 'react-router-dom';
import {
  GraduationCap,
  LayoutDashboard,
  CalendarDays,
  Clock,
  LogOut,
  Menu,
  X,
  CheckCircle2,
  Users,
  Compass,
  FileCheck2,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { Badge } from '../common/Badge';
import { NotificationBell } from '../common/NotificationBell';

export const AppLayout: React.FC = () => {
  const { user, role, logout } = useAuth();
  const navigate = useNavigate();
  const { projectId } = useParams<{ projectId: string }>();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const isStudent = role === 'student';
  const isFaculty = role === 'faculty';

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* Top Academic Header */}
      <header className="sticky top-0 z-40 bg-white border-b border-slate-200/80 shadow-2xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="lg:hidden p-2 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-lg"
              aria-label="Toggle navigation menu"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
            <Link to={isFaculty ? '/faculty' : '/projects'} className="flex items-center gap-2.5 group">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-700 to-indigo-500 text-white flex items-center justify-center shadow-xs group-hover:scale-105 transition-transform">
                <GraduationCap className="w-6 h-6" />
              </div>
              <div>
                <span className="font-bold text-slate-900 text-base tracking-tight block leading-tight">
                  Student Project Scheduler
                </span>
                <span className="text-[11px] text-indigo-600 font-medium tracking-wide block">
                  Priority • CPM • PERT Engine
                </span>
              </div>
            </Link>
          </div>

          <div className="flex items-center gap-4">
            <div className="hidden sm:flex items-center gap-2 bg-slate-100/80 text-slate-700 px-3 py-1.5 rounded-lg text-xs font-medium">
              <CalendarDays className="w-3.5 h-3.5 text-indigo-600" />
              <span>Academic Year 2025–2026</span>
            </div>

            <NotificationBell />

            <div className="flex items-center gap-3 pl-3 border-l border-slate-200">
              <div className="text-right hidden sm:block">
                <span className="text-sm font-semibold text-slate-800 block leading-tight">
                  {user?.full_name}
                </span>
                <span className="text-[11px] text-slate-500 truncate block max-w-[180px]">
                  {user?.department || (isFaculty ? 'Faculty Guide' : 'Student')}
                </span>
              </div>
              <Badge variant={isFaculty ? 'warning' : 'primary'} size="sm">
                {isFaculty ? 'Faculty Guide' : 'Student'}
              </Badge>
              <button
                onClick={handleLogout}
                className="p-2 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
                title="Log out"
                aria-label="Log out"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <div className="flex-1 flex max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 gap-6">
        {/* Desktop Sidebar */}
        <aside className="hidden lg:block w-64 shrink-0">
          <div className="sticky top-22 space-y-6">
            <nav className="bg-white rounded-2xl border border-slate-200/80 p-3 shadow-2xs space-y-1">
              {isStudent && (
                <>
                  <div className="px-3 py-2 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                    Student Navigation
                  </div>
                  <NavLink
                    to="/projects"
                    end
                    className={({ isActive }) =>
                      `flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-colors ${
                        isActive && !projectId
                          ? 'bg-indigo-50 text-indigo-700 font-semibold shadow-2xs'
                          : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                      }`
                    }
                  >
                    <LayoutDashboard className="w-4 h-4" />
                    <span>All Projects</span>
                  </NavLink>

                  {projectId && (
                    <>
                      <div className="pt-3 pb-1 px-3 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                        Active Project
                      </div>
                      <NavLink
                        to={`/projects/${projectId}`}
                        end
                        className={({ isActive }) =>
                          `flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-colors ${
                            isActive
                              ? 'bg-indigo-50 text-indigo-700 font-semibold shadow-2xs'
                              : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                          }`
                        }
                      >
                        <Compass className="w-4 h-4" />
                        <span>Project Overview</span>
                      </NavLink>
                      <NavLink
                        to={`/projects/${projectId}/scheduling`}
                        className={({ isActive }) =>
                          `flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-colors ${
                            isActive
                              ? 'bg-indigo-50 text-indigo-700 font-semibold shadow-2xs'
                              : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                          }`
                        }
                      >
                        <Clock className="w-4 h-4" />
                        <span>Scheduling Workspace</span>
                      </NavLink>
                      <NavLink
                        to={`/projects/${projectId}/milestones`}
                        className={({ isActive }) =>
                          `flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-colors ${
                            isActive
                              ? 'bg-indigo-50 text-indigo-700 font-semibold shadow-2xs'
                              : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                          }`
                        }
                      >
                        <CheckCircle2 className="w-4 h-4" />
                        <span>Milestones & Workload</span>
                      </NavLink>
                    </>
                  )}
                </>
              )}

              {isFaculty && (
                <>
                  <div className="px-3 py-2 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                    Faculty Guide Hub
                  </div>
                  <NavLink
                    to="/faculty"
                    end
                    className={({ isActive }) =>
                      `flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-colors ${
                        isActive
                          ? 'bg-indigo-50 text-indigo-700 font-semibold shadow-2xs'
                          : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                      }`
                    }
                  >
                    <LayoutDashboard className="w-4 h-4" />
                    <span>Supervised Projects</span>
                  </NavLink>
                </>
              )}
            </nav>

            {/* Academic Scheduling Highlights Box */}
            <div className="p-4 rounded-2xl bg-gradient-to-br from-indigo-900 to-slate-900 text-white shadow-xs">
              <span className="text-[10px] font-bold uppercase tracking-widest text-indigo-300">
                Methodology
              </span>
              <h4 className="text-xs font-semibold text-white mt-1">Multi-Algorithm Engine</h4>
              <p className="text-[11px] text-slate-300 mt-1 leading-relaxed">
                Uses Priority Scheduling for task dispatching, CPM for critical path detection, and PERT for probabilistic viva planning.
              </p>
            </div>
          </div>
        </aside>

        {/* Mobile Navigation Drawer */}
        {mobileMenuOpen && (
          <div className="lg:hidden fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex">
            <div className="w-72 bg-white h-full p-5 shadow-2xl flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between pb-4 border-b border-slate-100">
                  <span className="font-bold text-slate-800 text-sm">Navigation</span>
                  <button onClick={() => setMobileMenuOpen(false)} className="p-1 text-slate-400">
                    <X className="w-5 h-5" />
                  </button>
                </div>
                <div className="mt-4 space-y-1">
                  {isStudent && (
                    <>
                      <NavLink
                        to="/projects"
                        onClick={() => setMobileMenuOpen(false)}
                        className="flex items-center gap-3 px-3 py-2 text-sm text-slate-700 rounded-lg hover:bg-slate-50"
                      >
                        <LayoutDashboard className="w-4 h-4" />
                        <span>All Projects</span>
                      </NavLink>
                      {projectId && (
                        <>
                          <NavLink
                            to={`/projects/${projectId}`}
                            onClick={() => setMobileMenuOpen(false)}
                            className="flex items-center gap-3 px-3 py-2 text-sm text-slate-700 rounded-lg hover:bg-slate-50"
                          >
                            <Compass className="w-4 h-4" />
                            <span>Project Overview</span>
                          </NavLink>
                          <NavLink
                            to={`/projects/${projectId}/scheduling`}
                            onClick={() => setMobileMenuOpen(false)}
                            className="flex items-center gap-3 px-3 py-2 text-sm text-slate-700 rounded-lg hover:bg-slate-50"
                          >
                            <Clock className="w-4 h-4" />
                            <span>Scheduling Workspace</span>
                          </NavLink>
                          <NavLink
                            to={`/projects/${projectId}/milestones`}
                            onClick={() => setMobileMenuOpen(false)}
                            className="flex items-center gap-3 px-3 py-2 text-sm text-slate-700 rounded-lg hover:bg-slate-50"
                          >
                            <CheckCircle2 className="w-4 h-4" />
                            <span>Milestones & Workload</span>
                          </NavLink>
                        </>
                      )}
                    </>
                  )}
                  {isFaculty && (
                    <NavLink
                      to="/faculty"
                      onClick={() => setMobileMenuOpen(false)}
                      className="flex items-center gap-3 px-3 py-2 text-sm text-slate-700 rounded-lg hover:bg-slate-50"
                    >
                      <LayoutDashboard className="w-4 h-4" />
                      <span>Supervised Projects</span>
                    </NavLink>
                  )}
                </div>
              </div>

              <div className="pt-4 border-t border-slate-100">
                <button
                  onClick={handleLogout}
                  className="w-full flex items-center justify-center gap-2 py-2 px-3 text-rose-600 bg-rose-50 hover:bg-rose-100 rounded-xl text-sm font-medium"
                >
                  <LogOut className="w-4 h-4" />
                  <span>Log Out</span>
                </button>
              </div>
            </div>
            <div className="flex-1" onClick={() => setMobileMenuOpen(false)} />
          </div>
        )}

        {/* Content Area */}
        <main className="flex-1 min-w-0">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
