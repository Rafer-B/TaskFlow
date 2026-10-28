<script setup lang="ts">
interface DashboardCount {
  status?: 'todo' | 'in_progress' | 'done' | 'blocked'
  priority?: 'low' | 'medium' | 'high'
  count: number
}

interface DashboardTask {
  id: number
  title: string
  status: 'todo' | 'in_progress' | 'done' | 'blocked'
  priority: 'low' | 'medium' | 'high'
  project_name: string
  project_color: string
  assignee_name: string | null
  created_at: string
}

interface DashboardDeadline {
  id: number
  title: string
  deadline: string
  project_name: string
  project_color: string
  status: 'todo' | 'in_progress' | 'done' | 'blocked'
  days_left: number
}

interface DashboardProject {
  id: number
  name: string
  color: string
  task_count: number
  completed_count: number
  progress: number
}

interface DashboardStats {
  projects_total: number
  projects_active: number
  projects_archived: number
  tasks_total: number
  tasks_done: number
  tasks_in_progress: number
  tasks_todo: number
  tasks_blocked: number
  tasks_overdue: number
  completion_rate: number
  tasks_by_status: DashboardCount[]
  tasks_by_priority: DashboardCount[]
  recent_tasks: DashboardTask[]
  upcoming_deadlines: DashboardDeadline[]
  projects_summary: DashboardProject[]
}

const { token, user, request, restoreSession, signOut } = useTaskflow()
const stats = ref<DashboardStats | null>(null)
const loading = ref(true)
const refreshing = ref(false)
const error = ref('')

const statusMeta = {
  todo: { label: 'Por iniciar', color: '#94a3b8', icon: '○' },
  in_progress: { label: 'Em curso', color: '#5b7cfa', icon: '◐' },
  done: { label: 'Concluídas', color: '#20ad76', icon: '✓' },
  blocked: { label: 'Bloqueadas', color: '#e65f72', icon: '!' },
} as const

const priorityMeta = {
  low: { label: 'Baixa', color: '#31aa82' },
  medium: { label: 'Média', color: '#e39a38' },
  high: { label: 'Alta', color: '#db5c6e' },
} as const

const firstName = computed(() => user.value?.name.trim().split(/\s+/)[0] || 'Utilizador')
const todayLabel = computed(() => new Intl.DateTimeFormat('pt-PT', {
  weekday: 'long', day: 'numeric', month: 'long',
}).format(new Date()))

const completionMessage = computed(() => {
  if (!stats.value?.tasks_total) return 'Cria a primeira tarefa para começares a acompanhar o progresso.'
  if (stats.value.completion_rate === 100) return 'Excelente — todas as tarefas estão concluídas.'
  return `${stats.value.tasks_done} de ${stats.value.tasks_total} tarefas concluídas até agora.`
})

const statusItems = computed(() => (stats.value?.tasks_by_status ?? []).map((item) => {
  const status = item.status ?? 'todo'
  return { ...item, status, ...statusMeta[status] }
}))

const priorityItems = computed(() => (stats.value?.tasks_by_priority ?? []).map((item) => {
  const priority = item.priority ?? 'low'
  return { ...item, priority, ...priorityMeta[priority] }
}))

async function fetchStats(showSpinner = false) {
  if (!token.value) return
  if (showSpinner) refreshing.value = true
  error.value = ''
  try {
    stats.value = await request<DashboardStats>('/api/dashboard/stats')
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : 'Não foi possível carregar o dashboard.'
  } finally {
    loading.value = false
    refreshing.value = false
  }
}

function formatDate(date: string) {
  return new Intl.DateTimeFormat('pt-PT', { day: 'numeric', month: 'short' })
    .format(new Date(`${date}T00:00:00`))
}

