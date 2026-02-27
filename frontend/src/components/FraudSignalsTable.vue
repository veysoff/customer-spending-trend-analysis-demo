<template>
  <div class="card">
    <div class="card-header flex justify-between items-center">
      <div>
        <h2 class="text-lg font-semibold text-gray-900">
          🚨 Fraud Signals
          <span class="text-sm font-normal text-gray-500 ml-2">
            {{ fraudSignals.length }} transactions
          </span>
        </h2>
        <p class="text-sm text-gray-600 mt-1">Risk-scored transactions from the last {{ days }} days</p>
      </div>
      <div class="text-sm text-gray-600">
        Model: <span :class="{'font-bold text-green-600': modelStatus === 'trained', 'text-yellow-600': modelStatus === 'rule_based_only'}">
          {{ modelStatus === 'trained' ? '✓ Trained' : '⚠ Rule-based Only' }}
        </span>
      </div>
    </div>

    <div class="card-body">
      <div v-if="loading" class="text-center py-8">
        <div class="inline-block">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-red-600"></div>
          <p class="mt-2 text-gray-600 text-sm">Loading fraud signals...</p>
        </div>
      </div>

      <div v-else-if="fraudSignals.length === 0" class="text-center text-gray-500 py-8">
        ✅ No fraud signals detected
      </div>

      <div v-else>
        <!-- Filters -->
        <div class="mb-4 flex gap-4 items-end flex-wrap">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Min Score</label>
            <select v-model.number="minScore" class="px-3 py-2 border border-gray-300 rounded-md text-sm">
              <option :value="0.3">0.3 - All</option>
              <option :value="0.5">0.5 - Medium</option>
              <option :value="0.7">0.7 - High</option>
              <option :value="0.9">0.9 - Critical</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Days</label>
            <select v-model.number="days" class="px-3 py-2 border border-gray-300 rounded-md text-sm">
              <option :value="7">Last 7 days</option>
              <option :value="14">Last 14 days</option>
              <option :value="30">Last 30 days</option>
              <option :value="90">Last 90 days</option>
            </select>
          </div>
          <button
            @click="reload"
            :disabled="loading"
            class="px-4 py-2 bg-red-600 text-white rounded-md text-sm font-medium hover:bg-red-700 disabled:opacity-50"
          >
            Reload
          </button>
        </div>

        <!-- Table -->
        <div class="overflow-x-auto mb-4">
          <table class="w-full text-sm">
            <thead class="border-b border-gray-200">
              <tr>
                <th class="text-left py-3 px-4 font-semibold text-gray-700">Date</th>
                <th class="text-left py-3 px-4 font-semibold text-gray-700">Amount</th>
                <th class="text-left py-3 px-4 font-semibold text-gray-700">Merchant</th>
                <th class="text-left py-3 px-4 font-semibold text-gray-700">Fraud Score</th>
                <th class="text-left py-3 px-4 font-semibold text-gray-700">Flags</th>
                <th class="text-left py-3 px-4 font-semibold text-gray-700">Action</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-200">
              <tr v-for="(signal, idx) in filteredSignals" :key="idx" class="hover:bg-gray-50">
                <td class="py-3 px-4 text-sm">
                  {{ formatDate(signal.date) }}
                </td>
                <td class="py-3 px-4 text-sm font-medium">
                  AED {{ signal.amount.toFixed(2) }}
                </td>
                <td class="py-3 px-4 text-sm text-gray-700">
                  {{ signal.merchant_name }}
                </td>
                <td class="py-3 px-4">
                  <div class="flex items-center gap-2">
                    <div class="w-16 bg-gray-200 rounded-full h-2">
                      <div
                        class="h-2 rounded-full"
                        :class="getScoreColor(signal.fraud_score)"
                        :style="{ width: (signal.fraud_score * 100) + '%' }"
                      ></div>
                    </div>
                    <span class="font-bold text-sm" :class="getScoreTextColor(signal.fraud_score)">
                      {{ (signal.fraud_score * 100).toFixed(0) }}%
                    </span>
                  </div>
                </td>
                <td class="py-3 px-4">
                  <div class="flex flex-wrap gap-1">
                    <span
                      v-for="flag in signal.fraud_flags"
                      :key="flag"
                      class="inline-block px-2 py-0.5 bg-red-100 text-red-800 text-xs rounded font-medium"
                    >
                      {{ formatFlag(flag) }}
                    </span>
                  </div>
                </td>
                <td class="py-3 px-4">
                  <button
                    @click="selectTransaction(signal.transaction_id)"
                    class="text-blue-600 hover:text-blue-800 font-semibold text-sm"
                  >
                    Details →
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Pagination -->
        <div class="flex items-center justify-between border-t border-gray-200 pt-4">
          <button
            @click="previousPage"
            :disabled="currentPage === 1"
            class="px-3 py-2 rounded border border-gray-300 text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
          >
            ← Previous
          </button>

          <div class="flex items-center gap-2">
            <span class="text-sm text-gray-600">Page {{ currentPage }} of {{ totalPages }}</span>
            <div class="flex gap-1">
              <button
                v-for="page in visiblePages"
                :key="page"
                @click="goToPage(page)"
                :class="[
                  'px-2 py-1 rounded text-sm font-medium',
                  page === currentPage
                    ? 'bg-red-600 text-white'
                    : 'border border-gray-300 text-gray-700 hover:bg-gray-50'
                ]"
              >
                {{ page }}
              </button>
            </div>
          </div>

          <button
            @click="nextPage"
            :disabled="currentPage === totalPages"
            class="px-3 py-2 rounded border border-gray-300 text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
          >
            Next →
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { apiService } from '../services/api'

