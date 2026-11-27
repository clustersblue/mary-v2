<template>
  <div class="invoice-view">
    <el-card shadow="never" class="mb-4">
      <template #header>
        <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
          <div>
            <h2 class="text-xl font-bold text-gray-800 m-0">Client Invoice Management</h2>
            <p class="text-sm text-gray-500 m-0 mt-1">
              Track, bill, collect, and archive invoices generated for Service Users (clients) and funding bodies.
            </p>
          </div>
          <div class="actions flex items-center gap-2">
            <el-button type="primary" plain @click="fetchData" :loading="loading">
              <el-icon class="mr-1"><Refresh /></el-icon> Refresh
            </el-button>
            <el-button
              type="warning"
              plain
              @click="exportCurrentCsv"
              :disabled="!currentRawList.length"
            >
              <el-icon class="mr-1"><Download /></el-icon>
              {{ activeTab === 'manage' ? 'Export All Invoices' : 'Export All Invoices - History' }}
            </el-button>
          </div>
        </div>
      </template>

      <!-- KPI Summary Cards -->
      <!-- <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
        <el-card shadow="hover" class="stat-card border-l-4 border-amber-500">
          <div class="text-xs font-semibold text-gray-500 uppercase tracking-wide">Outstanding Invoices</div>
          <div class="text-2xl font-bold text-amber-600 mt-1">{{ pendingBatchCount }}</div>
        </el-card>

        <el-card shadow="hover" class="stat-card border-l-4 border-blue-500">
          <div class="text-xs font-semibold text-gray-500 uppercase tracking-wide">Total Outstanding (£)</div>
          <div class="text-2xl font-bold text-gray-900 mt-1">£{{ totalUnpaidAmount.toFixed(2) }}</div>
        </el-card>

        <el-card shadow="hover" class="stat-card border-l-4 border-green-500">
          <div class="text-xs font-semibold text-gray-500 uppercase tracking-wide">Settled Invoices (History)</div>
          <div class="text-2xl font-bold text-blue-600 mt-1">{{ paidBatchCount }}</div>
        </el-card>

        <el-card shadow="hover" class="stat-card border-l-4 border-purple-500">
          <div class="text-xs font-semibold text-gray-500 uppercase tracking-wide">Total Collected (£)</div>
          <div class="text-2xl font-bold text-green-600 mt-1">£{{ totalPaidAmount.toFixed(2) }}</div>
        </el-card>
      </div> -->

      <!-- TABS: EXACT LEGACY PARITY (Manage Invoices vs Invoice Records) -->
      <el-tabs v-model="activeTab" type="border-card">
        <!-- ========================================== -->
        <!-- TAB 0: MANAGE INVOICES (Uncollected / Pending) -->
        <!-- ========================================== -->
        <el-tab-pane label="Manage Invoices" name="manage">
          <!-- Toolbar & Global Search -->
          <div class="filter-toolbar mb-2.5 flex flex-col sm:flex-row justify-between items-center gap-3 p-3 rounded border">
            <div class="flex items-center gap-3 w-full sm:w-auto">
              <el-input
                v-model="searchQuery"
                placeholder="Search by Service User, Carer, Shift, Invoice #..."
                clearable
                style="width: 320px;"
                prefix-icon="Search"
              />
              <el-divider direction="vertical" />
              <el-dropdown trigger="click" @command="(cmd) => viewMode = cmd">
                <el-icon class="more-actions-icon" title="More Actions">
                  <MoreFilled />
                </el-icon>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item
                      command="expandable"
                      :class="{ 'is-active': viewMode === 'expandable' }"
                      @click="viewMode = 'expandable'"
                    >
                      Expandable Batches
                    </el-dropdown-item>
                    <el-dropdown-item
                      command="flat"
                      :class="{ 'is-active': viewMode === 'flat' }"
                      @click="viewMode = 'flat'"
                    >
                      All Shifts Table
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
            <div class="flex items-center gap-2"></div>
          </div>

          <div v-loading="loading">
            <!-- 1. EXPANDABLE ROWS VIEW (Exact Legacy Parity with nested details table and actions) -->
            <div v-if="viewMode === 'expandable'" class="expandable-table-wrapper">
              <el-table
                ref="unpaidTableRef"
                :data="groupedUnpaidList"
                row-key="key"
                stripe
                border
                style="width: 100%"
                empty-text="No outstanding invoice records found."
              >
                <!-- Expand Column -->
                <el-table-column type="expand" width="55">
                  <template #default="{ row }">
                    <div class="expanded-panel p-4 bg-slate-50">
                      <!-- Nested Details Table with Exact 11 Legacy Columns -->
                      <el-table
                        :data="row.items"
                        stripe
                        border
                        size="small"
                        style="width: 100%"
                        class="nested-details-table bg-white"
                      >
                        <!-- 1. Invoice -->
                        <el-table-column prop="invoice_number" label="Invoice" width="130" sortable>
                          <template #default="{ row: subRow }">
                            <el-tag size="small" type="primary" class="font-mono">{{ subRow.invoice_number }}</el-tag>
                          </template>
                        </el-table-column>

                        <!-- 2. Carer -->
                        <el-table-column prop="carer_full_name" label="Carer" min-width="150" sortable />

                        <!-- 3. Service User -->
                        <el-table-column prop="service_user" label="Service User" min-width="150" sortable />

                        <!-- 4. Service -->
                        <el-table-column prop="shift" label="Service" width="130" sortable />

                        <!-- 5. Date -->
                        <el-table-column prop="start_date" label="Date" width="120" sortable>
                          <template #default="{ row: subRow }">
                            {{ formatStartDate(subRow) }}
                          </template>
                        </el-table-column>

                        <!-- 6. Period -->
                        <el-table-column prop="date_range" label="Period" min-width="160" sortable />

                        <!-- 7. IN -->
                        <el-table-column prop="time_in" label="IN" width="90" align="center" sortable>
                          <template #default="{ row: subRow }">
                            {{ formatTime(subRow.time_in) }}
                          </template>
                        </el-table-column>

                        <!-- 8. OUT -->
                        <el-table-column prop="time_out" label="OUT" width="90" align="center" sortable>
                          <template #default="{ row: subRow }">
                            {{ formatTime(subRow.time_out) }}
                          </template>
                        </el-table-column>

                        <!-- 9. Hours -->
                        <el-table-column prop="hours" label="Hours" width="95" align="right" sortable>
                          <template #default="{ row: subRow }">
                            {{ formatHours(subRow.hours) }}
                          </template>
                        </el-table-column>

                        <!-- 10. Rates (Invoice Rate) -->
                        <el-table-column prop="invoice" label="Rates" width="120" align="right" sortable>
                          <template #default="{ row: subRow }">
                            {{ formatCurrency(subRow.invoice || subRow.invoice_rate || subRow.rate) }}
                          </template>
                        </el-table-column>

                        <!-- 11. Amount -->
                        <el-table-column prop="amount" label="Amount" width="120" align="right" sortable>
                          <template #default="{ row: subRow }">
                            <strong class="text-blue-700">{{ formatCurrency(subRow.amount) }}</strong>
                          </template>
                        </el-table-column>
                      </el-table>

                      <!-- Summary Information & Computed Values in Expanded Row (Legacy Group Footer) -->
                      <div class="mt-2 p-2 bg-white rounded border border-gray-200 flex justify-end items-center gap-4 text-sm font-bold text-gray-800">
                        <div>Total Hours: <span class="text-blue-600 font-mono">{{ row.totalHours.toFixed(2) }} hrs</span></div>
                        <div class="pl-4 border-l border-gray-300">
                          Total Amount: <span class="text-blue-700 font-mono text-base">{{ formatCurrency(row.totalAmount) }}</span>
                        </div>
                      </div>
                    </div>
                  </template>
                </el-table-column>

                <!-- Master Table Summary Columns -->
                <el-table-column prop="invoice_number" label="Invoice #" width="160" sortable>
                  <template #default="{ row }">
                    <el-tag size="small" type="primary" class="font-mono font-bold">{{ row.invoice_number }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="service_user" label="Service User (Client)" min-width="180" sortable>
                  <template #default="{ row }">
                    <span class="font-bold text-gray-900 flex items-center gap-1.5">
                      <el-icon class="text-blue-600"><User /></el-icon>
                      {{ row.service_user }}
                    </span>
                  </template>
                </el-table-column>
                <el-table-column prop="date_range" label="Billing Range" min-width="170" sortable />
                <el-table-column label="Shifts" width="90" align="center">
                  <template #default="{ row }">
                    <el-tag size="small" type="primary" effect="plain">{{ row.items.length }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="Total Hours" width="120" align="right">
                  <template #default="{ row }">
                    {{ row.totalHours.toFixed(2) }} hrs
                  </template>
                </el-table-column>
                <el-table-column label="Total Amount (£)" width="160" align="right" sortable :sort-by="(r) => r.totalAmount">
                  <template #default="{ row }">
                    <strong class="text-blue-700 text-base">{{ formatCurrency(row.totalAmount) }}</strong>
                  </template>
                </el-table-column>
                <el-table-column label="Status" width="100" align="center">
                  <template #default>
                    <el-tag type="warning" effect="dark" size="small">Pending</el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="Actions" width="230" align="center" fixed="right">
                  <template #default="{ row }">
                    <div class="flex items-center justify-center gap-1">
                      <el-button
                        size="small"
                        type="success"
                        round
                        @click.stop="handleGenerateInvoiceDoc(row)"
                        :loading="docGenerating === row.invoice_number"
                      >
                        Doc
                      </el-button>
                      <el-button
                        size="small"
                        type="warning"
                        round
                        @click.stop="handleMarkInvoice(row)"
                        :loading="actionLoading === row.invoice_number"
                      >
                        Mark Paid
                      </el-button>
                      <el-button
                        size="small"
                        type="danger"
                        circle
                        plain
                        @click.stop="handleDeleteInvoice(row)"
                        :loading="actionLoading === row.invoice_number"
                      >
                        <el-icon><Delete /></el-icon>
                      </el-button>
                    </div>
                  </template>
                </el-table-column>
              </el-table>
            </div>

            <!-- 2. FLAT TABLE VIEW (Exact 11 Legacy Columns with Total Summary) -->
            <div v-else class="flat-table-wrapper">
              <el-table
                :data="filteredUnpaidList"
                stripe
                border
                show-summary
                :summary-method="getUnpaidSummaries"
                style="width: 100%"
                empty-text="No outstanding invoice records found."
              >
                <!-- 1. Invoice -->
                <el-table-column prop="invoice_number" label="Invoice" width="140" sortable>
                  <template #default="{ row }">
                    <el-tag size="small" type="primary" class="font-mono">{{ row.invoice_number }}</el-tag>
                  </template>
                </el-table-column>

                <!-- 2. Carer -->
                <el-table-column prop="carer_full_name" label="Carer" min-width="150" sortable />

                <!-- 3. Service User -->
                <el-table-column prop="service_user" label="Service User" min-width="150" sortable />

                <!-- 4. Service -->
                <el-table-column prop="shift" label="Service" width="130" sortable />

                <!-- 5. Date -->
                <el-table-column prop="start_date" label="Date" width="120" sortable>
                  <template #default="{ row }">
                    {{ formatStartDate(row) }}
                  </template>
                </el-table-column>

                <!-- 6. Period -->
                <el-table-column prop="date_range" label="Period" min-width="160" sortable />

                <!-- 7. IN -->
                <el-table-column prop="time_in" label="IN" width="90" align="center" sortable>
                  <template #default="{ row }">
                    {{ formatTime(row.time_in) }}
                  </template>
                </el-table-column>

                <!-- 8. OUT -->
                <el-table-column prop="time_out" label="OUT" width="90" align="center" sortable>
                  <template #default="{ row }">
                    {{ formatTime(row.time_out) }}
                  </template>
                </el-table-column>

                <!-- 9. Hours -->
                <el-table-column prop="hours" label="Hours" width="95" align="right" sortable>
                  <template #default="{ row }">
                    {{ formatHours(row.hours) }}
                  </template>
                </el-table-column>

                <!-- 10. Rates -->
                <el-table-column prop="invoice" label="Rates" width="120" align="right" sortable>
                  <template #default="{ row }">
                    {{ formatCurrency(row.invoice || row.invoice_rate || row.rate) }}
                  </template>
                </el-table-column>

                <!-- 11. Amount -->
                <el-table-column prop="amount" label="Amount" width="120" align="right" sortable>
                  <template #default="{ row }">
                    <strong class="text-blue-700">{{ formatCurrency(row.amount) }}</strong>
                  </template>
                </el-table-column>

                <!-- Row Operations -->
                <el-table-column label="Actions" width="190" align="center" fixed="right">
                  <template #default="{ row }">
                    <div class="flex items-center justify-center gap-1">
                      <el-button
                        size="small"
                        type="warning"
                        round
                        @click="handleMarkInvoiceRow(row)"
                      >
                        Mark Paid
                      </el-button>
                      <el-button
                        size="small"
                        type="danger"
                        circle
                        plain
                        @click="handleDeleteInvoiceRow(row)"
                      >
                        <el-icon><Delete /></el-icon>
                      </el-button>
                    </div>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>
        </el-tab-pane>

        <!-- ========================================== -->
        <!-- TAB 1: INVOICE RECORDS (Historical / Settled) -->
        <!-- ========================================== -->
        <el-tab-pane label="Invoice Records" name="records">
          <!-- Toolbar & Global Search -->
          <div class="filter-toolbar mb-2.5 flex flex-col sm:flex-row justify-between items-center gap-3 p-3 rounded border">
            <div class="flex items-center gap-1 w-full sm:w-auto">
              <el-input
                v-model="searchQueryPaid"
                placeholder="Search history by Service User, Carer, Invoice #..."
                clearable
                style="width: 320px;"
                prefix-icon="Search"
              />
              <el-divider direction="vertical" />
              <el-dropdown trigger="click" @command="(cmd) => viewModePaid = cmd">
                <el-icon class="more-actions-icon" title="More Actions">
                  <MoreFilled />
                </el-icon>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item
                      command="expandable"
                      :class="{ 'is-active': viewModePaid === 'expandable' }"
                      @click="viewModePaid = 'expandable'"
                    >
                      Expandable Batches
                    </el-dropdown-item>
                    <el-dropdown-item
                      command="flat"
                      :class="{ 'is-active': viewModePaid === 'flat' }"
                      @click="viewModePaid = 'flat'"
                    >
                      All Shifts Table
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
            <div class="flex items-center gap-2"></div>
          </div>

          <div v-loading="loading">
            <!-- 1. EXPANDABLE ROWS VIEW (Exact Legacy Parity with nested details table and actions) -->
            <div v-if="viewModePaid === 'expandable'" class="expandable-table-wrapper">
              <el-table
                ref="paidTableRef"
                :data="groupedPaidList"
                row-key="key"
                stripe
                border
                style="width: 100%"
                empty-text="No historical invoice records found."
              >
                <!-- Expand Column -->
                <el-table-column type="expand" width="55">
                  <template #default="{ row }">
                    <div class="expanded-panel p-4 bg-slate-50">
                      <!-- Nested Details Table with Exact 11 Legacy Columns -->
                      <el-table
                        :data="row.items"
                        stripe
                        border
                        size="small"
                        style="width: 100%"
                        class="nested-details-table bg-white"
                      >
                        <!-- 1. Invoice -->
                        <el-table-column prop="invoice_number" label="Invoice" width="130" sortable>
                          <template #default="{ row: subRow }">
                            <el-tag size="small" type="success" class="font-mono">{{ subRow.invoice_number }}</el-tag>
                          </template>
                        </el-table-column>

                        <!-- 2. Carer -->
                        <el-table-column prop="carer_full_name" label="Carer" min-width="150" sortable />

                        <!-- 3. Service User -->
                        <el-table-column prop="service_user" label="Service User" min-width="150" sortable />

                        <!-- 4. Service -->
                        <el-table-column prop="shift" label="Service" width="130" sortable />

                        <!-- 5. Date -->
                        <el-table-column prop="start_date" label="Date" width="120" sortable>
                          <template #default="{ row: subRow }">
                            {{ formatStartDate(subRow) }}
                          </template>
                        </el-table-column>

                        <!-- 6. Period -->
                        <el-table-column prop="date_range" label="Period" min-width="160" sortable />

                        <!-- 7. IN -->
                        <el-table-column prop="time_in" label="IN" width="90" align="center" sortable>
                          <template #default="{ row: subRow }">
                            {{ formatTime(subRow.time_in) }}
                          </template>
                        </el-table-column>

                        <!-- 8. OUT -->
                        <el-table-column prop="time_out" label="OUT" width="90" align="center" sortable>
                          <template #default="{ row: subRow }">
                            {{ formatTime(subRow.time_out) }}
                          </template>
                        </el-table-column>

                        <!-- 9. Hours -->
                        <el-table-column prop="hours" label="Hours" width="95" align="right" sortable>
                          <template #default="{ row: subRow }">
                            {{ formatHours(subRow.hours) }}
                          </template>
                        </el-table-column>

                        <!-- 10. Rates -->
                        <el-table-column prop="invoice" label="Rates" width="120" align="right" sortable>
                          <template #default="{ row: subRow }">
                            {{ formatCurrency(subRow.invoice || subRow.invoice_rate || subRow.rate) }}
                          </template>
                        </el-table-column>

                        <!-- 11. Amount -->
                        <el-table-column prop="amount" label="Amount" width="120" align="right" sortable>
                          <template #default="{ row: subRow }">
                            <strong class="text-green-700">{{ formatCurrency(subRow.amount) }}</strong>
                          </template>
                        </el-table-column>
                      </el-table>

                      <!-- Summary Information & Computed Values in Expanded Row (Legacy Group Footer) -->
                      <div class="mt-2 p-2 bg-white rounded border border-gray-200 flex justify-end items-center gap-4 text-sm font-bold text-gray-800">
                        <div>Total Hours: <span class="text-blue-600 font-mono">{{ row.totalHours.toFixed(2) }} hrs</span></div>
                        <div class="pl-4 border-l border-gray-300">
                          Total Amount: <span class="text-green-700 font-mono text-base">{{ formatCurrency(row.totalAmount) }}</span>
                        </div>
                      </div>
                    </div>
                  </template>
                </el-table-column>

                <!-- Master Table Summary Columns -->
                <el-table-column prop="invoice_number" label="Invoice #" width="160" sortable>
                  <template #default="{ row }">
                    <el-tag size="small" type="success" class="font-mono font-bold">{{ row.invoice_number }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="service_user" label="Service User (Client)" min-width="180" sortable />
                <el-table-column prop="date_range" label="Billing Range" min-width="170" sortable />
                <el-table-column label="Shifts" width="90" align="center">
                  <template #default="{ row }">
                    <el-tag size="small" type="success" effect="plain">{{ row.items.length }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="Total Hours" width="120" align="right">
                  <template #default="{ row }">
                    {{ row.totalHours.toFixed(2) }} hrs
                  </template>
                </el-table-column>
                <el-table-column label="Settled Amount (£)" width="160" align="right" sortable :sort-by="(r) => r.totalAmount">
                  <template #default="{ row }">
                    <strong class="text-green-700 text-base">{{ formatCurrency(row.totalAmount) }}</strong>
                  </template>
                </el-table-column>
                <el-table-column label="Status" width="100" align="center">
                  <template #default>
                    <el-tag type="success" effect="dark" size="small">Settled</el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="Actions" width="160" align="center" fixed="right">
                  <template #default="{ row }">
                    <el-button
                      size="small"
                      type="success"
                      round
                      @click.stop="handleGenerateInvoiceDocCopy(row)"
                      :loading="docGenerating === row.invoice_number"
                    >
                      Doc Copy
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>

            <!-- 2. FLAT TABLE VIEW (Exact 11 Legacy Columns with Total Summary) -->
            <div v-else class="flat-table-wrapper">
              <el-table
                :data="filteredPaidList"
                stripe
                border
                show-summary
                :summary-method="getPaidSummaries"
                style="width: 100%"
                empty-text="No historical invoice records found."
              >
                <!-- 1. Invoice -->
                <el-table-column prop="invoice_number" label="Invoice" width="140" sortable>
                  <template #default="{ row }">
                    <el-tag size="small" type="success" class="font-mono">{{ row.invoice_number }}</el-tag>
                  </template>
                </el-table-column>

                <!-- 2. Carer -->
                <el-table-column prop="carer_full_name" label="Carer" min-width="150" sortable />

                <!-- 3. Service User -->
                <el-table-column prop="service_user" label="Service User" min-width="150" sortable />

                <!-- 4. Service -->
                <el-table-column prop="shift" label="Service" width="130" sortable />

                <!-- 5. Date -->
                <el-table-column prop="start_date" label="Date" width="120" sortable>
                  <template #default="{ row }">
                    {{ formatStartDate(row) }}
                  </template>
                </el-table-column>

                <!-- 6. Period -->
                <el-table-column prop="date_range" label="Period" min-width="160" sortable />

                <!-- 7. IN -->
                <el-table-column prop="time_in" label="IN" width="90" align="center" sortable>
                  <template #default="{ row }">
                    {{ formatTime(row.time_in) }}
                  </template>
                </el-table-column>

                <!-- 8. OUT -->
                <el-table-column prop="time_out" label="OUT" width="90" align="center" sortable>
                  <template #default="{ row }">
                    {{ formatTime(row.time_out) }}
                  </template>
                </el-table-column>

                <!-- 9. Hours -->
                <el-table-column prop="hours" label="Hours" width="95" align="right" sortable>
                  <template #default="{ row }">
                    {{ formatHours(row.hours) }}
                  </template>
                </el-table-column>

                <!-- 10. Rates -->
                <el-table-column prop="invoice" label="Rates" width="120" align="right" sortable>
                  <template #default="{ row }">
                    {{ formatCurrency(row.invoice || row.invoice_rate || row.rate) }}
                  </template>
                </el-table-column>

                <!-- 11. Amount -->
                <el-table-column prop="amount" label="Amount" width="120" align="right" sortable>
                  <template #default="{ row }">
                    <strong class="text-green-700">{{ formatCurrency(row.amount) }}</strong>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Download, Search, User, Document, DocumentCopy, Check, Delete, MoreFilled } from '@element-plus/icons-vue'
import FinanceService from '@/service/FinanceService'
import { useAuthStore } from '@/store/auth'
import Docxtemplater from 'docxtemplater'
import PizZip from 'pizzip'
import { saveAs } from 'file-saver'

const authStore = useAuthStore()

// Tabs: 'manage' = Manage Invoices (Tab 0), 'records' = Invoice Records (Tab 1)
const activeTab = ref('manage')
const viewMode = ref('expandable') // 'expandable' | 'flat'
const viewModePaid = ref('expandable') // 'expandable' | 'flat'

const unpaidTableRef = ref(null)
const paidTableRef = ref(null)
const isAllUnpaidExpanded = ref(false)
const isAllPaidExpanded = ref(false)

const loading = ref(false)
const actionLoading = ref(null)
const docGenerating = ref(null)

// Raw row-level data items directly from /getinvoices (matching legacy dataobjects & dataobjectshistory)
const dataobjects = ref([])
const dataobjectshistory = ref([])

const searchQuery = ref('')
const searchQueryPaid = ref('')

// Currency formatter matching legacy: formatCurrency(value)
function formatCurrency(val) {
  const num = Number(val) || 0
  return new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' }).format(num)
}

// Time formatter matching legacy: formattedDate(data, 'time_in') -> HH:mm:ss or HH:mm
function formatTime(val) {
  if (!val) return '—'
  if (typeof val === 'string') {
    if (val.includes('T')) {
      const timePart = val.split('T')[1]
      return timePart ? timePart.slice(0, 8) : val
    }
    if (val.length >= 5 && val.includes(':')) {
      return val.length === 5 ? `${val}:00` : val.slice(0, 8)
    }
  }
  const d = new Date(val)
  return isNaN(d) ? val : d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

// Date formatter matching legacy: start_date (DD/MM/YYYY)
function formatStartDate(row) {
  if (row.start_date) {
    if (row.start_date.includes('-')) {
      const parts = row.start_date.split('-')
      if (parts[0].length === 4) {
        return `${parts[2]}/${parts[1]}/${parts[0]}`
      }
      return `${parts[0]}/${parts[1]}/${parts[2]}`
    }
    return row.start_date
  }
  if (row.start) {
    const d = new Date(row.start)
    if (!isNaN(d)) {
      const day = String(d.getDate()).padStart(2, '0')
      const month = String(d.getMonth() + 1).padStart(2, '0')
      const year = d.getFullYear()
      return `${day}/${month}/${year}`
    }
  }
  return '—'
}

// Day of week formatter for invoice doc
function getDayOfWeek(row) {
  const dateStr = row.start_date || row.start
  if (!dateStr) return 'Monday'
  const d = new Date(dateStr)
  if (isNaN(d)) return 'Monday'
  return d.toLocaleDateString('en-GB', { weekday: 'long' })
}

// Hours duration formatter matching legacy: hours (e.g. 02:00 or 2.00)
function formatHours(val) {
  if (val === undefined || val === null || val === '') return '0.00'
  const str = String(val)
  if (str.includes(':')) return str
  const num = Number(str)
  return isNaN(num) ? str : num.toFixed(2)
}

// Expand / Collapse All Toggles
function toggleExpandAllUnpaid() {
  if (!unpaidTableRef.value) return
  isAllUnpaidExpanded.value = !isAllUnpaidExpanded.value
  groupedUnpaidList.value.forEach(row => {
    unpaidTableRef.value.toggleRowExpansion(row, isAllUnpaidExpanded.value)
  })
}

function toggleExpandAllPaid() {
  if (!paidTableRef.value) return
  isAllPaidExpanded.value = !isAllPaidExpanded.value
  groupedPaidList.value.forEach(row => {
    paidTableRef.value.toggleRowExpansion(row, isAllPaidExpanded.value)
  })
}

// Filtering matching legacy global filter fields
const filteredUnpaidList = computed(() => {
  if (!searchQuery.value) return dataobjects.value
  const q = searchQuery.value.toLowerCase().trim()
  return dataobjects.value.filter(item => {
    return (
      (item.invoice_number && item.invoice_number.toLowerCase().includes(q)) ||
      (item.carer_full_name && item.carer_full_name.toLowerCase().includes(q)) ||
      (item.service_user && item.service_user.toLowerCase().includes(q)) ||
      (item.shift && item.shift.toLowerCase().includes(q)) ||
      (item.start_date && item.start_date.toLowerCase().includes(q)) ||
      (item.date_range && item.date_range.toLowerCase().includes(q)) ||
      (item.time_in && item.time_in.toLowerCase().includes(q)) ||
      (item.time_out && item.time_out.toLowerCase().includes(q)) ||
      (item.hours && String(item.hours).toLowerCase().includes(q)) ||
      (item.amount && String(item.amount).toLowerCase().includes(q))
    )
  })
})

const filteredPaidList = computed(() => {
  if (!searchQueryPaid.value) return dataobjectshistory.value
  const q = searchQueryPaid.value.toLowerCase().trim()
  return dataobjectshistory.value.filter(item => {
    return (
      (item.invoice_number && item.invoice_number.toLowerCase().includes(q)) ||
      (item.carer_full_name && item.carer_full_name.toLowerCase().includes(q)) ||
      (item.service_user && item.service_user.toLowerCase().includes(q)) ||
      (item.shift && item.shift.toLowerCase().includes(q)) ||
      (item.start_date && item.start_date.toLowerCase().includes(q)) ||
      (item.date_range && item.date_range.toLowerCase().includes(q)) ||
      (item.time_in && item.time_in.toLowerCase().includes(q)) ||
      (item.time_out && item.time_out.toLowerCase().includes(q)) ||
      (item.hours && String(item.hours).toLowerCase().includes(q)) ||
      (item.amount && String(item.amount).toLowerCase().includes(q))
    )
  })
})

// Tab 0 Grouping: groupRowsBy="invoice_number" (Matching legacy Manage Invoices)
const groupedUnpaidList = computed(() => {
  const map = new Map()
  for (const item of filteredUnpaidList.value) {
    const key = item.invoice_number || `Invoice-${item.invoice_id}`
    if (!map.has(key)) {
      map.set(key, {
        key,
        invoice_id: item.invoice_id,
        invoice_number: item.invoice_number || 'N/A',
        service_user: item.service_user || 'Service User',
        su_id: item.su_id,
        su_number: item.su_number,
        carer_full_name: item.carer_full_name,
        home_address: item.home_address || item.address,
        service_start_date: item.service_start_date,
        date_range: item.date_range,
        items: []
      })
    }
    map.get(key).items.push(item)
  }

  return Array.from(map.values()).map(group => {
    const totalAmount = group.items.reduce((sum, row) => sum + (Number(row.amount) || 0), 0)
    const totalHours = group.items.reduce((sum, row) => sum + (Number(row.hours) || 0), 0)
    return {
      ...group,
      totalAmount,
      totalHours
    }
  })
})

// Tab 1 Grouping: groupRowsBy="invoice_number" (Matching legacy Invoice Records)
const groupedPaidList = computed(() => {
  const map = new Map()
  for (const item of filteredPaidList.value) {
    const key = item.invoice_number || `Invoice-${item.invoice_id}`
    if (!map.has(key)) {
      map.set(key, {
        key,
        invoice_id: item.invoice_id,
        invoice_number: item.invoice_number || 'N/A',
        service_user: item.service_user || 'Service User',
        su_id: item.su_id,
        su_number: item.su_number,
        carer_full_name: item.carer_full_name,
        home_address: item.home_address || item.address,
        service_start_date: item.service_start_date,
        date_range: item.date_range,
        items: []
      })
    }
    map.get(key).items.push(item)
  }

  return Array.from(map.values()).map(group => {
    const totalAmount = group.items.reduce((sum, row) => sum + (Number(row.amount) || 0), 0)
    const totalHours = group.items.reduce((sum, row) => sum + (Number(row.hours) || 0), 0)
    return {
      ...group,
      totalAmount,
      totalHours
    }
  })
})

// KPI Metrics
const pendingBatchCount = computed(() => {
  return new Set(dataobjects.value.map(i => i.invoice_number).filter(Boolean)).size
})

const paidBatchCount = computed(() => {
  return new Set(dataobjectshistory.value.map(i => i.invoice_number).filter(Boolean)).size
})

const totalUnpaidAmount = computed(() => {
  return dataobjects.value.reduce((acc, curr) => acc + (Number(curr.amount) || 0), 0)
})

const totalPaidAmount = computed(() => {
  return dataobjectshistory.value.reduce((acc, curr) => acc + (Number(curr.amount) || 0), 0)
})

const currentRawList = computed(() => {
  return activeTab.value === 'manage' ? dataobjects.value : dataobjectshistory.value
})

// Summary rows for flat tables
function getUnpaidSummaries(param) {
  const { columns, data } = param
  const sums = []
  columns.forEach((col, index) => {
    if (index === 0) {
      sums[index] = 'Total'
      return
    }
    if (col.property === 'hours') {
      const sum = data.reduce((prev, curr) => prev + (Number(curr.hours) || 0), 0)
      sums[index] = sum.toFixed(2)
      return
    }
    if (col.property === 'amount') {
      const sum = data.reduce((prev, curr) => prev + (Number(curr.amount) || 0), 0)
      sums[index] = formatCurrency(sum)
      return
    }
    sums[index] = ''
  })
  return sums
}

function getPaidSummaries(param) {
  const { columns, data } = param
  const sums = []
  columns.forEach((col, index) => {
    if (index === 0) {
      sums[index] = 'Total'
      return
    }
    if (col.property === 'hours') {
      const sum = data.reduce((prev, curr) => prev + (Number(curr.hours) || 0), 0)
      sums[index] = sum.toFixed(2)
      return
    }
    if (col.property === 'amount') {
      const sum = data.reduce((prev, curr) => prev + (Number(curr.amount) || 0), 0)
      sums[index] = formatCurrency(sum)
      return
    }
    sums[index] = ''
  })
  return sums
}

// Data fetching
async function fetchData() {
  loading.value = true
  try {
    const res = await FinanceService.getInvoices()
    const rawData1 = res.data1 || []
    const rawData2 = res.data2 || []

    dataobjects.value = rawData1.map(item => ({
      ...item
    }))

    dataobjectshistory.value = rawData2.map(item => ({
      ...item
    }))

    ElMessage.success(`There are ${rawData1.length} records found.`)
  } catch (err) {
    ElMessage.error('Error fetching invoice records: ' + (err.message || 'Server error'))
  } finally {
    loading.value = false
  }
}

// Legacy Parity Action 1: Mark as Paid / Settled (markInvoice)
async function handleMarkInvoice(group) {
  try {
    await ElMessageBox.confirm(
      'Do you want to Mark this Invoice as Paid?',
      group.service_user || group.invoice_number,
      {
        confirmButtonText: 'Mark as Paid',
        cancelButtonText: 'Cancel',
        type: 'warning'
      }
    )

    actionLoading.value = group.invoice_number
    const currentUser = authStore.user || {}
    const requestData = {
      user_id: currentUser.id || 1,
      invoice_number: group.invoice_number,
      data: group.items
    }

    const res = await FinanceService.markInvoices(requestData)
    if (res.success || res.message) {
      ElMessage.success('Mark successful')
      await fetchData()
    } else {
      ElMessage.error(res.error_message || 'Failed to update invoice.')
    }
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error('Error: ' + (err.message || 'Mark cancelled'))
    }
  } finally {
    actionLoading.value = null
  }
}

async function handleMarkInvoiceRow(row) {
  await handleMarkInvoice({
    invoice_number: row.invoice_number,
    service_user: row.service_user,
    items: [row]
  })
}

// Legacy Parity Action 2: Delete Invoice (deleteInvoice)
async function handleDeleteInvoice(group) {
  try {
    await ElMessageBox.confirm(
      'Do you want to Delete this Invoice?',
      `${group.invoice_number} - ${group.service_user}`,
      {
        confirmButtonText: 'Delete',
        cancelButtonText: 'Cancel',
        confirmButtonClass: 'el-button--danger',
        type: 'warning'
      }
    )

    actionLoading.value = group.invoice_number
    const currentUser = authStore.user || {}
    const requestData = {
      user_id: currentUser.id || 1,
      invoice_number: group.invoice_number,
      data: group.invoice_number
    }

    const res = await FinanceService.deleteInvoice(requestData)
    if (res.success || res.message) {
      ElMessage.success('Deleted')
      await fetchData()
    } else {
      ElMessage.error(res.error_message || 'Failed to delete invoice.')
    }
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error('Error: ' + (err.message || 'Delete cancelled'))
    }
  } finally {
    actionLoading.value = null
  }
}

async function handleDeleteInvoiceRow(row) {
  await handleDeleteInvoice({
    invoice_number: row.invoice_number,
    service_user: row.service_user
  })
}

// Legacy Parity Action 3: Generate Invoice Word Document (generateInvoiceDoc)
async function handleGenerateInvoiceDoc(group) {
  try {
    await ElMessageBox.confirm(
      'Do you want to Generate a Word document for this Invoice?',
      group.service_user,
      {
        confirmButtonText: 'Generate',
        cancelButtonText: 'Cancel',
        type: 'success'
      }
    )

    docGenerating.value = group.invoice_number

    const response = await fetch('/documents/MaryInvoiceTemplate.docx')
    if (!response.ok) {
      throw new Error('Invoice document template (/documents/MaryInvoiceTemplate.docx) not found.')
    }
    const arrayBuffer = await response.arrayBuffer()
    const zip = new PizZip(arrayBuffer)
    const doc = new Docxtemplater(zip, { paragraphLoop: true, linebreaks: true })

    const services = group.items.map(p => ({
      days: getDayOfWeek(p),
      start_date: formatStartDate(p),
      shift: p.shift || '',
      carer_full_name: p.carer_full_name || '',
      invoice: Number(p.invoice || p.invoice_rate || p.rate || 0).toFixed(2),
      hours: formatHours(p.hours),
      amount: Number(p.amount || 0).toFixed(2)
    }))

    const totalAmount = group.totalAmount

    const today = new Date()
    const currentDateStr = `${String(today.getDate()).padStart(2, '0')}/${String(today.getMonth() + 1).padStart(2, '0')}/${today.getFullYear()}`

    doc.render({
      current_date: currentDateStr,
      service_user: group.service_user,
      invoice_number: group.invoice_number,
      su_number: group.su_number || '',
      home_address: group.home_address || '',
      service_start_date: group.service_start_date || '',
      date_range: group.date_range || '',
      total: totalAmount.toFixed(2),
      services: services
    })

    const out = doc.getZip().generate({
      type: 'blob',
      mimeType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    })

    const fileName = `${group.invoice_number}_${group.service_user}.docx`
    saveAs(out, fileName)
    ElMessage.success(`Word document ${fileName} generated successfully.`)
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error('Doc generation error: ' + (err.message || 'Operation failed'))
    }
  } finally {
    docGenerating.value = null
  }
}

// Legacy Parity Action 4: Generate Invoice Doc Copy (generateInvoiceDocCopy)
async function handleGenerateInvoiceDocCopy(group) {
  try {
    await ElMessageBox.confirm(
      'Do you want to Generate a copy of this Invoice?',
      group.service_user,
      {
        confirmButtonText: 'Generate',
        cancelButtonText: 'Cancel',
        type: 'success'
      }
    )

    docGenerating.value = group.invoice_number

    const response = await fetch('/documents/MaryInvoiceTemplate.docx')
    if (!response.ok) {
      throw new Error('Invoice document template (/documents/MaryInvoiceTemplate.docx) not found.')
    }
    const arrayBuffer = await response.arrayBuffer()
    const zip = new PizZip(arrayBuffer)
    const doc = new Docxtemplater(zip, { paragraphLoop: true, linebreaks: true })

    const services = group.items.map(p => ({
      days: getDayOfWeek(p),
      start_date: formatStartDate(p),
      shift: p.shift || '',
      carer_full_name: p.carer_full_name || '',
      invoice: Number(p.invoice || p.invoice_rate || p.rate || 0).toFixed(2),
      hours: formatHours(p.hours),
      amount: Number(p.amount || 0).toFixed(2)
    }))

    const totalAmount = group.totalAmount

    const today = new Date()
    const currentDateStr = `${String(today.getDate()).padStart(2, '0')}/${String(today.getMonth() + 1).padStart(2, '0')}/${today.getFullYear()}`

    doc.render({
      current_date: currentDateStr,
      service_user: group.service_user,
      invoice_number: `${group.invoice_number} - COPY`,
      su_number: group.su_number || '',
      home_address: group.home_address || '',
      service_start_date: group.service_start_date || '',
      date_range: group.date_range || '',
      total: totalAmount.toFixed(2),
      services: services
    })

    const out = doc.getZip().generate({
      type: 'blob',
      mimeType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    })

    const fileName = `${group.invoice_number}_${group.service_user}_COPY.docx`
    saveAs(out, fileName)
    ElMessage.success(`Word document copy ${fileName} generated successfully.`)
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error('Doc copy generation error: ' + (err.message || 'Operation failed'))
    }
  } finally {
    docGenerating.value = null
  }
}

