<template>
  <div class="min-h-screen bg-gray-50 flex flex-col">
    <!-- Header -->
    <header class="bg-white border-b border-gray-200 shadow-sm">
      <div class="max-w-full mx-auto px-4 py-6 sm:px-6 lg:px-8 flex justify-between items-center">
        <div>
          <h1 class="text-3xl font-bold text-gray-900">
            📊 Customer Analytics Dashboard
          </h1>
          <p class="text-gray-600 mt-1">Unified spending trends & churn prediction</p>
        </div>
      </div>
    </header>

    <!-- Main Content with Sidebar -->
    <div class="flex flex-1 overflow-hidden">
      <!-- Main Content Area -->
      <main class="flex-1 overflow-y-auto px-4 py-8 sm:px-6 lg:px-8">
        <!-- Error Alert -->
        <div v-if="store.error" class="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p class="text-red-800">{{ store.error }}</p>
        </div>

        <!-- Loading State -->
        <div v-if="store.loading && !store.dataGenerated" class="text-center py-12">
          <div class="inline-block">
            <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-600"></div>
            <p class="mt-4 text-gray-600">Loading data...</p>
          </div>
        </div>

        <!-- UNIFIED DASHBOARD (when data loaded) -->
        <template v-else-if="store.dataGenerated">
          <!-- UC LEGEND (Compact Inline) -->
          <div class="flex gap-3 mb-6 flex-wrap items-center">
            <span class="text-xs font-semibold text-gray-600 uppercase tracking-wide">Use Cases:</span>
            <div class="flex gap-3 flex-wrap">
              <div class="inline-flex items-center gap-2 px-3 py-1.5 bg-green-50 border border-green-200 rounded-md hover:bg-green-100 transition-colors" title="Spending Trends & Behavior - Historical transaction analysis, trend detection, anomalies">
                <span class="bg-green-200 text-green-900 px-2 py-0.5 rounded font-bold text-xs">[UC-1]</span>
                <span class="text-xs font-medium text-green-900">Trends</span>
              </div>
              <div class="inline-flex items-center gap-2 px-3 py-1.5 bg-red-50 border border-red-200 rounded-md hover:bg-red-100 transition-colors" title="Churn Risk & Prediction - ML-based risk assessment, SHAP explainability, recommendations">
                <span class="bg-red-200 text-red-900 px-2 py-0.5 rounded font-bold text-xs">[UC-2]</span>
                <span class="text-xs font-medium text-red-900">Churn</span>
              </div>
            </div>
          </div>

          <!-- Customer Selector (Dropdown with Search) -->
          <div class="mb-8 relative" ref="selectorRef">
            <label class="block text-sm font-semibold text-gray-700 mb-2">👤 Select Customer</label>
            <!-- Trigger button -->
            <button
              @click="dropdownOpen = !dropdownOpen"
              class="w-full max-w-xl flex items-center justify-between px-4 py-2.5 bg-white border-2 border-gray-200 rounded-lg hover:border-brand-400 transition-colors text-left"
              :class="{ 'border-brand-500 ring-2 ring-brand-100': dropdownOpen }"
            >
              <span v-if="store.selectedCustomerId" class="flex items-center gap-3 min-w-0">
                <span class="font-medium text-gray-900 text-sm truncate">
                  {{ store.customers.find(c => c.customer_id === store.selectedCustomerId)?.name || store.selectedCustomerId }}
                </span>
                <span
                  v-if="store.customers.find(c => c.customer_id === store.selectedCustomerId)?.tier_label"
                  :class="{
                    'bg-green-100 text-green-700': ['stable','growth'].includes(store.customers.find(c => c.customer_id === store.selectedCustomerId)?.persona_tier),
                    'bg-yellow-100 text-yellow-700': store.customers.find(c => c.customer_id === store.selectedCustomerId)?.persona_tier === 'at_risk',
                    'bg-red-100 text-red-700': store.customers.find(c => c.customer_id === store.selectedCustomerId)?.persona_tier === 'anomaly',
                    'bg-gray-100 text-gray-600': !['stable','growth','at_risk','anomaly'].includes(store.customers.find(c => c.customer_id === store.selectedCustomerId)?.persona_tier)
                  }"
                  class="text-xs px-2 py-0.5 rounded flex-shrink-0"
                >
                  {{ store.customers.find(c => c.customer_id === store.selectedCustomerId)?.tier_label }}
                </span>
              </span>
              <span v-else class="text-gray-400 text-sm">Choose a customer...</span>
              <svg class="w-4 h-4 text-gray-400 flex-shrink-0 transition-transform" :class="{ 'rotate-180': dropdownOpen }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
              </svg>
            </button>

            <!-- Dropdown panel -->
            <div
              v-if="dropdownOpen"
              class="absolute z-50 mt-1 w-full max-w-xl bg-white border border-gray-200 rounded-lg shadow-lg"
            >
              <!-- Search input -->
              <div class="p-2 border-b border-gray-100">
                <div class="relative">
                  <svg class="absolute left-3 top-2.5 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
                  </svg>
                  <input
                    v-model="customerSearch"
                    ref="searchInput"
                    type="text"
                    placeholder="Search by name or ID..."
                    class="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 rounded-md focus:outline-none focus:border-brand-400"
                  />
                </div>
              </div>
              <!-- Customer list grouped by tier -->
              <div class="max-h-80 overflow-y-auto">
                <template v-for="(group, tier) in groupedCustomers" :key="tier">
                  <div v-if="group.length > 0" class="px-3 pt-2 pb-0.5 text-xs font-semibold uppercase tracking-wide text-gray-400 flex items-center gap-1.5">
                    <span :class="{
                      'text-green-500': tier === 'stable' || tier === 'growth',
                      'text-yellow-500': tier === 'at_risk',
                      'text-red-500': tier === 'anomaly',
                      'text-gray-400': tier === 'normal' || tier === 'lifestyle_shift' || tier === 'silent_churn'
                    }">●</span>
                    {{ tierGroupLabel(tier) }} ({{ group.length }})
                  </div>
                  <button
                    v-for="customer in group"
                    :key="customer.customer_id"
                    @click="selectAndClose(customer.customer_id)"
                    class="w-full flex items-center justify-between px-4 py-2 hover:bg-gray-50 text-left transition-colors"
                    :class="{ 'bg-brand-50': store.selectedCustomerId === customer.customer_id }"
                    :title="customer.narrative"
                  >
                    <span class="flex items-center gap-2 min-w-0">
                      <span class="font-medium text-sm text-gray-900 truncate">{{ customer.name }}</span>
                      <span v-if="customer.narrative" class="text-xs text-gray-400 truncate hidden sm:block max-w-32">{{ customer.narrative }}</span>
                    </span>
                    <span
                      v-if="customer.churn_risk_score != null"
                      :class="{
                        'bg-red-100 text-red-700': customer.churn_risk_score > 60,
                        'bg-yellow-100 text-yellow-700': customer.churn_risk_score >= 30 && customer.churn_risk_score <= 60,
                        'bg-green-100 text-green-700': customer.churn_risk_score < 30
                      }"
                      class="text-xs font-bold px-2 py-0.5 rounded-full flex-shrink-0 ml-2"
                    >
                      {{ Math.round(customer.churn_risk_score) }}%
                    </span>
                  </button>
                </template>
                <div v-if="filteredCustomers.length === 0" class="px-4 py-3 text-sm text-gray-400 text-center">
                  No customers found
                </div>
              </div>
              <div class="px-4 py-2 border-t border-gray-100 text-xs text-gray-400 text-right">
                {{ filteredCustomers.length }} of {{ store.customers.length }} customers
              </div>
            </div>
          </div>

          <!-- BLOCK A + BLOCK B (Two-column layout) -->
          <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            <!-- BLOCK A: Spending Trends & Behavior -->
            <div class="space-y-6">
              <!-- UC-1 Badge & Info Toggle -->
              <div class="flex items-center justify-between mb-2">
                <div class="flex items-center gap-2">
                  <span class="bg-green-200 text-green-900 px-3 py-1 rounded-full font-bold text-sm">[UC-1]</span>
                  <span class="text-xs text-gray-600 font-medium">Historical Analysis</span>
                </div>
                <button
                  @click="showUC1Info = !showUC1Info"
                  class="text-xs text-green-600 hover:text-green-800 font-semibold flex items-center gap-1"
                >
                  ℹ️ {{ showUC1Info ? 'Hide' : 'Info' }}
                </button>
              </div>

              <!-- UC-1 Info Panel (Collapsible) -->
              <div v-if="showUC1Info" class="bg-green-50 border-l-4 border-green-500 p-4 rounded text-sm text-gray-700 mb-4">
                <p><strong>Purpose:</strong> Detect spending trends, anomalies, behavior changes</p>
                <p class="mt-2"><strong>Data Source:</strong> 335,802 historical transactions (12 months)</p>
                <p class="mt-2"><strong>Methods:</strong> Prophet (trend forecasting), Isolation Forest (anomaly detection)</p>
                <p class="mt-2"><strong>Update Frequency:</strong> Real-time per transaction</p>
                <p class="mt-2"><strong>Key Metrics:</strong> Trend slope, volatility, category diversity, frequency</p>
              </div>

              <!-- Header -->
              <div class="bg-gradient-to-r from-green-50 to-emerald-50 p-6 rounded-lg border-2 border-green-300">
                <h2 class="text-xl font-bold text-gray-900 mb-2">💰 Spending Trends & Behavior</h2>
                <p class="text-sm text-gray-600">UC-1: Customer spending patterns, trend direction, behavioral anomalies</p>
                <div class="text-xs text-gray-500 mt-3 flex gap-4">
                  <span>📊 Data: 335,802 transactions</span>
                  <span>🔄 Real-time</span>
                  <span>📈 Prophet Forecasting</span>
                </div>
              </div>

              <!-- Profile -->
              <Dashboard v-if="store.customerProfile" :profile="store.customerProfile" />

              <!-- Behavior Change Alert (if exists) -->
              <div v-if="store.customerProfile?.behavior_change" class="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                <h4 class="font-semibold text-yellow-900">⚠️ Behavior Change Detected</h4>
                <p class="text-yellow-800 mt-1 text-sm">{{ store.customerProfile.behavior_change }}</p>
              </div>
            </div>

            <!-- BLOCK B: Churn Risk & Insights -->
            <div class="space-y-6">
              <!-- UC-2 Badge & Info Toggle -->
              <div class="flex items-center justify-between mb-2">
                <div class="flex items-center gap-2">
                  <span class="bg-red-200 text-red-900 px-3 py-1 rounded-full font-bold text-sm">[UC-2]</span>
                  <span class="text-xs text-gray-600 font-medium">ML-Based Risk Assessment</span>
                </div>
                <button
                  @click="showUC2Info = !showUC2Info"
                  class="text-xs text-red-600 hover:text-red-800 font-semibold flex items-center gap-1"
                >
                  ℹ️ {{ showUC2Info ? 'Hide' : 'Info' }}
                </button>
              </div>

              <!-- UC-2 Info Panel (Collapsible) -->
              <div v-if="showUC2Info" class="bg-red-50 border-l-4 border-red-500 p-4 rounded text-sm text-gray-700 mb-4">
                <p><strong>Purpose:</strong> ML-powered churn risk assessment, identify at-risk customers</p>
                <p class="mt-2"><strong>Data Source:</strong> 15 engineered features (7 UC-1 + 8 UC-2 metrics)</p>
                <p class="mt-2"><strong>Model:</strong> XGBoost Binary Classifier (F1=0.85, Precision=0.88, Recall=0.82)</p>
                <p class="mt-2"><strong>Explainability:</strong> SHAP values for feature importance</p>
                <p class="mt-2"><strong>Update Frequency:</strong> On-demand, cached 7 days</p>
              </div>

              <!-- Header -->
              <div class="bg-gradient-to-r from-red-50 to-rose-50 p-6 rounded-lg border-2 border-red-300">
                <h2 class="text-xl font-bold text-gray-900 mb-2">⚠️ Churn Risk & Prediction</h2>
                <p class="text-sm text-gray-600">UC-2: ML-powered churn prediction, risk drivers (SHAP), personalized recommendations</p>
                <div class="text-xs text-gray-500 mt-3 flex gap-4">
                  <span>🤖 XGBoost (F1=0.85)</span>
                  <span>📊 15 Features</span>
                  <span>⏱️ Cached 7d</span>
                </div>
              </div>

              <!-- Churn Prediction Gauge -->
              <ChurnPredictionCard :customerId="store.selectedCustomerId" />
            </div>
          </div>

          <!-- VISUALIZATION TABS (below fold) -->
          <div class="mb-8">
            <div class="bg-white rounded-lg border-2 border-gray-300 p-6">
              <div class="mb-6">
                <h2 class="text-lg font-bold text-gray-900 mb-2">📈 Detailed Analysis</h2>
                <p class="text-sm text-gray-600">
                  Select visualization to explore <span class="text-green-600 font-semibold">[UC-1]</span> trends or <span class="text-red-600 font-semibold">[UC-2]</span> risk drivers in detail
                </p>
              </div>

              <!-- Tab Navigation with UC Labels -->
              <div class="flex gap-2 mb-6 flex-wrap border-b border-gray-200">
                <!-- UC-1 Tabs (Green) -->
                <button
                  v-for="tab in ['Trends', 'Anomalies']"
                  :key="tab"
                  @click="activeVizTab = tab"
                  :class="[
                    'px-4 py-2 font-semibold border-b-2 transition-colors flex items-center gap-2',
                    activeVizTab === tab
                      ? 'border-green-600 text-green-600'
                      : 'border-transparent text-gray-600 hover:text-gray-900'
                  ]"
                >
                  <span class="text-xs bg-green-100 text-green-800 px-2 py-0.5 rounded font-bold">[UC-1]</span>
                  {{ tab }}
                </button>

                <!-- UC-2 Tabs (Red) -->
                <button
                  @click="activeVizTab = 'Features'"
                  :class="[
                    'px-4 py-2 font-semibold border-b-2 transition-colors flex items-center gap-2',
                    activeVizTab === 'Features'
                      ? 'border-red-600 text-red-600'
                      : 'border-transparent text-gray-600 hover:text-gray-900'
                  ]"
                >
                  <span class="text-xs bg-red-100 text-red-800 px-2 py-0.5 rounded font-bold">[UC-2]</span>
                  Features
                </button>
              </div>

              <!-- Tab Description -->
              <div class="text-sm text-gray-600 mb-4 p-3 bg-gray-50 rounded">
                <template v-if="['Trends', 'Anomalies'].includes(activeVizTab)">
                  <span class="text-green-600 font-semibold">[UC-1]</span> Historical spending analysis from 335,802 transactions using Prophet forecasting
                </template>
                <template v-else-if="activeVizTab === 'Features'">
                  <span class="text-red-600 font-semibold">[UC-2]</span> All 15 engineered features and their importance in churn prediction model
                </template>
              </div>

              <!-- Tab Content -->
              <div>
                <TrendChart v-if="activeVizTab === 'Trends' && store.customerTrends" :trends="store.customerTrends" />
                <AnomalyAlert v-else-if="activeVizTab === 'Anomalies' && store.customerAnomalies" :anomalies="store.customerAnomalies" />
                <FeatureImportanceChart v-if="activeVizTab === 'Features' && store.selectedCustomerId" :customerId="store.selectedCustomerId" />
              </div>
            </div>
          </div>

          <!-- HIGH RISK CUSTOMERS TABLE (below visualizations) -->
          <div class="mb-8">
            <div class="bg-white rounded-lg border-2 border-gray-300 p-6">
              <!-- Header -->
              <h2 class="text-lg font-bold text-gray-900 mb-2">⚠️ High Risk Customers</h2>
              <p class="text-sm text-gray-600 mb-4">
                Customers at risk of churning based on UC-2 churn prediction model
              </p>

              <HighRiskTable v-if="highRiskLoaded" :customers="store.highRiskCustomers" />
            </div>
          </div>
        </template>

        <!-- Loading State (Initial) -->
        <div v-else class="text-center py-16">
          <div class="text-6xl mb-4">⏳</div>
          <h2 class="text-2xl font-bold text-gray-900 mb-2">Initializing...</h2>
          <p class="text-gray-600">Loading data from database...</p>
        </div>
      </main>

    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useCustomerStore } from './stores/customer'
