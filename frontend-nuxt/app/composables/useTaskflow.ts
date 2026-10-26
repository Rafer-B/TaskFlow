// Tipos das respostas da API; os campos e uniões refletem o contrato consumido pela interface.
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

export interface Comment {
  id: number
  content: string
  task_id: number
  user_id: number
  created_at: string
  user: User
}

export interface Notification {
  id: number
  title: string
  message: string
  notification_type: string
  is_read: boolean
  created_at: string
}

export interface Attachment {
  id: number
  file_name: string
  url: string
  file_type: string
  size_bytes: number
  task_id: number
  uploaded_by_id: number | null
  created_at: string
}

interface AuthResult {
  access_token: string
  user: User
}

export function useTaskflow() {
  const config = useRuntimeConfig()
  // `useState` mantém sessão reativa entre componentes e permite hidratação segura no Nuxt.
  const token = useState<string | null>('taskflow-token', () => null)
  const user = useState<User | null>('taskflow-user', () => null)

  // Cliente HTTP partilhado: junta cabeçalhos da sessão e normaliza erros da API/rede.
  async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const headers = new Headers(options.headers)
    headers.set('Accept', 'application/json')
    if (options.body && !(typeof FormData !== 'undefined' && options.body instanceof FormData)) {
      headers.set('Content-Type', 'application/json')
    }
    if (token.value) headers.set('Authorization', `Bearer ${token.value}`)

    let response: Response
    try {
      response = await fetch(`${config.public.apiBase}${path}`, { ...options, headers })
    } catch (cause) {
      if (cause instanceof TypeError) {
        throw new Error(
          'Não foi possível ligar à API. Confirma que o backend está em execução e que o endereço está correto.',
        )
      }
      throw cause
    }
    if (!response.ok) {
      const body = await response.json().catch(() => null) as { detail?: string } | null
      throw new Error(body?.detail ?? 'Não foi possível concluir o pedido.')
    }
    // Respostas 204 não têm corpo JSON; o cast adapta esse caso ao tipo genérico do pedido.
    if (response.status === 204) return undefined as T
    return response.json() as Promise<T>
  }

  async function downloadFile(path: string, fileName: string) {
    const headers = new Headers({ Accept: '*/*' })
    if (token.value) headers.set('Authorization', `Bearer ${token.value}`)

    let response: Response
    try {
      response = await fetch(`${config.public.apiBase}${path}`, { headers })
    } catch (cause) {
      if (cause instanceof TypeError) {
        throw new Error(
          'Não foi possível ligar à API. Confirma que o backend está em execução e que o endereço está correto.',
        )
      }
      throw cause
    }
    if (!response.ok) {
      const body = await response.json().catch(() => null) as { detail?: string } | null
      throw new Error(body?.detail ?? 'Não foi possível transferir o anexo.')
    }

    const objectUrl = URL.createObjectURL(await response.blob())
    const link = document.createElement('a')
    link.href = objectUrl
    link.download = fileName
    document.body.append(link)
    link.click()
    link.remove()
    window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000)
  }

  // Login e registo partilham o endpoint, guardando o token só no navegador.
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

  // Acesso ao armazenamento é exclusivo do cliente; o token guardado é validado novamente na API.
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

  // Limpa o estado reativo e o token persistido para terminar a sessão neste dispositivo.
  function signOut() {
    token.value = null
    user.value = null
    if (import.meta.client) localStorage.removeItem('taskflow-token')
  }

  return { token, user, request, downloadFile, authenticate, restoreSession, signOut }
}
