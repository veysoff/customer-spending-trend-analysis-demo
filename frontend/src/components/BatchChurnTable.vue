<template>
  <div class="card">
    <div class="card-header">
      <div class="flex justify-between items-center">
        <div>
          <h2 class="text-lg font-semibold text-gray-900">⚠️ Top At-Risk Customers</h2>
          <p class="text-sm text-gray-500 mt-1">Ranked by churn probability (batch analysis)</p>
        </div>
        <button
          @click="loadBatchPredictions"
          :disabled="loading"
          class="btn-primary text-sm px-4 py-2"
        >
          {{ loading ? 'Loading...' : 'Refresh Predictions' }}
        </button>
      </div>
    </div>

    <div class="card-body">
      <!-- Loading State -->
      <div v-if="loading" class="text-center py-12">
        <div class="inline-block">
          <div class="animate-spin rounded-full h-10 w-10 border-b-2 border-brand-600"></div>
          <p class="mt-3 text-gray-600 text-sm">Running batch predictions for 1000 customers...</p>
        </div>
      </div>

      <!-- Summary Statistics -->
      <div v-else-if="predictions" class="mb-6">
        <div class="grid grid-cols-4 gap-4 mb-6">
          <div class="p-4 bg-blue-50 rounded-lg border border-blue-200">
            <p class="text-xs text-blue-600 mb-1 font-semibold">TOTAL CUSTOMERS</p>
            <p class="text-2xl font-bold text-blue-900">{{ predictions.total_customers }}</p>
          </div>

          <div class="p-4 bg-red-50 rounded-lg border border-red-200">
            <p class="text-xs text-red-600 mb-1 font-semibold">AT RISK (CHURNED)</p>
            <p class="text-2xl font-bold text-red-900">{{ predictions.churned_count }}</p>
            <p class="text-xs text-red-700 mt-1">
              {{ Math.round((predictions.churned_count / predictions.total_customers) * 100) }}%
            </p>
          </div>

          <div class="p-4 bg-green-50 rounded-lg border border-green-200">
            <p class="text-xs text-green-600 mb-1 font-semibold">STABLE</p>
            <p class="text-2xl font-bold text-green-900">{{ predictions.stable_count }}</p>
            <p class="text-xs text-green-700 mt-1">
              {{ Math.round((predictions.stable_count / predictions.total_customers) * 100) }}%
            </p>
          </div>

          <div class="p-4 bg-amber-50 rounded-lg border border-amber-200">
            <p class="text-xs text-amber-600 mb-1 font-semibold">AVG CHURN RISK</p>
            <p class="text-2xl font-bold text-amber-900">
              {{ Math.round(predictions.average_churn_probability * 100) }}%
            </p>
          </div>
        </div>

        <!-- Filter Controls -->
        <div class="flex gap-2 mb-4">
          <button
            v-for="riskLevel in ['CRITICAL', 'HIGH', 'ALL']"
            :key="riskLevel"
            @click="selectedRiskLevel = riskLevel"
            :class="[
              'px-4 py-2 rounded-lg border text-sm font-medium transition-colors',
              selectedRiskLevel === riskLevel
                ? riskLevelColors[riskLevel].button
                : 'bg-white border-gray-200 text-gray-700 hover:bg-gray-50'
            ]"
          >
            {{ riskLevel === 'CRITICAL' ? '🔴 Critical' : riskLevel === 'HIGH' ? '🟠 High' : '📊 All Risks' }}
          </button>
        </div>

        <!-- Table Scroll Container -->
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead class="bg-gray-50 border-b border-gray-200">
              <tr>
                <th class="px-4 py-3 text-left font-semibold text-gray-900 w-12">#</th>
                <th class="px-4 py-3 text-left font-semibold text-gray-900 cursor-pointer hover:bg-gray-100"
                    @click="sortBy('customer_id')">
                  Customer ID {{ getSortIndicator('customer_id') }}
                </th>
                <th class="px-4 py-3 text-left font-semibold text-gray-900 cursor-pointer hover:bg-gray-100"
                    @click="sortBy('churn_probability')">
                  Churn Risk {{ getSortIndicator('churn_probability') }}
                </th>
                <th class="px-4 py-3 text-left font-semibold text-gray-900">Status</th>
                <th class="px-4 py-3 text-left font-semibold text-gray-900">Category</th>
                <th class="px-4 py-3 text-left font-semibold text-gray-900">Balance</th>
                <th class="px-4 py-3 text-left font-semibold text-gray-900">Dormancy</th>
                <th class="px-4 py-3 text-center font-semibold text-gray-900">Action</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(customer, index) in filteredAndSortedPredictions"
                :key="customer.customer_id"
                class="border-b border-gray-200 hover:bg-gray-50 transition-colors"
              >
                <td class="px-4 py-3 text-gray-600 font-medium">{{ index + 1 }}</td>
                <td class="px-4 py-3 text-gray-900 font-medium">{{ customer.customer_id }}</td>

                <!-- Churn Probability Bar -->
                <td class="px-4 py-3">
                  <div class="flex items-center gap-2">
                    <div class="h-1.5 w-20 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        class="h-full rounded-full"
                        :class="getRiskColor(customer.churn_probability)"
                        :style="{ width: customer.churn_probability * 100 + '%' }"
                      />
                    </div>
                    <span class="font-semibold text-gray-900 w-12 text-right">
                      {{ Math.round(customer.churn_probability * 100) }}%
                    </span>
                  </div>
                </td>

                <!-- Prediction Status -->
                <td class="px-4 py-3">
                  <span
                    :class="[
                      'px-2 py-1 rounded text-xs font-semibold',
                      customer.churn_prediction === 'churned'
                        ? 'bg-red-100 text-red-800'
                        : 'bg-green-100 text-green-800'
                    ]"
                  >
                    {{ customer.churn_prediction.toUpperCase() }}
                  </span>
                </td>

                <!-- Risk Category -->
                <td class="px-4 py-3">
                  <span
                    :class="[
                      'px-2 py-1 rounded text-xs font-semibold',
                      getRiskCategoryClass(customer.churn_probability)
                    ]"
                  >
                    {{ getRiskCategory(customer.churn_probability) }}
                  </span>
                </td>

                <!-- Balance -->
                <td class="px-4 py-3 text-gray-900">
                  ${{ Math.round(customer.account_metrics.current_balance).toLocaleString() }}
                </td>

                <!-- Dormancy Days -->
                <td class="px-4 py-3" :class="getDormancyColor(customer.account_metrics.dormancy_days)">
                  {{ Math.round(customer.account_metrics.dormancy_days) }} days
                </td>

                <!-- Action Button -->
                <td class="px-4 py-3 text-center">
                  <button
                    @click="selectCustomer(customer.customer_id)"
                    class="text-xs px-3 py-1.5 rounded bg-brand-100 text-brand-700 hover:bg-brand-200 font-medium transition-colors"
                  >
                    View
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Pagination Info -->
        <div class="mt-4 text-xs text-gray-600 text-center">
          Showing {{ filteredAndSortedPredictions.length }} of {{ predictions.predictions.length }} customers
        </div>
      </div>

      <!-- No Data State -->
      <div v-else class="text-center py-12 text-gray-500">
        <p class="text-sm">Click "Refresh Predictions" to run batch analysis</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { apiService } from '../services/api'
