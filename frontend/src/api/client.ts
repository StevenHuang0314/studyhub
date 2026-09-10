/**
 * Thin fetch wrapper around the StudyHub API.
 *
 * It attaches the bearer token, unwraps JSON, and turns FastAPI's error
 * payloads into a single ApiError with a readable message, so components can
 * just `catch (err) { setError(err.message) }`.
 */

import type {
  AuthResponse,
  Group,
  Note,
  NoteSort,
  Paginated,
  Rating,
  User,
} from '../types'

const TOKEN_KEY = 'studyhub.token'

export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string | null): void {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

/** FastAPI returns `detail` as either a string or a list of validation errors. */
function readErrorMessage(payload: unknown, status: number): string {
  if (payload && typeof payload === 'object' && 'detail' in payload) {
    const detail = (payload as { detail: unknown }).detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      const first = detail[0] as { loc?: unknown[]; msg?: string } | undefined
      if (first?.msg) {
        const field = Array.isArray(first.loc) ? String(first.loc[first.loc.length - 1]) : ''
        return field ? `${field}: ${first.msg}` : first.msg
      }
    }
  }
  return `Request failed (${status})`
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  if (options.body !== undefined) headers.set('Content-Type', 'application/json')
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)

  const response = await fetch(`/api${path}`, { ...options, headers })

  if (response.status === 204) return undefined as T

  const text = await response.text()
  const payload = text ? JSON.parse(text) : null

  if (!response.ok) {
    if (response.status === 401 && getToken()) setToken(null)
    throw new ApiError(readErrorMessage(payload, response.status), response.status)
  }
  return payload as T
}

function query(params: Record<string, string | number | boolean | undefined>): string {
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== '' && value !== false) search.set(key, String(value))
  })
  const stringified = search.toString()
  return stringified ? `?${stringified}` : ''
}

export interface NoteFilters {
  search?: string
  course_code?: string
  tag?: string
  sort?: NoteSort
  skip?: number
  limit?: number
}

export interface NotePayload {
  title: string
  content: string
  course_code: string
  tags: string[]
  resource_url: string
}

export interface GroupPayload {
  name: string
  description: string
  course_code: string
  meeting_time: string
  location: string
  capacity: number
}

export const api = {
  // auth
  register: (email: string, username: string, password: string) =>
    request<AuthResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, username, password }),
    }),
  login: (email: string, password: string) =>
    request<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),
  me: () => request<User>('/auth/me'),

  // notes
  listNotes: (filters: NoteFilters = {}) =>
    request<Paginated<Note>>(`/notes${query({ ...filters })}`),
  getNote: (id: number) => request<Note>(`/notes/${id}`),
  createNote: (payload: NotePayload) =>
    request<Note>('/notes', { method: 'POST', body: JSON.stringify(payload) }),
  updateNote: (id: number, payload: Partial<NotePayload>) =>
    request<Note>(`/notes/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteNote: (id: number) => request<void>(`/notes/${id}`, { method: 'DELETE' }),
  listCourses: () => request<string[]>('/notes/courses'),

  // ratings
  listRatings: (noteId: number) => request<Rating[]>(`/notes/${noteId}/ratings`),
  rateNote: (noteId: number, score: number, comment: string) =>
    request<Rating>(`/notes/${noteId}/ratings`, {
      method: 'PUT',
      body: JSON.stringify({ score, comment }),
    }),
  deleteMyRating: (noteId: number) =>
    request<void>(`/notes/${noteId}/ratings/me`, { method: 'DELETE' }),

  // groups
  listGroups: (filters: { search?: string; course_code?: string; has_space?: boolean } = {}) =>
    request<Paginated<Group>>(`/groups${query({ ...filters })}`),
  getGroup: (id: number) => request<Group>(`/groups/${id}`),
  createGroup: (payload: GroupPayload) =>
    request<Group>('/groups', { method: 'POST', body: JSON.stringify(payload) }),
  updateGroup: (id: number, payload: Partial<GroupPayload>) =>
    request<Group>(`/groups/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteGroup: (id: number) => request<void>(`/groups/${id}`, { method: 'DELETE' }),
  joinGroup: (id: number) => request<Group>(`/groups/${id}/members`, { method: 'POST' }),
  leaveGroup: (id: number) => request<void>(`/groups/${id}/members/me`, { method: 'DELETE' }),

  // dashboard
  myNotes: () => request<Note[]>('/users/me/notes'),
  myGroups: () => request<Group[]>('/users/me/groups'),
}
