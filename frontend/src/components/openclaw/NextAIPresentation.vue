<template>
  <section class="oc-presentation" :data-kind="presentation.kind">
    <header class="oc-presentation-header">
      <div class="oc-presentation-title-row">
        <component :is="kindIcon" class="h-4 w-4 shrink-0" aria-hidden="true" />
        <h3>{{ presentation.title }}</h3>
        <span v-if="audienceLabel" class="oc-audience-chip">{{ audienceLabel }}</span>
      </div>
      <p v-if="presentation.summary">{{ presentation.summary }}</p>
    </header>

    <div v-if="presentation.work" class="oc-work-state" :data-state="presentation.work.state">
      <span class="oc-work-dot" />
      <div class="min-w-0">
        <div class="font-medium">{{ presentation.work.label }}</div>
        <div v-if="presentation.work.detail" class="text-xs text-ink-gray-6">
          {{ presentation.work.detail }}
        </div>
      </div>
    </div>

    <div v-if="presentation.kpis?.length" class="oc-kpi-grid">
      <div
        v-for="kpi in presentation.kpis"
        :key="kpi.label + '-' + kpi.value"
        class="oc-kpi"
        :data-tone="kpi.tone || 'neutral'"
      >
        <span>{{ kpi.label }}</span>
        <strong>{{ kpi.value }}</strong>
        <small v-if="kpi.detail">{{ kpi.detail }}</small>
      </div>
    </div>

    <div v-if="presentation.trends?.length" class="oc-trends">
      <div v-for="trend in presentation.trends" :key="trend.id" class="oc-trend">
        <div class="oc-section-heading">
          <span>{{ trend.label }}</span>
          <span v-if="trend.unit">{{ trend.unit }}</span>
        </div>
        <div class="oc-trend-bars" :style="{ '--trend-columns': trend.points.length }">
          <div v-for="point in trend.points" :key="point.label" class="oc-trend-point">
            <div class="oc-trend-track">
              <span :style="{ height: trendHeight(trend.points, point.value) + '%' }" />
            </div>
            <strong>{{ point.value }}</strong>
            <small>{{ point.label }}</small>
          </div>
        </div>
      </div>
    </div>

    <div v-if="presentation.filters?.length" class="oc-filter-grid">
      <label v-for="filter in presentation.filters" :key="filter.id" class="oc-filter">
        <span>{{ filter.label }}</span>
        <select
          :value="filter.selected || ''"
          :disabled="!filter.options?.length || !filter.action?.command"
          @change="applyFilter(filter, $event)"
        >
          <option value="" disabled>Select</option>
          <option v-for="option in filter.options || []" :key="option.value" :value="option.value">
            {{ option.label }}
          </option>
        </select>
      </label>
    </div>

    <div v-if="presentation.tables?.length" class="oc-table-stack">
      <section v-for="table in presentation.tables" :key="table.id" class="oc-table-section">
        <div v-if="table.title" class="oc-section-heading">{{ table.title }}</div>
        <div class="oc-table-scroll">
          <table>
            <thead>
              <tr>
                <th v-for="column in table.columns" :key="column" scope="col">{{ column }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!table.rows?.length">
                <td :colspan="Math.max(1, table.columns.length)">No rows</td>
              </tr>
              <tr v-for="(row, rowIndex) in table.rows || []" :key="table.id + '-' + rowIndex">
                <td v-for="(cell, cellIndex) in row" :key="cellIndex">
                  <a
                    v-if="safeHref(cell)"
                    :href="safeHref(cell) || undefined"
                    target="_blank"
                    rel="noopener"
                    class="oc-table-link"
                  >
                    {{ linkLabel(table.columns[cellIndex], cell) }}
                    <LucideArrowUpRight class="h-3.5 w-3.5" aria-hidden="true" />
                  </a>
                  <span v-else>{{ cell }}</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="table.pagination" class="oc-pagination">
          <span>Page {{ table.pagination.page }}</span>
          <span>{{ table.pagination.totalRows }} rows</span>
        </div>
      </section>
    </div>

    <div v-if="allActions.length" class="oc-presentation-actions">
      <button
        v-for="action in allActions"
        :key="action.id"
        type="button"
        :class="actionClass(action.style)"
        :title="action.detail || action.label"
        @click="emitAction(action.command)"
      >
        {{ action.label }}
        <LucideChevronRight class="h-3.5 w-3.5" aria-hidden="true" />
      </button>
    </div>

    <footer v-if="presentation.notice || presentation.privacy?.note" class="oc-presentation-footer">
      <LucideShieldCheck
        v-if="presentation.privacy?.note"
        class="h-3.5 w-3.5 shrink-0 text-teal-700"
        aria-hidden="true"
      />
      <span>{{ presentation.notice || presentation.privacy?.note }}</span>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import LucideArrowUpRight from '~icons/lucide/arrow-up-right'
import LucideBarChart3 from '~icons/lucide/bar-chart-3'
import LucideChevronRight from '~icons/lucide/chevron-right'
import LucideCircleCheck from '~icons/lucide/circle-check'
import LucideLayoutGrid from '~icons/lucide/layout-grid'
import LucideListChecks from '~icons/lucide/list-checks'
import LucideShieldCheck from '~icons/lucide/shield-check'

type PresentationAction = {
  id: string
  label: string
  command: string
  detail?: string
  style?: 'default' | 'primary' | 'danger'
  kind?: string
}

type PresentationFilter = {
  id: string
  label: string
  selected?: string
  options?: Array<{ label: string; value: string }>
  action?: PresentationAction
}

type Presentation = {
  kind: 'menu' | 'report' | 'status' | 'form'
  title: string
  summary: string
  audience?: 'general' | 'self' | 'manager' | 'admin'
  kpis?: Array<{ label: string; value: string; detail?: string; tone?: string }>
  trends?: Array<{
    id: string
    label: string
    unit?: string
    points: Array<{ label: string; value: number }>
  }>
  tables?: Array<{
    id: string
    title?: string
    columns: string[]
    rows: string[][]
    pagination?: { page: number; pageSize: number; totalRows: number }
  }>
  filters?: PresentationFilter[]
  drilldowns?: PresentationAction[]
  actions?: PresentationAction[]
  work?: { id: string; state: string; label: string; detail?: string; updatedAt?: string }
  notice?: string
  privacy?: { rawPromptsIncluded: boolean; note?: string }
}

const props = defineProps<{ presentation: Presentation }>()
const emit = defineEmits<{ (event: 'action', command: string): void }>()

const kindIcon = computed(
  () =>
    ({
      menu: LucideLayoutGrid,
      report: LucideBarChart3,
      status: LucideCircleCheck,
      form: LucideListChecks,
    })[props.presentation.kind] || LucideLayoutGrid,
)

const audienceLabel = computed(
  () =>
    ({
      self: 'Personal',
      manager: 'Manager',
      admin: 'Admin',
    })[props.presentation.audience || 'general'] || '',
)

const allActions = computed(() =>
  [...(props.presentation.drilldowns || []), ...(props.presentation.actions || [])].filter(
    (action) => action?.command && action?.label,
  ),
)

function safeHref(value: string): string | null {
  const candidate = String(value || '').trim()
  return /^(?:https?:\/\/|\/(?:app|helpdesk|files)\/)/i.test(candidate) ? candidate : null
}

function linkLabel(column: string, value: string): string {
  if (/^(?:open|link|record)$/i.test(String(column || '').trim())) return 'Open record'
  try {
    const url = new URL(value, window.location.origin)
    return url.pathname.split('/').filter(Boolean).pop() || 'Open'
  } catch {
    return 'Open'
  }
}

function trendHeight(points: Array<{ value: number }>, value: number): number {
  const max = Math.max(1, ...points.map((point) => Math.abs(Number(point.value) || 0)))
  return Math.max(4, Math.round((Math.abs(Number(value) || 0) / max) * 100))
}

function actionClass(style?: string): string {
  return [
    'oc-presentation-action',
    style === 'primary' ? 'oc-presentation-action--primary' : '',
    style === 'danger' ? 'oc-presentation-action--danger' : '',
  ]
    .filter(Boolean)
    .join(' ')
}

function emitAction(command: string) {
  if (command?.trim()) emit('action', command.trim())
}

function applyFilter(filter: PresentationFilter, event: Event) {
  const value = (event.target as HTMLSelectElement)?.value
  const template = filter.action?.command
  if (!value || !template) return
  const command = template.includes('{value}')
    ? template.replaceAll('{value}', value)
    : template + ' ' + filter.id + '=' + value
  emitAction(command)
}
</script>

<style scoped>
.oc-presentation {
  width: 100%;
  overflow: hidden;
  border: 1px solid var(--surface-gray-3, #e5e7eb);
  border-radius: 8px;
  background: var(--surface-white, #fff);
  color: var(--ink-gray-8, #1f2937);
  box-shadow: 0 6px 18px rgba(15, 23, 42, 0.07);
  animation: oc-presentation-in 160ms ease-out both;
}
.oc-presentation-header {
  padding: 0.875rem 1rem 0.75rem;
  border-bottom: 1px solid var(--surface-gray-2, #f3f4f6);
}
.oc-presentation-title-row {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 0.5rem;
  color: #0f766e;
}
.oc-presentation-title-row h3 {
  min-width: 0;
  flex: 1;
  margin: 0;
  color: var(--ink-gray-9, #111827);
  font-size: 0.875rem;
  font-weight: 650;
  line-height: 1.25rem;
}
.oc-presentation-header p {
  margin: 0.375rem 0 0;
  color: var(--ink-gray-6, #4b5563);
  font-size: 0.75rem;
  line-height: 1.15rem;
}
.oc-audience-chip {
  flex: 0 0 auto;
  border: 1px solid #99f6e4;
  border-radius: 999px;
  background: #f0fdfa;
  padding: 0.1rem 0.45rem;
  color: #115e59;
  font-size: 0.625rem;
  font-weight: 600;
}
.oc-work-state {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  padding: 0.625rem 1rem;
  border-bottom: 1px solid var(--surface-gray-2, #f3f4f6);
  background: #f8fafc;
  font-size: 0.75rem;
}
.oc-work-dot {
  width: 0.5rem;
  height: 0.5rem;
  margin-top: 0.25rem;
  flex: 0 0 auto;
  border-radius: 50%;
  background: #0f766e;
}
.oc-work-state[data-state='failed'] .oc-work-dot {
  background: #b91c1c;
}
.oc-work-state[data-state='waiting'] .oc-work-dot {
  background: #b45309;
}
.oc-kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(7rem, 1fr));
  border-bottom: 1px solid var(--surface-gray-2, #f3f4f6);
}
.oc-kpi {
  min-width: 0;
  padding: 0.7rem 0.85rem;
  border-right: 1px solid var(--surface-gray-2, #f3f4f6);
}
.oc-kpi:last-child {
  border-right: 0;
}
.oc-kpi span,
.oc-kpi small {
  display: block;
  overflow-wrap: anywhere;
  color: var(--ink-gray-5, #6b7280);
  font-size: 0.65rem;
  line-height: 1rem;
}
.oc-kpi strong {
  display: block;
  margin-top: 0.1rem;
  color: var(--ink-gray-9, #111827);
  font-size: 1rem;
  font-weight: 680;
  line-height: 1.25rem;
}
.oc-kpi[data-tone='positive'] strong {
  color: #047857;
}
.oc-kpi[data-tone='warning'] strong {
  color: #b45309;
}
.oc-kpi[data-tone='critical'] strong {
  color: #b91c1c;
}
.oc-trends,
.oc-table-stack {
  display: grid;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--surface-gray-2, #f3f4f6);
}
.oc-section-heading {
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
  margin-bottom: 0.4rem;
  color: var(--ink-gray-7, #374151);
  font-size: 0.7rem;
  font-weight: 650;
}
.oc-trend-bars {
  display: grid;
  grid-template-columns: repeat(var(--trend-columns), minmax(1.5rem, 1fr));
  gap: 0.35rem;
  overflow-x: auto;
}
.oc-trend-point {
  display: grid;
  min-width: 1.5rem;
  justify-items: center;
  gap: 0.15rem;
  font-size: 0.6rem;
}
.oc-trend-track {
  display: flex;
  width: 0.6rem;
  height: 3.5rem;
  align-items: flex-end;
  overflow: hidden;
  border-radius: 3px;
  background: var(--surface-gray-2, #f3f4f6);
}
.oc-trend-track span {
  width: 100%;
  background: #0f766e;
}
.oc-trend-point small {
  max-width: 4rem;
  overflow: hidden;
  color: var(--ink-gray-5, #6b7280);
  text-overflow: ellipsis;
  white-space: nowrap;
}
.oc-filter-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(8rem, 1fr));
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--surface-gray-2, #f3f4f6);
}
.oc-filter {
  display: grid;
  gap: 0.25rem;
  color: var(--ink-gray-6, #4b5563);
  font-size: 0.65rem;
  font-weight: 600;
}
.oc-filter select {
  width: 100%;
  min-width: 0;
  height: 2rem;
  border: 1px solid var(--surface-gray-4, #d1d5db);
  border-radius: 6px;
  background: #fff;
  padding: 0 0.5rem;
  color: var(--ink-gray-8, #1f2937);
  font-size: 0.75rem;
}
.oc-table-section {
  min-width: 0;
}
.oc-table-scroll {
  max-width: 100%;
  overflow-x: auto;
  border: 1px solid var(--surface-gray-3, #e5e7eb);
  border-radius: 6px;
}
.oc-table-scroll table {
  width: 100%;
  min-width: 30rem;
  border-collapse: collapse;
  font-size: 0.7rem;
}
.oc-table-scroll th,
.oc-table-scroll td {
  max-width: 18rem;
  padding: 0.5rem 0.6rem;
  border-right: 1px solid var(--surface-gray-2, #f3f4f6);
  border-bottom: 1px solid var(--surface-gray-2, #f3f4f6);
  overflow-wrap: anywhere;
  text-align: left;
  vertical-align: top;
}
.oc-table-scroll th {
  background: #f8fafc;
  color: var(--ink-gray-6, #4b5563);
  font-size: 0.625rem;
  font-weight: 650;
  text-transform: uppercase;
}
.oc-table-scroll tr:last-child td {
  border-bottom: 0;
}
.oc-table-scroll th:last-child,
.oc-table-scroll td:last-child {
  border-right: 0;
}
.oc-table-scroll th:first-child,
.oc-table-scroll td:first-child {
  position: sticky;
  left: 0;
  z-index: 1;
  background: #fff;
  font-weight: 600;
}
.oc-table-scroll th:first-child {
  background: #f8fafc;
}
.oc-table-link {
  display: inline-flex;
  align-items: center;
  gap: 0.2rem;
  color: #0f766e;
  font-weight: 650;
  text-decoration: none;
}
.oc-table-link:hover {
  text-decoration: underline;
  text-underline-offset: 2px;
}
.oc-pagination {
  display: flex;
  justify-content: space-between;
  padding-top: 0.35rem;
  color: var(--ink-gray-5, #6b7280);
  font-size: 0.625rem;
}
.oc-presentation-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  padding: 0.75rem 1rem;
}
.oc-presentation-action {
  display: inline-flex;
  min-height: 2rem;
  align-items: center;
  gap: 0.2rem;
  border: 1px solid var(--surface-gray-4, #d1d5db);
  border-radius: 6px;
  background: #fff;
  padding: 0.35rem 0.6rem;
  color: var(--ink-gray-8, #1f2937);
  font-size: 0.7rem;
  font-weight: 600;
}
.oc-presentation-action:hover {
  border-color: #5eead4;
  background: #f0fdfa;
}
.oc-presentation-action--primary {
  border-color: #0f766e;
  background: #0f766e;
  color: #fff;
}
.oc-presentation-action--primary:hover {
  border-color: #115e59;
  background: #115e59;
}
.oc-presentation-action--danger {
  border-color: #fecaca;
  color: #b91c1c;
}
.oc-presentation-action--danger:hover {
  border-color: #fca5a5;
  background: #fef2f2;
}
.oc-presentation-footer {
  display: flex;
  align-items: flex-start;
  gap: 0.35rem;
  border-top: 1px solid var(--surface-gray-2, #f3f4f6);
  background: #fafafa;
  padding: 0.55rem 1rem;
  color: var(--ink-gray-5, #6b7280);
  font-size: 0.625rem;
  line-height: 1rem;
}
@keyframes oc-presentation-in {
  from {
    opacity: 0;
    transform: translateY(3px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
@media (max-width: 640px) {
  .oc-kpi-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .oc-kpi:nth-child(2n) {
    border-right: 0;
  }
  .oc-table-scroll table {
    min-width: 36rem;
  }
  .oc-presentation-actions {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .oc-presentation-action {
    justify-content: space-between;
  }
}
</style>