import { useCustomerStore } from '../stores/customer'

const store = useCustomerStore()

const predictions = ref(null)
const loading = ref(false)
const selectedRiskLevel = ref('ALL')
const sortField = ref('churn_probability')
const sortOrder = ref('desc')

const riskLevelColors = {
  CRITICAL: { button: 'bg-red-100 border-red-300 text-red-800' },
  HIGH: { button: 'bg-orange-100 border-orange-300 text-orange-800' },
  ALL: { button: 'bg-brand-100 border-brand-300 text-brand-800' }
}

// Cache for batch predictions
let batchPredictionsCache = null
let cacheTimestamp = null
const CACHE_DURATION_MS = 5 * 60 * 1000 // 5 minutes

// Load batch predictions with caching
async function loadBatchPredictions() {
  // Return cached predictions if still valid
  if (batchPredictionsCache && cacheTimestamp && (Date.now() - cacheTimestamp) < CACHE_DURATION_MS) {
    predictions.value = batchPredictionsCache
    console.log('[BatchCache] Loaded predictions from cache (expires in', Math.round((CACHE_DURATION_MS - (Date.now() - cacheTimestamp)) / 1000), 'seconds)')
    return
  }

  loading.value = true
  try {
    const data = await apiService.predictAllChurn()
    predictions.value = data
    // Cache the results
    batchPredictionsCache = data
    cacheTimestamp = Date.now()
    console.log('[BatchCache] Stored batch predictions in cache (5 minute TTL)')
  } catch (err) {
    console.error('Failed to load batch predictions:', err)
    predictions.value = null
  } finally {
    loading.value = false
  }
}

