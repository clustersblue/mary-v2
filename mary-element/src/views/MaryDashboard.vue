<template>
  <div class="dashboard-container" v-loading="loading">
    <el-result
      v-if="!allowed"
      icon="warning"
      title="Dashboard restricted"
      sub-title="Attendance and care analytics are available to administrators."
    />

    <template v-else>
      <div class="toolbar">
        <div>
          <h2>Executive dashboard</h2>
          <p>Organisation totals stay fixed. Charts follow the selected period.</p>
        </div>
        <div class="toolbar-actions">
          <el-radio-group v-model="period" @change="load">
            <el-radio-button value="daily">Daily</el-radio-button>
            <el-radio-button value="weekly">Weekly</el-radio-button>
            <el-radio-button value="monthly">Monthly</el-radio-button>
          </el-radio-group>
          <el-button icon="Refresh" :loading="loading" @click="load">Refresh</el-button>
        </div>
      </div>

      <el-row :gutter="16">
        <el-col :xs="24" :sm="12" :lg="6" v-for="card in primaryCards" :key="card.label">
          <el-card shadow="hover" class="stat-card">
            <div class="stat-content">
              <el-icon :class="['stat-icon', card.tone]"><component :is="card.icon" /></el-icon>
              <div class="stat-info">
                <span class="stat-title">{{ card.label }}</span>
                <span class="stat-value">{{ card.value }}</span>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="16" class="mt-16">
        <el-col :span="24">
          <el-card shadow="never">
            <template #header><span>Attendance overview</span></template>
            <VChart class="chart" :option="attendanceOption" autoresize />
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="16" class="mt-16">
        <el-col :span="24">
          <el-card shadow="never">
            <template #header><span>Carer attendance trend</span></template>
            <VChart class="chart" :option="qualityOption" autoresize />
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="16" class="mt-16">
        <el-col :span="24">
          <el-card shadow="never">
            <template #header><span>Visit status</span></template>
            <VChart v-if="visitTotal" class="chart" :option="statusOption" autoresize />
            <el-empty v-else description="No visits in this period" />
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="16" class="mt-16">
        <el-col :xs="24" :lg="14">
          <el-card shadow="never">
            <template #header>
              <div class="card-header">
                <span>Care notes activity</span>
                <el-radio-group v-model="noteGroup" size="small">
                  <el-radio-button value="day">By day</el-radio-button>
                  <el-radio-button value="carer">By carer</el-radio-button>
                  <el-radio-button value="service_user">By service user</el-radio-button>
                </el-radio-group>
              </div>
            </template>
            <VChart v-if="noteChart.labels.length" class="chart" :option="notesOption" autoresize />
            <el-empty v-else description="No care notes in this period" />
          </el-card>
        </el-col>
        <el-col :xs="24" :lg="10">
          <el-card shadow="never">
            <template #header><span>Carer workload</span></template>
            <VChart v-if="report.workload.labels.length" class="chart" :option="workloadOption" autoresize />
            <el-empty v-else description="No carer workload in this period" />
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="16" class="mt-16">
        <el-col :span="24">
          <el-card shadow="never">
            <template #header><span>Monthly service delivery</span></template>
            <VChart class="chart" :option="deliveryOption" autoresize />
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="16" class="mt-16">
        <el-col :span="24">
          <el-card shadow="never">
            <template #header>
              <div class="card-header">
                <span>Payroll and invoice records</span>
                <span class="stat-note">Batch counts, not currency</span>
              </div>
            </template>
            <VChart class="chart" :option="chargesOption" autoresize />
          </el-card>
        </el-col>
      </el-row>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useDark } from '@vueuse/core'
import { ElMessage } from 'element-plus'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, LineChart, PieChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import api from '@/service/api'
import { useAuthStore } from '@/store/auth'

use([CanvasRenderer, LineChart, BarChart, PieChart, GridComponent, TooltipComponent, LegendComponent])

const authStore = useAuthStore()
const isDark = useDark()
const allowed = computed(() => authStore.isAdmin)
const loading = ref(false)
const period = ref('monthly')
const noteGroup = ref('day')
const emptyReport = () => ({
  kpis: {},
  attendance: { labels: [], clock_ins: [], clock_outs: [], hours: [] },
  attendance_quality: { labels: [], attended: [], missed: [], late: [] },
  visit_status: { scheduled: 0, active: 0, completed: 0, missed: 0 },
  notes_by_day: { labels: [], notes: [] },
  notes_by_carer: { labels: [], values: [] },
  notes_by_service_user: { labels: [], values: [] },
  workload: { labels: [], hours: [], visits: [] },
  delivery: { labels: [], scheduled_hours: [], completed_hours: [], missed_hours: [], overtime_hours: [] },
  charges: { labels: [], visits: [], payrolls: [], invoices: [] }
})
const report = ref(emptyReport())

