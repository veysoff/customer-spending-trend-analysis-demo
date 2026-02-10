<template>
  <div class="card">
    <div class="card-header">
      <div class="flex justify-between items-center">
        <div>
          <h2 class="text-lg font-semibold text-gray-900">📈 Feature Importance (Model Level)</h2>
          <p class="text-sm text-gray-500 mt-1">Which features matter most for churn prediction</p>
        </div>
        <button
          @click="loadFeatureImportance"
          :disabled="loading"
          class="btn-primary text-sm px-4 py-2"
        >
          {{ loading ? 'Loading...' : 'Refresh' }}
        </button>
      </div>
    </div>

    <div class="card-body">
      <!-- Loading State -->
      <div v-if="loading" class="text-center py-12">
        <div class="inline-block">
          <div class="animate-spin rounded-full h-10 w-10 border-b-2 border-brand-600"></div>
          <p class="mt-3 text-gray-600 text-sm">Loading feature importance...</p>
        </div>
      </div>

      <!-- Content -->
      <div v-else-if="features">
        <!-- Model Performance Summary -->
        <div class="mb-6 grid grid-cols-4 gap-3">
          <div class="p-3 bg-blue-50 rounded-lg border border-blue-200">
            <p class="text-xs text-blue-600 mb-1 font-semibold">F1-SCORE</p>
            <p class="text-xl font-bold text-blue-900">
              {{ (features.model_performance.f1_score * 100).toFixed(2) }}%
            </p>
          </div>
          <div class="p-3 bg-purple-50 rounded-lg border border-purple-200">
            <p class="text-xs text-purple-600 mb-1 font-semibold">PRECISION</p>
            <p class="text-xl font-bold text-purple-900">
              {{ (features.model_performance.precision * 100).toFixed(2) }}%
            </p>
          </div>
          <div class="p-3 bg-green-50 rounded-lg border border-green-200">
            <p class="text-xs text-green-600 mb-1 font-semibold">RECALL</p>
            <p class="text-xl font-bold text-green-900">
              {{ (features.model_performance.recall * 100).toFixed(2) }}%
            </p>
          </div>
          <div class="p-3 bg-amber-50 rounded-lg border border-amber-200">
            <p class="text-xs text-amber-600 mb-1 font-semibold">ROC-AUC</p>
            <p class="text-xl font-bold text-amber-900">
              {{ (features.model_performance.roc_auc * 100).toFixed(2) }}%
            </p>
          </div>
        </div>

        <!-- ApexCharts Horizontal Bar -->
        <div ref="chartContainer" class="mb-6">
          <apexchart
            type="barh"
            :options="chartOptions"
            :series="chartSeries"
            height="400"
          />
        </div>

        <!-- Feature Details Table -->
        <div class="space-y-2">
          <h3 class="text-sm font-semibold text-gray-900 mb-3">All Features Ranked</h3>

          <!-- Tabs for filtering -->
          <div class="flex gap-2 mb-4">
            <button
              v-for="category in ['All', 'UC-2', 'UC-1']"
              :key="category"
              @click="selectedCategory = category"
              :class="[
                'px-3 py-1.5 rounded text-xs font-medium transition-colors',
                selectedCategory === category
                  ? 'bg-brand-100 border-brand-300 text-brand-800 border'
                  : 'bg-white border-gray-200 text-gray-700 hover:bg-gray-50 border'
              ]"
            >
              {{ category }}
            </button>
          </div>

          <div class="overflow-x-auto">
            <table class="w-full text-xs">
              <thead class="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th class="px-4 py-2 text-left font-semibold text-gray-900">#</th>
                  <th class="px-4 py-2 text-left font-semibold text-gray-900">Feature</th>
                  <th class="px-4 py-2 text-left font-semibold text-gray-900">Type</th>
                  <th class="px-4 py-2 text-left font-semibold text-gray-900">Importance</th>
                  <th class="px-4 py-2 text-left font-semibold text-gray-900">Interpretation</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(feature, index) in filteredFeatures"
                  :key="feature.rank"
                  class="border-b border-gray-200 hover:bg-gray-50 transition-colors"
                >
                  <td class="px-4 py-2 text-gray-600 font-semibold">{{ feature.rank }}</td>
                  <td class="px-4 py-2 font-medium text-gray-900">{{ formatFeatureName(feature.feature_name) }}</td>
                  <td class="px-4 py-2">
                    <span
                      :class="[
                        'px-2 py-0.5 rounded text-xs font-semibold',
                        isUC2Feature(feature.feature_name)
                          ? 'bg-purple-100 text-purple-800'
                          : 'bg-blue-100 text-blue-800'
                      ]"
                    >
                      {{ isUC2Feature(feature.feature_name) ? 'UC-2' : 'UC-1' }}
                    </span>
                  </td>
                  <td class="px-4 py-2">
                    <div class="flex items-center gap-2">
                      <div class="h-1.5 w-16 bg-gray-200 rounded-full overflow-hidden">
                        <div
                          class="h-full bg-gradient-to-r from-brand-500 to-brand-600 rounded-full"
                          :style="{ width: (feature.importance_score / topScore) * 100 + '%' }"
                        />
                      </div>
                      <span class="font-semibold text-gray-700 w-10 text-right">
                        {{ (feature.importance_score * 100).toFixed(1) }}%
                      </span>
                    </div>
                  </td>
                  <td class="px-4 py-2 text-gray-600 max-w-xs">
                    {{ feature.interpretation }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Key Findings -->
        <div class="mt-6 p-4 bg-green-50 border border-green-200 rounded-lg">
          <p class="text-sm font-semibold text-green-900 mb-2">🎯 Key Findings</p>
          <ul class="text-sm text-green-800 space-y-1 list-disc list-inside">
            <li v-for="finding in keyFindings" :key="finding">{{ finding }}</li>
          </ul>
        </div>

        <!-- Category Breakdown -->
        <div class="mt-4 grid grid-cols-2 gap-4">
          <div class="p-4 bg-purple-50 rounded-lg border border-purple-200">
            <p class="text-xs font-semibold text-purple-600 mb-2">UC-2 Features (Credit)</p>
            <p class="text-sm text-purple-800">
              {{ (uc2Importance * 100).toFixed(1) }}% combined importance
            </p>
            <p class="text-xs text-purple-700 mt-1">
              Focus: Credit metrics, dormancy, payment behavior
            </p>
          </div>
          <div class="p-4 bg-blue-50 rounded-lg border border-blue-200">
            <p class="text-xs font-semibold text-blue-600 mb-2">UC-1 Features (Trends)</p>
            <p class="text-sm text-blue-800">
              {{ (uc1Importance * 100).toFixed(1) }}% combined importance
            </p>
            <p class="text-xs text-blue-700 mt-1">
              Focus: Spending trends, categories, channels
            </p>
          </div>
        </div>
      </div>

      <!-- No Data State -->
      <div v-else class="text-center py-12 text-gray-500">
        <p class="text-sm">Click "Refresh" to load feature importance</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, watch } from 'vue'