function formatDateTime(date: string) {
  return new Intl.DateTimeFormat('pt-PT', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
    .format(new Date(date))
}

function deadlineText(daysLeft: number) {
  if (daysLeft === 0) return 'Termina hoje'
  if (daysLeft === 1) return 'Termina amanhã'
  return `Faltam ${daysLeft} dias`
}

function leave() {
  signOut()
  navigateTo('/')
}

onMounted(async () => {
  await restoreSession()
  if (!token.value) {
    await navigateTo('/')
    return
  }
  await fetchStats()
})
</script>

<template>
  <main class="insights-page">
    <div class="insights-orb insights-orb-one" aria-hidden="true"></div>
    <div class="insights-orb insights-orb-two" aria-hidden="true"></div>

    <header class="insights-topbar">
      <NuxtLink to="/" class="insights-brand" aria-label="Voltar ao TaskFlow">
        <span class="insights-brand-mark">TF</span>
        <span>taskflow<span>.</span></span>
      </NuxtLink>
      <div class="insights-topbar-actions">
        <NuxtLink class="insights-back-link" to="/">Abrir projetos <span>↗</span></NuxtLink>
        <button class="insights-avatar" type="button" :title="user?.name ?? 'Utilizador'" @click="leave">
          {{ firstName.slice(0, 1).toUpperCase() }}
        </button>
      </div>
    </header>

    <section class="insights-shell">
      <div class="insights-heading">
        <div>
          <p class="insights-kicker"><span></span>{{ todayLabel }}</p>
          <h1>Olá, {{ firstName }} <i>✦</i></h1>
          <p>Aqui está uma visão clara do ritmo dos teus projetos.</p>
        </div>
        <div class="insights-actions">
          <button class="insights-refresh" type="button" :disabled="refreshing" @click="fetchStats(true)">
            <span :class="{ spinning: refreshing }">↻</span>{{ refreshing ? 'A atualizar' : 'Atualizar' }}
          </button>
          <NuxtLink class="insights-primary-action" to="/">Ver projetos <span>→</span></NuxtLink>
        </div>
      </div>

      <div v-if="error" class="insights-error">
        <span>!</span><p>{{ error }}</p><button type="button" @click="fetchStats(true)">Tentar novamente</button>
      </div>

      <template v-if="loading && !stats">
        <section class="insights-skeleton-grid" aria-label="A carregar dashboard">
          <span v-for="index in 4" :key="index" class="insights-skeleton"></span>
        </section>
      </template>

      <template v-else-if="stats">
        <section class="insights-kpis" aria-label="Resumo do trabalho">
          <article class="insights-kpi insights-kpi-main">
            <div class="insights-kpi-icon icon-indigo">✓</div>
            <div><span>Conclusão global</span><strong>{{ stats.completion_rate }}<small>%</small></strong></div>
            <svg class="insights-kpi-ring" viewBox="0 0 42 42" aria-hidden="true">
              <circle cx="21" cy="21" r="16" fill="none" stroke="currentColor" stroke-width="3.5" opacity=".14" />
              <circle cx="21" cy="21" r="16" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round" :stroke-dasharray="`${stats.completion_rate} 100`" transform="rotate(-90 21 21)" />
            </svg>
          </article>
          <article class="insights-kpi">
            <div class="insights-kpi-icon icon-blue">◐</div>
            <div><span>Em curso</span><strong>{{ stats.tasks_in_progress }}</strong><small>{{ stats.tasks_todo }} por iniciar</small></div>
          </article>
          <article class="insights-kpi">
            <div class="insights-kpi-icon icon-amber">◷</div>
            <div><span>Prazos em risco</span><strong>{{ stats.tasks_overdue }}</strong><small>{{ stats.tasks_overdue ? 'Requerem atenção' : 'Tudo sob controlo' }}</small></div>
          </article>
          <article class="insights-kpi">
            <div class="insights-kpi-icon icon-coral">▤</div>
            <div><span>Projetos ativos</span><strong>{{ stats.projects_active }}</strong><small>{{ stats.projects_archived }} arquivados</small></div>
          </article>
        </section>

        <section class="insights-progress-card">
          <div class="insights-progress-copy">
            <span>O TEU PROGRESSO</span>
            <h2>{{ completionMessage }}</h2>
          </div>
          <strong>{{ stats.completion_rate }}%</strong>
          <div class="insights-progress-track" aria-label="Progresso global"><i :style="{ width: `${stats.completion_rate}%` }"></i></div>
          <div class="insights-progress-legend">
            <span><i class="legend-done"></i>{{ stats.tasks_done }} concluídas</span>
            <span><i class="legend-progress"></i>{{ stats.tasks_in_progress }} em curso</span>
            <span><i class="legend-todo"></i>{{ stats.tasks_todo }} por iniciar</span>
          </div>
        </section>

        <section class="insights-grid">
          <article class="insights-panel insights-status-panel">
            <header><div><span class="insights-panel-kicker">DISTRIBUIÇÃO</span><h2>Estado das tarefas</h2></div><span class="insights-panel-total">{{ stats.tasks_total }} total</span></header>
            <div v-if="stats.tasks_total" class="insights-status-bar" aria-label="Distribuição por estado">
              <i v-for="item in statusItems" :key="item.status" :style="{ width: `${item.count / stats.tasks_total * 100}%`, background: item.color }"></i>
            </div>
            <p v-else class="insights-empty-copy">Ainda não existem tarefas para distribuir.</p>
            <ul class="insights-status-list">
              <li v-for="item in statusItems" :key="item.status">
                <span class="insights-status-dot" :style="{ background: item.color }">{{ item.icon }}</span>
                <span>{{ item.label }}</span><strong>{{ item.count }}</strong>
              </li>
            </ul>
          </article>

          <article class="insights-panel insights-priority-panel">
            <header><div><span class="insights-panel-kicker">FOCO</span><h2>Prioridades</h2></div><span class="insights-spark">✦</span></header>
            <div class="insights-priority-list">
              <div v-for="item in priorityItems" :key="item.priority" class="insights-priority-row">
                <div><span :style="{ background: item.color }"></span><b>{{ item.label }}</b></div>
                <div class="insights-priority-meter"><i :style="{ width: `${stats.tasks_total ? item.count / stats.tasks_total * 100 : 0}%`, background: item.color }"></i></div>
                <strong>{{ item.count }}</strong>
              </div>
            </div>
          </article>

          <article class="insights-panel insights-deadline-panel">
            <header><div><span class="insights-panel-kicker">PRÓXIMOS 7 DIAS</span><h2>Prazos a acompanhar</h2></div><span class="insights-calendar-icon">⌁</span></header>
            <div v-if="stats.upcoming_deadlines.length" class="insights-deadline-list">
              <div v-for="task in stats.upcoming_deadlines" :key="task.id" class="insights-deadline-item">
                <time><b>{{ formatDate(task.deadline).split(' ')[0] }}</b><span>{{ formatDate(task.deadline).split(' ')[1] }}</span></time>
                <div><strong>{{ task.title }}</strong><small><i :style="{ background: task.project_color }"></i>{{ task.project_name }}</small></div>
                <em :class="{ urgent: task.days_left <= 1 }">{{ deadlineText(task.days_left) }}</em>
              </div>
            </div>
            <div v-else class="insights-empty-state"><span>☀</span><p>Não tens prazos para os próximos 7 dias.</p></div>
          </article>

          <article class="insights-panel insights-project-panel">
            <header><div><span class="insights-panel-kicker">PANORAMA</span><h2>Projetos em destaque</h2></div><NuxtLink to="/">Ver todos →</NuxtLink></header>
            <div v-if="stats.projects_summary.length" class="insights-project-list">
              <div v-for="project in stats.projects_summary" :key="project.id" class="insights-project-row">
                <span class="insights-project-mark" :style="{ background: `${project.color}18`, color: project.color }">▤</span>
                <div><strong>{{ project.name }}</strong><small>{{ project.completed_count }}/{{ project.task_count }} tarefas concluídas</small><span class="insights-mini-progress"><i :style="{ width: `${project.progress}%`, background: project.color }"></i></span></div>
                <b>{{ project.progress }}%</b>
              </div>
            </div>
            <div v-else class="insights-empty-state"><span>◇</span><p>Cria um projeto para começar a organizar o teu trabalho.</p></div>
          </article>

          <article class="insights-panel insights-activity-panel">
            <header><div><span class="insights-panel-kicker">ATIVIDADE</span><h2>Tarefas recentes</h2></div><span class="insights-live-dot">Atualizado</span></header>
            <div v-if="stats.recent_tasks.length" class="insights-activity-list">
              <div v-for="task in stats.recent_tasks" :key="task.id" class="insights-activity-item">
                <span class="insights-activity-dot" :style="{ background: statusMeta[task.status].color }"></span>
                <div><strong>{{ task.title }}</strong><small>{{ task.project_name }} · {{ task.assignee_name ?? 'Sem responsável' }}</small></div>
                <time>{{ formatDateTime(task.created_at) }}</time>
              </div>
            </div>
            <div v-else class="insights-empty-state"><span>✦</span><p>As novas tarefas aparecerão aqui.</p></div>
          </article>
        </section>
      </template>
    </section>
  </main>
</template>

<style scoped>
.insights-page { position: relative; min-height: 100vh; overflow: hidden; color: #25324a; background: #f7f8ff; }
.insights-orb { position: fixed; z-index: 0; width: 440px; height: 440px; border-radius: 50%; filter: blur(4px); opacity: .42; pointer-events: none; }
.insights-orb-one { top: -220px; right: -130px; background: #ddd9ff; }.insights-orb-two { bottom: -280px; left: -160px; background: #d9f4ee; }
.insights-topbar, .insights-shell { position: relative; z-index: 1; width: min(1240px, calc(100% - 48px)); margin: 0 auto; }
.insights-topbar { display: flex; height: 82px; align-items: center; justify-content: space-between; }
.insights-brand { display: inline-flex; align-items: center; gap: 9px; color: #29344e; font: 800 19px Outfit, sans-serif; letter-spacing: -1px; }.insights-brand > span:last-child span { color: #6e63e8; }.insights-brand-mark { display: grid; width: 31px; height: 31px; place-items: center; border-radius: 10px; color: white; background: linear-gradient(135deg, #8075f4, #5d55ca); box-shadow: 0 9px 18px #7368e644; font-size: 10px; letter-spacing: -.5px; }
.insights-topbar-actions { display: flex; align-items: center; gap: 18px; }.insights-back-link { color: #7a8193; font-size: 12px; font-weight: 700; }.insights-back-link span { margin-left: 4px; color: #7469e8; }.insights-avatar { display: grid; width: 35px; height: 35px; place-items: center; border: 2px solid white; border-radius: 12px; color: #6359c6; background: #eae8ff; box-shadow: 0 5px 15px #44416f14; font: 800 13px Outfit, sans-serif; }
.insights-shell { padding: 34px 0 68px; }.insights-heading { display: flex; align-items: flex-end; justify-content: space-between; gap: 24px; margin-bottom: 26px; }.insights-kicker, .insights-panel-kicker { margin: 0; color: #8991a6; font: 800 10px Outfit, sans-serif; letter-spacing: 1.1px; }.insights-kicker { display: flex; align-items: center; gap: 8px; text-transform: uppercase; }.insights-kicker span { width: 7px; height: 7px; border-radius: 50%; background: #47bd91; box-shadow: 0 0 0 4px #47bd9117; }.insights-heading h1 { margin: 10px 0 5px; color: #26324d; font: 800 clamp(30px, 4vw, 43px)/1.1 Outfit, sans-serif; letter-spacing: -2px; }.insights-heading h1 i { color: #f4ad4c; font-size: .48em; font-style: normal; vertical-align: top; }.insights-heading > div > p:last-child { margin: 0; color: #8790a5; font-size: 13px; }.insights-actions { display: flex; gap: 9px; }.insights-refresh, .insights-primary-action { display: inline-flex; min-height: 40px; align-items: center; justify-content: center; gap: 8px; padding: 0 13px; border-radius: 11px; font-size: 12px; font-weight: 800; }.insights-refresh { border: 1px solid #e4e6f1; color: #626b82; background: #ffffffbb; }.insights-refresh span { font-size: 16px; }.insights-refresh .spinning { animation: insightspin .8s linear infinite; }.insights-primary-action { color: white; background: #7065e8; box-shadow: 0 10px 22px #7065e833; }.insights-primary-action span { font-size: 16px; }
.insights-error { display: flex; align-items: center; gap: 10px; margin-bottom: 18px; padding: 12px 14px; border: 1px solid #ffd9df; border-radius: 12px; color: #a54257; background: #fff4f6; font-size: 12px; }.insights-error > span { display: grid; width: 19px; height: 19px; place-items: center; border-radius: 50%; color: white; background: #d85b70; font-weight: 800; }.insights-error p { margin: 0; }.insights-error button { margin-left: auto; border: 0; color: #a54257; background: transparent; font: inherit; font-weight: 800; }
.insights-kpis { display: grid; grid-template-columns: 1.14fr repeat(3, 1fr); gap: 14px; }.insights-kpi { position: relative; display: flex; min-height: 132px; align-items: flex-start; gap: 12px; overflow: hidden; padding: 18px; border: 1px solid #eaebf3; border-radius: 17px; background: #ffffffd9; box-shadow: 0 10px 29px #3c416008; }.insights-kpi-main { color: white; border: 0; background: linear-gradient(122deg, #7065e8, #8078f7); box-shadow: 0 14px 32px #7065e834; }.insights-kpi-icon { display: grid; width: 34px; height: 34px; flex: 0 0 34px; place-items: center; border-radius: 11px; font-size: 17px; font-weight: 800; }.insights-kpi-main .insights-kpi-icon { color: #665bd7; background: white; }.icon-blue { color: #5277dc; background: #eaf0ff; }.icon-amber { color: #c88732; background: #fff3df; }.icon-coral { color: #d45c70; background: #ffedf0; }.insights-kpi span { display: block; color: #8991a4; font: 800 10px Outfit, sans-serif; letter-spacing: .55px; text-transform: uppercase; }.insights-kpi-main span { color: #e5e2ff; }.insights-kpi strong { display: block; margin-top: 8px; color: #2f3a53; font: 800 30px/1 Outfit, sans-serif; letter-spacing: -1.7px; }.insights-kpi-main strong { color: white; }.insights-kpi strong small { font-size: 15px; letter-spacing: 0; }.insights-kpi > div small { display: block; margin-top: 8px; color: #9ca4b5; font-size: 11px; }.insights-kpi-ring { position: absolute; right: 12px; bottom: 10px; width: 62px; color: white; }
.insights-progress-card { display: grid; grid-template-columns: 1fr auto; gap: 11px 25px; margin-top: 14px; padding: 18px 20px 16px; border: 1px solid #e9eaf2; border-radius: 17px; background: #ffffffcf; }.insights-progress-copy span { color: #9298aa; font: 800 9px Outfit, sans-serif; letter-spacing: 1px; }.insights-progress-copy h2 { margin: 6px 0 0; color: #374158; font: 700 13px Outfit, sans-serif; }.insights-progress-card > strong { color: #6e63df; font: 800 24px Outfit, sans-serif; }.insights-progress-track { grid-column: 1 / -1; height: 8px; overflow: hidden; border-radius: 10px; background: #edecf7; }.insights-progress-track i { display: block; height: 100%; border-radius: inherit; background: linear-gradient(90deg, #776be9, #9b92ff); transition: width .45s ease; }.insights-progress-legend { display: flex; grid-column: 1 / -1; gap: 18px; color: #8b92a4; font-size: 10px; }.insights-progress-legend span { display: flex; align-items: center; gap: 6px; }.insights-progress-legend i { width: 7px; height: 7px; border-radius: 50%; }.legend-done { background: #20ad76; }.legend-progress { background: #5b7cfa; }.legend-todo { background: #b1b8c6; }
.insights-grid { display: grid; grid-template-columns: repeat(12, 1fr); gap: 14px; margin-top: 14px; }.insights-panel { min-width: 0; padding: 19px; border: 1px solid #e8eaf2; border-radius: 17px; background: #ffffffd9; box-shadow: 0 10px 29px #3c416006; }.insights-panel header { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }.insights-panel h2 { margin: 5px 0 0; color: #354057; font: 800 15px Outfit, sans-serif; letter-spacing: -.45px; }.insights-panel-total { padding: 5px 8px; border-radius: 8px; color: #7066d8; background: #f0efff; font: 800 10px Outfit, sans-serif; }.insights-status-panel { grid-column: span 5; }.insights-priority-panel { grid-column: span 3; }.insights-deadline-panel { grid-column: span 4; }.insights-project-panel { grid-column: span 7; }.insights-activity-panel { grid-column: span 5; }.insights-status-bar { display: flex; height: 11px; overflow: hidden; margin: 23px 0 17px; border-radius: 12px; background: #f0f1f5; }.insights-status-bar i { min-width: 0; transition: width .35s ease; }.insights-status-list { display: grid; grid-template-columns: repeat(2, 1fr); gap: 11px 16px; padding: 0; margin: 0; list-style: none; }.insights-status-list li { display: flex; min-width: 0; align-items: center; gap: 8px; color: #677188; font-size: 11px; }.insights-status-list strong { margin-left: auto; color: #3b465d; font: 800 12px Outfit, sans-serif; }.insights-status-dot { display: grid; width: 19px; height: 19px; flex: 0 0 19px; place-items: center; border-radius: 6px; color: white; font-size: 11px; font-weight: 800; }.insights-spark { display: grid; width: 28px; height: 28px; place-items: center; border-radius: 9px; color: #da9b40; background: #fff4df; }.insights-priority-list { display: grid; gap: 17px; margin-top: 27px; }.insights-priority-row { display: grid; grid-template-columns: 68px 1fr 18px; align-items: center; gap: 8px; }.insights-priority-row > div:first-child { display: flex; align-items: center; gap: 5px; color: #6d7689; font-size: 10px; }.insights-priority-row > div:first-child span { width: 7px; height: 7px; border-radius: 50%; }.insights-priority-row b { font-weight: 700; }.insights-priority-row strong { color: #3a465e; font: 800 11px Outfit, sans-serif; text-align: right; }.insights-priority-meter { height: 7px; overflow: hidden; border-radius: 8px; background: #eff0f5; }.insights-priority-meter i { display: block; height: 100%; border-radius: inherit; }.insights-calendar-icon { color: #7569e1; font-size: 22px; }.insights-deadline-list { display: grid; gap: 11px; margin-top: 17px; }.insights-deadline-item { display: grid; grid-template-columns: 37px minmax(0, 1fr) auto; align-items: center; gap: 10px; padding: 8px 0; border-bottom: 1px solid #f0f1f5; }.insights-deadline-item:last-child { border: 0; }.insights-deadline-item time { display: grid; width: 36px; height: 39px; place-items: center; align-content: center; border-radius: 10px; color: #5d57b9; background: #f0efff; line-height: 1; }.insights-deadline-item time b { font: 800 14px Outfit, sans-serif; }.insights-deadline-item time span { margin-top: 3px; font: 800 8px Outfit, sans-serif; text-transform: uppercase; }.insights-deadline-item > div { min-width: 0; }.insights-deadline-item strong, .insights-project-row strong, .insights-activity-item strong { display: block; overflow: hidden; color: #3a455b; font: 700 11px Outfit, sans-serif; text-overflow: ellipsis; white-space: nowrap; }.insights-deadline-item small { display: flex; align-items: center; gap: 5px; margin-top: 4px; overflow: hidden; color: #9299a9; font-size: 9px; text-overflow: ellipsis; white-space: nowrap; }.insights-deadline-item small i { width: 6px; height: 6px; border-radius: 2px; }.insights-deadline-item em { padding: 4px 6px; border-radius: 6px; color: #5a946f; background: #edfaf2; font-size: 8px; font-style: normal; font-weight: 700; white-space: nowrap; }.insights-deadline-item em.urgent { color: #c56b48; background: #fff1e9; }.insights-project-panel header > a { color: #7065d8; font-size: 10px; font-weight: 800; }.insights-project-list, .insights-activity-list { display: grid; margin-top: 17px; }.insights-project-row { display: grid; grid-template-columns: 32px minmax(0, 1fr) 35px; align-items: center; gap: 10px; padding: 10px 0; border-bottom: 1px solid #f0f1f5; }.insights-project-row:last-child, .insights-activity-item:last-child { border-bottom: 0; }.insights-project-mark { display: grid; width: 31px; height: 31px; place-items: center; border-radius: 9px; font-size: 14px; }.insights-project-row > div { min-width: 0; }.insights-project-row small { display: block; margin-top: 3px; color: #959caf; font-size: 9px; }.insights-project-row > b { color: #4d5970; font: 800 11px Outfit, sans-serif; text-align: right; }.insights-mini-progress { display: block; height: 5px; overflow: hidden; margin-top: 7px; border-radius: 5px; background: #f0f1f5; }.insights-mini-progress i { display: block; height: 100%; border-radius: inherit; }.insights-live-dot { display: flex; align-items: center; gap: 5px; color: #8d95a7; font-size: 9px; }.insights-live-dot::before { width: 6px; height: 6px; border-radius: 50%; background: #43b987; content: ''; }.insights-activity-item { display: grid; grid-template-columns: 9px minmax(0, 1fr) auto; align-items: center; gap: 9px; padding: 11px 0; border-bottom: 1px solid #f0f1f5; }.insights-activity-dot { width: 7px; height: 7px; border-radius: 50%; box-shadow: 0 0 0 4px #f2f3f7; }.insights-activity-item small { display: block; overflow: hidden; margin-top: 4px; color: #969daf; font-size: 9px; text-overflow: ellipsis; white-space: nowrap; }.insights-activity-item time { color: #a1a8b7; font-size: 8px; text-align: right; }.insights-empty-state { display: grid; min-height: 142px; place-items: center; align-content: center; color: #98a0b1; text-align: center; }.insights-empty-state span { display: grid; width: 36px; height: 36px; place-items: center; margin-bottom: 9px; border-radius: 12px; color: #8175e9; background: #f1efff; font-size: 17px; }.insights-empty-state p, .insights-empty-copy { margin: 0; color: #98a0b1; font-size: 11px; }.insights-empty-copy { margin-top: 28px; }
.insights-skeleton-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }.insights-skeleton { display: block; height: 132px; border-radius: 17px; background: linear-gradient(90deg, #eeeef5 25%, #fafaff 45%, #eeeef5 65%); background-size: 400% 100%; animation: insightskeleton 1.3s ease infinite; }
@keyframes insightspin { to { transform: rotate(360deg); } } @keyframes insightskeleton { to { background-position: -135% 0; } }
@media (max-width: 930px) { .insights-kpis { grid-template-columns: repeat(2, 1fr); }.insights-status-panel, .insights-priority-panel, .insights-deadline-panel, .insights-project-panel, .insights-activity-panel { grid-column: span 6; }.insights-deadline-panel { grid-column: span 12; }.insights-deadline-list { grid-template-columns: repeat(2, 1fr); }.insights-deadline-item:nth-last-child(2) { border-bottom: 0; } }
@media (max-width: 620px) { .insights-topbar, .insights-shell { width: min(100% - 30px, 1240px); }.insights-topbar { height: 67px; }.insights-back-link { display: none; }.insights-shell { padding-top: 22px; }.insights-heading { align-items: flex-start; flex-direction: column; margin-bottom: 18px; }.insights-heading h1 { font-size: 31px; }.insights-actions { width: 100%; }.insights-refresh, .insights-primary-action { flex: 1; }.insights-kpis, .insights-skeleton-grid { grid-template-columns: 1fr 1fr; gap: 9px; }.insights-kpi { min-height: 126px; flex-direction: column; gap: 8px; padding: 14px; }.insights-kpi strong { margin-top: 4px; font-size: 26px; }.insights-kpi > div small { margin-top: 5px; font-size: 9px; }.insights-kpi-main .insights-kpi-ring { width: 49px; }.insights-progress-card { padding: 16px; }.insights-progress-copy h2 { font-size: 11px; }.insights-progress-legend { flex-wrap: wrap; gap: 7px 11px; }.insights-grid { gap: 10px; }.insights-panel { grid-column: span 12; padding: 16px; }.insights-status-list { gap: 10px; }.insights-deadline-list { grid-template-columns: 1fr; }.insights-deadline-item:nth-last-child(2) { border-bottom: 1px solid #f0f1f5; }.insights-activity-item { grid-template-columns: 8px minmax(0, 1fr); }.insights-activity-item time { display: none; } }
@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation-duration: 0s !important; transition-duration: 0s !important; } }
</style>