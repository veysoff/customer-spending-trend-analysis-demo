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
        <!-- Toggle AI Insights Button (always visible) -->
        <button
          @click="showAIInsights = !showAIInsights"
          :class="[
            'px-4 py-2 rounded-lg font-semibold transition-colors flex items-center gap-2',
            showAIInsights
              ? 'bg-blue-600 text-white'
              : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
          ]"
          title="Toggle AI Insights Panel"
        >
          <span>🤖</span>
          <span class="hidden sm:inline">{{ showAIInsights ? 'Hide' : 'Show' }} Insights</span>
          <span class="sm:hidden">{{ showAIInsights ? '✕' : '✓' }}</span>
        </button>
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
          <!-- Customer Selector (Small, top-left) -->
          <div class="mb-6 max-w-xs">
            <div class="card">
              <div class="card-header">
                <h2 class="text-lg font-semibold text-gray-900">Customer</h2>
              </div>
              <div class="card-body max-h-72 overflow-y-auto">
                <div class="space-y-2">
                  <button
                    v-for="customer in store.customers"
                    :key="customer.customer_id"
                    @click="store.selectCustomer(customer.customer_id)"
                    :class="{
                      'bg-brand-50 border-brand-300 text-brand-700': store.selectedCustomerId === customer.customer_id,
                      'bg-white border-gray-200 text-gray-700 hover:bg-gray-50': store.selectedCustomerId !== customer.customer_id
                    }"
                    class="w-full text-left px-3 py-2 rounded border transition-colors text-sm"
                  >
                    <div class="font-medium text-sm">{{ customer.name }}</div>
                    <div class="text-xs text-gray-500">{{ customer.customer_id }}</div>
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- BLOCK A + BLOCK B (Two-column layout) -->
          <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            <!-- BLOCK A: Spending Trends & Behavior -->
            <div class="space-y-6">
              <!-- Header -->
              <div class="bg-gradient-to-r from-green-50 to-emerald-50 p-6 rounded-lg border border-green-200">
                <h2 class="text-xl font-bold text-gray-900 mb-2">💰 Spending Trends & Behavior</h2>
                <p class="text-sm text-gray-600">Customer spending patterns and activity trends</p>
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
              <!-- Header -->
              <div class="bg-gradient-to-r from-red-50 to-rose-50 p-6 rounded-lg border border-red-200">
                <h2 class="text-xl font-bold text-gray-900 mb-2">⚠️ Churn Risk & Prediction</h2>
                <p class="text-sm text-gray-600">ML-powered churn prediction with risk drivers</p>
              </div>

              <!-- Churn Prediction Gauge -->
              <ChurnPredictionCard :customerId="store.selectedCustomerId" />

              <!-- AI Insights Summary (in a card) -->
              <AIInsightsSummary :customerId="store.selectedCustomerId" />
            </div>
          </div>

          <!-- VISUALIZATION TABS (below fold) -->
          <div class="mb-8">
            <div class="bg-white rounded-lg border border-gray-200 p-6">
              <h2 class="text-lg font-bold text-gray-900 mb-4">📈 Detailed Analysis</h2>

              <!-- Tab Navigation -->
              <div class="flex gap-2 mb-6 flex-wrap border-b border-gray-200">
                <button
                  v-for="tab in visualizationTabs"
                  :key="tab"
                  @click="activeVizTab = tab"
                  :class="[
                    'px-4 py-2 font-semibold border-b-2 transition-colors',
                    activeVizTab === tab
                      ? 'border-brand-600 text-brand-600'
                      : 'border-transparent text-gray-600 hover:text-gray-900'
                  ]"
                >
                  {{ tab }}
                </button>
              </div>

              <!-- Tab Content -->
              <div>
                <TrendChart v-if="activeVizTab === 'Trends' && store.customerTrends" :trends="store.customerTrends" />
                <AnomalyAlert v-else-if="activeVizTab === 'Anomalies' && store.customerAnomalies" :anomalies="store.customerAnomalies" />
                <ChurnFactorsChart v-else-if="activeVizTab === 'Risk Drivers' && store.selectedCustomerId" :customerId="store.selectedCustomerId" />
                <FeatureImportanceChart v-else-if="activeVizTab === 'Features' && store.selectedCustomerId" :customerId="store.selectedCustomerId" />
              </div>
            </div>
          </div>

          <!-- HIGH RISK CUSTOMERS TABLE (below visualizations) -->
          <div class="mb-8">
            <HighRiskTable v-if="highRiskLoaded" :customers="store.highRiskCustomers" />
          </div>
        </template>

        <!-- Loading State (Initial) -->
        <div v-else class="text-center py-16">
          <div class="text-6xl mb-4">⏳</div>
          <h2 class="text-2xl font-bold text-gray-900 mb-2">Initializing...</h2>
          <p class="text-gray-600">Loading data from database...</p>
        </div>
      </main>

      <!-- AI Insights Sidebar (Always Available) -->
      <aside
        v-if="showAIInsights"
        class="w-96 bg-white border-l border-gray-200 shadow-lg overflow-y-auto flex-shrink-0 transition-all duration-300"
      >
        <div class="sticky top-0 bg-white border-b border-gray-200 p-4 flex justify-between items-center z-10">
          <h2 class="text-lg font-bold text-gray-900 flex items-center gap-2">
            <span>🤖</span>AI Insights
          </h2>
          <button
            @click="showAIInsights = false"
            class="p-1 hover:bg-gray-100 rounded transition-colors"
            title="Close AI Insights"
          >
            <span class="text-gray-500 text-xl">✕</span>
          </button>
        </div>
        <div class="p-4">
          <AIInsightsPanel :customerId="store.selectedCustomerId" />
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useCustomerStore } from './stores/customer'
import Dashboard from './components/Dashboard.vue'
import TrendChart from './components/TrendChart.vue'
import AnomalyAlert from './components/AnomalyAlert.vue'
import HighRiskTable from './components/HighRiskTable.vue'
import ChurnPredictionCard from './components/ChurnPredictionCard.vue'
import ChurnFactorsChart from './components/ChurnFactorsChart.vue'
import FeatureImportanceChart from './components/FeatureImportanceChart.vue'
import AIInsightsPanel from './components/AIInsightsPanel.vue'
import AIInsightsSummary from './components/AIInsightsSummary.vue'

const store = useCustomerStore()
const highRiskLoaded = ref(false)
const showAIInsights = ref(true)  // Show AI Insights sidebar by default
const activeVizTab = ref('Trends')  // Visualization tab selection
const visualizationTabs = ['Trends', 'Anomalies', 'Risk Drivers', 'Features']

onMounted(async () => {
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
</script>
