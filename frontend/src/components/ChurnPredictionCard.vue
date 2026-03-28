<template>
  <div class="card">
    <div class="card-header">
      <h2 class="text-lg font-semibold text-gray-900">🎯 Churn Prediction</h2>
      <p class="text-sm text-gray-500 mt-1">ML-powered churn risk assessment</p>
    </div>

    <div class="card-body">
      <!-- Loading State -->
      <div v-if="loading" class="text-center py-8">
        <div class="inline-block">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-600"></div>
          <p class="mt-2 text-sm text-gray-600">Loading prediction...</p>
        </div>
      </div>

      <!-- Error State with Retry -->
      <div v-else-if="error" class="p-4 bg-red-50 border border-red-200 rounded-lg">
        <p class="text-red-800 text-sm mb-3">{{ error }}</p>
        <button
          @click="loadPrediction"
          class="px-3 py-1 text-sm bg-red-600 text-white rounded hover:bg-red-700 transition-colors"
        >
          🔄 Retry
        </button>
      </div>

      <!-- Prediction Content -->
      <div v-else-if="prediction" class="space-y-6">
        <!-- Churn Risk Gauge -->
        <div class="flex flex-col items-center">
          <div class="relative w-32 h-32">
            <!-- Circular Progress -->
            <svg class="w-full h-full transform -rotate-90" viewBox="0 0 120 120">
              <!-- Background circle -->
              <circle cx="60" cy="60" r="54" fill="none" stroke="#e5e7eb" stroke-width="8" />
              <!-- Progress circle -->
              <circle
                cx="60"
                cy="60"
                r="54"
                fill="none"
                :stroke="riskColor"
                stroke-width="8"
                stroke-dasharray="339.29"
                :stroke-dashoffset="339.29 * (1 - prediction.churn_probability)"
                class="transition-all duration-500"
              />
            </svg>
            <!-- Center text -->
            <div class="absolute inset-0 flex flex-col items-center justify-center">
              <div class="text-3xl font-bold" :class="riskColorClass">
                {{ Math.round(prediction.churn_probability * 100) }}%
              </div>
              <div class="text-xs text-gray-600 text-center">
                Churn Risk
              </div>
            </div>
          </div>

          <!-- Risk Category Badge -->
          <div class="mt-4 inline-block">
            <span
              :class="[
                'px-4 py-2 rounded-full font-semibold text-sm',
                riskCategoryBadge
              ]"
            >
              {{ prediction.churn_prediction.toUpperCase() }}
            </span>
          </div>

          <!-- Confidence Score -->
          <div class="mt-3 text-center">
            <p class="text-xs text-gray-600">Model Confidence</p>
            <div class="flex items-center justify-center gap-2 mt-1">
              <div class="h-1.5 w-24 bg-gray-200 rounded-full overflow-hidden">
                <div
                  class="h-full bg-green-500 rounded-full transition-all"
                  :style="{ width: Math.round(prediction.confidence * 100) + '%' }"
                />
              </div>
              <span class="text-sm font-semibold text-gray-700">
                {{ Math.round(prediction.confidence * 100) }}%
              </span>
            </div>
          </div>
        </div>

        <!-- Divider -->
        <div class="border-t border-gray-200"></div>

        <!-- Account Metrics Grid -->
        <div>
          <h3 class="text-sm font-semibold text-gray-900 mb-3">Account Metrics</h3>
          <div class="grid grid-cols-2 gap-4">
            <!-- Credit Limit -->
            <div class="p-3 bg-gray-50 rounded-lg">
              <p class="text-xs text-gray-600 mb-1">Credit Limit</p>
              <p class="text-lg font-semibold text-gray-900">
                ${{ formatNumber(prediction.account_metrics.credit_limit) }}
              </p>
            </div>

            <!-- Current Balance -->
            <div class="p-3 bg-gray-50 rounded-lg">
              <p class="text-xs text-gray-600 mb-1">Current Balance</p>
              <p class="text-lg font-semibold text-gray-900">
                ${{ formatNumber(prediction.account_metrics.current_balance) }}
              </p>
            </div>

            <!-- Utilization -->
            <div class="p-3 bg-gray-50 rounded-lg">
              <p class="text-xs text-gray-600 mb-1">Utilization</p>
              <div class="flex items-center gap-2">
                <div class="h-1.5 w-12 bg-gray-300 rounded-full overflow-hidden">
                  <div
                    class="h-full rounded-full"
                    :class="utilization > 0.8 ? 'bg-red-500' : utilization > 0.5 ? 'bg-yellow-500' : 'bg-green-500'"
                    :style="{ width: Math.min(utilization * 100, 100) + '%' }"
                  />
                </div>
                <span class="text-sm font-semibold text-gray-700">
                  {{ Math.round(utilization * 100) }}%
                </span>
              </div>
            </div>

            <!-- Dormancy -->
            <div class="p-3 bg-gray-50 rounded-lg">
              <p class="text-xs text-gray-600 mb-1">Dormancy</p>
              <p class="text-lg font-semibold" :class="getDormancyColor()">
                {{ Math.round(prediction.account_metrics.dormancy_days) }} days
              </p>
            </div>

            <!-- Payment Delay -->
            <div class="p-3 bg-gray-50 rounded-lg">
              <p class="text-xs text-gray-600 mb-1">Payment Risk</p>
              <div class="flex items-center gap-2">
                <div class="h-1.5 w-12 bg-gray-300 rounded-full overflow-hidden">
                  <div
                    class="h-full rounded-full bg-red-500"
                    :style="{ width: Math.min(prediction.account_metrics.payment_delay_score * 100, 100) + '%' }"
                  />
                </div>
                <span class="text-sm font-semibold text-gray-700">
                  {{ Math.round(prediction.account_metrics.payment_delay_score * 100) }}%
                </span>
              </div>
            </div>

            <!-- Support Sentiment -->
            <div class="p-3 bg-gray-50 rounded-lg">
              <p class="text-xs text-gray-600 mb-1">Support Sentiment</p>
              <div class="flex items-center gap-2">
                <div class="h-1.5 w-12 bg-gray-300 rounded-full overflow-hidden">
                  <div
                    class="h-full rounded-full"
                    :class="prediction.account_metrics.support_sentiment_score > 0.7 ? 'bg-green-500' : 'bg-yellow-500'"
                    :style="{ width: prediction.account_metrics.support_sentiment_score * 100 + '%' }"
                  />
                </div>
                <span class="text-sm font-semibold text-gray-700">
                  {{ Math.round(prediction.account_metrics.support_sentiment_score * 100) }}%
                </span>
              </div>
            </div>

            <!-- Inactive Months -->
            <div class="p-3 bg-gray-50 rounded-lg">
              <p class="text-xs text-gray-600 mb-1">Inactive Months</p>
              <p class="text-lg font-semibold" :class="getInactiveColor()">
                {{ Math.round(prediction.account_metrics.inactive_months_count) }} / 6
              </p>
            </div>
          </div>
        </div>

        <!-- Risk Assessment -->
        <div class="p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <p class="text-sm font-semibold text-blue-900 mb-2">🔍 Risk Assessment</p>
          <p class="text-sm text-blue-800 leading-relaxed">
            {{ riskAssessment }}
          </p>
        </div>

        <!-- Top Contributing Factors -->
        <div v-if="prediction.top_5_factors && prediction.top_5_factors.length > 0">
          <h3 class="text-sm font-semibold text-gray-900 mb-3">Top Contributing Factors</h3>
          <div class="space-y-2">
            <div
              v-for="(factor, index) in prediction.top_5_factors"
              :key="index"
              class="flex items-start justify-between p-3 bg-gray-50 rounded-lg"
            >
              <div class="flex-1">
                <p class="text-sm font-medium text-gray-900">
                  {{ index + 1 }}. {{ formatFeatureName(factor.feature_name) }}
                </p>
                <p class="text-xs text-gray-600 mt-0.5">
                  Value: {{ formatFeatureValue(factor.feature_value, factor.feature_name) }}
                </p>
              </div>
              <div class="ml-3 text-right">
                <span
                  :class="[
                    'inline-block px-2 py-1 rounded text-xs font-semibold',
                    factor.contribution_direction === 'increases_churn'
                      ? 'bg-red-100 text-red-800'
                      : 'bg-green-100 text-green-800'
                  ]"
                >
                  {{ factor.contribution_direction === 'increases_churn' ? '⬆️ Increases' : '⬇️ Decreases' }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- No Data State -->
      <div v-else class="text-center py-8 text-gray-500">
        <p class="text-sm">Select a customer to view churn prediction</p>
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

const prediction = ref(null)
const loading = ref(false)
const error = ref(null)

// Computed properties
const riskColor = computed(() => {
  if (!prediction.value) return '#e5e7eb'
  const prob = prediction.value.churn_probability
  if (prob >= 0.8) return '#ef4444'
  if (prob >= 0.6) return '#f97316'
  if (prob >= 0.4) return '#eab308'
  return '#22c55e'
})

const riskColorClass = computed(() => {
  if (!prediction.value) return 'text-gray-900'
  const prob = prediction.value.churn_probability
  if (prob >= 0.8) return 'text-red-600'
  if (prob >= 0.6) return 'text-orange-600'
  if (prob >= 0.4) return 'text-yellow-600'
  return 'text-green-600'
})

const riskCategoryBadge = computed(() => {
  if (!prediction.value) return 'bg-gray-100 text-gray-700'
  const pred = prediction.value.churn_prediction
  if (pred === 'churned') return 'bg-red-100 text-red-800'
  return 'bg-green-100 text-green-800'
})

const utilization = computed(() => {
  return prediction.value?.account_metrics?.utilization_ratio || 0
})

const riskAssessment = computed(() => {
  if (!prediction.value) return ''
  const prob = prediction.value.churn_probability
  const dormancy = prediction.value.account_metrics.dormancy_days
  const inactive = prediction.value.account_metrics.inactive_months_count

  if (prob >= 0.8) {
    return `CRITICAL RISK: Customer has ${dormancy} days without transactions and ${inactive} inactive months. Immediate retention action recommended.`
  } else if (prob >= 0.6) {
    return `HIGH RISK: Customer shows signs of disengagement with ${dormancy} days dormancy. Consider targeted retention campaign.`
  } else if (prob >= 0.4) {
    return `MEDIUM RISK: Customer engagement is declining. Monitor account closely and reach out proactively.`
  } else {
    return `LOW RISK: Customer appears engaged and active. Continue standard service.`
  }
})

// Methods
function formatNumber(value) {
  if (!value) return '0'
  return Math.round(value).toLocaleString()
}

function formatFeatureName(name) {
  return name
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase())
}

