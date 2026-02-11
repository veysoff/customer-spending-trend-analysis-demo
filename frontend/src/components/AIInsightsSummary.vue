<template>
  <div class="card">
    <div class="card-header">
      <h2 class="text-lg font-semibold text-gray-900 flex items-center gap-2">
        <span>🤖</span> AI Insights Summary
      </h2>
    </div>

    <div class="card-body">
      <!-- Loading State -->
      <div v-if="loading" class="text-center py-8">
        <div class="inline-block">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          <p class="mt-2 text-sm text-gray-600">Generating insights...</p>
        </div>
      </div>

      <!-- Error State with Retry -->
      <div v-else-if="error" class="p-4 bg-red-50 border border-red-200 rounded-lg">
        <p class="text-red-800 text-sm mb-3">{{ error }}</p>
        <button
          @click="loadInsights"
          class="px-3 py-1 text-sm bg-red-600 text-white rounded hover:bg-red-700 transition-colors"
        >
          🔄 Retry
        </button>
      </div>

      <!-- Summary Content -->
      <div v-else-if="summary" class="space-y-4">
        <!-- Risk Level Badge -->
        <div class="flex items-center justify-between p-3 rounded-lg" :class="riskBackgroundClass">
          <div class="flex items-center gap-3">
            <span class="text-2xl">{{ summary.summary_icon }}</span>
            <div>
              <p class="text-sm font-semibold text-gray-700">Risk Level</p>
              <p class="text-lg font-bold" :class="riskColorClass">
                {{ summary.summary }}
              </p>
            </div>
          </div>
          <div class="text-right">
            <p class="text-xs text-gray-600">Confidence</p>
            <p class="text-lg font-bold text-gray-900">
              {{ Math.round(summary.confidence_score * 100) }}%
            </p>
          </div>
        </div>

        <!-- Key Findings (First 2 Only) -->
        <div v-if="summary.key_findings && summary.key_findings.length > 0">
          <p class="text-sm font-semibold text-gray-700 mb-2">Key Findings</p>
          <div class="space-y-2">
            <div
              v-for="(finding, index) in summary.key_findings.slice(0, 2)"
              :key="index"
              class="flex gap-2 text-sm text-gray-700"
            >
              <span class="text-blue-600 font-bold flex-shrink-0">•</span>
              <p class="text-gray-600">{{ finding }}</p>
            </div>
          </div>
        </div>

        <!-- Business Advice Summary (First 100 chars) -->
        <div v-if="summary.business_advice" class="p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <p class="text-xs font-semibold text-blue-900 mb-1">💡 Recommendation</p>
          <p class="text-sm text-blue-800 line-clamp-2">
            {{ truncateText(summary.business_advice, 150) }}
          </p>
        </div>

        <!-- View Full Insights Link -->
        <button
          @click="$emit('open-panel')"
          class="w-full mt-2 py-2 px-3 text-sm font-semibold text-blue-600 hover:text-blue-700 hover:bg-blue-50 rounded-lg transition-colors"
        >
          View Full Insights →
        </button>
      </div>

      <!-- No Data State -->
      <div v-else class="text-center py-6 text-gray-500">
        <p class="text-sm">Select a customer to view AI insights</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { apiService } from '../services/api'

const props = defineProps({
  customerId: String
})

const emit = defineEmits(['open-panel'])

const summary = ref(null)
const loading = ref(false)
const error = ref(null)

// Computed properties
const riskColorClass = computed(() => {
  if (!summary.value) return 'text-gray-900'
  const risk = summary.value.summary
  if (risk === 'CRITICAL') return 'text-red-600'
  if (risk === 'WARNING') return 'text-orange-600'
  if (risk === 'AT_RISK') return 'text-yellow-600'
  return 'text-green-600'
})

const riskBackgroundClass = computed(() => {
  if (!summary.value) return 'bg-gray-50'
  const risk = summary.value.summary
  if (risk === 'CRITICAL') return 'bg-red-50 border border-red-200'
  if (risk === 'WARNING') return 'bg-orange-50 border border-orange-200'
  if (risk === 'AT_RISK') return 'bg-yellow-50 border border-yellow-200'
  return 'bg-green-50 border border-green-200'
})

// Methods
function truncateText(text, length) {
  if (!text) return ''
  if (text.length <= length) return text
  return text.substring(0, length).trim() + '...'
}

// Load insights when customer changes
async function loadInsights() {
  if (!props.customerId) {
    summary.value = null
    return
  }

  loading.value = true
  error.value = null
  try {
    summary.value = await apiService.getInsights(props.customerId)
  } catch (err) {
    error.value = 'Failed to load insights'
    summary.value = null
    console.error('Insights error:', err)
  } finally {
    loading.value = false
  }
}

watch(() => props.customerId, loadInsights, { immediate: true })
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

.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
