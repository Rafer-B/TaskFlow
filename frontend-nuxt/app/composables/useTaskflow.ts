export interface User {
  id: number
  name: string
  email: string
}

export interface Project {
  id: number
  name: string
  description: string
  category: string
  color: string
  archived: boolean
  owner_id: number
  created_at: string
  members: User[]
  task_count: number
  completed_count: number
}

export interface Task {
  id: number
  title: string
  description: string
  status: 'todo' | 'in_progress' | 'done' | 'blocked'
  priority: 'low' | 'medium' | 'high'
  category: string
  deadline: string | null
  project_id: number
  assignee_id: number | null
  assignee: User | null
  created_at: string
}

interface AuthResult {
  access_token: string
  user: User
}

export function useTaskflow() {
  const config = useRuntimeConfig()
  const token = useState<string | null>('taskflow-token', () => null)
  const user = useState<User | null>('taskflow-user', () => null)

  async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const headers = new Headers(options.headers)
    headers.set('Accept', 'application/json')
    if (options.body) headers.set('Content-Type', 'application/json')
    if (token.value) headers.set('Authorization', `Bearer ${token.value}`)

    const response = await fetch(`${config.public.apiBase}${path}`, { ...options, headers })
    if (!response.ok) {
      const body = await response.json().catch(() => null) as { detail?: string } | null
      throw new Error(body?.detail ?? 'Não foi possível concluir o pedido.')
    }
    if (response.status === 204) return undefined as T
    return response.json() as Promise<T>
  }

  async function authenticate(path: '/api/auth/login' | '/api/auth/register', payload: object) {
    const result = await request<AuthResult>(path, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
    token.value = result.access_token
    user.value = result.user
    if (import.meta.client) localStorage.setItem('taskflow-token', result.access_token)
    return result.user
  }

  async function restoreSession() {
    if (!import.meta.client) return
    const savedToken = localStorage.getItem('taskflow-token')
    if (!savedToken) return
    token.value = savedToken
    try {
      user.value = await request<User>('/api/auth/me')
    } catch {
      signOut()
    }
  }

  function signOut() {
    token.value = null
    user.value = null
    if (import.meta.client) localStorage.removeItem('taskflow-token')
  }

  return { token, user, request, authenticate, restoreSession, signOut }
}
