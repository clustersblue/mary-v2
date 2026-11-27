<template>
  <div class="payroll-view">
    <el-card shadow="never" class="mb-4">
      <template #header>
        <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
          <div>
            <h2 class="text-xl font-bold text-gray-800 m-0">Carer Payroll Management</h2>
            <p class="text-sm text-gray-500 m-0 mt-1">
              Manage carer payroll batches, review individual shift line items, and disburse payments.
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
              {{ activeTab === 'manage' ? 'Export All Payroll' : 'Export All Payroll - History' }}
            </el-button>
          </div>
        </div>
      </template>

      <!-- TABS: EXACT LEGACY PARITY (Manage Payroll vs Payroll Records) -->
      <el-tabs v-model="activeTab" type="border-card">
        <!-- ========================================== -->
        <!-- TAB 0: MANAGE PAYROLL (Unfinalized / Unpaid) -->
        <!-- ========================================== -->
        <el-tab-pane label="Manage Payroll" name="manage">
          <!-- Toolbar & Global Search -->
          <div class="filter-toolbar mb-2.5 flex flex-col sm:flex-row justify-between items-center gap-3 p-3 rounded border">
            <div class="flex items-center gap-3 w-full sm:w-auto">
              <el-input
                v-model="searchQuery"
                placeholder="Search by Carer, Service User, Shift, Payroll #..."
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
                empty-text="No unfinalized payroll records found."
              >
                <!-- Expand Column -->
                <el-table-column type="expand" width="55">
                  <template #default="{ row }">
                    <div class="expanded-panel p-4 bg-slate-50 border-y border-slate-200">
                      <!-- Nested Details Table with Exact 11 Legacy Columns -->
                      <el-table
                        :data="row.items"
                        stripe
                        border
                        size="small"
                        style="width: 100%"
                        class="nested-details-table bg-white"
                      >
                        <!-- 1. Payroll -->
                        <el-table-column prop="payroll_number" label="Payroll" width="130" sortable>
                          <template #default="{ row: subRow }">
                            <el-tag size="small" type="info" class="font-mono">{{ subRow.payroll_number }}</el-tag>
                          </template>
                        </el-table-column>

                        <!-- 2. Carer -->
                        <el-table-column prop="carer_full_name" label="Carer" min-width="150" sortable />

                        <!-- 3. Service User -->
                        <el-table-column prop="service_user" label="Service User" min-width="150" sortable />

                        <!-- 4. Service -->
                        <el-table-column prop="shift" label="Service" width="130" sortable />

                        <!-- 5. Start -->
                        <el-table-column prop="start_date" label="Start" width="120" sortable>
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

                        <!-- 9. Hour -->
                        <el-table-column prop="hours" label="Hour" width="95" align="right" sortable>
                          <template #default="{ row: subRow }">
                            {{ formatHours(subRow.hours) }}
                          </template>
                        </el-table-column>

                        <!-- 10. Rates (Editable with Popover) -->
                        <el-table-column prop="rate" label="Rates" width="130" align="right" sortable>
                          <template #default="{ row: subRow }">
                            <div class="flex items-center justify-end gap-1">
                              <span>{{ formatCurrency(subRow.rate) }}</span>
                              <el-popover
                                placement="top"
                                :width="220"
                                trigger="click"
                                v-model:visible="subRow._editRateVisible"
                              >
                                <template #reference>
                                  <el-button link type="primary" size="small" :icon="Edit" />
                                </template>
                                <div class="p-1">
                                  <div class="text-xs font-semibold mb-2 text-gray-700">Update Rate (£/h)</div>
                                  <el-input-number
                                    v-model="subRow._newRate"
                                    :min="0"
                                    :precision="2"
                                    :step="0.5"
                                    size="small"
                                    style="width: 100%;"
                                  />
                                  <div class="flex justify-end gap-2 mt-2">
                                    <el-button size="small" text @click="subRow._editRateVisible = false">Cancel</el-button>
                                    <el-button
                                      size="small"
                                      type="primary"
                                      @click="saveRateChange(subRow)"
                                      :loading="subRow._savingRate"
                                    >
                                      Save
                                    </el-button>
                                  </div>
                                </div>
                              </el-popover>
                            </div>
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
                <el-table-column prop="carer_full_name" label="Carer" min-width="180" sortable>
                  <template #default="{ row }">
                    <span class="font-bold text-gray-900 flex items-center gap-1.5">
                      <el-icon class="text-blue-600"><User /></el-icon>
                      {{ row.carer_full_name }}
                    </span>
                  </template>
                </el-table-column>
                <el-table-column prop="payroll_number" label="Payroll #" width="160" sortable>
                  <template #default="{ row }">
                    <el-tag size="small" type="info" class="font-mono font-bold">{{ row.payroll_number }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="date_range" label="Period" min-width="170" sortable />
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
                <el-table-column label="Gross Total (£)" width="150" align="right" sortable :sort-by="(r) => r.totalAmount">
                  <template #default="{ row }">
                    <strong class="text-amber-700 text-base">{{ formatCurrency(row.totalAmount) }}</strong>
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
                        @click.stop="handleGeneratePayrollDoc(row)"
                        :loading="docGenerating === row.payroll_number"
                      >
                        Doc
                      </el-button>
                      <el-button
                        size="small"
                        type="warning"
                        round
                        @click.stop="handleMarkPayroll(row)"
                        :loading="actionLoading === row.payroll_number"
                      >
                        Mark Paid
                      </el-button>
                      <el-button
                        size="small"
                        type="danger"
                        circle
                        plain
                        @click.stop="handleDeletePayroll(row)"
                        :loading="actionLoading === row.payroll_number"
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
                empty-text="No unfinalized payroll records found."
              >
                <!-- 1. Payroll -->
                <el-table-column prop="payroll_number" label="Payroll" width="140" sortable>
                  <template #default="{ row }">
                    <el-tag size="small" type="info" class="font-mono">{{ row.payroll_number }}</el-tag>
                  </template>
                </el-table-column>

                <!-- 2. Carer -->
                <el-table-column prop="carer_full_name" label="Carer" min-width="150" sortable />

                <!-- 3. Service User -->
                <el-table-column prop="service_user" label="Service User" min-width="150" sortable />

                <!-- 4. Service -->
                <el-table-column prop="shift" label="Service" width="130" sortable />

                <!-- 5. Start -->
                <el-table-column prop="start_date" label="Start" width="120" sortable>
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

                <!-- 9. Hour -->
                <el-table-column prop="hours" label="Hour" width="95" align="right" sortable>
                  <template #default="{ row }">
                    {{ formatHours(row.hours) }}
                  </template>
                </el-table-column>

                <!-- 10. Rates -->
                <el-table-column prop="rate" label="Rates" width="130" align="right" sortable>
                  <template #default="{ row }">
                    <div class="flex items-center justify-end gap-1">
                      <span>{{ formatCurrency(row.rate) }}</span>
                      <el-popover
                        placement="top"
                        :width="220"
                        trigger="click"
                        v-model:visible="row._editRateVisible"
                      >
                        <template #reference>
                          <el-button link type="primary" size="small" :icon="Edit" />
                        </template>
                        <div class="p-1">
                          <div class="text-xs font-semibold mb-2 text-gray-700">Update Rate (£/h)</div>
                          <el-input-number
                            v-model="row._newRate"
                            :min="0"
                            :precision="2"
                            :step="0.5"
                            size="small"
                            style="width: 100%;"
                          />
                          <div class="flex justify-end gap-2 mt-2">
                            <el-button size="small" text @click="row._editRateVisible = false">Cancel</el-button>
                            <el-button
                              size="small"
                              type="primary"
                              @click="saveRateChange(row)"
                              :loading="row._savingRate"
                            >
                              Save
                            </el-button>
                          </div>
                        </div>
                      </el-popover>
                    </div>
                  </template>
                </el-table-column>

                <!-- 11. Amount -->
                <el-table-column prop="amount" label="Amount" width="120" align="right" sortable>
                  <template #default="{ row }">
                    <strong class="text-green-700">{{ formatCurrency(row.amount) }}</strong>
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
                        @click="handleMarkPayrollRow(row)"
                      >
                        Mark Paid
                      </el-button>
                      <el-button
                        size="small"
                        type="danger"
                        circle
                        plain
                        @click="handleDeletePayrollRow(row)"
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
        <!-- TAB 1: PAYROLL RECORDS (Historical / Paid) -->
        <!-- ========================================== -->
        <el-tab-pane label="Payroll Records" name="records">
          <!-- Toolbar & Global Search -->
          <div class="filter-toolbar mb-2.5 flex flex-col sm:flex-row justify-between items-center gap-3 p-3 rounded border">
            <div class="flex items-center gap-3 w-full sm:w-auto">
              <el-input
                v-model="searchQueryPaid"
                placeholder="Search history by Carer, Service User, Payroll #..."
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
                empty-text="No historical payroll records found."
              >
                <!-- Expand Column -->
                <el-table-column type="expand" width="55">
                  <template #default="{ row }">
                    <div class="expanded-panel p-4 bg-slate-50 border-y border-slate-200">
                      <!-- Nested Details Table with Exact 11 Legacy Columns -->
                      <el-table
                        :data="row.items"
                        stripe
                        border
                        size="small"
                        style="width: 100%"
                        class="nested-details-table bg-white"
                      >
                        <!-- 1. Payroll -->
                        <el-table-column prop="payroll_number" label="Payroll" width="130" sortable>
                          <template #default="{ row: subRow }">
                            <el-tag size="small" type="success" class="font-mono">{{ subRow.payroll_number }}</el-tag>
                          </template>
                        </el-table-column>

                        <!-- 2. Carer -->
                        <el-table-column prop="carer_full_name" label="Carer" min-width="150" sortable />

                        <!-- 3. Service User -->
                        <el-table-column prop="service_user" label="Service User" min-width="150" sortable />

                        <!-- 4. Service -->
                        <el-table-column prop="shift" label="Service" width="130" sortable />

                        <!-- 5. Date (Legacy Tab 1 Column 5 Header: 'Date') -->
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

                        <!-- 9. Hours (Legacy Tab 1 Column 9 Header: 'Hours') -->
                        <el-table-column prop="hours" label="Hours" width="95" align="right" sortable>
                          <template #default="{ row: subRow }">
                            {{ formatHours(subRow.hours) }}
                          </template>
                        </el-table-column>

                        <!-- 10. Rates -->
                        <el-table-column prop="rate" label="Rates" width="120" align="right" sortable>
                          <template #default="{ row: subRow }">
                            {{ formatCurrency(subRow.rate) }}
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
                <el-table-column prop="payroll_number" label="Payroll #" width="160" sortable>
                  <template #default="{ row }">
                    <el-tag size="small" type="success" class="font-mono font-bold">{{ row.payroll_number }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="carer_full_name" label="Carer" min-width="180" sortable />
                <el-table-column prop="date_range" label="Period" min-width="170" sortable />
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
                <el-table-column label="Paid Amount (£)" width="150" align="right" sortable :sort-by="(r) => r.totalAmount">
                  <template #default="{ row }">
                    <strong class="text-green-700 text-base">{{ formatCurrency(row.totalAmount) }}</strong>
                  </template>
                </el-table-column>
                <el-table-column label="Status" width="100" align="center">
                  <template #default>
                    <el-tag type="success" effect="dark" size="small">Paid</el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="Actions" width="150" align="center" fixed="right">
                  <template #default="{ row }">
                    <el-button
                      size="small"
                      type="success"
                      round
                      @click.stop="handleGeneratePayrollDocCopy(row)"
                      :loading="docGenerating === row.payroll_number"
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
                empty-text="No historical payroll records found."
              >
                <!-- 1. Payroll -->
                <el-table-column prop="payroll_number" label="Payroll" width="140" sortable>
                  <template #default="{ row }">
                    <el-tag size="small" type="success" class="font-mono">{{ row.payroll_number }}</el-tag>
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
                <el-table-column prop="rate" label="Rates" width="120" align="right" sortable>
                  <template #default="{ row }">
                    {{ formatCurrency(row.rate) }}
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
import { Refresh, Download, Search, User, Document, DocumentCopy, Check, Delete, Edit, MoreFilled } from '@element-plus/icons-vue'
import FinanceService from '@/service/FinanceService'
import { useAuthStore } from '@/store/auth'
import Docxtemplater from 'docxtemplater'
import PizZip from 'pizzip'
import { saveAs } from 'file-saver'

const authStore = useAuthStore()

// Tabs: 'manage' = Manage Payroll (Tab 0), 'records' = Payroll Records (Tab 1)
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

// Raw row-level data items directly from /getpayrolls (matching legacy dataobjects & dataobjectshistory)
const dataobjects = ref([])
const dataobjectshistory = ref([])

const searchQuery = ref('')
const searchQueryPaid = ref('')

// Currency formatter matching legacy: formatCurrency(value)
function formatCurrency(val) {
  const num = Number(val) || 0
  return new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' }).format(num)
}

// Time formatter matching legacy: formattedDate(data, 'time_in') -> HH:mm
function formatTime(val) {
  if (!val) return '—'
  if (typeof val === 'string') {
    if (val.includes('T')) {
      const timePart = val.split('T')[1]
      return timePart ? timePart.slice(0, 5) : val
    }
    if (val.length >= 5 && val.includes(':')) {
      return val.slice(0, 5)
    }
  }
  const d = new Date(val)
  return isNaN(d) ? val : d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })
}

