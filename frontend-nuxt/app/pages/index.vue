<script setup lang="ts">
import completedIllustration from '~/assets/images/dashboard-completed-modern.svg'
import overdueIllustration from '~/assets/images/dashboard-overdue-modern.svg'
import pendingIllustration from '~/assets/images/dashboard-pending-modern.svg'
import projectsIllustration from '~/assets/images/dashboard-projects-modern.svg'
import type { Attachment, Comment, Notification, Project, Task, User } from '~/composables/useTaskflow'

const { token, user, request, downloadFile, authenticate, restoreSession, signOut } = useTaskflow()
// Estado de domínio e de navegação; `ref` permite que as alterações atualizem a vista.
const projects = ref<Project[]>([])
const tasks = ref<Task[]>([])
const dashboardTasks = ref<Task[]>([])
const comments = ref<Comment[]>([])
const notifications = ref<Notification[]>([])
const attachments = ref<Attachment[]>([])
const activeProjectId = ref<number | null>(null)
const activeView = ref<'overview' | 'projects' | 'project' | 'tasks' | 'calendar' | 'team' | 'documents' | 'notifications' | 'task'>('projects')
const selectedTaskId = ref<number | null>(null)
const attachmentInput = ref<HTMLInputElement | null>(null)
const uploadingAttachment = ref(false)
const commentDraft = ref('')
const calendarMonth = ref(new Date(new Date().getFullYear(), new Date().getMonth(), 1))
const showArchivedProjects = ref(false)
const members = ref<User[]>([])
const loading = ref(true)
const busy = ref(false)
const error = ref('')
const notice = ref('')
const authMode = ref<'login' | 'register'>('login')
const authName = ref('')
const authEmail = ref('')
const authPassword = ref('')
const showPassword = ref(false)
const showProjectForm = ref(false)
const showTaskForm = ref(false)
const showInvite = ref(false)
const accountMenuOpen = ref(false)
const editingProject = ref(false)
const projectForm = reactive({
  name: '',
  description: '',
  category: 'Desenvolvimento',
  color: '#6c63ff',
})
const taskForm = reactive({
  title: '',
  description: '',
  category: 'Execução',
  priority: 'medium',
  deadline: '',
  assignee_id: '',
})
const inviteEmail = ref('')
const statusFilter = ref('')
const priorityFilter = ref('')
const assigneeFilter = ref('')
const search = ref('')
const projectSearch = ref('')
const projectStatusFilter = ref('')
const today = new Date().toISOString().slice(0, 10)

// Seleções derivadas mantêm detalhes e contadores sincronizados com os dados carregados.
const activeProject = computed(() =>
  projects.value.find((project) => project.id === activeProjectId.value) ?? null,
)
const selectedTask = computed(() =>
  tasks.value.find((task) => task.id === selectedTaskId.value) ?? null,
)
const selectedTaskAttachments = computed(() =>
  attachments.value.filter((attachment) => attachment.task_id === selectedTaskId.value),
)
const unreadNotifications = computed(() => notifications.value.filter((item) => !item.is_read).length)
const calendarCells = computed(() => {
  const year = calendarMonth.value.getFullYear()
  const month = calendarMonth.value.getMonth()
  const firstWeekday = new Date(year, month, 1).getDay()
  // Ajusta o início para segunda-feira e cria seis semanas para uma grelha estável.
  const start = new Date(year, month, 1 - ((firstWeekday + 6) % 7))
  return Array.from({ length: 42 }, (_, index) => {
    const day = new Date(start.getFullYear(), start.getMonth(), start.getDate() + index)
    const key = `${day.getFullYear()}-${String(day.getMonth() + 1).padStart(2, '0')}-${String(day.getDate()).padStart(2, '0')}`
    return {
      key,
      day: day.getDate(),
      inMonth: day.getMonth() === month,
      tasks: dashboardTasks.value.filter((task) => task.deadline === key),
    }
  })
})
const visibleTasks = computed(() => tasks.value.filter((task) => {
  const matchesSearch = `${task.title} ${task.description}`.toLowerCase().includes(search.value.toLowerCase())
  return matchesSearch
    && (!statusFilter.value || task.status === statusFilter.value)
    && (!priorityFilter.value || task.priority === priorityFilter.value)
    && (!assigneeFilter.value || String(task.assignee_id) === assigneeFilter.value)
}))
const completedTasks = computed(() => tasks.value.filter((task) => task.status === 'done').length)
const progress = computed(() => tasks.value.length ? Math.round(completedTasks.value / tasks.value.length * 100) : 0)
const overdueTasks = computed(() => tasks.value.filter((task) => task.deadline && task.deadline < today && task.status !== 'done').length)
const initials = computed(() => user.value?.name.split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase() ?? 'TF')
// Os indicadores do resumo combinam tarefas de todos os projetos; a vista de detalhe usa `tasks`.
const projectDashboardStats = computed(() => ({
  active: projects.value.length,
  inProgress: dashboardTasks.value.filter((task) => task.status === 'in_progress').length,
  completed: dashboardTasks.value.filter((task) => task.status === 'done').length,
  atRisk: projects.value.filter((project) =>
    dashboardTasks.value.some((task) =>
      task.project_id === project.id && task.deadline && task.deadline < today && task.status !== 'done',
    ),
  ).length,
}))
const recentProjectTasks = computed(() => [...tasks.value]
  .sort((first, second) => second.created_at.localeCompare(first.created_at))
  .slice(0, 5))
const projectTeam = computed(() => {
  const team = new Map<number, User>()
  if (activeProject.value && user.value?.id === activeProject.value.owner_id) {
    team.set(user.value.id, user.value)
  }
  for (const member of members.value) team.set(member.id, member)
  return [...team.values()]
})
const filteredProjects = computed(() => projects.value.filter((project) => {
  const matchesSearch = `${project.name} ${project.category} ${project.description}`
    .toLowerCase()
    .includes(projectSearch.value.trim().toLowerCase())
  const projectTasks = dashboardTasks.value.filter((task) => task.project_id === project.id)
  const completion = projectTasks.length
    ? projectTasks.filter((task) => task.status === 'done').length / projectTasks.length
    : 0
  const atRisk = projectTasks.some((task) =>
    task.deadline && task.deadline < today && task.status !== 'done',
  )
  const matchesStatus = !projectStatusFilter.value
    || (projectStatusFilter.value === 'completed' && projectTasks.length > 0 && completion === 1)
    || (projectStatusFilter.value === 'in_progress' && projectStatus(project.id) === 'Em curso')
    || (projectStatusFilter.value === 'todo' && projectStatus(project.id) === 'Por iniciar')
    || (projectStatusFilter.value === 'at_risk' && atRisk)
  return matchesSearch && matchesStatus
}))

// Estado, prioridade e prazo do projeto são inferidos das tarefas carregadas para o dashboard.
function projectProgress(projectId: number) {
  const projectTasks = dashboardTasks.value.filter((task) => task.project_id === projectId)
  return projectTasks.length
    ? Math.round(projectTasks.filter((task) => task.status === 'done').length / projectTasks.length * 100)
    : 0
}

function projectStatus(projectId: number) {
  const projectTasks = dashboardTasks.value.filter((task) => task.project_id === projectId)
  if (projectTasks.length && projectTasks.every((task) => task.status === 'done')) return 'Concluído'
  if (projectTasks.some((task) =>
    task.deadline && task.deadline < today && task.status !== 'done',
  )) return 'Em risco'
  if (projectTasks.some((task) => task.status === 'in_progress')) return 'Em curso'
  return 'Por iniciar'
}

function projectPriority(projectId: number) {
  const priorities = dashboardTasks.value
    .filter((task) => task.project_id === projectId && task.status !== 'done')
    .map((task) => task.priority)
  if (priorities.includes('high')) return 'Alta'
  if (priorities.includes('medium')) return 'Média'
  if (priorities.includes('low')) return 'Baixa'
  return '—'
}

function projectPriorityClass(projectId: number) {
  const priority = projectPriority(projectId)
  if (priority === 'Alta') return 'high'
  if (priority === 'Média') return 'medium'
  if (priority === 'Baixa') return 'low'
  return 'none'
}

