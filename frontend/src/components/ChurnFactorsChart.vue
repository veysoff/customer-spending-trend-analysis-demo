<template>
  <div class="card">
    <div class="card-header">
      <h2 class="text-lg font-semibold text-gray-900">📊 SHAP Explanation (Top 5 Factors)</h2>
      <p class="text-sm text-gray-500 mt-1">Which features drive the churn prediction</p>
    </div>

    <div class="card-body">
      <!-- Loading State -->
      <div v-if="loading" class="text-center py-8">
        <div class="inline-block">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-600"></div>
        </div>
      </div>

      <!-- No Data State -->
      <div v-else-if="!factors || factors.length === 0" class="text-center py-8 text-gray-500">
        <p class="text-sm">No prediction data available</p>
      </div>

      <!-- Chart Content -->
      <div v-else>
        <!-- ApexCharts Bar Chart -->
        <div ref="chartContainer" class="mb-6">
          <apexchart
            type="barh"
            :options="chartOptions"
            :series="chartSeries"
            height="350"
          />
        </div>

        <!-- Legend and Explanation -->
        <div class="space-y-3">
          <div class="flex items-center gap-4 text-xs">
            <div class="flex items-center gap-2">
              <div class="w-3 h-3 bg-red-500 rounded"></div>
              <span class="text-gray-700">Increases Churn Risk</span>
            </div>
            <div class="flex items-center gap-2">
              <div class="w-3 h-3 bg-green-500 rounded"></div>
              <span class="text-gray-700">Decreases Churn Risk</span>
            </div>
          </div>
        </div>

        <!-- Detailed Factor Table -->
        <div class="mt-6 space-y-2">
          <h3 class="text-sm font-semibold text-gray-900 mb-3">Factor Details</h3>
          <div
            v-for="(factor, index) in factors"
            :key="index"
            class="p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <div class="flex items-start justify-between mb-2">
              <div>
                <p class="font-semibold text-sm text-gray-900">
                  {{ index + 1 }}. {{ formatFeatureName(factor.feature_name) }}
                </p>
                <p class="text-xs text-gray-600 mt-1">
                  Current Value: {{ formatFeatureValue(factor.feature_value, factor.feature_name) }}
                </p>
              </div>
              <span
                :class="[
                  'text-xs font-semibold px-2 py-1 rounded',
                  factor.contribution_direction === 'increases_churn'
                    ? 'bg-red-100 text-red-800'
                    : 'bg-green-100 text-green-800'
                ]"
              >
                {{ factor.contribution_direction === 'increases_churn' ? '⬆️ +Churn' : '⬇️ -Churn' }}
              </span>
            </div>

            <!-- SHAP Value Bar -->
            <div class="flex items-center gap-2">
              <div class="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
                <div
                  class="h-full rounded-full transition-all"
                  :class="factor.contribution_direction === 'increases_churn' ? 'bg-red-500' : 'bg-green-500'"
                  :style="{ width: Math.abs(factor.shap_value) * 200 + '%' }"
                />
              </div>
              <span class="text-xs font-mono text-gray-700 w-12 text-right">
                {{ Math.abs(factor.shap_value).toFixed(3) }}
              </span>
            </div>

            <!-- Interpretation -->
            <p class="text-xs text-gray-600 mt-2">
              {{ getFactorInterpretation(factor) }}
            </p>
          </div>
        </div>

        <!-- Key Insights -->
        <div class="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <p class="text-sm font-semibold text-blue-900 mb-2">💡 Key Insights</p>
          <ul class="text-sm text-blue-800 space-y-1 list-disc list-inside">
            <li v-for="insight in keyInsights" :key="insight">{{ insight }}</li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import ApexCharts from 'apexcharts'
import { apiService } from '../services/api'

const props = defineProps({
  customerId: String
})

const factors = ref(null)
const loading = ref(false)
const chartOptions = ref({})
const chartSeries = ref([])

// Load SHAP data when customer changes
async function loadChurnPrediction() {
  if (!props.customerId) {
    factors.value = null
    return
  }

  loading.value = true
  try {
    const prediction = await apiService.getChurnPrediction(props.customerId)
    factors.value = prediction.top_5_factors || []
    await nextTick()
    updateChart()
  } catch (err) {
    console.error('Failed to load churn prediction:', err)
    factors.value = null
  } finally {
    loading.value = false
  }
}