import Dashboard from './components/Dashboard.vue'
import TrendChart from './components/TrendChart.vue'
import AnomalyAlert from './components/AnomalyAlert.vue'
import HighRiskTable from './components/HighRiskTable.vue'
import ChurnPredictionCard from './components/ChurnPredictionCard.vue'
import FeatureImportanceChart from './components/FeatureImportanceChart.vue'

const store = useCustomerStore()
const highRiskLoaded = ref(false)
const activeVizTab = ref('Trends')  // Visualization tab selection
const visualizationTabs = ['Trends', 'Anomalies', 'Risk Drivers', 'Features']

// UC Info Panel Toggles
const showUC1Info = ref(false)  // UC-1 Spending Trends info
const showUC2Info = ref(false)  // UC-2 Churn Prediction info

// Customer dropdown state
const dropdownOpen = ref(false)
const customerSearch = ref('')
const selectorRef = ref(null)
const searchInput = ref(null)

const filteredCustomers = computed(() => {
  const q = customerSearch.value.toLowerCase().trim()
  if (!q) return store.customers
  return store.customers.filter(c =>
    c.customer_id.toLowerCase().includes(q) ||
    (c.name || '').toLowerCase().includes(q) ||
    (c.pattern || '').toLowerCase().includes(q) ||
    (c.tier_label || '').toLowerCase().includes(q) ||
    (c.narrative || '').toLowerCase().includes(q)
  )
})

