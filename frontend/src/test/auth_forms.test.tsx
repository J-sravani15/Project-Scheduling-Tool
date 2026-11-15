import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { LoginPage } from '../pages/auth/LoginPage';
import { RegisterPage } from '../pages/auth/RegisterPage';
import { AuthProvider } from '../context/AuthContext';
import { api } from '../api/client';

vi.mock('../api/client', () => ({
  api: {
    auth: {
      login: vi.fn(),
      register: vi.fn(),
      me: vi.fn(),
      logout: vi.fn(),
    },
  },
  getToken: vi.fn(() => null),
  setToken: vi.fn(),
  onUnauthorized: vi.fn(),
}));

describe('Authentication Forms', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders login form elements and handles successful login', async () => {
    (api.auth.login as any).mockResolvedValueOnce({
      access_token: 'fake-jwt-token',
      token_type: 'bearer',
    });
    (api.auth.me as any).mockResolvedValueOnce({
      id: 'user-123',
      email: 'student@college.edu',
      full_name: 'Test Student',
      role: 'student',
    });

    render(
      <MemoryRouter>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </MemoryRouter>
    );

    expect(screen.getByText(/sign in to your account/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/student@college.edu/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/••••••••/i)).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText(/student@college.edu/i), {
      target: { value: 'student@college.edu' },
    });
    fireEvent.change(screen.getByPlaceholderText(/••••••••/i), {
      target: { value: 'Password123!' },
    });

    const submitBtn = screen.getByRole('button', { name: /sign in/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(api.auth.login).toHaveBeenCalledWith('student@college.edu', 'Password123!');
    });
  });

  it('displays error message when login fails', async () => {
    (api.auth.login as any).mockRejectedValueOnce(new Error('Invalid email or password.'));

    render(
      <MemoryRouter>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </MemoryRouter>
    );

    fireEvent.change(screen.getByPlaceholderText(/student@college.edu/i), {
      target: { value: 'wrong@college.edu' },
    });
    fireEvent.change(screen.getByPlaceholderText(/••••••••/i), {
      target: { value: 'WrongPassword' },
    });

    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByText(/invalid email or password/i)).toBeInTheDocument();
    });
  });

  it('renders registration form with role selection and handles submit', async () => {
    (api.auth.register as any).mockResolvedValueOnce({
      id: 'new-user-1',
      email: 'alex@college.edu',
      full_name: 'Alex Johnson',
      role: 'student',
    });
    (api.auth.login as any).mockResolvedValueOnce({
      access_token: 'fake-token-new',
      token_type: 'bearer',
    });
    (api.auth.me as any).mockResolvedValueOnce({
      id: 'new-user-1',
      email: 'alex@college.edu',
      full_name: 'Alex Johnson',
      role: 'student',
    });

    render(
      <MemoryRouter>
        <AuthProvider>
          <RegisterPage />
        </AuthProvider>
      </MemoryRouter>
    );

    expect(screen.getByText(/create an academic account/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /student/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /faculty guide/i })).toBeInTheDocument();

    // Toggle to Faculty
    fireEvent.click(screen.getByRole('button', { name: /faculty guide/i }));
    expect(screen.getByText(/faculty employee id/i)).toBeInTheDocument();

    // Toggle back to Student
    fireEvent.click(screen.getByRole('button', { name: /student/i }));
    expect(screen.getByText(/student roll number/i)).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText(/alex johnson/i), {
      target: { value: 'Alex Johnson' },
    });
    fireEvent.change(screen.getByPlaceholderText(/student@college.edu/i), {
      target: { value: 'alex@college.edu' },
    });
    fireEvent.change(screen.getByPlaceholderText(/at least 6 characters/i), {
      target: { value: 'SecretPassword123' },
    });

    fireEvent.click(screen.getByRole('button', { name: /complete registration/i }));

    await waitFor(() => {
      expect(api.auth.register).toHaveBeenCalledWith(
        expect.objectContaining({
          full_name: 'Alex Johnson',
          email: 'alex@college.edu',
          password: 'SecretPassword123',
          role: 'student',
        })
      );
    });
  });
});
