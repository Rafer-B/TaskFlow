<script setup lang="ts">
import type { Project, Task, User } from '~/composables/useTaskflow'

const { token, user, request, authenticate, restoreSession, signOut } = useTaskflow()
const projects = ref<Project[]>([])
const tasks = ref<Task[]>([])
const activeProjectId = ref<number | null>(null)
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
const today = new Date().toISOString().slice(0, 10)

const activeProject = computed(() =>
  projects.value.find((project) => project.id === activeProjectId.value) ?? null,
)
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

function setError(message: unknown) {
  error.value = message instanceof Error ? message.message : 'Ocorreu um erro inesperado.'
  notice.value = ''
}

function clearMessages() {
  error.value = ''
  notice.value = ''
}

async function loadProjects() {
  projects.value = await request<Project[]>(`/api/projects?archived=${showArchivedProjects.value}`)
  if (!activeProjectId.value || !projects.value.some((project) => project.id === activeProjectId.value)) {
    activeProjectId.value = projects.value[0]?.id ?? null
  }
}

async function loadProjectData() {
  if (!activeProjectId.value) {
    tasks.value = []
    members.value = []
    return
  }
  const id = activeProjectId.value
  const [loadedTasks, loadedMembers] = await Promise.all([
    request<Task[]>(`/api/projects/${id}/tasks`),
    request<User[]>(`/api/projects/${id}/members`),
  ])
  tasks.value = loadedTasks
  members.value = loadedMembers
}

async function refresh() {
  if (!token.value) return
  try {
    await loadProjects()
    await loadProjectData()
  } catch (cause) {
    setError(cause)
  } finally {
    loading.value = false
  }
}

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
  } catch (cause) {
    setError(cause)
  } finally {
    busy.value = false
  }
}

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
    await loadProjectData()
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
  } catch (cause) {
    setError(cause)
  }
}

function formatDate(date: string | null) {
  if (!date) return 'Sem prazo'
  return new Intl.DateTimeFormat('pt-PT', { day: 'numeric', month: 'short' }).format(new Date(`${date}T00:00:00`))
}

function statusLabel(status: string) {
  return ({ todo: 'Por iniciar', in_progress: 'Em curso', done: 'Concluída', blocked: 'Bloqueada' })[status] ?? status
}

function priorityLabel(priority: string) {
  return ({ low: 'Baixa', medium: 'Média', high: 'Alta' })[priority] ?? priority
}

function handleSignOut() {
  accountMenuOpen.value = false
  signOut()
  projects.value = []
  tasks.value = []
  activeProjectId.value = null
  loading.value = false
}
</script>