const props = defineProps({
  customerId: {
    type: String,
    required: true
  },
  modelStatus: {
    type: String,
    default: 'rule_based_only'
  }
})

const emit = defineEmits(['select-transaction'])

const fraudSignals = ref([])
const loading = ref(false)
const error = ref(null)
const days = ref(30)
const minScore = ref(0.3)
const currentPage = ref(1)
const pageSize = ref(10)

const filteredSignals = computed(() => {
  const filtered = fraudSignals.value.filter(s => s.fraud_score >= minScore.value)
  return filtered.slice(
    (currentPage.value - 1) * pageSize.value,
    currentPage.value * pageSize.value
  )
})

const totalPages = computed(() => {
  const filtered = fraudSignals.value.filter(s => s.fraud_score >= minScore.value)
  return Math.ceil(filtered.length / pageSize.value)
})

const visiblePages = computed(() => {
  const pages = []
  const maxVisible = 5
  let start = Math.max(1, currentPage.value - 2)
  let end = Math.min(totalPages.value, start + maxVisible - 1)
  if (end - start < maxVisible - 1) start = Math.max(1, end - maxVisible + 1)
  for (let i = start; i <= end; i++) pages.push(i)
  return pages
})

function getScoreColor(score) {
  if (score >= 0.8) return 'bg-red-600'
  if (score >= 0.6) return 'bg-orange-500'
  if (score >= 0.4) return 'bg-yellow-500'
  return 'bg-yellow-400'
}

function getScoreTextColor(score) {
  if (score >= 0.8) return 'text-red-600'
  if (score >= 0.6) return 'text-orange-600'
  if (score >= 0.4) return 'text-yellow-600'
  return 'text-yellow-600'
}

function formatDate(dateStr) {
  const date = new Date(dateStr)
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

function formatFlag(flag) {
  return flag.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')
}

function nextPage() {
  if (currentPage.value < totalPages.value) currentPage.value++
}

function previousPage() {
  if (currentPage.value > 1) currentPage.value--
}

function goToPage(page) {
  currentPage.value = page
}

function selectTransaction(txId) {
  emit('select-transaction', txId)
}

async function loadFraudSignals() {
  loading.value = true
  error.value = null
  currentPage.value = 1
  try {
    const data = await apiService.getFraudSignals(props.customerId, days.value, minScore.value, 50)
    fraudSignals.value = data.signals || []
  } catch (err) {
    error.value = err.message
    console.error('Failed to load fraud signals:', err)
  } finally {
    loading.value = false
  }
}

async function reload() {
  await loadFraudSignals()
}

watch(() => props.customerId, () => {
  loadFraudSignals()
}, { immediate: true })

watch([days, minScore], () => {
  loadFraudSignals()
})
</script>

<style scoped>
.card {
  @apply bg-white rounded-lg border border-gray-200;
}

.card-header {
  @apply px-6 py-4 border-b border-gray-200 bg-gray-50;
}

.card-body {
  @apply px-6 py-4;
}
</style>