function projectDeadline(projectId: number) {
  const deadlines = dashboardTasks.value.flatMap((task) =>
    task.project_id === projectId && task.deadline && task.status !== 'done'
      ? [task.deadline]
      : [],
  ).sort()
  return deadlines[0] ?? null
}

function setError(message: unknown) {
  error.value = message instanceof Error ? message.message : 'Ocorreu um erro inesperado.'
  notice.value = ''
}

function clearMessages() {
  error.value = ''
  notice.value = ''
}

// Endpoints de carregamento alimentam separadamente a lista, o resumo e o projeto selecionado.
async function loadProjects() {
  projects.value = await request<Project[]>(`/api/projects?archived=${showArchivedProjects.value}`)
  if (!activeProjectId.value || !projects.value.some((project) => project.id === activeProjectId.value)) {
    activeProjectId.value = projects.value[0]?.id ?? null
  }
}

async function loadDashboardData() {
  const loaded = await Promise.all(
    projects.value.map((project) => request<Task[]>(`/api/projects/${project.id}/tasks`)),
  )
  dashboardTasks.value = loaded.flat()
}

async function loadNotifications() {
  notifications.value = await request<Notification[]>('/api/notifications')
}

async function openDocuments() {
  if (!activeProjectId.value) return
  activeView.value = 'documents'
  try {
    attachments.value = await request<Attachment[]>(
      `/api/projects/${activeProjectId.value}/attachments`,
    )
  } catch (cause) {
    setError(cause)
  }
}

async function loadProjectData() {
  if (!activeProjectId.value) {
    tasks.value = []
    members.value = []
    attachments.value = []
    return
  }
  const id = activeProjectId.value
  const [loadedTasks, loadedMembers, loadedAttachments] = await Promise.all([
    request<Task[]>(`/api/projects/${id}/tasks`),
    request<User[]>(`/api/projects/${id}/members`),
    request<Attachment[]>(`/api/projects/${id}/attachments`),
  ])
  if (activeProjectId.value === id) {
    tasks.value = loadedTasks
    members.value = loadedMembers
    attachments.value = loadedAttachments
  }
}

async function refresh() {
  if (!token.value) return
  try {
    await loadProjects()
    await Promise.all([loadProjectData(), loadDashboardData(), loadNotifications()])
  } catch (cause) {
    setError(cause)
  } finally {
    loading.value = false
  }
}

// Restaura a sessão apenas no cliente e recarrega os dados sempre que muda o projeto ativo.
onMounted(async () => {
  await restoreSession()
  if (token.value) await refresh()
  else loading.value = false
})

watch(activeProjectId, () => {
  if (token.value && !loading.value) loadProjectData().catch(setError)
})

async function submitAuth() {
  busy.value = true
  clearMessages()
  try {
    await authenticate(
      authMode.value === 'login' ? '/api/auth/login' : '/api/auth/register',
      authMode.value === 'login'
        ? { email: authEmail.value, password: authPassword.value }
        : { name: authName.value, email: authEmail.value, password: authPassword.value },
    )
    loading.value = true
    await refresh()
  } catch (cause) {
    setError(cause)
  } finally {
    busy.value = false
  }
}

// Os formulários reutilizam estado reativo; Object.assign atualiza os campos sem trocar o objeto.
function openProjectForm(project?: Project) {
  clearMessages()
  editingProject.value = Boolean(project)
  Object.assign(projectForm, project
    ? { name: project.name, description: project.description, category: project.category, color: project.color }
    : { name: '', description: '', category: 'Desenvolvimento', color: '#6c63ff' })
  showProjectForm.value = true
}

async function saveProject() {
  busy.value = true
  clearMessages()
  try {
    const path = editingProject.value ? `/api/projects/${activeProjectId.value}` : '/api/projects'
    await request(path, { method: editingProject.value ? 'PATCH' : 'POST', body: JSON.stringify(projectForm) })
    showProjectForm.value = false
    notice.value = editingProject.value ? 'Projeto atualizado.' : 'Projeto criado com sucesso.'
    await loadProjects()
    await loadDashboardData()
  } catch (cause) {
    setError(cause)
  } finally {
    busy.value = false
  }
}

// Operações de escrita atualizam a API e recarregam os dados afetados para refletir o resultado.
async function archiveProject() {
  if (!activeProject.value) return
  const action = activeProject.value.archived ? 'desarquivar' : 'arquivar'
  if (!window.confirm(`Queres ${action} este projeto?`)) return
  try {
    await request(`/api/projects/${activeProject.value.id}`, {
      method: 'PATCH',
      body: JSON.stringify({ archived: !activeProject.value.archived }),
    })
    notice.value = `Projeto ${activeProject.value.archived ? 'desarquivado' : 'arquivado'}.`
    await loadProjects()
    await Promise.all([loadProjectData(), loadDashboardData()])
  } catch (cause) {
    setError(cause)
  }
}

async function createTask() {
  if (!activeProjectId.value) return
  busy.value = true
  clearMessages()
  try {
    await request(`/api/projects/${activeProjectId.value}/tasks`, {
      method: 'POST',
      body: JSON.stringify({
        ...taskForm,
        deadline: taskForm.deadline || null,
        assignee_id: taskForm.assignee_id ? Number(taskForm.assignee_id) : user.value?.id,
      }),
    })
    showTaskForm.value = false
    Object.assign(taskForm, { title: '', description: '', category: 'Execução', priority: 'medium', deadline: '', assignee_id: '' })
    notice.value = 'Tarefa adicionada ao projeto.'
    await loadProjectData()
    await loadProjects()
    await loadDashboardData()
  } catch (cause) {
    setError(cause)
  } finally {
    busy.value = false
  }
}

async function updateTask(task: Task, changes: Partial<Task>) {
  if (!activeProjectId.value) return
  try {
    await request(`/api/projects/${activeProjectId.value}/tasks/${task.id}`, {
      method: 'PATCH',
      body: JSON.stringify(changes),
    })
    await loadProjectData()
    await loadProjects()
    await loadDashboardData()
  } catch (cause) {
    setError(cause)
  }
}

async function removeTask(task: Task) {
  if (!activeProjectId.value || !window.confirm(`Eliminar a tarefa "${task.title}"?`)) return
  try {
    await request(`/api/projects/${activeProjectId.value}/tasks/${task.id}`, { method: 'DELETE' })
    notice.value = 'Tarefa eliminada.'
    await loadProjectData()
    await loadProjects()
    await loadDashboardData()
  } catch (cause) {
    setError(cause)
  }
}

async function inviteMember() {
  if (!activeProjectId.value) return
  try {
    members.value = await request<User[]>(`/api/projects/${activeProjectId.value}/members`, {
      method: 'POST',
      body: JSON.stringify({ email: inviteEmail.value }),
    })
    inviteEmail.value = ''
    showInvite.value = false
    notice.value = 'Membro adicionado ao projeto.'
    await loadDashboardData()
  } catch (cause) {
    setError(cause)
  }
}

// Abrir tarefa também seleciona o respetivo projeto antes de carregar a conversa associada.
async function openTask(task: Task) {
  selectedTaskId.value = task.id
  activeProjectId.value = task.project_id
  comments.value = []
  commentDraft.value = ''
  activeView.value = 'task'
  try {
    comments.value = await request<Comment[]>(
      `/api/projects/${task.project_id}/tasks/${task.id}/comments`,
    )
  } catch (cause) {
    setError(cause)
  }
}

async function addComment() {
  if (!selectedTask.value || !commentDraft.value.trim()) return
  try {
    const comment = await request<Comment>(
      `/api/projects/${selectedTask.value.project_id}/tasks/${selectedTask.value.id}/comments`,
      { method: 'POST', body: JSON.stringify({ content: commentDraft.value }) },
    )
    comments.value.push(comment)
    commentDraft.value = ''
  } catch (cause) {
    setError(cause)
  }
}

