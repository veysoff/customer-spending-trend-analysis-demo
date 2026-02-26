<template>
  <div class="card">
    <div class="card-header flex justify-between items-center">
      <div>
        <h2 class="text-lg font-semibold text-gray-900">
          🔍 Fraud Signal Detail
        </h2>
        <p class="text-sm text-gray-600 mt-1" v-if="detail">
          Transaction {{ detail.transaction_id }} - {{ formatDate(detail.transaction_date) }}
        </p>
      </div>
      <button
        @click="$emit('close')"
        class="text-gray-600 hover:text-gray-900 text-lg font-bold"
      >
        ×
      </button>
    </div>

    <div class="card-body">
      <div v-if="loading" class="text-center py-8">
        <div class="inline-block">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-red-600"></div>
          <p class="mt-2 text-gray-600 text-sm">Loading detail...</p>
        </div>
      </div>

      <div v-else-if="error" class="p-4 bg-red-50 border border-red-200 rounded-lg">
        <p class="text-red-800">{{ error }}</p>
      </div>

      <div v-else-if="detail">
        <!-- Transaction Info -->
        <div class="grid grid-cols-2 gap-4 mb-6 p-4 bg-gray-50 rounded-lg">
          <div>
            <label class="text-xs font-semibold text-gray-600 uppercase">Amount</label>
            <p class="text-xl font-bold text-gray-900 mt-1">AED {{ detail.amount.toFixed(2) }}</p>
          </div>
          <div>
            <label class="text-xs font-semibold text-gray-600 uppercase">Merchant</label>
            <p class="text-lg font-semibold text-gray-900 mt-1">{{ detail.merchant_name }}</p>
          </div>
          <div>
            <label class="text-xs font-semibold text-gray-600 uppercase">Channel</label>
            <p class="text-lg font-semibold text-gray-900 mt-1 capitalize">{{ detail.channel }}</p>
          </div>
          <div>
            <label class="text-xs font-semibold text-gray-600 uppercase">Location</label>
            <p class="text-lg font-semibold text-gray-900 mt-1">{{ detail.location }}</p>
          </div>
        </div>

        <!-- Fraud Score -->
        <div class="mb-6 p-4 rounded-lg" :class="getScoreBgColor(detail.fraud_score)">
          <div class="flex items-center justify-between mb-3">
            <h3 class="font-semibold text-lg" :class="getScoreTextColor(detail.fraud_score)">
              Fraud Risk Score
            </h3>
            <span class="text-3xl font-bold" :class="getScoreTextColor(detail.fraud_score)">
              {{ (detail.fraud_score * 100).toFixed(0) }}%
            </span>
          </div>
          <div class="w-full bg-gray-200 rounded-full h-3">
            <div
              class="h-3 rounded-full"
              :class="getScoreColor(detail.fraud_score)"
              :style="{ width: (detail.fraud_score * 100) + '%' }"
            ></div>
          </div>
        </div>

        <!-- Feature Vector -->
        <div class="mb-6">
          <h3 class="font-semibold text-gray-900 mb-3">📊 Feature Vector (8 Features)</h3>
          <div class="bg-gray-50 rounded-lg p-4 space-y-2">
            <div
              v-for="(value, feature) in detail.feature_vector"
              :key="feature"
              class="flex items-center justify-between py-2 border-b border-gray-200 last:border-0"
            >
              <span class="text-sm font-medium text-gray-700">{{ formatFeatureName(feature) }}</span>
              <span class="text-sm font-bold text-gray-900">{{ value.toFixed(3) }}</span>
            </div>
          </div>
        </div>

        <!-- Baseline Comparison -->
        <div v-if="detail.baseline_comparison" class="mb-6">
          <h3 class="font-semibold text-gray-900 mb-3">📈 vs. Customer Baseline</h3>
          <div class="grid grid-cols-2 gap-4">
            <div
              v-for="(baseline, metric) in detail.baseline_comparison"
              :key="metric"
              class="p-4 bg-blue-50 border border-blue-200 rounded-lg"
            >
              <p class="text-sm font-medium text-gray-700 mb-2">{{ formatFeatureName(metric) }}</p>
              <div class="flex items-baseline gap-2">
                <span class="text-2xl font-bold text-blue-900">{{ baseline.tx_value.toFixed(3) }}</span>
                <span class="text-xs text-gray-600">
                  {{ baseline.tx_value > baseline.mean ? '↑' : '↓' }}
                  {{ Math.abs((baseline.tx_value - baseline.mean) / baseline.mean * 100).toFixed(0) }}% vs baseline
                </span>
              </div>
              <p class="text-xs text-gray-600 mt-1">Baseline: {{ baseline.mean.toFixed(3) }}</p>
            </div>
          </div>
        </div>

        <!-- Fraud Flags -->
        <div v-if="detail.fraud_flags && detail.fraud_flags.length > 0" class="mb-6">
          <h3 class="font-semibold text-gray-900 mb-3">🚩 Fraud Flags</h3>
          <div class="flex flex-wrap gap-2">
            <span
              v-for="flag in detail.fraud_flags"
              :key="flag"
              class="inline-block px-3 py-1 bg-red-100 text-red-800 rounded-full text-sm font-semibold"
            >
              {{ formatFlag(flag) }}
            </span>
          </div>
        </div>

        <!-- Prior History Stats -->
        <div v-if="detail.prior_fraud_score_mean != null" class="p-4 bg-gray-50 rounded-lg">
          <h3 class="font-semibold text-gray-900 mb-3">📋 Customer Fraud History (Prior Transactions)</h3>
          <div class="grid grid-cols-3 gap-4">
            <div>
              <label class="text-xs font-semibold text-gray-600 uppercase">Mean Score</label>
              <p class="text-xl font-bold text-gray-900 mt-1">{{ (detail.prior_fraud_score_mean * 100).toFixed(1) }}%</p>
            </div>
            <div>
              <label class="text-xs font-semibold text-gray-600 uppercase">Max Score</label>
              <p class="text-xl font-bold text-gray-900 mt-1">{{ (detail.prior_fraud_score_max * 100).toFixed(1) }}%</p>
            </div>
            <div>
              <label class="text-xs font-semibold text-gray-600 uppercase">Transactions</label>
              <p class="text-xl font-bold text-gray-900 mt-1">{{ detail.prior_fraud_count }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { apiService } from '../services/api'

const props = defineProps({
  customerId: {
    type: String,
    required: true
  },
  transactionId: {
    type: String,
    required: true
  }
})

const emit = defineEmits(['close'])

const detail = ref(null)
const loading = ref(false)
const error = ref(null)

function getScoreColor(score) {
  if (score >= 0.8) return 'bg-red-600'
  if (score >= 0.6) return 'bg-orange-500'
  if (score >= 0.4) return 'bg-yellow-500'
  return 'bg-yellow-400'
}

function getScoreBgColor(score) {
  if (score >= 0.8) return 'bg-red-50 border border-red-200'
  if (score >= 0.6) return 'bg-orange-50 border border-orange-200'
  if (score >= 0.4) return 'bg-yellow-50 border border-yellow-200'
  return 'bg-yellow-50 border border-yellow-200'
}

function getScoreTextColor(score) {
  if (score >= 0.8) return 'text-red-600'
  if (score >= 0.6) return 'text-orange-600'
  if (score >= 0.4) return 'text-yellow-600'
  return 'text-yellow-600'
}

function formatDate(dateStr) {
  const date = new Date(dateStr)
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function formatFeatureName(feature) {
  const names = {
    'geo_risk': 'Geographic Risk',
    'night_activity': 'Night Activity',
    'card_testing': 'Card Testing',
    'structuring': 'Structuring',
    'amount_spike': 'Amount Spike',
    'high_velocity': 'High Velocity',
    'merchant_drift': 'Merchant Drift',
    'channel_anomaly': 'Channel Anomaly'
  }
  return names[feature] || feature.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')
}

function formatFlag(flag) {
  return flag.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')
}

async function loadDetail() {
  loading.value = true
  error.value = null
  try {
    const data = await apiService.getFraudTransactionDetail(props.customerId, props.transactionId)
    detail.value = data
  } catch (err) {
    error.value = err.message
    console.error('Failed to load fraud transaction detail:', err)
  } finally {
    loading.value = false
  }
}

watch([() => props.customerId, () => props.transactionId], () => {
  loadDetail()
}, { immediate: true })

onMounted(() => {
  loadDetail()
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
