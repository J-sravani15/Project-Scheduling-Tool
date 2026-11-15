import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { ProtectedRoute } from '../components/auth/ProtectedRoute';
import * as AuthContextModule from '../context/AuthContext';

describe('Protected Routes & Role Guards', () => {
  it('redirects unauthenticated users to /login', () => {
    vi.spyOn(AuthContextModule, 'useAuth').mockReturnValue({
      user: null,
      token: null,
      isLoading: false,
      isAuthenticated: false,
      role: null,
      login: vi.fn(),
      register: vi.fn(),
      logout: vi.fn(),
      refreshUser: vi.fn(),
    });

    render(
      <MemoryRouter initialEntries={['/projects']}>
        <Routes>
          <Route path="/login" element={<div>Login Page Mock</div>} />
          <Route
            path="/projects"
            element={
              <ProtectedRoute>
                <div>Secret Project Page</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText('Login Page Mock')).toBeInTheDocument();
    expect(screen.queryByText('Secret Project Page')).not.toBeInTheDocument();
  });

  it('allows authenticated student to access student route', () => {
    vi.spyOn(AuthContextModule, 'useAuth').mockReturnValue({
      user: {
        id: 'u1',
        full_name: 'Student One',
        email: 'student@college.edu',
        role: 'student',
        is_active: true,
        created_at: '2026-01-01',
      },
      token: 'valid-token',
      isLoading: false,
      isAuthenticated: true,
      role: 'student',
      login: vi.fn(),
      register: vi.fn(),
      logout: vi.fn(),
      refreshUser: vi.fn(),
    });

    render(
      <MemoryRouter initialEntries={['/projects']}>
        <Routes>
          <Route
            path="/projects"
            element={
              <ProtectedRoute allowedRoles={['student']}>
                <div>Student Projects Dashboard</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText('Student Projects Dashboard')).toBeInTheDocument();
  });

  it('redirects student attempting to access faculty portal to /projects', () => {
    vi.spyOn(AuthContextModule, 'useAuth').mockReturnValue({
      user: {
        id: 'u1',
        full_name: 'Student One',
        email: 'student@college.edu',
        role: 'student',
        is_active: true,
        created_at: '2026-01-01',
      },
      token: 'valid-token',
      isLoading: false,
      isAuthenticated: true,
      role: 'student',
      login: vi.fn(),
      register: vi.fn(),
      logout: vi.fn(),
      refreshUser: vi.fn(),
    });

    render(
      <MemoryRouter initialEntries={['/faculty']}>
        <Routes>
          <Route path="/projects" element={<div>Student Projects Fallback</div>} />
          <Route
            path="/faculty"
            element={
              <ProtectedRoute allowedRoles={['faculty']}>
                <div>Faculty Only Portal</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText('Student Projects Fallback')).toBeInTheDocument();
    expect(screen.queryByText('Faculty Only Portal')).not.toBeInTheDocument();
  });
});
