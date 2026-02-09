<template>
  <div class="card">
    <div class="card-header">
      <h2 class="text-lg font-semibold text-gray-900">Customer Profile</h2>
    </div>
    <div class="card-body">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <!-- Left Column -->
        <div>
          <h3 class="text-sm font-medium text-gray-500 uppercase">Customer ID</h3>
          <p class="text-2xl font-bold text-gray-900 mt-1">{{ profile.customer_id }}</p>

          <h3 class="text-sm font-medium text-gray-500 uppercase mt-6">Current Monthly Spending</h3>
          <p class="text-2xl font-bold text-brand-600 mt-1">
            £{{ profile.current_monthly_spending.toFixed(2) }}
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
          <h3 class="text-sm font-medium text-gray-500 uppercase">Churn Risk</h3>
          <div class="mt-1 flex items-center">
            <div class="flex-1">
              <div class="w-full bg-gray-200 rounded-full h-3">
                <div
                  class="h-3 rounded-full transition-all"
                  :class="riskColor"
                  :style="{ width: (profile.churn_risk * 100) + '%' }"
                ></div>
              </div>
            </div>
            <span class="ml-3 text-xl font-bold" :class="riskColor">
              {{ (profile.churn_risk * 100).toFixed(0) }}%
            </span>
          </div>
          <span :class="'badge ' + badgeClass" class="mt-3">
            {{ profile.risk_category }}
          </span>

          <h3 class="text-sm font-medium text-gray-500 uppercase mt-6">Total Transactions</h3>
          <p class="text-2xl font-bold text-gray-900 mt-1">{{ profile.total_transactions }}</p>

          <h3 class="text-sm font-medium text-gray-500 uppercase mt-6">Period</h3>
          <p class="text-sm text-gray-600 mt-1">
            {{ profile.date_range[0] }} to {{ profile.date_range[1] }}
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

const riskColor = computed(() => {
  if (props.profile.churn_risk >= 0.8) return 'bg-red-600'
  if (props.profile.churn_risk >= 0.6) return 'bg-orange-500'
  if (props.profile.churn_risk >= 0.4) return 'bg-yellow-500'
  return 'bg-green-500'
})

const badgeClass = computed(() => {
  if (props.profile.risk_category === 'CRITICAL') return 'badge-critical'
  if (props.profile.risk_category === 'HIGH') return 'badge-high'
  if (props.profile.risk_category === 'MEDIUM') return 'badge-medium'
  return 'badge-low'
})
</script>