const primaryCards = computed(() => [
  { label: 'Service users', value: report.value.kpis.service_users ?? 0, icon: 'User', tone: 'primary' },
  { label: 'Carers', value: report.value.kpis.carers ?? 0, icon: 'UserFilled', tone: 'success' },
  { label: 'Active shifts', value: report.value.kpis.active_shifts ?? 0, icon: 'Calendar', tone: 'warning' },
  { label: 'Attendance today', value: report.value.kpis.attendance_today ?? 0, icon: 'Clock', tone: 'danger' }
])
const visitTotal = computed(() => Object.values(report.value.visit_status).reduce((sum, value) => sum + Number(value || 0), 0))
const noteChart = computed(() => {
  if (noteGroup.value === 'carer') return { labels: report.value.notes_by_carer.labels, values: report.value.notes_by_carer.values }
  if (noteGroup.value === 'service_user') return { labels: report.value.notes_by_service_user.labels, values: report.value.notes_by_service_user.values }
  return { labels: report.value.notes_by_day.labels, values: report.value.notes_by_day.notes }
})
function palette() {
  const dark = isDark.value
  return {
    text: dark ? '#E5EAF3' : '#303133',
    muted: dark ? '#A3A6AD' : '#606266',
    line: dark ? '#4C4D4F' : '#DCDFE6',
    blue: '#409EFF',
    green: '#67C23A',
    amber: '#E6A23C',
    red: '#F56C6C',
    gray: '#909399'
  }
}
function axis(color) {
  return {
    axisLabel: { color: color.muted },
    axisLine: { lineStyle: { color: color.line } },
    splitLine: { lineStyle: { color: color.line } },
    nameTextStyle: { color: color.muted }
  }
}
function base(color) {
  return {
    backgroundColor: 'transparent',
    textStyle: { color: color.text },
    tooltip: { trigger: 'axis' },
    legend: { textStyle: { color: color.muted }, top: 0 },
    grid: { left: 16, right: 16, top: 40, bottom: 8, containLabel: true }
  }
}
const attendanceOption = computed(() => {
  const color = palette()
  const rows = report.value.attendance
  return {
    ...base(color),
    xAxis: { type: 'category', data: rows.labels, ...axis(color) },
    yAxis: [
      { type: 'value', name: 'Clocks', ...axis(color) },
      { type: 'value', name: 'Hours', ...axis(color) }
    ],
    series: [
      { name: 'Clock in', type: 'line', smooth: true, data: rows.clock_ins, color: color.blue },
      { name: 'Clock out', type: 'line', smooth: true, data: rows.clock_outs, color: color.green },
      { name: 'Hours worked', type: 'line', smooth: true, yAxisIndex: 1, data: rows.hours, color: color.amber }
    ]
  }
})
const qualityOption = computed(() => {
  const color = palette()
  const rows = report.value.attendance_quality
  return {
    ...base(color),
    xAxis: { type: 'category', data: rows.labels, ...axis(color) },
    yAxis: { type: 'value', ...axis(color) },
    series: [
      { name: 'Attended', type: 'line', smooth: true, areaStyle: { opacity: 0.18 }, data: rows.attended, color: color.green },
      { name: 'Missed', type: 'line', smooth: true, data: rows.missed, color: color.red },
      { name: 'Late clock-ins', type: 'line', smooth: true, data: rows.late, color: color.amber }
    ]
  }
})
const statusOption = computed(() => {
  const color = palette()
  const status = report.value.visit_status
  return {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item' },
    legend: { bottom: 0, textStyle: { color: color.muted } },
    series: [{
      type: 'pie',
      radius: ['48%', '72%'],
      label: { color: color.text },
      data: [
        { name: 'Scheduled', value: status.scheduled, itemStyle: { color: color.gray } },
        { name: 'Active', value: status.active, itemStyle: { color: color.amber } },
        { name: 'Completed', value: status.completed, itemStyle: { color: color.green } },
        { name: 'Missed', value: status.missed, itemStyle: { color: color.red } }
      ]
    }]
  }
})
const notesOption = computed(() => {
  const color = palette()
  return {
    ...base(color),
    xAxis: { type: 'category', data: noteChart.value.labels, axisLabel: { color: color.muted, rotate: noteGroup.value === 'day' ? 0 : 30 }, axisLine: { lineStyle: { color: color.line } } },
    yAxis: { type: 'value', ...axis(color) },
    series: [{ name: 'Notes', type: 'bar', data: noteChart.value.values, color: color.green, barMaxWidth: 36 }]
  }
})
const workloadOption = computed(() => {
  const color = palette()
  const rows = report.value.workload
  return {
    ...base(color),
    grid: { left: 8, right: 16, top: 40, bottom: 8, containLabel: true },
    xAxis: { type: 'value', ...axis(color) },
    yAxis: { type: 'category', data: [...rows.labels].reverse(), axisLabel: { color: color.muted } },
    series: [
      { name: 'Hours worked', type: 'bar', data: [...rows.hours].reverse(), color: color.blue, barMaxWidth: 18 },
      { name: 'Assigned visits', type: 'bar', data: [...rows.visits].reverse(), color: color.amber, barMaxWidth: 18 }
    ]
  }
})
const deliveryOption = computed(() => {
  const color = palette()
  const rows = report.value.delivery
  return {
    ...base(color),
    xAxis: { type: 'category', data: rows.labels, ...axis(color) },
    yAxis: { type: 'value', name: 'Hours', ...axis(color) },
    series: [
      { name: 'Completed hours', type: 'bar', stack: 'delivery', data: rows.completed_hours, color: color.green, barMaxWidth: 28 },
      { name: 'Missed hours', type: 'bar', stack: 'delivery', data: rows.missed_hours, color: color.red, barMaxWidth: 28 },
      { name: 'Scheduled hours', type: 'line', data: rows.scheduled_hours, color: color.gray },
      { name: 'Overtime hours', type: 'line', data: rows.overtime_hours, color: color.amber }
    ]
  }
})
const chargesOption = computed(() => {
  const color = palette()
  const rows = report.value.charges
  return {
    ...base(color),
    xAxis: { type: 'category', data: rows.labels, ...axis(color) },
    yAxis: { type: 'value', ...axis(color) },
    series: [
      { name: 'Visits', type: 'bar', data: rows.visits, color: color.blue, barMaxWidth: 24 },
      { name: 'Payroll batches', type: 'bar', data: rows.payrolls, color: color.green, barMaxWidth: 24 },
      { name: 'Invoice batches', type: 'bar', data: rows.invoices, color: color.amber, barMaxWidth: 24 }
    ]
  }
})

