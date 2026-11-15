import { describe, it, expect, beforeEach, vi } from 'vitest';
import { api, getToken, setToken, ApiError, onUnauthorized } from '../api/client';

describe('API Client and Storage', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('manages token storage correctly', () => {
    expect(getToken()).toBeNull();
    setToken('sample-jwt-token');
    expect(getToken()).toBe('sample-jwt-token');
    setToken(null);
    expect(getToken()).toBeNull();
  });

  it('captures structured API errors correctly', () => {
    const error = new ApiError(400, 'Assigned faculty guide must have FACULTY role.', {
      detail: 'Assigned faculty guide must have FACULTY role.',
    });
    expect(error.status).toBe(400);
    expect(error.message).toBe('Assigned faculty guide must have FACULTY role.');
    expect(error.name).toBe('ApiError');
  });

  it('invokes unauthorized handler on 401 response', async () => {
    const unauthorizedCallback = vi.fn();
    onUnauthorized(unauthorizedCallback);

    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: false,
      status: 401,
      statusText: 'Unauthorized',
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({ detail: 'Token has expired' }),
    } as any);

    await expect(api.projects.list()).rejects.toThrow('Token has expired');
    expect(unauthorizedCallback).toHaveBeenCalled();
  });

  it('handles successful API requests with token header injection', async () => {
    setToken('valid-auth-token');

    const mockFetch = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      status: 200,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => [{ id: 'p1', title: 'Smart Grid Capstone' }],
    } as any);

    const projects = await api.projects.list();
    expect(projects).toHaveLength(1);
    expect(projects[0].title).toBe('Smart Grid Capstone');

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/projects'),
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: 'Bearer valid-auth-token',
        }),
      })
    );
  });

  describe('Scheduling API Endpoints', () => {
    it('calls CPM endpoint via GET /projects/:id/schedule/cpm', async () => {
      const mockFetch = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({
          project_id: 'proj-123',
          total_project_duration_hours: 24,
          critical_tasks: ['t1'],
          critical_paths: [['t1']],
          tasks: {},
        }),
      } as any);

      const res = await api.scheduling.calculateCpm('proj-123');
      expect(res.project_id).toBe('proj-123');
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringMatching(/\/projects\/proj-123\/schedule\/cpm$/),
        expect.objectContaining({
          method: 'GET',
        })
      );
    });

    it('calls Priority endpoint via GET /projects/:id/schedule/priority', async () => {
      const mockFetch = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({
          project_id: 'proj-123',
          recommended_tasks: [],
          blocked_tasks: [],
          completed_tasks: [],
          weights: {},
        }),
      } as any);

      const res = await api.scheduling.calculatePriority('proj-123', undefined, '2026-03-01');
      expect(res.project_id).toBe('proj-123');
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringMatching(/\/projects\/proj-123\/schedule\/priority\?reference_date=2026-03-01$/),
        expect.objectContaining({
          method: 'GET',
        })
      );
    });

    it('calls PERT endpoint via POST /projects/:id/schedule/pert', async () => {
      const mockFetch = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({
          project_id: 'proj-123',
          critical_path_expected_duration_hours: 30,
          critical_path_variance: 2.5,
          critical_path_std_dev: 1.58,
          tasks: {},
        }),
      } as any);

      const estimates = [
        { task_id: 't1', optimistic_hours: 4, most_likely_hours: 6, pessimistic_hours: 8 },
      ];
      const res = await api.scheduling.calculatePert('proj-123', estimates, 35);
      expect(res.project_id).toBe('proj-123');
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringMatching(/\/projects\/proj-123\/schedule\/pert$/),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            estimates,
            target_deadline_hours: 35,
          }),
        })
      );
    });
  });
});
