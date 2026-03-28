<template>
  <div class="card">
    <div class="card-header">
      <h2 class="text-lg font-semibold text-gray-900">Customer Profile</h2>
    </div>
    <div class="card-body">
      <!-- Persona Info (if available) -->
      <div v-if="profile.persona" class="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <h3 class="font-semibold text-blue-900">Persona: {{ profile.persona.persona_name }}</h3>
        <p class="text-blue-800 mt-2">{{ profile.persona.narrative }}</p>
        <div class="mt-2 text-sm text-blue-700">
          Expected Risk Score: {{ (profile.persona.expected_risk_score * 100).toFixed(0) }}%
        </div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <!-- Left Column -->
        <div>
          <h3 class="text-sm font-medium text-gray-500 uppercase">Customer ID</h3>
          <p class="text-2xl font-bold text-gray-900 mt-1">{{ profile.customer_id }}</p>

          <h3 class="text-sm font-medium text-gray-500 uppercase mt-6">Current Monthly Spending</h3>
          <p class="text-2xl font-bold text-brand-600 mt-1">
            AED {{ profile.current_monthly_spending.toFixed(2) }}
          </p>

          <h3 class="text-sm font-medium text-gray-500 uppercase mt-6">Spending Trend</h3>
          <div class="mt-1 flex items-center">
            <span :class="trendClass" class="text-lg font-bold">
              {{ profile.spending_trend }}
            </span>
            <span class="ml-2">
              {{ profile.spending_trend === 'INCREASING' ? '📈' : profile.spending_trend === 'DECREASING' ? '📉' : '➡️' }}
            </span>
          </div>
        </div>

        <!-- Right Column -->
        <div>
          <h3 class="text-sm font-medium text-gray-500 uppercase">Total Transactions</h3>
          <p class="text-2xl font-bold text-gray-900 mt-1">{{ profile.total_transactions }}</p>

          <h3 class="text-sm font-medium text-gray-500 uppercase mt-6">Date Range</h3>
          <p class="text-sm text-gray-600 mt-1">
            {{ profile.date_range[0] }} to {{ profile.date_range[1] }}
          </p>

          <h3 class="text-sm font-medium text-gray-500 uppercase mt-6">Analysis Period</h3>
          <p class="text-sm text-gray-600 mt-1">
            12 months of transaction history
          </p>
        </div>
      </div>

      <!-- Behavior Change Alert -->
      <div v-if="profile.behavior_change" class="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
        <h4 class="font-semibold text-yellow-900">Behavior Change Detected</h4>
        <p class="text-yellow-800 mt-1">{{ profile.behavior_change }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  profile: {
    type: Object,
    required: true
  }
})

const trendClass = computed(() => {
  if (props.profile.spending_trend === 'INCREASING') return 'text-green-600'
  if (props.profile.spending_trend === 'DECREASING') return 'text-red-600'
  return 'text-gray-600'
})
</script>
