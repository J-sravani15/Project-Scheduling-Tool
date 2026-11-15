import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ProtectedRoute } from './components/auth/ProtectedRoute';
import { AppLayout } from './components/layout/AppLayout';
import { LoginPage } from './pages/auth/LoginPage';
import { RegisterPage } from './pages/auth/RegisterPage';
import { ProjectsPage } from './pages/projects/ProjectsPage';
import { ProjectDashboardPage } from './pages/projects/ProjectDashboardPage';
import { SchedulingPage } from './pages/scheduling/SchedulingPage';
import { MilestonesWorkloadPage } from './pages/milestones/MilestonesWorkloadPage';
import { FacultyDashboardPage } from './pages/faculty/FacultyDashboardPage';

// Root redirect component based on authentication & role
const RootRedirect: React.FC = () => {
  const { isAuthenticated, role, isLoading } = useAuth();

  if (isLoading) {
    return null;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (role === 'faculty') {
    return <Navigate to="/faculty" replace />;
  }

  return <Navigate to="/projects" replace />;
};

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Public Auth Routes */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />

          {/* Root Redirect */}
          <Route path="/" element={<RootRedirect />} />

          {/* Protected Application Routes */}
          <Route
            element={
              <ProtectedRoute>
                <AppLayout />
              </ProtectedRoute>
            }
          >
            {/* Student Project Routes */}
            <Route
              path="/projects"
              element={
                <ProtectedRoute allowedRoles={['student']}>
                  <ProjectsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/projects/:projectId"
              element={
                <ProtectedRoute allowedRoles={['student']}>
                  <ProjectDashboardPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/projects/:projectId/scheduling"
              element={
                <ProtectedRoute allowedRoles={['student']}>
                  <SchedulingPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/projects/:projectId/milestones"
              element={
                <ProtectedRoute allowedRoles={['student']}>
                  <MilestonesWorkloadPage />
                </ProtectedRoute>
              }
            />

            {/* Faculty Guide Routes */}
            <Route
              path="/faculty"
              element={
                <ProtectedRoute allowedRoles={['faculty']}>
                  <FacultyDashboardPage />
                </ProtectedRoute>
              }
            />
          </Route>

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
};

export default App;
