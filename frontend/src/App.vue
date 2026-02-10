<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Header -->
    <header class="bg-white border-b border-gray-200 shadow-sm">
      <div class="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
        <div>
          <h1 class="text-3xl font-bold text-gray-900">
            📊 Customer Spending Trend Analysis
          </h1>
          <p class="text-gray-600 mt-1">ML-powered banking analytics PoC</p>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
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

      <!-- Main Content (when data loaded) -->
      <template v-else-if="store.dataGenerated">
        <!-- Tab Navigation for UC-1 vs UC-2 -->
        <div class="flex gap-2 mb-6">
          <button
            v-for="tab in ['UC-1', 'UC-2']"
            :key="tab"
            @click="activeTab = tab"
            :class="[
              'px-6 py-3 rounded-lg font-semibold transition-colors',
              activeTab === tab
                ? 'bg-brand-600 text-white'
                : 'bg-white border border-gray-200 text-gray-700 hover:bg-gray-50'
            ]"
          >
            {{ tab === 'UC-1' ? '💰 Spending Trends & Anomalies' : '⚠️ Churn Prediction' }}
          </button>
        </div>

        <!-- UC-1 Tab: Spending Trends and Anomalies -->
        <template v-if="activeTab === 'UC-1'">
          <div class="grid grid-cols-1 lg:grid-cols-4 gap-6 mb-8">
            <!-- Sidebar: Customer List -->
            <div class="card">
              <div class="card-header">
                <h2 class="text-lg font-semibold text-gray-900">Customers</h2>
              </div>
              <div class="card-body max-h-96 overflow-y-auto">
                <div class="space-y-2">
                  <button
                    v-for="customer in store.customers"
                    :key="customer.customer_id"
                    @click="store.selectCustomer(customer.customer_id)"
                    :class="{
                      'bg-brand-50 border-brand-300 text-brand-700': store.selectedCustomerId === customer.customer_id,
                      'bg-white border-gray-200 text-gray-700 hover:bg-gray-50': store.selectedCustomerId !== customer.customer_id
                    }"
                    class="w-full text-left px-3 py-2 rounded border transition-colors"
                  >
                    <div class="font-medium text-sm">{{ customer.name }}</div>
                    <div class="text-xs text-gray-500">{{ customer.customer_id }}</div>
                  </button>
                </div>
              </div>
            </div>

            <!-- Main Content Area -->
            <div class="lg:col-span-3 space-y-6">
              <!-- Customer Profile Card -->
              <Dashboard v-if="store.customerProfile" :profile="store.customerProfile" />

              <!-- Trend Chart -->
              <TrendChart v-if="store.customerTrends" :trends="store.customerTrends" />

              <!-- Anomalies -->
              <AnomalyAlert v-if="store.customerAnomalies" :anomalies="store.customerAnomalies" />

              <!-- Explainability Panel -->
              <ExplainabilityPanel v-if="store.customerProfile" :profile="store.customerProfile" />
            </div>
          </div>

          <!-- High Risk Customers Table -->
          <HighRiskTable v-if="highRiskLoaded" :customers="store.highRiskCustomers" />
        </template>

        <!-- UC-2 Tab: Churn Prediction -->
        <template v-else-if="activeTab === 'UC-2'">
          <div class="space-y-6">
            <!-- Top Section: Single Customer Churn Prediction -->
            <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <!-- Customer Selector -->
              <div class="card">
                <div class="card-header">
                  <h2 class="text-lg font-semibold text-gray-900">Select Customer</h2>
                </div>
                <div class="card-body max-h-96 overflow-y-auto">
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
                      <div class="font-medium">{{ customer.name }}</div>
                      <div class="text-xs text-gray-500">{{ customer.customer_id }}</div>
                    </button>
                  </div>
                </div>
              </div>

              <!-- Single Customer Churn Prediction -->
              <div class="lg:col-span-2">
                <ChurnPredictionCard :customerId="store.selectedCustomerId" />
              </div>
            </div>

            <!-- SHAP Explanation Chart -->
            <ChurnFactorsChart :customerId="store.selectedCustomerId" />

            <!-- Batch Predictions Table -->
            <BatchChurnTable />

            <!-- Feature Importance Chart -->
            <FeatureImportanceChart :customerId="store.selectedCustomerId" />
          </div>
        </template>
      </template>

      <!-- Loading State (Initial) -->
      <div v-else class="text-center py-16">
        <div class="text-6xl mb-4">⏳</div>
        <h2 class="text-2xl font-bold text-gray-900 mb-2">Initializing...</h2>
        <p class="text-gray-600">Loading data from database...</p>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useCustomerStore } from './stores/customer'
import Dashboard from './components/Dashboard.vue'
import TrendChart from './components/TrendChart.vue'
import AnomalyAlert from './components/AnomalyAlert.vue'
import ExplainabilityPanel from './components/ExplainabilityPanel.vue'
import HighRiskTable from './components/HighRiskTable.vue'
import ChurnPredictionCard from './components/ChurnPredictionCard.vue'
import ChurnFactorsChart from './components/ChurnFactorsChart.vue'
import BatchChurnTable from './components/BatchChurnTable.vue'
import FeatureImportanceChart from './components/FeatureImportanceChart.vue'

const store = useCustomerStore()
const highRiskLoaded = ref(false)
const activeTab = ref('UC-1')

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