import ApexCharts from 'apexcharts'
import { apiService } from '../services/api'

const props = defineProps({
  customerId: String
})

const features = ref(null)
const loading = ref(false)
const selectedCategory = ref('All')
const chartOptions = ref({})
const chartSeries = ref([])

const uc2Features = [
  'utilization_ratio',
  'dormancy_days',
  'payment_delay_score',
  'support_sentiment_score',
  'campaign_engagement_score',
  'account_age_months',
  'balance_to_spending_ratio',
  'inactive_months_count'
]

// Load feature importance
async function loadFeatureImportance() {
  loading.value = true
  try {
    features.value = await apiService.getFeatureImportance()
    await nextTick()
    updateChart()
  } catch (err) {
    console.error('Failed to load feature importance:', err)
    features.value = null
  } finally {
    loading.value = false
  }
}

// Update chart
function updateChart() {
  if (!features.value) return

  const top10 = features.value.top_features.slice(0, 10).reverse()

  chartSeries.value = [
    {
      name: 'Importance Score',
      data: top10.map(f => ({
        x: formatFeatureName(f.feature_name),
        y: f.importance_score
      }))
    }
  ]

  chartOptions.value = {
    chart: {
      type: 'barh',
      toolbar: {
        show: false
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
        return (val * 100).toFixed(1) + '%'
      },
      offsetX: 5
    },
    xaxis: {
      categories: top10.map(f => formatFeatureName(f.feature_name))
    },
    colors: top10.map(f =>
      isUC2Feature(f.feature_name) ? '#a78bfa' : '#60a5fa'
    ),
    tooltip: {
      theme: 'light',
      y: {
        formatter: function (val) {
          return (val * 100).toFixed(2) + '%'
        }
      }
    }
  }
}

// Compute properties
const topScore = computed(() => {
  if (!features.value || features.value.top_features.length === 0) return 1
  return features.value.top_features[0].importance_score
})

const filteredFeatures = computed(() => {
  if (!features.value) return []

  const all = features.value.top_features

  if (selectedCategory.value === 'UC-2') {
    return all.filter(f => isUC2Feature(f.feature_name))
  } else if (selectedCategory.value === 'UC-1') {
    return all.filter(f => !isUC2Feature(f.feature_name))
  }

  return all
})

const uc2Importance = computed(() => {
  if (!features.value) return 0
  return features.value.top_features
    .filter(f => isUC2Feature(f.feature_name))
    .reduce((sum, f) => sum + f.importance_score, 0)
})

const uc1Importance = computed(() => {
  if (!features.value) return 0
  return features.value.top_features
    .filter(f => !isUC2Feature(f.feature_name))
    .reduce((sum, f) => sum + f.importance_score, 0)
})

const keyFindings = computed(() => {
  if (!features.value) return []

  const top1 = features.value.top_features[0]
  const top5 = features.value.top_features.slice(0, 5)

  const uc2Count = top5.filter(f => isUC2Feature(f.feature_name)).length

  return [
    `Top predictor: ${formatFeatureName(top1.feature_name)} (${(top1.importance_score * 100).toFixed(1)}%)`,
    `UC-2 features dominate: ${uc2Count}/5 in top features`,
    `Model performance: F1=${(features.value.model_performance.f1_score * 100).toFixed(1)}%, AUC=${(features.value.model_performance.roc_auc * 100).toFixed(1)}%`,
    `Inactivity/dormancy metrics are strongest churn signals`
  ]
})

// Methods
function isUC2Feature(featureName) {
  return uc2Features.includes(featureName)
}

function formatFeatureName(name) {
  return name
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase())
}

// Load feature importance when component mounts or customer changes
watch(() => props.customerId, loadFeatureImportance, { immediate: true })
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
