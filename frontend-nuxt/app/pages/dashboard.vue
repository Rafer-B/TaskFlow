<script setup lang="ts">
const { user, request, signOut } = useTaskflow()

const stats = ref<any>(null)
const loading = ref(true)
const error = ref('')

async function fetchStats() {
  try {
    stats.value = await request<any>('/api/dashboard/stats')
  } catch (err: any) {
    error.value = err.message || 'NÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â£o foi possÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â­vel carregar as estatÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â­sticas.'
  } finally {
    loading.value = false
  }
}

const statusLabels: Record<string, string> = {
  todo: 'Por iniciar',
  in_progress: 'Em curso',
  done: 'ConcluÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â­das',
  blocked: 'Bloqueadas',
}

const priorityLabels: Record<string, string> = {
  low: 'Baixa',
  medium: 'MÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â©dia',
  high: 'Alta',
}

const statusColors: Record<string, string> = {
  todo: '#94a3b8',
  in_progress: '#3b82f6',
  done: '#10b981',
  blocked: '#ef4444',
}

const priorityColors: Record<string, string> = {
  low: '#10b981',
  medium: '#f59e0b',
  high: '#ef4444',
}

function formatDateTime(iso: string | null) {
  if (!iso) return ''
  return new Date(iso).toLocaleString('pt-PT', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

function statusColor(status: string) {
  return statusColors[status] ?? '#94a3b8'
}

function priorityColor(priority: string) {
  return priorityColors[priority] ?? '#94a3b8'
}

function cumulativeOffset(index: number, items: any[] = stats.value?.tasks_by_status || []): number {
  let offset = 0
  for (let i = 0; i < index; i++) {
    offset += (items[i]?.count ?? 0) / (stats.value?.tasks_total || 1) * 251
  }
  return offset
}

fetchStats()
</script>
<template>
  <div class="dashboard">
    <header class="dashboard-header">
      <div class="header-content">
        <div class="header-meta">
          <span class="header-kicker">TaskFlow ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· Dashboard</span>
          <h1 class="header-title">OlÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¡, {{ user?.name ? user.name : 'Utilizador' }}!</h1>
          <p class="header-subtitle">Acompanhe o progresso dos seus projetos e tarefas em tempo real.</p>
        </div>
        <div class="header-actions">
          <button class="button button-soft" @click="fetchStats"><span>Atualizar</span></button>
          <button class="button button-outline-danger" @click="signOut"><span>Sair</span></button>
        </div>
      </div>
    </header>

    <div v-if="error" class="message message-error">{{ error }}</div>

    <div v-if="loading && !stats" class="dashboard-loading">
      <div class="spinner"><style scoped>.dashboard {
  min-height: 100vh;
  background: #f7f8fc;
  color: #292a3c;
  font-family: 'DM Sans', sans-serif;
}

.dashboard-header {
  background: linear-gradient(135deg, #7165e8 0%, #5b4fd6 100%);
  padding: 40px 24px 32px;
  color: #fff;
}

.header-content {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

@media (min-width: 768px) {
  .header-content {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
  }
}

.header-meta {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.header-kicker {
  font: 700 11px Manrope, sans-serif;
  letter-spacing: 1.5px;
  color: #b6b0ff;
  text-transform: uppercase;
}

.header-title {
  margin: 0;
  font: 800 28px Manrope, sans-serif;
  letter-spacing: -0.5px;
  color: #fff;
}

.header-subtitle {
  margin: 4px 0 0;
  font-size: 14px;
  color: #d8d4ff;
  opacity: 0.9;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.kpi-grid {
  max-width: 1200px;
  margin: -20px auto 32px;
  padding: 0 24px;
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
}

@media (min-width: 640px) {
  .kpi-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (min-width: 1024px) {
  .kpi-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}

.kpi-card {
  background: #fff;
  border-radius: 16px;
  padding: 20px 24px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 4px 20px #1a1a1a08;
  border: 1px solid #ededef;
  transition: transform 0.2s, box-shadow 0.2s;
}

.kpi-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 30px #1a1a1a0c;
}

.kpi-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  font-size: 24px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}

.kpi-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.kpi-label {
  margin: 0;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.5px;
  color: #8b8d9e;
  text-transform: uppercase;
}

.kpi-value {
  margin: 0;
  font: 800 26px Manrope, sans-serif;
  letter-spacing: -1px;
  color: #292a3c;
}

.kpi-trend {
  margin: 0;
  font-size: 12px;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 6px;
}

.kpi-trend.positive { color: #10b981; }
.kpi-trend.negative { color: #ef4444; }
.kpi-trend.neutral { color: #f59e0b; }

.charts-grid {
  max-width: 1200px;
  margin: 0 auto 32px;
  padding: 0 24px;
  display: grid;
  grid-template-columns: 1fr;
  gap: 20px;
}

@media (min-width: 768px) {
  .charts-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

.chart-card {
  background: #fff;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 4px 20px #1a1a1a08;
  border: 1px solid #ededef;
}

.chart-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.chart-kicker {
  font: 700 10px Manrope, sans-serif;
  letter-spacing: 1.2px;
  color: #8b8d9e;
  text-transform: uppercase;
}

.chart-title {
  margin: 0;
  font: 700 16px Manrope, sans-serif;
  color: #292a3c;
}

.chart-donut-wrapper {
  width: 160px;
  height: 160px;
  margin: 0 auto 20px;
  position: relative;
}

.donut-chart {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}

.donut-track {
  fill: none;
}

.donut-slice {
  fill: none;
  stroke-linecap: round;
}

.donut-legend {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.legend-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
  color: #4a4c5d;
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-right: 8px;
  flex-shrink: 0;
}

.legend-count {
  font-weight: 700;
  color: #292a3c;
}

.dashboard-rows {
  max-width: 1200px;
  margin: 0 auto 32px;
  padding: 0 24px;
  display: grid;
  grid-template-columns: 1fr;
  gap: 20px;
}

@media (min-width: 768px) {
  .dashboard-rows {
    grid-template-columns: repeat(2, 1fr);
  }
}

.dashboard-panel.full-width {
  grid-column: 1 / -1;
}

.dashboard-panel {
  background: #fff;
  border-radius: 16px;
  border: 1px solid #ededef;
  box-shadow: 0 4px 20px #1a1a1a08;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 20px 24px;
  border-bottom: 1px solid #f1f5f9;
  background: #fafafa;
}

.panel-kicker {
  font-size: 18px;
}

.panel-title {
  margin: 0;
  font: 700 16px Manrope, sans-serif;
  color: #292a3c;
}

.panel-body {
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  flex: 1;
}

.deadline-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.deadline-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: #fafafa;
  border-radius: 10px;
  border: 1px solid #f1f5f9;
}

.deadline-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.deadline-info strong {
  display: block;
  font-size: 14px;
  color: #292a3c;
}

.deadline-project {
  font-size: 12px;
  font-weight: 500;
  color: #64748b;
}

.deadline-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
}

.deadline-days {
  font-size: 12px;
  font-weight: 700;
  color: #ef4444;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.4px;
  text-transform: uppercase;
}

.status-pill.status-todo { background: #e2e8f0; color: #475569; }
.status-pill.status-in_progress { background: #dbeafe; color: #1d4ed8; }
.status-pill.status-done { background: #d1fae5; color: #059669; }
.status-pill.status-blocked { background: #fee2e2; color: #dc2626; }

.projects-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.project-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  background: #fafafa;
  border-radius: 10px;
  border: 1px solid #f1f5f9;
}

.project-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.project-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.project-info > div {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.project-info strong {
  display: block;
  font-size: 14px;
  color: #292a3c;
}

.project-meta {
  font-size: 12px;
  color: #64748b;
}

.project-progress {
  display: flex;
  align-items: center;
  gap: 10px;
}

.progress-bar {
  width: 80px;
  height: 6px;
  background: #e2e8f0;
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.6s ease;
}

.progress-pct {
  font-size: 12px;
  font-weight: 700;
  color: #292a3c;
  min-width: 30px;
  text-align: right;
}

.activity-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.activity-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 16px;
  background: #fafafa;
  border-radius: 10px;
  border: 1px solid #f1f5f9;
}

.activity-avatar {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: grid;
  place-items: center;
  font-weight: 700;
  font-size: 15px;
  color: #fff;
  flex-shrink: 0;
  box-shadow: 0 2px 6px rgba(0,0,0,0.1);
}

.activity-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.activity-content strong {
  display: block;
  font-size: 14px;
  color: #292a3c;
}

.activity-meta {
  font-size: 12px;
  color: #64748b;
  display: flex;
  gap: 6px;
  align-items: center;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 40px 20px;
  color: #8b8d9e;
  text-align: center;
}

.empty-icon {
  font-size: 32px;
}

.empty-state p {
  margin: 0;
  font-size: 14px;
}

.dashboard-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 60px 20px;
  color: #8b8d9e;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #e2e8f0;
  border-top-color: #7165e8;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.message {
  max-width: 1200px;
  margin: 0 auto 24px;
  padding: 0 24px;
}

@media (max-width: 640px) {
  .header-title {
    font-size: 22px;
  }
  .kpi-value {
    font-size: 20px;
  }
}
</template>

/* Entrance animations */
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes pulse {
  0% { opacity: 1; }
  50% { opacity: 0.5; }
  100% { opacity: 1; }
}

/* Reduced motion preference */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0s !important;
    transition-duration: 0s !important;
  }
}

/* Tooltip styles */
.tooltip {
  position: relative;
  cursor: help;
}

.tooltip::after {
  content: attr(data-tip);
  position: absolute;
  left: 50%;
  bottom: 100%;
  transform: translateX(-50%);
  padding: 6px 10px;
  background: #292a3c;
  color: #fff;
  font-size: 12px;
  border-radius: 6px;
  white-space: nowrap;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.2s;
  width: max-content;
  max-width: 200px;
  margin-bottom: 8px;
}

.tooltip:hover::after {
  opacity: 1;
}

/* Card hover enhancement */
.kpi-card,
.chart-card,
.dashboard-panel {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.kpi-card:hover,
.chart-card:hover,
.dashboard-panel:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 30px rgba(0,0,0,0.15);
}

/::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: #f1f5f9;
}

::-webkit-scrollbar-thumb {
  background: #cbd5e0;
  border-radius: 3px;
}


/* Entrance animations */
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes pulse {
  0% { opacity: 1; }
  50% { opacity: 0.5; }
  100% { opacity: 1; }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Reduced motion preference */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0s !important;
    transition-duration: 0s !important;
  }
}

.kpi-card,
.chart-card,
.dashboard-panel {
  opacity: 0;
  transform: translateY(20px);
  animation: fadeInUp 0.6s ease forwards;
}

.kpi-card:nth-child(1) { animation-delay: 0.1s; }
.kpi-card:nth-child(2) { animation-delay: 0.2s; }
.kpi-card:nth-child(3) { animation-delay: 0.3s; }
.kpi-card:nth-child(4) { animation-delay: 0.4s; }

.chart-card { animation-delay: 0.15s; }
.dashboard-panel { animation-delay: 0.2s; }

@media (prefers-reduced-motion: reduce) {
  .kpi-card,
  .chart-card,
  .dashboard-panel {
    animation: none;
    opacity: 1;
    transform: none;
  }
}

.kpi-card:hover {
  transform: translateY(-4px) scale(1.02);
  box-shadow: 0 12px 30px rgba(113, 101, 232, 0.15);
}

.kpi-card:hover .kpi-icon {
  transform: scale(1.1);
}

.kpi-card:hover::before {
  height: 100%;
}

.kpi-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 3px;
  height: 0%;
  background: linear-gradient(to bottom, #7165e8, #5b4fd6);
  transition: height 0.3s ease;
}

.chart-card:hover::before {
  opacity: 1;
}

.dashboard-panel:hover {
  border-color: #7165e8;
  box-shadow: 0 8px 25px rgba(113, 101, 232, 0.1);
}

.dashboard-panel:hover::before {
  opacity: 1;
}

.dashboard-panel {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.dashboard-panel {
  position: relative;
  overflow: hidden;
}

.dashboard-panel::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: #f7f8fc;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.deadline-item:hover {
  background: #f0f4f8;
  border-color: #e2e8f0;
}

.deadline-item:hover .deadline-project {
  color: #7165e8;
}

.status-pill:hover {
  transform: translateY(-2px);
}

.project-row:hover {
  background: #f0f4f8;
  border-color: #e2e8f0;
}

.project-row:hover .project-dot {
  background: #7165e8;
}

.activity-item:hover {
  background: #f0f4f8;
  border-color: #e2e8f0;
}

.activity-item:hover .activity-avatar {
  background: #7165e8;
}
</style></div><p>A carregar o seu dashboardÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¦</p>
    </div