async function uploadAttachment(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  const task = selectedTask.value
  input.value = ''
  if (!file || !task) return

  const formData = new FormData()
  formData.append('file', file)
  uploadingAttachment.value = true
  clearMessages()
  try {
    const attachment = await request<Attachment>(
      `/api/projects/${task.project_id}/tasks/${task.id}/attachments`,
      { method: 'POST', body: formData },
    )
    attachments.value = [attachment, ...attachments.value]
    notice.value = 'Anexo carregado.'
  } catch (cause) {
    setError(cause)
  } finally {
    uploadingAttachment.value = false
  }
}

async function downloadAttachment(event: MouseEvent, attachment: Attachment) {
  if (!attachment.url.startsWith('/api/')) return
  event.preventDefault()
  try {
    await downloadFile(attachment.url, attachment.file_name)
  } catch (cause) {
    setError(cause)
  }
}

async function markNotificationRead(notification: Notification) {
  if (notification.is_read) return
  try {
    const updated = await request<Notification>(
      `/api/notifications/${notification.id}/read`,
      { method: 'PATCH' },
    )
    notifications.value = notifications.value.map((item) =>
      item.id === updated.id ? updated : item,
    )
  } catch (cause) {
    setError(cause)
  }
}

// O construtor Date normaliza automaticamente mudanças de ano ao navegar entre meses.
function changeCalendarMonth(amount: number) {
  calendarMonth.value = new Date(
    calendarMonth.value.getFullYear(),
    calendarMonth.value.getMonth() + amount,
    1,
  )
}

function formatDate(date: string | null) {
  if (!date) return 'Sem prazo'
  return new Intl.DateTimeFormat('pt-PT', { day: 'numeric', month: 'short' }).format(new Date(`${date}T00:00:00`))
}