function formatFeatureValue(value, featureName) {
  if (featureName.includes('ratio') || featureName.includes('score')) {
    return `${Math.round(value * 100)}%`
  }
  if (featureName.includes('days') || featureName.includes('months')) {
    return `${Math.round(value)}`
  }
  return value.toFixed(2)
}

function getDormancyColor() {
  if (!prediction.value) return 'text-gray-900'
  const days = prediction.value.account_metrics.dormancy_days
  if (days >= 180) return 'text-red-600'
  if (days >= 60) return 'text-orange-600'
  return 'text-green-600'
}

function getInactiveColor() {
  if (!prediction.value) return 'text-gray-900'
  const inactive = prediction.value.account_metrics.inactive_months_count
  if (inactive >= 5) return 'text-red-600'
  if (inactive >= 3) return 'text-orange-600'
  return 'text-green-600'
}

// Load prediction when customer changes
async function loadPrediction() {
  if (!props.customerId) {
    prediction.value = null
    return
  }

  loading.value = true
  error.value = null
  try {
    prediction.value = await apiService.getChurnPrediction(props.customerId)
  } catch (err) {
    error.value = 'Failed to load churn prediction: ' + err.message
    prediction.value = null
  } finally {
    loading.value = false
  }
}

watch(() => props.customerId, loadPrediction, { immediate: true })
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
</style>