// Date formatter matching legacy: start_date (DD-MM-YYYY or DD/MM/YYYY)
function formatStartDate(row) {
  if (row.start_date) return row.start_date
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
      (item.payroll_number && item.payroll_number.toLowerCase().includes(q)) ||
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
      (item.payroll_number && item.payroll_number.toLowerCase().includes(q)) ||
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

// Tab 0 Grouping: groupRowsBy="carer_full_name" (Matching legacy Manage Payroll)
const groupedUnpaidList = computed(() => {
  const map = new Map()
  for (const item of filteredUnpaidList.value) {
    const key = item.carer_full_name || `Carer-${item.id || item.user_id}`
    if (!map.has(key)) {
      map.set(key, {
        key,
        id: item.id || item.user_id,
        carer_full_name: item.carer_full_name || 'Carer Staff',
        payroll_number: item.payroll_number || 'N/A',
        su_number: item.su_number,
        ni_num: item.ni_num,
        home_address: item.home_address,
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

// Tab 1 Grouping: groupRowsBy="payroll_number" (Matching legacy Payroll Records)
const groupedPaidList = computed(() => {
  const map = new Map()
  for (const item of filteredPaidList.value) {
    const key = item.payroll_number || `Payroll-${item.payroll_id}`
    if (!map.has(key)) {
      map.set(key, {
        key,
        id: item.id || item.user_id,
        payroll_number: item.payroll_number || 'N/A',
        carer_full_name: item.carer_full_name || 'Carer Staff',
        su_number: item.su_number,
        ni_num: item.ni_num,
        home_address: item.home_address,
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
  return new Set(dataobjects.value.map(i => i.payroll_number).filter(Boolean)).size
})

const paidBatchCount = computed(() => {
  return new Set(dataobjectshistory.value.map(i => i.payroll_number).filter(Boolean)).size
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
    const res = await FinanceService.getPayrolls()
    const rawData1 = res.data1 || []
    const rawData2 = res.data2 || []

    // Initialize editing properties on each row
    dataobjects.value = rawData1.map(item => ({
      ...item,
      _editRateVisible: false,
      _newRate: Number(item.rate) || 15.0,
      _savingRate: false
    }))

    dataobjectshistory.value = rawData2.map(item => ({
      ...item
    }))

    ElMessage.success('Payroll records loaded successfully.')
  } catch (err) {
    ElMessage.error('Error fetching payroll records: ' + (err.message || 'Server error'))
  } finally {
    loading.value = false
  }
}

// Legacy Parity Action 1: Mark as Paid (markPayroll)
async function handleMarkPayroll(group) {
  try {
    await ElMessageBox.confirm(
      'Do you want to Mark this Payroll as Paid?',
      group.carer_full_name,
      {
        confirmButtonText: 'Mark as Paid',
        cancelButtonText: 'Cancel',
        type: 'warning'
      }
    )

    actionLoading.value = group.payroll_number
    const currentUser = authStore.user || {}
    const requestData = {
      user_id: currentUser.id || 1,
      payroll_number: group.payroll_number,
      data: group.items
    }

    const res = await FinanceService.markPayrolls(requestData)
    if (res.success || res.message) {
      ElMessage.success('Mark successful')
      await fetchData()
    } else {
      ElMessage.error(res.error_message || 'Failed to update payroll.')
    }
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error('Error: ' + (err.message || 'Mark cancelled'))
    }
  } finally {
    actionLoading.value = null
  }
}

async function handleMarkPayrollRow(row) {
  await handleMarkPayroll({
    payroll_number: row.payroll_number,
    carer_full_name: row.carer_full_name,
    items: [row]
  })
}

// Legacy Parity Action 2: Delete Payroll (deletePayroll)
async function handleDeletePayroll(group) {
  try {
    await ElMessageBox.confirm(
      'Do you want to Delete this Payroll?',
      `${group.payroll_number} - ${group.carer_full_name}`,
      {
        confirmButtonText: 'Delete',
        cancelButtonText: 'Cancel',
        confirmButtonClass: 'el-button--danger',
        type: 'warning'
      }
    )

    actionLoading.value = group.payroll_number
    const currentUser = authStore.user || {}
    const requestData = {
      user_id: currentUser.id || 1,
      payroll_number: group.payroll_number,
      data: group.payroll_number
    }

    const res = await FinanceService.deletePayroll(requestData)
    if (res.success || res.message) {
      ElMessage.success('Mark successful')
      await fetchData()
    } else {
      ElMessage.error(res.error_message || 'Failed to delete payroll.')
    }
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error('Error: ' + (err.message || 'Delete cancelled'))
    }
  } finally {
    actionLoading.value = null
  }
}

async function handleDeletePayrollRow(row) {
  await handleDeletePayroll({
    payroll_number: row.payroll_number,
    carer_full_name: row.carer_full_name
  })
}

// Legacy Parity Action 3: Generate Payroll Word Document (generatePayrollDoc)
async function handleGeneratePayrollDoc(group) {
  try {
    await ElMessageBox.confirm(
      'Do you want to Generate a Word document for this Payroll?',
      group.carer_full_name,
      {
        confirmButtonText: 'Generate',
        cancelButtonText: 'Cancel',
        type: 'success'
      }
    )

    docGenerating.value = group.payroll_number

    const response = await fetch('/documents/MaryPayrollTemplate.docx')
    if (!response.ok) {
      throw new Error('Payroll document template (/documents/MaryPayrollTemplate.docx) not found.')
    }
    const arrayBuffer = await response.arrayBuffer()
    const zip = new PizZip(arrayBuffer)
    const doc = new Docxtemplater(zip, { paragraphLoop: true, linebreaks: true })

    const periods = group.date_range ? group.date_range.split(' - ') : ['', '']
    const services = group.items.map(p => ({
      date: formatStartDate(p),
      service_user: p.service_user || '',
      shift: p.shift || '',
      time_in: formatTime(p.time_in),
      time_out: formatTime(p.time_out),
      rate: Number(p.rate || 0).toFixed(2),
      hours: formatHours(p.hours),
      amount: Number(p.amount || 0).toFixed(2)
    }))

    const totalAmount = group.totalAmount
    const totalHours = group.totalHours

    const today = new Date()
    const currentDateStr = `${String(today.getDate()).padStart(2, '0')}/${String(today.getMonth() + 1).padStart(2, '0')}/${today.getFullYear()}`

    doc.render({
      current_date: currentDateStr,
      carer_full_name: group.carer_full_name,
      payroll_number: group.payroll_number,
      su_number: group.su_number || '',
      ni_num: group.ni_num || '',
      period_start: periods[0] || '',
      period_end: periods[1] || '',
      home_address: group.home_address || '',
      service_start_date: group.service_start_date || '',
      date_range: group.date_range || '',
      total: totalAmount.toFixed(2),
      total_hours_worked: totalHours.toFixed(2),
      services: services
    })

    const out = doc.getZip().generate({
      type: 'blob',
      mimeType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    })

    const fileName = `${group.payroll_number}_${group.carer_full_name}.docx`
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

// Legacy Parity Action 4: Generate Payroll Doc Copy (generatePayrollDocCopy)
async function handleGeneratePayrollDocCopy(group) {
  try {
    await ElMessageBox.confirm(
      'Do you want to Generate a copy of this Payroll?',
      group.carer_full_name,
      {
        confirmButtonText: 'Generate',
        cancelButtonText: 'Cancel',
        type: 'success'
      }
    )

    docGenerating.value = group.payroll_number

    const response = await fetch('/documents/MaryPayrollTemplate.docx')
    if (!response.ok) {
      throw new Error('Payroll document template (/documents/MaryPayrollTemplate.docx) not found.')
    }
    const arrayBuffer = await response.arrayBuffer()
    const zip = new PizZip(arrayBuffer)
    const doc = new Docxtemplater(zip, { paragraphLoop: true, linebreaks: true })

    const periods = group.date_range ? group.date_range.split(' - ') : ['', '']
    const services = group.items.map(p => ({
      date: formatStartDate(p),
      service_user: p.service_user || '',
      shift: p.shift || '',
      time_in: formatTime(p.time_in),
      time_out: formatTime(p.time_out),
      rate: Number(p.rate || 0).toFixed(2),
      hours: formatHours(p.hours),
      amount: Number(p.amount || 0).toFixed(2)
    }))

    const totalAmount = group.totalAmount
    const totalHours = group.totalHours

    const today = new Date()
    const currentDateStr = `${String(today.getDate()).padStart(2, '0')}/${String(today.getMonth() + 1).padStart(2, '0')}/${today.getFullYear()}`

    doc.render({
      current_date: currentDateStr,
      carer_full_name: `${group.carer_full_name} - COPY`,
      payroll_number: group.payroll_number,
      su_number: group.su_number || '',
      ni_num: group.ni_num || '',
      period_start: periods[0] || '',
      period_end: periods[1] || '',
      home_address: group.home_address || '',
      service_start_date: group.service_start_date || '',
      date_range: group.date_range || '',
      total: totalAmount.toFixed(2),
      total_hours_worked: totalHours.toFixed(2),
      services: services
    })

    const out = doc.getZip().generate({
      type: 'blob',
      mimeType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    })

    const fileName = `${group.payroll_number}_${group.carer_full_name}_COPY.docx`
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

// Inline Rate Editing (onCellEditComplete parity)
async function saveRateChange(row) {
  if (row._newRate === undefined || row._newRate === null || row._newRate < 0) {
    ElMessage.warning('Please enter a valid rate.')
    return
  }

  row._savingRate = true
  try {
    const res = await FinanceService.updateTransactionRate({
      id: row.tx_id,
      rate: row._newRate
    })

    if (res.success || res.message) {
      row.rate = row._newRate
      const hoursNum = Number(row.hours) || 0
      row.amount = Number((hoursNum * row.rate).toFixed(2))
      row._editRateVisible = false
      ElMessage.success('Rates updated successfully.')
    } else {
      ElMessage.error(res.error || 'Failed to update rates.')
    }
  } catch (err) {
    ElMessage.error('Rate update error: ' + (err.message || 'Server error'))
  } finally {
    row._savingRate = false
  }
}

// CSV Export: Exact 11 Legacy Columns Matching Legacy headers
function exportCurrentCsv() {
  const isManage = activeTab.value === 'manage'
  const list = isManage ? filteredUnpaidList.value : filteredPaidList.value
  if (!list.length) return

  const headers = [
    'Payroll',
    'Carer',
    'Service User',
    'Service',
    isManage ? 'Start' : 'Date',
    'Period',
    'IN',
    'OUT',
    isManage ? 'Hour' : 'Hours',
    'Rates',
    'Amount'
  ]

  const rows = list.map(item => [
    `"${item.payroll_number || ''}"`,
    `"${item.carer_full_name || ''}"`,
    `"${item.service_user || ''}"`,
    `"${item.shift || ''}"`,
    `"${formatStartDate(item)}"`,
    `"${item.date_range || ''}"`,
    `"${formatTime(item.time_in)}"`,
    `"${formatTime(item.time_out)}"`,
    `"${formatHours(item.hours)}"`,
    Number(item.rate || 0).toFixed(2),
    Number(item.amount || 0).toFixed(2)
  ])

  const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map(e => e.join(','))].join('\n')
  const encodedUri = encodeURI(csvContent)
  const link = document.createElement('a')
  link.setAttribute('href', encodedUri)
  const filename = isManage
    ? `Payroll_${new Date().toISOString().slice(0, 10)}.csv`
    : `Payroll_History_${new Date().toISOString().slice(0, 10)}.csv`
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
.payroll-view {
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
  border-left: 4px solid #67c23a;
}
.nested-details-table {
  border-radius: 4px;
  overflow: hidden;
}
</style>