// CSV Export: Exact 11 Legacy Columns Matching Legacy headers
function exportCurrentCsv() {
  const isManage = activeTab.value === 'manage'
  const list = isManage ? filteredUnpaidList.value : filteredPaidList.value
  if (!list.length) return

  const headers = [
    'Invoice',
    'Carer',
    'Service User',
    'Service',
    'Date',
    'Period',
    'IN',
    'OUT',
    'Hours',
    'Rates',
    'Amount'
  ]

  const rows = list.map(item => [
    `"${item.invoice_number || ''}"`,
    `"${item.carer_full_name || ''}"`,
    `"${item.service_user || ''}"`,
    `"${item.shift || ''}"`,
    `"${formatStartDate(item)}"`,
    `"${item.date_range || ''}"`,
    `"${formatTime(item.time_in)}"`,
    `"${formatTime(item.time_out)}"`,
    `"${formatHours(item.hours)}"`,
    Number(item.invoice || item.invoice_rate || item.rate || 0).toFixed(2),
    Number(item.amount || 0).toFixed(2)
  ])

  const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map(e => e.join(','))].join('\n')
  const encodedUri = encodeURI(csvContent)
  const link = document.createElement('a')
  link.setAttribute('href', encodedUri)
  const filename = isManage
    ? `Invoices_${new Date().toISOString().slice(0, 10)}.csv`
    : `Invoices_History_${new Date().toISOString().slice(0, 10)}.csv`
  link.setAttribute('download', filename)
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.invoice-view {
  padding: 0;
}
.filter-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  background-color: var(--el-fill-color-light);
  padding: 12px 16px;
  border-radius: 4px;
  border: 1px solid var(--el-border-color-light);
  margin-bottom: 10px;
}
.filter-toolbar > div:first-child {
  display: flex;
  align-items: center;
  gap: 12px;
}
.more-actions-icon {
  cursor: pointer;
  font-size: 18px;
  color: var(--el-text-color-regular);
  padding: 6px;
  border-radius: 4px;
  transition: all 0.2s ease-in-out;
  outline: none;
}
.more-actions-icon:hover {
  color: var(--el-color-primary, #409eff);
  background-color: var(--el-fill-color);
}
:deep(.el-dropdown-menu__item.is-active) {
  color: var(--el-color-primary, #409eff);
  font-weight: 600;
}
.stat-card {
  border-radius: 4px;
}
.nested-details-table {
  border-radius: 4px;
  overflow: hidden;
}
</style>