function formatFileSize(sizeBytes: number) {
  if (sizeBytes < 1024 * 1024) return `${(sizeBytes / 1024).toFixed(1)} KB`
  return `${(sizeBytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatCommentDate(value: string) {
  return new Intl.DateTimeFormat('pt-PT', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}

function statusLabel(status: string) {
  return ({ todo: 'Por iniciar', in_progress: 'Em curso', done: 'Concluída', blocked: 'Bloqueada' })[status] ?? status
}

function priorityLabel(priority: string) {
  return ({ low: 'Baixa', medium: 'Média', high: 'Alta' })[priority] ?? priority
}

// Terminar sessão também descarta dados em memória para não os mostrar a outra conta.
function handleSignOut() {
  accountMenuOpen.value = false
  signOut()
  projects.value = []
  tasks.value = []
  dashboardTasks.value = []
  notifications.value = []
  comments.value = []
  attachments.value = []
  activeView.value = 'projects'
  activeProjectId.value = null
  loading.value = false
}
</script>

<template>
  <!-- Visitantes recebem o formulário; após autenticação, a mesma rota mostra o espaço de trabalho. -->
  <main v-if="!user" class="auth-page">
    <section class="auth-panel">
      <NuxtLink to="/" class="brand auth-brand"><span class="brand-mark">TF</span><span>taskflow<span class="brand-period">.</span></span></NuxtLink>
      <div class="auth-copy">
        <h1>A solução completa<br>para gerir os teus<br>projetos.</h1>
        <p>Organiza tarefas, cumpre prazos e colabora com a tua equipa — tudo num só lugar.</p>
        <img
          class="auth-illustration"
          src="~/assets/images/taskflow-academic-projects.svg"
          alt="Ilustração de um computador com calendário, lista de tarefas e progresso de projetos académicos"
          width="620"
          height="360"
        >
        <div class="auth-proof">
          <div class="avatar-stack"><span>R</span><span>M</span><span>A</span></div>
          <span>Equipas a transformar ideias em resultados.</span>
        </div>
        <ul class="auth-benefits">
          <li>Planeia e acompanha cada tarefa</li>
          <li>Coordena o trabalho da tua equipa</li>
          <li>Mantém todos os prazos sob controlo</li>
        </ul>
      </div>
      <p class="auth-foot">ARROW4D <span>·</span> TASKFLOW</p>
    </section>
    <section class="auth-form-wrap">
      <div class="auth-form">
        <div class="mobile-brand brand"><span class="brand-mark">TF</span><span>taskflow<span class="brand-period">.</span></span></div>
        <img
          class="auth-mobile-illustration"
          src="~/assets/images/taskflow-academic-projects.svg"
          alt="Computador com calendário, tarefas e progresso de projetos académicos"
          width="620"
          height="360"
        >
        <div class="form-heading">
          <h2>{{ authMode === 'login' ? 'Bem-vindo de volta!' : 'Cria a tua conta' }}</h2>
          <p>
            {{ authMode === 'login' ? 'Ainda não tens conta?' : 'Já tens uma conta?' }}
            <button type="button" @click="authMode = authMode === 'login' ? 'register' : 'login'; clearMessages()">
              {{ authMode === 'login' ? 'Criar conta' : 'Iniciar sessão' }}
            </button>
          </p>
        </div>
        <form class="stack-form" @submit.prevent="submitAuth">
          <label v-if="authMode === 'register'" class="field-label">Nome completo
            <input v-model="authName" autocomplete="name" placeholder="Como te chamamos?" minlength="2" required>
          </label>
          <label class="field-label">Endereço de email
            <input v-model="authEmail" autocomplete="email" type="email" placeholder="Introduz o teu email" required>
          </label>
          <label class="field-label">Palavra-passe
            <span class="password-field">
              <input v-model="authPassword" :autocomplete="authMode === 'login' ? 'current-password' : 'new-password'" :type="showPassword ? 'text' : 'password'" placeholder="Introduz a tua palavra-passe" minlength="8" required>
              <button
                class="password-toggle"
                type="button"
                :aria-label="showPassword ? 'Ocultar palavra-passe' : 'Mostrar palavra-passe'"
                :aria-pressed="showPassword"
                @click="showPassword = !showPassword"
              >
                <svg v-if="showPassword" viewBox="0 0 24 24" aria-hidden="true"><path d="M3 3l18 18M10.6 10.6a2 2 0 002.8 2.8M9.9 5.2A10.8 10.8 0 0112 5c5 0 8.5 4.2 9.5 7-.4 1.1-1.2 2.3-2.3 3.3M6.2 6.2C4.2 7.5 2.9 9.5 2.5 12c.9 2.8 4.5 7 9.5 7 1.4 0 2.7-.4 3.8-1" /></svg>
                <svg v-else viewBox="0 0 24 24" aria-hidden="true"><path d="M2.5 12C3.5 9.2 7 5 12 5s8.5 4.2 9.5 7c-1 2.8-4.5 7-9.5 7s-8.5-4.2-9.5-7z" /><circle cx="12" cy="12" r="2.5" /></svg>
              </button>
            </span>
          </label>
          <p v-if="error" class="message message-error">{{ error }}</p>
          <button class="button button-primary button-wide" :disabled="busy">
            {{ busy ? 'A processar…' : authMode === 'login' ? 'Iniciar sessão' : 'Criar conta' }}
          </button>
        </form>
        <p class="auth-legal">Ao continuar, concordas com a utilização responsável da plataforma.</p>
      </div>
    </section>
  </main>

  <!-- A navegação lateral escolhe vistas sem trocar de rota; a área principal renderiza a vista ativa. -->
  <main v-else class="workspace" :class="{ 'projects-workspace': ['projects', 'project', 'task'].includes(activeView), 'project-detail-workspace': activeView === 'project', 'task-detail-workspace': activeView === 'task' }">
    <aside class="sidebar">
      <NuxtLink to="/" class="brand"><span class="brand-mark">TF</span><span>taskflow<span class="brand-period">.</span></span></NuxtLink>
      <div class="workspace-label"><span class="workspace-avatar">A</span><span><strong>ARROW4D</strong><small>Workspace académico</small></span><span class="chevron">⌄</span></div>
      <div class="nav-heading">MENU</div>
      <button class="nav-link" :class="{ active: activeView === 'overview' }" @click="activeView = 'overview'"><span class="nav-icon">▦</span> Início</button>
      <button class="nav-link" :class="{ active: activeView === 'projects' }" @click="activeView = 'projects'"><span class="nav-icon">▤</span> Projetos</button>
      <button class="nav-link" :class="{ active: activeView === 'tasks' }" @click="activeView = 'tasks'"><span class="nav-icon">✓</span> Tarefas</button>
      <button class="nav-link" :class="{ active: activeView === 'calendar' }" @click="activeView = 'calendar'"><span class="nav-icon">▦</span> Calendário</button>
      <button class="nav-link" :class="{ active: activeView === 'team' }" @click="activeView = 'team'"><span class="nav-icon">♧</span> Equipa</button>
      <button class="nav-link" :class="{ active: activeView === 'notifications' }" @click="activeView = 'notifications'"><span class="nav-icon">♧</span> Notificações <span v-if="unreadNotifications" class="nav-badge">{{ unreadNotifications }}</span></button>
      <div class="project-heading"><span>{{ showArchivedProjects ? 'PROJETOS ARQUIVADOS' : 'OS TEUS PROJETOS' }}</span><span class="project-heading-actions"><button :aria-label="showArchivedProjects ? 'Ver projetos ativos' : 'Ver projetos arquivados'" :title="showArchivedProjects ? 'Ver projetos ativos' : 'Ver projetos arquivados'" @click="showArchivedProjects = !showArchivedProjects; loadProjects()">⌑</button><button aria-label="Criar projeto" title="Criar projeto" @click="openProjectForm()">＋</button></span></div>
      <div class="project-nav">
        <button v-for="project in projects" :key="project.id" class="project-link" :class="{ selected: project.id === activeProjectId }" @click="activeProjectId = project.id; activeView = 'project'">
          <span class="project-dot" :style="{ background: project.color }"></span>
          <span class="project-link-copy"><strong>{{ project.name }}</strong><small>{{ project.category }}</small></span>
          <span class="project-count">{{ project.task_count }}</span>
        </button>
        <div v-if="projects.length === 0 && !loading" class="empty-sidebar">Ainda sem projetos.<br>Cria o primeiro!</div>
      </div>
      <div class="sidebar-bottom">
        <div class="help-card"><span class="help-spark">✳</span><strong>Um passo de cada vez.</strong><p>Grandes projetos começam com tarefas pequenas.</p></div>
        <div class="profile-row"><span class="profile-avatar">{{ initials }}</span><span class="profile-copy"><strong>{{ user.name }}</strong><small>{{ user.email }}</small></span><button class="sign-out-button" title="Terminar sessão" @click="handleSignOut"><span aria-hidden="true">↪</span> Sair</button></div>
      </div>
    </aside>

    <section class="main-area">
      <header class="topbar">
        <div v-if="activeView === 'projects'" class="projects-top-heading"><strong>Projetos</strong><small>Gere e acompanha os teus projetos ativos</small></div>
        <div v-else-if="activeView === 'project' && activeProject" class="projects-top-heading project-detail-breadcrumb"><button @click="activeView = 'projects'">Projetos</button><span>/</span><strong>Detalhes do projeto</strong></div>
        <div v-else class="breadcrumb"><span>Workspace</span><span class="crumb-sep">/</span><strong>{{ ['project', 'documents'].includes(activeView) ? activeProject?.name : ({ overview: 'Início', projects: 'Projetos', tasks: 'Tarefas', calendar: 'Calendário', team: 'Equipa', documents: 'Documentos', notifications: 'Notificações', task: 'Detalhe da tarefa' }[activeView] ?? 'Início') }}</strong></div>
        <div class="topbar-actions">
          <label v-if="activeView === 'projects'" class="projects-top-search"><span aria-hidden="true">⌕</span><input v-model="projectSearch" placeholder="Pesquisar..." aria-label="Pesquisar projetos"></label>
          <span v-else class="today-label">{{ new Intl.DateTimeFormat('pt-PT', { weekday: 'long', day: 'numeric', month: 'long' }).format(new Date()) }}</span>
          <button v-if="['projects', 'project', 'task'].includes(activeView)" class="projects-notifications" aria-label="Ver notificações" @click="activeView = 'notifications'">♧<i v-if="unreadNotifications"></i></button>
          <div class="account-menu-wrap"><button class="profile-avatar top-profile" :title="user.name" :aria-label="`Menu da conta de ${user.name}`" :aria-expanded="accountMenuOpen" @click="accountMenuOpen = !accountMenuOpen">{{ initials }}</button><div v-if="accountMenuOpen" class="account-menu"><strong>{{ user.name }}</strong><span>{{ user.email }}</span><button @click="handleSignOut"><span aria-hidden="true">↪</span> Terminar sessão</button></div></div>
        </div>
      </header>

      <div class="page-content">
        <div v-if="error" class="message message-error global-message"><span>{{ error }}</span><button @click="clearMessages">×</button></div>
        <div v-if="notice" class="message message-success global-message"><span>{{ notice }}</span><button @click="notice = ''">×</button></div>

        <!-- Resumo transversal: estatísticas e prazos são calculados sobre todas as tarefas acessíveis. -->
        <template v-if="activeView === 'overview'">
          <div class="page-intro">
            <div class="page-title-group"><span class="eyebrow"><span class="eyebrow-dot"></span> O TEU ESPAÇO DE TRABALHO</span><h1>Olá, {{ user.name.split(' ')[0] }}!</h1><p>Aqui está o resumo dos teus projetos e do que merece atenção.</p></div>
            <div class="intro-actions"><button class="button button-primary" @click="openProjectForm()">＋ Novo projeto</button></div>
          </div>
          <section class="stats-grid">
            <article class="stat-card stat-card-modern stat-card-projects"><div class="stat-illustration-wrapper"><img class="stat-illustration" :src="projectsIllustration" alt="" aria-hidden="true"></div><div class="stat-top"><span class="stat-caption">PROJETOS ATIVOS</span></div><div class="stat-value">{{ projects.length }}</div><div class="stat-foot">Os teus espaços de trabalho</div></article>
            <article class="stat-card stat-card-modern stat-card-pending"><div class="stat-illustration-wrapper"><img class="stat-illustration" :src="pendingIllustration" alt="" aria-hidden="true"></div><div class="stat-top"><span class="stat-caption">TAREFAS PENDENTES</span></div><div class="stat-value">{{ dashboardTasks.filter((task) => task.status !== 'done').length }}</div><div class="stat-foot">Em todos os projetos</div></article>
            <article class="stat-card stat-card-modern stat-card-completed"><div class="stat-illustration-wrapper"><img class="stat-illustration" :src="completedIllustration" alt="" aria-hidden="true"></div><div class="stat-top"><span class="stat-caption">CONCLUÍDAS</span></div><div class="stat-value">{{ dashboardTasks.filter((task) => task.status === 'done').length }}</div><div class="stat-foot"><span class="positive-dot"></span> Cada passo conta</div></article>
            <article class="stat-card stat-card-modern stat-card-overdue"><div class="stat-illustration-wrapper"><img class="stat-illustration" :src="overdueIllustration" alt="" aria-hidden="true"></div><div class="stat-top"><span class="stat-caption">TAREFAS EM ATRASO</span></div><div class="stat-value">{{ dashboardTasks.filter((task) => task.deadline && task.deadline < today && task.status !== 'done').length }}</div><div class="stat-foot">Precisam da tua atenção</div></article>
          </section>
          <section class="tasks-section overview-tasks">
            <div class="section-header"><div><span class="section-kicker">PRÓXIMOS PASSOS</span><h2>Tarefas próximas do prazo</h2></div><button class="text-button" @click="activeView = 'tasks'">Ver todas →</button></div>
            <div v-if="dashboardTasks.filter((task) => task.status !== 'done').length" class="overview-task-list">
              <button v-for="task in dashboardTasks.filter((item) => item.status !== 'done').slice(0, 6)" :key="task.id" class="overview-task" @click="openTask(task)">
                <span class="project-dot" :style="{ background: projects.find((project) => project.id === task.project_id)?.color ?? '#7165e8' }"></span>
                <span class="overview-task-copy"><strong>{{ task.title }}</strong><small>{{ projects.find((project) => project.id === task.project_id)?.name ?? 'Projeto' }} · {{ formatDate(task.deadline) }}</small></span>
                <span class="priority-pill" :class="`priority-${task.priority}`"><i></i>{{ priorityLabel(task.priority) }}</span>
              </button>
            </div>
            <div v-else class="empty-state"><span class="empty-icon">✳</span><h3>Está tudo em dia.</h3><p>Cria um projeto ou tarefa para começares.</p><button class="button button-primary" @click="openProjectForm()">＋ Novo projeto</button></div>
          </section>
          <section class="tasks-section">
            <div class="section-header"><div><span class="section-kicker">VISÃO GERAL</span><h2>Os teus projetos</h2></div><button class="text-button" @click="activeView = 'projects'">Ver projetos →</button></div>
            <div class="project-card-grid">
              <button v-for="project in projects.slice(0, 3)" :key="project.id" class="project-card" @click="activeProjectId = project.id; activeView = 'project'">
                <span class="project-card-icon" :style="{ color: project.color, background: `${project.color}18` }">▤</span><span class="project-card-state">Em curso</span>
                <strong>{{ project.name }}</strong><small>{{ project.category }} · {{ project.task_count }} tarefas</small>
                <span class="project-progress"><i :style="{ width: `${project.task_count ? Math.round(project.completed_count / project.task_count * 100) : 0}%`, background: project.color }"></i></span>
                <span class="project-progress-label">{{ project.task_count ? Math.round(project.completed_count / project.task_count * 100) : 0 }}% concluído</span>
              </button>
            </div>
          </section>
        </template>

        <!-- Pesquisa e filtros afetam a coleção visível sem alterar os projetos originais. -->
        <template v-else-if="activeView === 'projects'">
          <section class="project-metrics" aria-label="Resumo dos projetos">
            <article class="project-metric metric-projects"><strong>{{ projectDashboardStats.active }}</strong><span>{{ showArchivedProjects ? 'Projetos arquivados' : 'Projetos ativos' }}</span></article>
            <article class="project-metric metric-progress"><strong>{{ projectDashboardStats.inProgress }}</strong><span>Tarefas em curso</span></article>
            <article class="project-metric metric-completed"><strong>{{ projectDashboardStats.completed }}</strong><span>Tarefas concluídas</span></article>
            <article class="project-metric metric-risk"><strong>{{ projectDashboardStats.atRisk }} <small>{{ projectDashboardStats.atRisk === 1 ? 'projeto' : 'projetos' }}</small></strong><span>Em risco</span></article>
          </section>
          <section class="projects-board">
            <header class="projects-board-header">
              <div><h1>Todos os projetos</h1><p>{{ filteredProjects.length }} {{ filteredProjects.length === 1 ? 'projeto' : 'projetos' }} visíveis</p></div>
              <div class="projects-board-actions">
                <label class="projects-filter"><span class="sr-only">Filtrar projetos por estado</span><span aria-hidden="true">☷</span><select v-model="projectStatusFilter"><option value="">Todos os estados</option><option value="todo">Por iniciar</option><option value="in_progress">Em curso</option><option value="completed">Concluídos</option><option value="at_risk">Em risco</option></select></label>
                <button class="button button-primary projects-create-button" @click="openProjectForm()"><span aria-hidden="true">＋</span> Novo projeto</button>
              </div>
            </header>
            <div v-if="loading" class="loading-state"><span class="spinner"></span> A carregar projetos…</div>
            <div v-else-if="filteredProjects.length" class="project-card-grid project-card-grid-dashboard">
              <article v-for="project in filteredProjects" :key="project.id" class="project-dashboard-card">
                <header class="project-dashboard-card-header">
                  <button class="project-dashboard-title" @click="activeProjectId = project.id; activeView = 'project'">{{ project.name }}</button>
                  <span class="project-dashboard-project-icon" :style="{ color: project.color, background: `${project.color}18` }" :title="project.category">▤</span>
                </header>
                <div class="project-card-badges">
                  <span class="project-status-badge" :class="{ 'project-status-completed': projectStatus(project.id) === 'Concluído', 'project-status-risk': projectStatus(project.id) === 'Em risco', 'project-status-progress': projectStatus(project.id) === 'Em curso', 'project-status-todo': projectStatus(project.id) === 'Por iniciar' }">{{ projectStatus(project.id) }}</span>
                  <span class="project-priority-badge" :class="`project-priority-${projectPriorityClass(project.id)}`">{{ projectPriority(project.id) === '—' ? 'Sem prioridade' : `Prioridade ${projectPriority(project.id).toLowerCase()}` }}</span>
                </div>
                <div class="project-dashboard-progress">
                  <div><span>Progresso</span><strong>{{ projectProgress(project.id) }}%</strong></div>
                  <span class="project-progress"><i :style="{ width: `${projectProgress(project.id)}%`, background: project.color }"></i></span>
                  <small>{{ project.completed_count }} / {{ project.task_count }} tarefas concluídas</small>
                </div>
                <footer class="project-dashboard-card-footer">
                  <div class="project-member-stack" :aria-label="`${project.members.length + (project.owner_id === user.id ? 1 : 0)} membros`">
                    <span v-for="member in (project.owner_id === user.id ? [user, ...project.members] : project.members).slice(0, 3)" :key="member.id" class="mini-avatar" :title="member.name">{{ member.name.slice(0, 1).toUpperCase() }}</span>
                    <span v-if="project.members.length + (project.owner_id === user.id ? 1 : 0) > 3" class="project-member-more">+{{ project.members.length + (project.owner_id === user.id ? 1 : 0) - 3 }}</span>
                    <span v-if="!project.members.length && project.owner_id !== user.id" class="project-member-empty">Sem membros</span>
                  </div>
                  <span class="project-card-deadline">Prazo: {{ formatDate(projectDeadline(project.id)) }}</span>
                </footer>
              </article>
            </div>
            <div v-else class="empty-state project-empty-state">
              <span class="empty-icon">▤</span>
              <h3>{{ projects.length ? 'Nenhum projeto corresponde aos filtros.' : 'Ainda não tens projetos.' }}</h3>
              <p>{{ projects.length ? 'Experimenta outra pesquisa ou estado.' : 'Cria o teu primeiro projeto e convida a equipa.' }}</p>
              <button v-if="!projects.length" class="button button-primary" @click="openProjectForm()">＋ Criar projeto</button>
            </div>
          </section>
        </template>

        <!-- As tarefas globais podem ser abertas para consultar ou atualizar os seus detalhes. -->
        <template v-else-if="activeView === 'tasks'">
          <div class="page-intro"><div class="page-title-group"><span class="eyebrow">PLANO DE TRABALHO</span><h1>Todas as tarefas</h1><p>Pesquisa e acompanha tarefas dos teus projetos.</p></div></div>
          <div class="filter-bar"><label class="search-box"><span>⌕</span><input v-model="search" placeholder="Procurar tarefas..." aria-label="Procurar tarefas"></label><select v-model="statusFilter"><option value="">Todos os estados</option><option value="todo">Por iniciar</option><option value="in_progress">Em curso</option><option value="done">Concluídas</option><option value="blocked">Bloqueadas</option></select></div>
          <div class="task-list">
            <button v-for="task in dashboardTasks.filter((item) => `${item.title} ${item.description}`.toLowerCase().includes(search.toLowerCase()) && (!statusFilter || item.status === statusFilter))" :key="task.id" class="overview-task all-task-row" @click="openTask(task)">
              <span class="project-dot" :style="{ background: projects.find((project) => project.id === task.project_id)?.color ?? '#7165e8' }"></span><span class="overview-task-copy"><strong>{{ task.title }}</strong><small>{{ projects.find((project) => project.id === task.project_id)?.name ?? 'Projeto' }}</small></span>
              <span class="priority-pill" :class="`priority-${task.priority}`"><i></i>{{ priorityLabel(task.priority) }}</span><span class="task-deadline">{{ formatDate(task.deadline) }}</span><span class="status-select" :class="`status-${task.status}`">{{ statusLabel(task.status) }}</span>
            </button>
            <div v-if="!dashboardTasks.length" class="empty-state"><h3>Sem tarefas registadas.</h3><p>Adiciona uma tarefa num dos teus projetos.</p></div>
          </div>
        </template>

        <!-- Grelha mensal com prazos; cada evento abre o detalhe da tarefa correspondente. -->
        <template v-else-if="activeView === 'calendar'">
          <div class="page-intro"><div class="page-title-group"><span class="eyebrow">PLANEAMENTO</span><h1>Calendário</h1><p>Vê os prazos de todos os teus projetos num só lugar.</p></div></div>
          <section class="calendar-panel">
            <header class="calendar-header"><div><span class="section-kicker">AGENDA MENSAL</span><h2>{{ new Intl.DateTimeFormat('pt-PT', { month: 'long', year: 'numeric' }).format(calendarMonth) }}</h2></div><div class="calendar-controls"><button class="button button-soft" @click="changeCalendarMonth(-1)">←</button><button class="button button-soft" @click="calendarMonth = new Date(new Date().getFullYear(), new Date().getMonth(), 1)">Hoje</button><button class="button button-soft" @click="changeCalendarMonth(1)">→</button></div></header>
            <div class="calendar-grid calendar-weekdays"><span v-for="day in ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']" :key="day">{{ day }}</span></div>
            <div class="calendar-grid calendar-days"><div v-for="cell in calendarCells" :key="cell.key" class="calendar-cell" :class="{ 'outside-month': !cell.inMonth, 'calendar-today': cell.key === today }"><span>{{ cell.day }}</span><button v-for="task in cell.tasks.slice(0, 2)" :key="task.id" class="calendar-event" @click="openTask(task)">{{ task.title }}</button><small v-if="cell.tasks.length > 2">+{{ cell.tasks.length - 2 }} mais</small></div></div>
          </section>
        </template>

        <!-- A equipa é contextual ao projeto selecionado e só o responsável pode convidar membros. -->
        <template v-else-if="activeView === 'team'">
          <div class="page-intro"><div class="page-title-group"><span class="eyebrow">COLABORAÇÃO</span><h1>Equipa</h1><p>{{ activeProject ? `Membros de ${activeProject.name}.` : 'Seleciona um projeto para veres a equipa.' }}</p></div><div v-if="activeProject?.owner_id === user.id" class="intro-actions"><button class="button button-primary" @click="showInvite = true">＋ Convidar membro</button></div></div>
          <div v-if="activeProject" class="team-member-list"><article v-for="member in members" :key="member.id" class="team-member-card"><span class="profile-avatar">{{ member.name.slice(0, 1).toUpperCase() }}</span><span><strong>{{ member.name }}</strong><small>{{ member.email }}</small></span><span class="member-role">{{ member.id === activeProject.owner_id ? 'Líder do projeto' : 'Membro' }}</span></article></div>
          <div v-else class="empty-state"><h3>Escolhe um projeto</h3><p>Abre um projeto para consultar e gerir os membros da equipa.</p><button class="button button-primary" @click="activeView = 'projects'">Ver projetos</button></div>
        </template>

        <!-- Marcar como lida confirma a alteração na API e substitui apenas o registo atualizado. -->
        <template v-else-if="activeView === 'notifications'">
          <div class="page-intro"><div class="page-title-group"><span class="eyebrow">ATUALIZAÇÕES</span><h1>Notificações</h1><p>{{ unreadNotifications }} por ler.</p></div></div>
          <div v-if="notifications.length" class="notification-list"><button v-for="notification in notifications" :key="notification.id" class="notification-card" :class="{ 'notification-unread': !notification.is_read }" @click="markNotificationRead(notification)"><span class="notification-icon">♧</span><span><strong>{{ notification.title }}</strong><small>{{ notification.message }}</small><small>{{ formatDate(notification.created_at.slice(0, 10)) }}</small></span><i v-if="!notification.is_read"></i></button></div>
          <div v-else class="empty-state"><span class="empty-icon">✓</span><h3>Estás a par de tudo.</h3><p>As notificações dos teus projetos vão aparecer aqui.</p></div>
        </template>

        <!-- Os anexos pertencem ao projeto ativo e são apresentados como ligações para os ficheiros. -->
        <template v-else-if="activeView === 'documents'">
          <div class="page-intro"><div class="page-title-group"><span class="eyebrow">FICHEIROS DO PROJETO</span><h1>Documentos</h1><p>{{ activeProject?.name ?? 'Seleciona um projeto para consultar os documentos.' }}</p></div></div>
          <div v-if="attachments.length" class="document-list"><a v-for="attachment in attachments" :key="attachment.id" class="document-card" :href="attachment.url" target="_blank" rel="noopener noreferrer" @click="downloadAttachment($event, attachment)"><span class="document-icon">↗</span><span><strong>{{ attachment.file_name }}</strong><small>{{ attachment.file_type }} · {{ (attachment.size_bytes / 1024).toFixed(1) }} KB</small></span><span class="document-task">{{ dashboardTasks.find((task) => task.id === attachment.task_id)?.title ?? 'Tarefa' }}</span></a></div>
          <div v-else class="empty-state"><span class="empty-icon">▤</span><h3>Sem documentos anexados.</h3><p>Os ficheiros associados às tarefas deste projeto serão apresentados aqui.</p><button class="button button-soft" @click="activeView = 'project'">Voltar ao projeto</button></div>
        </template>

        <!-- Detalhe da tarefa reúne conversa, anexos e atributos editáveis num só contexto. -->
        <template v-else-if="activeView === 'task' && selectedTask">
          <nav class="task-detail-breadcrumb" aria-label="Navegação da tarefa">
            <button @click="activeView = 'project'">{{ projects.find((project) => project.id === selectedTask.project_id)?.name ?? 'Projeto' }}</button>
            <span>/</span>
            <span>{{ statusLabel(selectedTask.status) }}</span>
          </nav>
          <article class="task-detail-shell">
            <header class="task-detail-toolbar">
              <div class="task-detail-toolbar-project"><span class="task-detail-project-mark">T</span><strong>TaskFlow</strong></div>
              <div class="task-detail-toolbar-actions">
                <button class="task-toolbar-icon" aria-label="Voltar ao projeto" title="Voltar ao projeto" @click="activeView = 'project'">↗</button>
                <button class="task-toolbar-icon" aria-label="Eliminar tarefa" title="Eliminar tarefa" @click="removeTask(selectedTask)">×</button>
              </div>
            </header>
            <div class="task-detail-columns">
              <section class="task-detail-content">
                <div class="task-detail-project-link">
                  <span class="project-detail-category">{{ projects.find((project) => project.id === selectedTask.project_id)?.name ?? 'Projeto' }}</span>
                  <span>/</span>
                  <span class="project-status-badge" :class="`status-${selectedTask.status}`">{{ statusLabel(selectedTask.status) }}</span>
                </div>
                <div class="task-detail-heading">
                  <button class="task-detail-complete" :class="{ 'is-complete': selectedTask.status === 'done' }" :aria-label="selectedTask.status === 'done' ? 'Reabrir tarefa' : 'Concluir tarefa'" @click="updateTask(selectedTask, { status: selectedTask.status === 'done' ? 'todo' : 'done' })">{{ selectedTask.status === 'done' ? '✓' : '' }}</button>
                  <h1>{{ selectedTask.title }}</h1>
                </div>
                <p class="task-detail-description">{{ selectedTask.description || 'Esta tarefa ainda não tem descrição.' }}</p>
                <p class="task-detail-created">Criada em {{ formatCommentDate(selectedTask.created_at) }}</p>

                <section class="task-detail-section task-attachments-section">
                  <header><h2><span aria-hidden="true">⌁</span> Anexos <span>({{ selectedTaskAttachments.length }})</span></h2><button v-if="selectedTaskAttachments.length" class="task-detail-more" aria-label="Ver todos os anexos" @click="openDocuments()">•••</button></header>
                  <div v-if="selectedTaskAttachments.length" class="task-attachment-list">
                    <a v-for="attachment in selectedTaskAttachments" :key="attachment.id" class="task-attachment" :href="attachment.url" target="_blank" rel="noopener noreferrer" :download="attachment.file_name" @click="downloadAttachment($event, attachment)">
                      <span class="task-attachment-icon">↧</span>
                      <span class="task-attachment-copy"><strong>{{ attachment.file_name }}</strong><small>{{ formatFileSize(attachment.size_bytes) }} · {{ attachment.file_type }}</small></span>
                      <span class="task-attachment-download" aria-label="Transferir anexo">↓</span>
                    </a>
                  </div>
                  <p v-else class="task-detail-empty">Ainda não existem anexos nesta tarefa.</p>
                  <input ref="attachmentInput" class="sr-only" type="file" aria-label="Selecionar anexo" @change="uploadAttachment">
                  <button class="task-attachment-upload" type="button" :disabled="uploadingAttachment" :title="uploadingAttachment ? 'A carregar ficheiro…' : 'Tamanho máximo: 10 MB'" @click="attachmentInput?.click()">{{ uploadingAttachment ? 'A carregar anexo…' : '＋ Adicionar anexo' }}</button>
                </section>

                <section class="task-detail-section task-comments-section">
                  <header><h2>◷ Comentários <span>({{ comments.length }})</span></h2></header>
                  <div v-if="comments.length" class="task-comments-list">
                    <article v-for="comment in comments" :key="comment.id" class="task-comment">
                      <span class="task-comment-avatar">{{ comment.user.name.slice(0, 1).toUpperCase() }}</span>
                      <div><strong>{{ comment.user.name }}</strong><small>{{ formatCommentDate(comment.created_at) }}</small><p>{{ comment.content }}</p></div>
                    </article>
                  </div>
                  <p v-else class="task-detail-empty">Ainda não há comentários. Inicia a conversa com a equipa.</p>
                  <form class="task-comment-form" @submit.prevent="addComment">
                    <textarea v-model="commentDraft" required maxlength="4000" aria-label="Escrever comentário" placeholder="Escreve um comentário…"></textarea>
                    <button class="task-comment-send" type="submit" :disabled="!commentDraft.trim()" aria-label="Enviar comentário">↑</button>
                  </form>
                </section>
              </section>

              <aside class="task-detail-attributes">
                <p class="task-detail-created-sidebar">Criada em <strong>{{ formatCommentDate(selectedTask.created_at) }}</strong></p>
                <section class="task-attributes-section">
                  <h2>Atributos</h2>
                  <label class="task-attribute-row"><span>◷ <strong>Prazo</strong></span><input type="date" :value="selectedTask.deadline ?? ''" aria-label="Prazo da tarefa" @change="updateTask(selectedTask, { deadline: ($event.target as HTMLInputElement).value || null })"></label>
                  <label class="task-attribute-row"><span>♧ <strong>Atribuído a</strong></span><select :value="selectedTask.assignee_id ?? ''" aria-label="Responsável pela tarefa" @change="updateTask(selectedTask, { assignee_id: ($event.target as HTMLSelectElement).value ? Number(($event.target as HTMLSelectElement).value) : null })"><option value="">Sem responsável</option><option v-for="member in members" :key="member.id" :value="member.id">{{ member.name }}</option></select></label>
                  <div class="task-attribute-row"><span>◇ <strong>Prioridade</strong></span><select :value="selectedTask.priority" aria-label="Prioridade da tarefa" @change="updateTask(selectedTask, { priority: ($event.target as HTMLSelectElement).value as Task['priority'] })"><option value="low">Baixa</option><option value="medium">Média</option><option value="high">Alta</option></select></div>
                  <div class="task-attribute-row"><span>▤ <strong>Estado</strong></span><select :value="selectedTask.status" aria-label="Estado da tarefa" @change="updateTask(selectedTask, { status: ($event.target as HTMLSelectElement).value as Task['status'] })"><option value="todo">Por iniciar</option><option value="in_progress">Em curso</option><option value="done">Concluída</option><option value="blocked">Bloqueada</option></select></div>
                </section>
              </aside>
            </div>
          </article>
        </template>

        <!-- Visão do projeto agrega equipa, métricas e tarefas; permissões condicionam ações de gestão. -->
        <template v-else-if="activeView === 'project' && activeProject">
          <nav class="project-tabs" aria-label="Secções do projeto">
            <button class="project-tab active">Visão geral</button>
            <button class="project-tab" @click="activeView = 'tasks'">Tarefas <span>{{ tasks.length }}</span></button>
            <button class="project-tab" @click="openDocuments()">Anexos <span>{{ attachments.length }}</span></button>
          </nav>
          <header class="project-detail-hero">
            <span class="project-detail-mark" :style="{ color: activeProject.color, background: `${activeProject.color}18` }">{{ activeProject.category.slice(0, 1).toUpperCase() }}</span>
            <div class="project-detail-title">
              <span class="project-detail-category">{{ activeProject.category }}</span>
              <h1>{{ activeProject.name }}</h1>
              <span class="project-detail-status" :class="{ 'project-status-completed': projectStatus(activeProject.id) === 'Concluído', 'project-status-risk': projectStatus(activeProject.id) === 'Em risco', 'project-status-progress': projectStatus(activeProject.id) === 'Em curso', 'project-status-todo': projectStatus(activeProject.id) === 'Por iniciar' }">{{ projectStatus(activeProject.id) }}</span>
            </div>
            <div class="project-detail-members">
              <div class="project-member-stack">
                <span v-for="member in projectTeam.slice(0, 4)" :key="member.id" class="mini-avatar" :title="member.name">{{ member.name.slice(0, 1).toUpperCase() }}</span>
                <span v-if="projectTeam.length > 4" class="project-member-more">+{{ projectTeam.length - 4 }}</span>
              </div>
              <span>{{ projectTeam.length }} {{ projectTeam.length === 1 ? 'membro' : 'membros' }}</span>
            </div>
            <div class="project-detail-actions">
              <button v-if="activeProject.owner_id === user.id" class="button button-soft" @click="showInvite = true">＋ Convidar</button>
              <button v-if="activeProject.owner_id === user.id" class="button button-outline-danger project-archive-action" :aria-label="activeProject.archived ? 'Desarquivar projeto' : 'Arquivar projeto'" :title="activeProject.archived ? 'Desarquivar projeto' : 'Arquivar projeto'" @click="archiveProject">{{ activeProject.archived ? '↶' : '↗' }}</button>
              <button class="button button-primary" @click="showTaskForm = true">＋ Nova tarefa</button>
            </div>
          </header>

          <div class="project-detail-grid">
            <aside class="project-detail-sidebar">
              <section class="detail-card project-info-card">
                <h2>Informação geral</h2>
                <dl>
                  <div><dt>Estado</dt><dd><span class="project-status-badge" :class="{ 'project-status-completed': projectStatus(activeProject.id) === 'Concluído', 'project-status-risk': projectStatus(activeProject.id) === 'Em risco', 'project-status-progress': projectStatus(activeProject.id) === 'Em curso', 'project-status-todo': projectStatus(activeProject.id) === 'Por iniciar' }">{{ projectStatus(activeProject.id) }}</span></dd></div>
                  <div><dt>Categoria</dt><dd>{{ activeProject.category }}</dd></div>
                  <div><dt>Responsável</dt><dd>{{ projectTeam.find((member) => member.id === activeProject.owner_id)?.name ?? '—' }}</dd></div>
                  <div><dt>Criado em</dt><dd>{{ formatDate(activeProject.created_at.slice(0, 10)) }}</dd></div>
                  <div><dt>Próximo prazo</dt><dd>{{ formatDate(projectDeadline(activeProject.id)) }}</dd></div>
                </dl>
              </section>
              <section class="detail-card project-team-card">
                <header><h2>Equipa</h2><button v-if="activeProject.owner_id === user.id" aria-label="Convidar membro" @click="showInvite = true">＋</button></header>
                <div v-if="projectTeam.length" class="project-team-list">
                  <article v-for="member in projectTeam" :key="member.id" class="project-team-member">
                    <span class="profile-avatar">{{ member.name.slice(0, 1).toUpperCase() }}</span>
                    <span><strong>{{ member.name }}</strong><small>{{ member.id === activeProject.owner_id ? 'Responsável pelo projeto' : 'Membro da equipa' }}</small></span>
                  </article>
                </div>
                <p v-else class="project-team-empty">Ainda não há membros neste projeto.</p>
              </section>
            </aside>

            <div class="project-detail-main">
              <section class="project-detail-metrics">
                <article class="detail-card project-progress-card">
                  <header><h2>Progresso</h2><span class="project-detail-metric-icon">✓</span></header>
                  <small>{{ completedTasks }} de {{ tasks.length }} tarefas concluídas</small>
                  <strong>{{ progress }}<span>%</span></strong>
                  <div class="project-progress"><i :style="{ width: `${progress}%`, background: activeProject.color }"></i></div>
                  <footer><span>{{ tasks.filter((task) => task.status === 'in_progress').length }} em curso</span><span>{{ tasks.filter((task) => task.status !== 'done').length }} por concluir</span></footer>
                </article>
                <article class="detail-card project-task-summary-card">
                  <header><h2>Tarefas</h2><span class="project-detail-metric-icon">▤</span></header>
                  <small>Resumo do trabalho</small>
                  <strong>{{ tasks.length }}</strong>
                  <div class="project-task-summary-bar">
                    <i v-for="status in ['done', 'in_progress', 'todo', 'blocked'] as const" :key="status" :class="`summary-${status}`" :style="{ width: `${tasks.length ? tasks.filter((task) => task.status === status).length / tasks.length * 100 : 0}%` }"></i>
                  </div>
                  <footer><span>{{ tasks.filter((task) => task.status === 'done').length }} concluídas</span><span>{{ tasks.filter((task) => task.status === 'blocked').length }} bloqueadas</span></footer>
                </article>
              </section>

              <section class="detail-card project-description-card">
                <h2>Descrição</h2>
                <p>{{ activeProject.description || 'Ainda não foi adicionada uma descrição a este projeto.' }}</p>
                <button v-if="activeProject.owner_id === user.id && !activeProject.description" class="text-button" @click="openProjectForm(activeProject)">Adicionar descrição →</button>
              </section>

              <section class="detail-card project-activity-card">
                <header><h2>Tarefas recentes</h2><button class="text-button" @click="activeView = 'tasks'">Ver tarefas →</button></header>
                <div v-if="recentProjectTasks.length" class="project-activity-list">
                  <button v-for="task in recentProjectTasks" :key="task.id" class="project-activity-item" @click="openTask(task)">
                    <span class="project-activity-dot" :class="`activity-${task.status}`"></span>
                    <span class="project-activity-copy"><strong>{{ task.title }}</strong><small>Criada em {{ formatDate(task.created_at.slice(0, 10)) }} · {{ task.assignee?.name ?? 'Sem responsável' }}</small></span>
                    <span class="status-select" :class="`status-${task.status}`">{{ statusLabel(task.status) }}</span>
                  </button>
                </div>
                <div v-else class="project-activity-empty"><p>Ainda não há tarefas neste projeto.</p><button class="button button-soft" @click="showTaskForm = true">Criar a primeira tarefa</button></div>
              </section>
            </div>
          </div>
        </template>

        <!-- Estado inicial da área de projetos, exibido quando ainda não há projeto selecionado. -->
        <section v-else-if="activeView === 'project' && !loading" class="welcome-state"><span class="welcome-orbit">✳</span><span class="eyebrow"><span class="eyebrow-dot"></span> UM NOVO SEMESTRE, NOVAS POSSIBILIDADES</span><h1>As grandes ideias<br>merecem um <span>plano.</span></h1><p>Cria o teu primeiro projeto e reúne aqui as tarefas, os prazos e a equipa. O próximo passo começa agora.</p><button class="button button-primary" @click="openProjectForm()">＋ Criar o meu primeiro projeto</button><div class="welcome-note">✦ &nbsp;Feito para aprender, criar e chegar mais longe.</div></section>
      </div>
      <footer class="page-footer"><span>© 2026 ARROW4D <i>·</i> TASKFLOW</span><span>Um passo de cada vez. <b>✳</b></span></footer>
    </section>

    <!-- Diálogos de edição/criação mantêm o contexto da página e fecham ao clicar fora do cartão. -->
    <div v-if="showProjectForm" class="modal-backdrop" @click.self="showProjectForm = false">
      <section class="modal-card" role="dialog" aria-modal="true" aria-labelledby="project-modal-title">
        <button class="modal-close" aria-label="Fechar" @click="showProjectForm = false">×</button>
        <span class="section-kicker">{{ editingProject ? 'O TEU ESPAÇO DE TRABALHO' : 'UM NOVO COMEÇO' }}</span><h2 id="project-modal-title">{{ editingProject ? 'Editar projeto' : 'Criar projeto' }}</h2><p class="modal-subtitle">Dá forma à ideia. O resto constrói-se em equipa.</p>
        <form class="stack-form" @submit.prevent="saveProject">
          <label class="field-label">Nome do projeto<input v-model="projectForm.name" required minlength="2" maxlength="160" placeholder="Ex.: Investigação sobre sustentabilidade"></label>
          <label class="field-label">Descrição<textarea v-model="projectForm.description" rows="3" maxlength="4000" placeholder="O que querem alcançar juntos?"></textarea></label>
          <label class="field-label">Tipo de projeto<select v-model="projectForm.category"><option>Desenvolvimento</option><option>Investigação</option><option>Seminário</option><option>Estudo de caso</option><option>Outro</option></select></label>
          <label class="field-label color-field">Cor de identificação<input v-model="projectForm.color" type="color" aria-label="Cor do projeto"></label>
          <button class="button button-primary button-wide" :disabled="busy">{{ busy ? 'A guardar…' : editingProject ? 'Guardar alterações' : 'Criar projeto' }} <span>→</span></button>
        </form>
      </section>
    </div>
    <div v-if="showTaskForm" class="modal-backdrop" @click.self="showTaskForm = false">
      <section class="modal-card" role="dialog" aria-modal="true" aria-labelledby="task-modal-title">
        <button class="modal-close" aria-label="Fechar" @click="showTaskForm = false">×</button>
        <span class="section-kicker">PROJETO · {{ activeProject?.name }}</span><h2 id="task-modal-title">Uma tarefa de cada vez.</h2><p class="modal-subtitle">Define o próximo passo e partilha-o com a equipa.</p>
        <form class="stack-form" @submit.prevent="createTask">
          <label class="field-label">Título da tarefa<input v-model="taskForm.title" required minlength="2" maxlength="200" placeholder="Ex.: Rever a literatura existente"></label>
          <label class="field-label">Descrição<textarea v-model="taskForm.description" rows="3" maxlength="4000" placeholder="Mais contexto ajuda toda a equipa."></textarea></label>
          <div class="form-grid"><label class="field-label">Categoria<select v-model="taskForm.category"><option>Planeamento</option><option>Pesquisa</option><option>Conceção</option><option>Execução</option><option>Validação</option><option>Documentação</option></select></label><label class="field-label">Prioridade<select v-model="taskForm.priority"><option value="low">Baixa</option><option value="medium">Média</option><option value="high">Alta</option></select></label></div>
          <div class="form-grid"><label class="field-label">Prazo<input v-model="taskForm.deadline" type="date"></label><label class="field-label">Responsável<select v-model="taskForm.assignee_id"><option value="">{{ user.name }} (eu)</option><option v-for="member in members.filter((item) => item.id !== user?.id)" :key="member.id" :value="String(member.id)">{{ member.name }}</option></select></label></div>
          <button class="button button-primary button-wide" :disabled="busy">{{ busy ? 'A adicionar…' : 'Adicionar tarefa' }} <span>→</span></button>
        </form>
      </section>
    </div>
    <div v-if="showInvite" class="modal-backdrop" @click.self="showInvite = false">
      <section class="modal-card invite-modal" role="dialog" aria-modal="true" aria-labelledby="invite-modal-title">
        <button class="modal-close" aria-label="Fechar" @click="showInvite = false">×</button>
        <span class="section-kicker">MAIS IDEIAS, MAIS OLHARES</span><h2 id="invite-modal-title">A equipa fica melhor junta.</h2><p class="modal-subtitle">Adiciona alguém que já tenha uma conta TaskFlow.</p>
        <form class="stack-form" @submit.prevent="inviteMember"><label class="field-label">Email do membro<input v-model="inviteEmail" type="email" required placeholder="colega@universidade.pt"></label><button class="button button-primary button-wide">Adicionar à equipa <span>→</span></button></form>
      </section>
    </div>
  </main>
</template>