<template>
  <main v-if="!user" class="auth-page">
    <section class="auth-panel">
      <NuxtLink to="/" class="brand auth-brand"><span class="brand-mark">TF</span><span>taskflow<span class="brand-period">.</span></span></NuxtLink>
      <div class="auth-copy">
        <span class="eyebrow"><span class="eyebrow-dot"></span> O teu espaço de trabalho</span>
        <h1>Projetos académicos,<br><span>com rumo.</span></h1>
        <p>Menos dispersão. Mais clareza. Tudo o que a tua equipa precisa para chegar à entrega final.</p>
        <div class="auth-proof">
          <div class="avatar-stack"><span>R</span><span>M</span><span>A</span><span>+</span></div>
          <span>Feito para equipas que fazem acontecer.</span>
        </div>
      </div>
      <p class="auth-foot">ARROW4D <span>·</span> Évora, Portugal</p>
    </section>
    <section class="auth-form-wrap">
      <div class="auth-form">
        <div class="mobile-brand brand"><span class="brand-mark">TF</span><span>taskflow<span class="brand-period">.</span></span></div>
        <div class="form-heading">
          <span class="eyebrow">BEM-VINDO{{ authMode === 'register' ? ' À EQUIPA' : ' DE VOLTA' }}</span>
          <h2>{{ authMode === 'login' ? 'Continua de onde ficaste.' : 'Vamos começar juntos.' }}</h2>
          <p>{{ authMode === 'login' ? 'Entra na tua conta para acompanhar os teus projetos.' : 'Cria a tua conta e dá o primeiro passo.' }}</p>
        </div>
        <form class="stack-form" @submit.prevent="submitAuth">
          <label v-if="authMode === 'register'" class="field-label">Nome completo
            <input v-model="authName" autocomplete="name" placeholder="Como te chamamos?" minlength="2" required>
          </label>
          <label class="field-label">Email
            <input v-model="authEmail" autocomplete="email" type="email" placeholder="nome@universidade.pt" required>
          </label>
          <label class="field-label">Palavra-passe
            <input v-model="authPassword" autocomplete="current-password" type="password" placeholder="Mínimo 8 caracteres" minlength="8" required>
          </label>
          <p v-if="error" class="message message-error">{{ error }}</p>
          <button class="button button-primary button-wide" :disabled="busy">
            {{ busy ? 'A processar…' : authMode === 'login' ? 'Entrar na plataforma' : 'Criar conta' }}
            <span aria-hidden="true">→</span>
          </button>
        </form>
        <p class="switch-auth">
          {{ authMode === 'login' ? 'Ainda não tens conta?' : 'Já tens uma conta?' }}
          <button type="button" @click="authMode = authMode === 'login' ? 'register' : 'login'; clearMessages()">
            {{ authMode === 'login' ? 'Criar conta' : 'Iniciar sessão' }}
          </button>
        </p>
        <p class="auth-legal">Ao continuar, concordas com a utilização responsável da plataforma.</p>
      </div>
    </section>
  </main>

  <main v-else class="workspace">
    <aside class="sidebar">
      <NuxtLink to="/" class="brand"><span class="brand-mark">TF</span><span>taskflow<span class="brand-period">.</span></span></NuxtLink>
      <div class="workspace-label"><span class="workspace-avatar">A</span><span><strong>ARROW4D</strong><small>Workspace académico</small></span><span class="chevron">⌄</span></div>
      <div class="nav-heading">MENU</div>
      <button class="nav-link active" @click="activeProjectId = projects[0]?.id ?? null"><span class="nav-icon">▦</span> Visão geral <span class="nav-shortcut">⌘ 1</span></button>
      <div class="project-heading"><span>{{ showArchivedProjects ? 'PROJETOS ARQUIVADOS' : 'OS TEUS PROJETOS' }}</span><span class="project-heading-actions"><button :aria-label="showArchivedProjects ? 'Ver projetos ativos' : 'Ver projetos arquivados'" :title="showArchivedProjects ? 'Ver projetos ativos' : 'Ver projetos arquivados'" @click="showArchivedProjects = !showArchivedProjects; loadProjects()">⌑</button><button aria-label="Criar projeto" title="Criar projeto" @click="openProjectForm()">＋</button></span></div>
      <div class="project-nav">
        <button v-for="project in projects" :key="project.id" class="project-link" :class="{ selected: project.id === activeProjectId }" @click="activeProjectId = project.id">
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
        <div class="breadcrumb"><span>Workspace</span><span class="crumb-sep">/</span><strong>{{ activeProject?.name ?? 'Visão geral' }}</strong></div>
        <div class="topbar-actions"><span class="today-label">{{ new Intl.DateTimeFormat('pt-PT', { weekday: 'long', day: 'numeric', month: 'long' }).format(new Date()) }}</span><div class="account-menu-wrap"><button class="profile-avatar top-profile" :title="user.name" :aria-label="`Menu da conta de ${user.name}`" :aria-expanded="accountMenuOpen" @click="accountMenuOpen = !accountMenuOpen">{{ initials }}</button><div v-if="accountMenuOpen" class="account-menu"><strong>{{ user.name }}</strong><span>{{ user.email }}</span><button @click="handleSignOut"><span aria-hidden="true">↪</span> Terminar sessão</button></div></div></div>
      </header>

      <div class="page-content">
        <div v-if="error" class="message message-error global-message"><span>{{ error }}</span><button @click="clearMessages">×</button></div>
        <div v-if="notice" class="message message-success global-message"><span>{{ notice }}</span><button @click="notice = ''">×</button></div>

        <template v-if="activeProject">
          <div class="page-intro">
            <div class="page-title-group"><span class="eyebrow"><span class="eyebrow-dot"></span> {{ activeProject.category }} <span class="intro-divider">·</span> Projeto</span><h1>{{ activeProject.name }}</h1><p>{{ activeProject.description || 'Organiza o trabalho da tua equipa, uma tarefa de cada vez.' }}</p></div>
            <div class="intro-actions"><button v-if="activeProject.owner_id === user.id" class="button button-soft" @click="openProjectForm(activeProject)"><span>✎</span> Editar</button><button v-if="activeProject.owner_id === user.id" class="button button-outline-danger" @click="archiveProject">{{ activeProject.archived ? '↶ Desarquivar' : '↗ Arquivar' }}</button><button class="button button-primary" @click="showTaskForm = true"><span>＋</span> Nova tarefa</button></div>
          </div>

          <section class="stats-grid">
            <article class="stat-card"><div class="stat-top"><span class="stat-icon icon-violet">▦</span><span class="stat-caption">TOTAL NO PROJETO</span></div><div class="stat-value">{{ tasks.length }}<span class="stat-unit"> tarefas</span></div><div class="stat-foot">O plano da tua equipa</div></article>
            <article class="stat-card"><div class="stat-top"><span class="stat-icon icon-green">✓</span><span class="stat-caption">CONCLUÍDAS</span></div><div class="stat-value">{{ completedTasks }}<span class="stat-unit"> de {{ tasks.length }}</span></div><div class="stat-foot"><span class="positive-dot"></span> Bom trabalho, equipa!</div></article>
            <article class="stat-card"><div class="stat-top"><span class="stat-icon icon-amber">◷</span><span class="stat-caption">EM CURSO</span></div><div class="stat-value">{{ tasks.filter((task) => task.status === 'in_progress').length }}<span class="stat-unit"> tarefas</span></div><div class="stat-foot">O trabalho está a avançar</div></article>
            <article class="stat-card"><div class="stat-top"><span class="stat-icon icon-rose">!</span><span class="stat-caption">A PRECISAR DE ATENÇÃO</span></div><div class="stat-value">{{ overdueTasks }}<span class="stat-unit"> atrasadas</span></div><div class="stat-foot">{{ tasks.filter((task) => task.status === 'blocked').length }} bloqueadas</div></article>
          </section>

          <section class="progress-panel">
            <div class="progress-copy"><div><span class="section-kicker">RITMO DO PROJETO</span><h2>Todo o progresso conta.</h2><p>{{ completedTasks }} de {{ tasks.length }} tarefas concluídas. Continua assim!</p></div><div class="progress-number">{{ progress }}<span>%</span></div></div>
            <div class="progress-track"><div class="progress-fill" :style="{ width: `${progress}%`, background: activeProject.color }"></div></div>
          </section>

          <section class="tasks-section">
            <div class="section-header"><div><span class="section-kicker">PLANO DE TRABALHO</span><h2>As tarefas do projeto <span class="task-total">{{ tasks.length }}</span></h2></div><button class="text-button" @click="showTaskForm = true">＋ Adicionar tarefa</button></div>
            <div class="filter-bar">
              <label class="search-box"><span>⌕</span><input v-model="search" placeholder="Procurar tarefas..." aria-label="Procurar tarefas"></label>
              <select v-model="statusFilter" aria-label="Filtrar por estado"><option value="">Todos os estados</option><option value="todo">Por iniciar</option><option value="in_progress">Em curso</option><option value="done">Concluídas</option><option value="blocked">Bloqueadas</option></select>
              <select v-model="priorityFilter" aria-label="Filtrar por prioridade"><option value="">Todas as prioridades</option><option value="high">Prioridade alta</option><option value="medium">Prioridade média</option><option value="low">Prioridade baixa</option></select>
              <select v-model="assigneeFilter" aria-label="Filtrar por responsável"><option value="">Toda a equipa</option><option v-for="member in members" :key="member.id" :value="String(member.id)">{{ member.name }}</option></select>
            </div>

            <div v-if="loading" class="loading-state"><span class="spinner"></span> A organizar o teu espaço…</div>
            <div v-else-if="visibleTasks.length" class="task-list">
              <article v-for="task in visibleTasks" :key="task.id" class="task-row" :class="{ 'task-complete': task.status === 'done' }">
                <button class="task-check" :class="`check-${task.status}`" :aria-label="task.status === 'done' ? 'Reabrir tarefa' : 'Concluir tarefa'" @click="updateTask(task, { status: task.status === 'done' ? 'todo' : 'done' })">{{ task.status === 'done' ? '✓' : task.status === 'blocked' ? '!' : '' }}</button>
                <div class="task-main"><strong>{{ task.title }}</strong><p>{{ task.description || task.category }}</p></div>
                <span class="priority-pill" :class="`priority-${task.priority}`"><i></i>{{ priorityLabel(task.priority) }}</span>
                <label class="status-select-wrap"><span class="sr-only">Estado de {{ task.title }}</span><select class="status-select" :class="`status-${task.status}`" :value="task.status" @change="updateTask(task, { status: ($event.target as HTMLSelectElement).value as Task['status'] })"><option value="todo">Por iniciar</option><option value="in_progress">Em curso</option><option value="done">Concluída</option><option value="blocked">Bloqueada</option></select></label>
                <span class="task-assignee" :title="task.assignee?.name ?? 'Sem responsável'"><span class="mini-avatar">{{ task.assignee?.name.slice(0, 1).toUpperCase() ?? '?' }}</span>{{ task.assignee?.name.split(' ')[0] ?? 'Sem responsável' }}</span>
                <span class="task-deadline" :class="{ 'deadline-late': task.deadline && task.deadline < today && task.status !== 'done' }">◷ {{ formatDate(task.deadline) }}</span>
                <button class="icon-button task-remove" title="Eliminar tarefa" :aria-label="`Eliminar ${task.title}`" @click="removeTask(task)">×</button>
              </article>
            </div>
            <div v-else class="empty-state"><span class="empty-icon">✳</span><h3>{{ tasks.length ? 'Nada por aqui.' : 'O primeiro passo é teu.' }}</h3><p>{{ tasks.length ? 'Experimenta ajustar os filtros ou a pesquisa.' : 'Adiciona uma tarefa e transforma este plano em progresso.' }}</p><button v-if="!tasks.length" class="button button-primary" @click="showTaskForm = true">＋ Criar primeira tarefa</button></div>
          </section>

          <section class="team-strip"><div class="team-copy"><span class="section-kicker">A TUA EQUIPA</span><strong>{{ members.length }} {{ members.length === 1 ? 'membro' : 'membros' }} neste projeto</strong></div><div class="team-avatars"><span v-for="(member, index) in members.slice(0, 5)" :key="member.id" class="team-avatar" :style="{ zIndex: members.length - index }" :title="member.name">{{ member.name.slice(0, 1).toUpperCase() }}</span><button v-if="activeProject.owner_id === user.id" class="team-add" aria-label="Convidar membro" @click="showInvite = true">＋</button></div><button v-if="activeProject.owner_id === user.id" class="text-button team-invite" @click="showInvite = true">Convidar alguém →</button></section>
        </template>

        <section v-else-if="!loading" class="welcome-state"><span class="welcome-orbit">✳</span><span class="eyebrow"><span class="eyebrow-dot"></span> UM NOVO SEMESTRE, NOVAS POSSIBILIDADES</span><h1>As grandes ideias<br>merecem um <span>plano.</span></h1><p>Cria o teu primeiro projeto e reúne aqui as tarefas, os prazos e a equipa. O próximo passo começa agora.</p><button class="button button-primary" @click="openProjectForm()">＋ Criar o meu primeiro projeto</button><div class="welcome-note">✦ &nbsp;Feito para aprender, criar e chegar mais longe.</div></section>
      </div>
      <footer class="page-footer"><span>© 2026 ARROW4D <i>·</i> TASKFLOW</span><span>Um passo de cada vez. <b>✳</b></span></footer>
    </section>

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