// Filter and sort predictions
const filteredAndSortedPredictions = computed(() => {
  if (!predictions.value) return []

  let filtered = predictions.value.predictions

  // Filter by risk level
  if (selectedRiskLevel.value !== 'ALL') {
    filtered = filtered.filter(c => {
      if (selectedRiskLevel.value === 'CRITICAL') return c.churn_probability >= 0.8
      if (selectedRiskLevel.value === 'HIGH') return c.churn_probability >= 0.6 && c.churn_probability < 0.8
      return true
    })
  }

  // Sort
  const sorted = [...filtered].sort((a, b) => {
    let aVal = a[sortField.value]
    let bVal = b[sortField.value]

    if (sortField.value === 'churn_probability') {
      aVal = a.churn_probability
      bVal = b.churn_probability
    }

    const comparison = aVal < bVal ? -1 : aVal > bVal ? 1 : 0
    return sortOrder.value === 'asc' ? comparison : -comparison
  })

  return sorted
})

// Methods
function sortBy(field) {
  if (sortField.value === field) {
    sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortField.value = field
    sortOrder.value = 'desc'
  }
}

function getSortIndicator(field) {
  if (sortField.value !== field) return ''
  return sortOrder.value === 'asc' ? '↑' : '↓'
}

function getRiskColor(prob) {
  if (prob >= 0.8) return 'bg-red-500'
  if (prob >= 0.6) return 'bg-orange-500'
  if (prob >= 0.4) return 'bg-yellow-500'
  return 'bg-green-500'
}

function getRiskCategory(prob) {
  if (prob >= 0.8) return 'CRITICAL'
  if (prob >= 0.6) return 'HIGH'
  if (prob >= 0.4) return 'MEDIUM'
  return 'LOW'
}

function getRiskCategoryClass(prob) {
  if (prob >= 0.8) return 'bg-red-100 text-red-800'
  if (prob >= 0.6) return 'bg-orange-100 text-orange-800'
  if (prob >= 0.4) return 'bg-yellow-100 text-yellow-800'
  return 'bg-green-100 text-green-800'
}

function getDormancyColor(days) {
  if (days >= 180) return 'text-red-600 font-semibold'
  if (days >= 60) return 'text-orange-600 font-semibold'
  return 'text-gray-900'
}

function selectCustomer(customerId) {
  store.selectCustomer(customerId)
}

// Load predictions on mount
loadBatchPredictions()
</script>

<style scoped>
.card {
  @apply bg-white rounded-lg border border-gray-200 shadow-sm;
}

.card-header {
  @apply px-6 py-4 border-b border-gray-200;
}

.card-body {
  @apply px-6 py-4;
}

.btn-primary {
  @apply bg-brand-600 text-white rounded hover:bg-brand-700 disabled:bg-gray-400 transition-colors;
}
</style>