// Update chart when factors change
function updateChart() {
  if (!factors.value || factors.value.length === 0) return

  const sortedFactors = [...factors.value].reverse()

  chartSeries.value = [
    {
      name: 'SHAP Value (Impact)',
      data: sortedFactors.map(f => ({
        x: formatFeatureName(f.feature_name),
        y: f.shap_value,
        fillColor: f.contribution_direction === 'increases_churn' ? '#ef4444' : '#22c55e'
      }))
    }
  ]

  chartOptions.value = {
    chart: {
      type: 'barh',
      toolbar: {
        show: false
      },
      sparkline: {
        enabled: false
      }
    },
    plotOptions: {
      bar: {
        distributed: true,
        horizontal: true,
        dataLabels: {
          position: 'right'
        }
      }
    },
    dataLabels: {
      enabled: true,
      formatter: function (val) {
        return (Math.abs(val) * 100).toFixed(1) + '%'
      },
      offsetX: 5
    },
    xaxis: {
      categories: sortedFactors.map(f => formatFeatureName(f.feature_name)),
      type: 'numeric',
      axisBorder: {
        show: false
      }
    },
    yaxis: {
      title: {
        text: 'Features'
      }
    },
    grid: {
      yaxis: {
        lines: {
          show: false
        }
      }
    },
    colors: sortedFactors.map(f =>
      f.contribution_direction === 'increases_churn' ? '#ef4444' : '#22c55e'
    ),
    tooltip: {
      theme: 'light',
      y: {
        formatter: function (val) {
          return (Math.abs(val) * 100).toFixed(2) + '% Impact'
        }
      }
    }
  }
}

// Compute key insights
const keyInsights = computed(() => {
  if (!factors.value || factors.value.length === 0) return []

  const insights = []

  // Find top risk factor
  const topRisk = factors.value.find(f => f.contribution_direction === 'increases_churn')
  if (topRisk) {
    insights.push(`Dormancy is the top churn driver: ${Math.round(topRisk.shap_value * 100)}% impact`)
  }

  // Count positive vs negative factors
  const positiveCount = factors.value.filter(f => f.contribution_direction === 'increases_churn').length
  const negativeCount = factors.value.filter(f => f.contribution_direction === 'decreases_churn').length

  if (positiveCount > negativeCount) {
    insights.push(`More risk factors (${positiveCount}) than protective factors (${negativeCount})`)
  } else {
    insights.push(`More protective factors (${negativeCount}) than risk factors (${positiveCount})`)
  }

  // Dormancy specifics
  const dormancy = factors.value.find(f => f.feature_name === 'dormancy_days')
  if (dormancy) {
    insights.push(`Customer has ${Math.round(dormancy.feature_value)} days without activity`)
  }

  return insights
})

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

function getFactorInterpretation(factor) {
  const interpretations = {
    dormancy_days: 'Days without any transaction activity. Higher values indicate increased risk.',
    inactive_months_count: 'Number of recent months with no transactions. Strong churn signal.',
    balance_to_spending_ratio: 'Ratio of balance to spending. High values suggest low engagement.',
    support_sentiment_score: 'Customer satisfaction from support interactions. Lower scores increase risk.',
    payment_delay_score: 'Payment behavior risk indicator. Higher scores indicate payment issues.',
    utilization_ratio: 'Credit utilization level. Affects account engagement.',
    trend_slope: 'Monthly spending trend. Negative slope suggests declining activity.',
    spending_volatility: 'Transaction amount variation. High volatility can indicate instability.',
    category_entropy: 'Spending diversity. Low entropy (narrow spending) increases risk.',
    transaction_count_trend: 'Transaction frequency trend. Declining frequency suggests disengagement.',
    account_age_months: 'Account age in months. Newer accounts have higher churn risk.',
    campaign_engagement_score: 'Response to marketing campaigns. Lower engagement increases risk.',
    pos_ratio: 'In-store vs online ratio. Affects usage patterns.',
    online_ratio: 'Online transaction percentage. Affects engagement style.',
    avg_transaction_amount: 'Average transaction size. Low amounts may indicate reduced activity.'
  }

  return interpretations[factor.feature_name] || 'Feature contribution to churn prediction'
}

watch(() => props.customerId, loadChurnPrediction, { immediate: true })
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