async function load() {
  if (!allowed.value) return
  loading.value = true
  try {
    const response = await api.get('/dashboard-analytics', { params: { period: period.value } })
    report.value = { ...emptyReport(), ...(response.data || {}) }
  } catch (error) {
    report.value = emptyReport()
    const detail = error?.response?.data?.detail
    ElMessage.error(typeof detail === 'string' ? detail : 'The dashboard could not be loaded')
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.dashboard-container { width: 100%; }
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}
.toolbar h2 { margin: 0 0 4px; font-size: 22px; }
.toolbar p, .stat-note { margin: 0; color: var(--el-text-color-secondary); font-size: 13px; }
.toolbar-actions { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
.mt-16 { margin-top: 16px; }
.stat-card { border-radius: 8px; margin-bottom: 0; }
.stat-content { display: flex; align-items: center; gap: 16px; }
.stat-icon { font-size: 32px; padding: 12px; border-radius: 8px; }
.stat-icon.primary { background: var(--el-color-primary-light-9); color: var(--el-color-primary); }
.stat-icon.success { background: var(--el-color-success-light-9); color: var(--el-color-success); }
.stat-icon.warning { background: var(--el-color-warning-light-9); color: var(--el-color-warning); }
.stat-icon.danger { background: var(--el-color-danger-light-9); color: var(--el-color-danger); }
.stat-info { display: flex; flex-direction: column; }
.stat-title { font-size: 13px; color: var(--el-text-color-secondary); }
.stat-value { font-size: 22px; font-weight: 700; color: var(--el-text-color-primary); }
.card-header { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; font-weight: 600; }
.chart { width: 100%; height: 320px; }
@media (max-width: 768px) {
  .chart { height: 280px; }
  .toolbar-actions, .toolbar-actions :deep(.el-radio-group) { width: 100%; }
}
</style>