// Group customers by tier for organised dropdown display
const TIER_ORDER = ['stable', 'growth', 'at_risk', 'anomaly', 'normal', 'silent_churn', 'lifestyle_shift']
const groupedCustomers = computed(() => {
  const groups = {}
  for (const tier of TIER_ORDER) groups[tier] = []
  for (const c of filteredCustomers.value) {
    const tier = c.persona_tier || c.pattern || 'normal'
    if (!groups[tier]) groups[tier] = []
    groups[tier].push(c)
  }
  return groups
})

function tierGroupLabel(tier) {
  const labels = {
    stable: '✅ Stable',
    growth: '📈 Growth',
    at_risk: '⚠️ At Risk',
    anomaly: '🔴 Anomaly',
    normal: 'Normal',
    silent_churn: 'Silent Churn',
    lifestyle_shift: 'Lifestyle Shift',
  }
  return labels[tier] || tier
}

function selectAndClose(customerId) {
  store.selectCustomer(customerId)
  dropdownOpen.value = false
  customerSearch.value = ''
}

// Close dropdown when clicking outside
function handleClickOutside(e) {
  if (selectorRef.value && !selectorRef.value.contains(e.target)) {
    dropdownOpen.value = false
    customerSearch.value = ''
  }
}

// Focus search when dropdown opens
import { watch } from 'vue'
watch(dropdownOpen, async (open) => {
  if (open) {
    await nextTick()
    searchInput.value?.focus()
  }
})

onMounted(async () => {
  document.addEventListener('mousedown', handleClickOutside)
  // Auto-load data from database on app startup
  try {
    // Load customers (from database - already persisted)
    await store.loadCustomers()
    await store.loadHighRiskCustomers()
    highRiskLoaded.value = true

    // Select first customer by default
    if (store.customers.length > 0) {
      await store.selectCustomer(store.customers[0].customer_id)
    }
  } catch (err) {
    console.error('Failed to load data:', err)
  }
})

onUnmounted(() => {
  document.removeEventListener('mousedown', handleClickOutside)
})
</script>
