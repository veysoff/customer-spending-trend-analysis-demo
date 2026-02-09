<template>
  <div class="card">
    <div class="card-header">
      <h2 class="text-lg font-semibold text-gray-900">Risk Assessment & Explanation</h2>
    </div>
    <div class="card-body">
      <div class="mb-6">
        <h3 class="text-sm font-medium text-gray-500 uppercase">Churn Risk Summary</h3>
        <div class="mt-3 p-4 bg-gray-50 rounded-lg">
          <p class="text-gray-700">
            {{ riskSummary }}
          </p>
        </div>
      </div>

      <div class="border-t pt-6">
        <h3 class="text-sm font-medium text-gray-500 uppercase mb-4">Feature Importance (SHAP-style)</h3>

        <!-- Feature bars -->
        <div class="space-y-4">
          <div>
            <div class="flex justify-between items-center mb-1">
              <span class="text-sm font-medium text-gray-700">Trend Slope</span>
              <span :class="getFeatureColor(profile.spending_trend)" class="text-sm font-bold">
                {{ profile.spending_trend === 'DECREASING' ? 'High Risk ↓' : 'Low Risk ↑' }}
              </span>
            </div>
            <div class="w-full bg-gray-200 rounded-full h-2">
              <div class="h-2 rounded-full bg-blue-500" style="width: 75%"></div>
            </div>
          </div>

          <div>
            <div class="flex justify-between items-center mb-1">
              <span class="text-sm font-medium text-gray-700">Transaction Frequency</span>
              <span :class="getFrequencyColor()" class="text-sm font-bold">
                {{ profile.total_transactions > 300 ? 'Healthy' : 'Declining' }}
              </span>
            </div>
            <div class="w-full bg-gray-200 rounded-full h-2">
              <div class="h-2 rounded-full bg-green-500" :style="{ width: (profile.total_transactions / 400) * 100 + '%' }"></div>
            </div>
          </div>

          <div>
            <div class="flex justify-between items-center mb-1">
              <span class="text-sm font-medium text-gray-700">Behavior Stability</span>
              <span :class="getBehaviorColor()" class="text-sm font-bold">
                {{ profile.behavior_change ? 'Changed' : 'Stable' }}
              </span>
            </div>
            <div class="w-full bg-gray-200 rounded-full h-2">
              <div class="h-2 rounded-full" :class="profile.behavior_change ? 'bg-orange-500' : 'bg-green-500'" style="width: 100%"></div>
            </div>
          </div>

          <div>
            <div class="flex justify-between items-center mb-1">
              <span class="text-sm font-medium text-gray-700">Churn Risk Score</span>
              <span :class="{
                'text-red-600': profile.churn_risk >= 0.8,
                'text-orange-600': profile.churn_risk >= 0.6 && profile.churn_risk < 0.8,
                'text-yellow-600': profile.churn_risk >= 0.4 && profile.churn_risk < 0.6,
                'text-green-600': profile.churn_risk < 0.4
              }" class="text-sm font-bold">
                {{ (profile.churn_risk * 100).toFixed(0) }}% Risk
              </span>
            </div>
            <div class="w-full bg-gray-200 rounded-full h-2">
              <div class="h-2 rounded-full" :class="{
                'bg-red-600': profile.churn_risk >= 0.8,
                'bg-orange-500': profile.churn_risk >= 0.6 && profile.churn_risk < 0.8,
                'bg-yellow-500': profile.churn_risk >= 0.4 && profile.churn_risk < 0.6,
                'bg-green-500': profile.churn_risk < 0.4
              }" :style="{ width: (profile.churn_risk * 100) + '%' }"></div>
            </div>
          </div>
        </div>
      </div>

      <!-- Recommendation -->
      <div class="mt-6 p-4 rounded-lg" :class="{
        'bg-red-50 border border-red-200': profile.risk_category === 'CRITICAL',
        'bg-orange-50 border border-orange-200': profile.risk_category === 'HIGH',
        'bg-yellow-50 border border-yellow-200': profile.risk_category === 'MEDIUM',
        'bg-green-50 border border-green-200': profile.risk_category === 'LOW'
      }">
        <h4 class="font-semibold" :class="{
          'text-red-900': profile.risk_category === 'CRITICAL',
          'text-orange-900': profile.risk_category === 'HIGH',
          'text-yellow-900': profile.risk_category === 'MEDIUM',
          'text-green-900': profile.risk_category === 'LOW'
        }">
          Recommended Action
        </h4>
        <p class="mt-1 text-sm" :class="{
          'text-red-800': profile.risk_category === 'CRITICAL',
          'text-orange-800': profile.risk_category === 'HIGH',
          'text-yellow-800': profile.risk_category === 'MEDIUM',
          'text-green-800': profile.risk_category === 'LOW'
        }">
          {{ getRecommendation() }}
        </p>
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

const riskSummary = computed(() => {
  if (props.profile.churn_risk >= 0.8) {
    return `CRITICAL: ${props.profile.customer_id} shows severe churn indicators. Immediate intervention recommended. Primary issue: ${props.profile.spending_trend === 'DECREASING' ? 'Spending is declining rapidly' : 'Behavior has changed significantly'}`
  } else if (props.profile.churn_risk >= 0.6) {
    return `HIGH RISK: ${props.profile.customer_id} exhibits concerning patterns. ${props.profile.behavior_change ? 'Customer behavior has shifted significantly.' : ''} A targeted retention campaign is recommended.`
  } else if (props.profile.churn_risk >= 0.4) {
    return `MEDIUM RISK: ${props.profile.customer_id} shows moderate churn signals. Monitor closely and consider a gentle engagement initiative.`
  } else {
    return `LOW RISK: ${props.profile.customer_id} demonstrates stable spending patterns and engagement. Maintain regular service quality.`
  }
})

const getFeatureColor = () => {
  return props.profile.spending_trend === 'DECREASING' ? 'text-red-600' : 'text-green-600'
}

const getFrequencyColor = () => {
  return props.profile.total_transactions > 300 ? 'text-green-600' : 'text-orange-600'
}

const getBehaviorColor = () => {
  return props.profile.behavior_change ? 'text-orange-600' : 'text-green-600'
}

const getRecommendation = () => {
  if (props.profile.risk_category === 'CRITICAL') {
    return 'Urgent: Personal outreach by account manager, special retention offer, or VIP service upgrade.'
  } else if (props.profile.risk_category === 'HIGH') {
    return 'Launch targeted retention campaign, offer incentives for increased engagement.'
  } else if (props.profile.risk_category === 'MEDIUM') {
    return 'Monitor closely, send relevant product recommendations or service updates.'
  } else {
    return 'Continue standard service delivery, maintain relationship quality.'
  }
}
</script>
