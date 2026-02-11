import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { apiService } from '../services/api'

export const useCustomerStore = defineStore('customer', () => {
  // State
  const customers = ref([])
  const selectedCustomerId = ref(null)
  const customerProfile = ref(null)
  const customerTrends = ref(null)
  const customerAnomalies = ref(null)
  const highRiskCustomers = ref([])
  const loading = ref(false)
  const error = ref(null)
  const dataGenerated = ref(false)

  // Cache for customer data to prevent redundant API calls
  const dataCache = new Map()
  let loadingTimeout = null

  // Computed
  const selectedCustomer = computed(() =>
    customers.value.find(c => c.customer_id === selectedCustomerId.value)
  )

  const riskDistribution = computed(() => {
    if (!highRiskCustomers.value.length) return { low: 0, medium: 0, high: 0, critical: 0 }

    const dist = { low: 0, medium: 0, high: 0, critical: 0 }
    highRiskCustomers.value.forEach(c => {
      if (c.risk_category === 'CRITICAL') dist.critical++
      else if (c.risk_category === 'HIGH') dist.high++
      else if (c.risk_category === 'MEDIUM') dist.medium++
      else dist.low++
    })
    return dist
  })

  // Actions
  async function selectCustomer(customerId) {
    // IMPORTANT: Update selectedCustomerId FIRST to prevent race conditions
    if (selectedCustomerId.value === customerId) {
      // Already selected, don't reload
      return
    }
    selectedCustomerId.value = customerId
    await loadCustomerData(customerId)
  }

  async function loadCustomerData(customerId) {
    // SAFETY: Verify this is still the selected customer (prevent stale updates)
    if (selectedCustomerId.value !== customerId) {
      console.log(`[Cache] Ignoring stale load request for ${customerId}`)
      return
    }

    // Return cached data if available
    if (dataCache.has(customerId)) {
      const cached = dataCache.get(customerId)
      // SAFETY: Verify selection hasn't changed during cache retrieval
      if (selectedCustomerId.value === customerId) {
        customerProfile.value = cached.profile
        customerTrends.value = cached.trends
        customerAnomalies.value = cached.anomalies
        console.log(`[Cache] Loaded ${customerId} from cache (avoiding redundant API calls)`)
      }
      return
    }

    loading.value = true
    error.value = null

    // Cancel any pending load
    if (loadingTimeout) {
      clearTimeout(loadingTimeout)
    }

    try {
      const [profile, trends, anomalies] = await Promise.all([
        apiService.getCustomerProfile(customerId),
        apiService.getCustomerTrends(customerId),
        apiService.getCustomerAnomalies(customerId)
      ])

      // SAFETY: Double-check selection hasn't changed during API call
      if (selectedCustomerId.value !== customerId) {
        console.log(`[Cache] API completed for ${customerId}, but user selected ${selectedCustomerId.value}. Discarding old data.`)
        return
      }

      customerProfile.value = profile
      customerTrends.value = trends
      customerAnomalies.value = anomalies

      // Cache the data for future selections
      dataCache.set(customerId, { profile, trends, anomalies })
      console.log(`[Cache] Stored ${customerId} in cache for future selections`)
    } catch (err) {
      // SAFETY: Only set error if this is still the selected customer
      if (selectedCustomerId.value === customerId) {
        error.value = err.message
      }
      throw err
    } finally {
      // SAFETY: Only hide loading if this is still the selected customer
      if (selectedCustomerId.value === customerId) {
        loading.value = false
      }
    }
  }

  async function loadCustomers() {
    loading.value = true
    error.value = null
    try {
      // Load actual database customers from API
      const response = await apiService.getAllCustomers()
      customers.value = response.customers || []
      dataGenerated.value = true
      console.log(`Loaded ${customers.value.length} customers from database`)
      return response
    } catch (err) {
      error.value = err.message
      console.error('Failed to load customers:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function loadHighRiskCustomers() {
    loading.value = true
    error.value = null
    try {
      const data = await apiService.getHighRiskCustomers()
      highRiskCustomers.value = data.customers
      return data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  // Clear cache when needed (e.g., after data refresh)
  function clearDataCache() {
    dataCache.clear()
    console.log('[Cache] Cleared all cached customer data')
  }

  return {
    // State
    customers,
    selectedCustomerId,
    customerProfile,
    customerTrends,
    customerAnomalies,
    highRiskCustomers,
    loading,
    error,
    dataGenerated,

    // Computed
    selectedCustomer,
    riskDistribution,

    // Actions
    selectCustomer,
    loadCustomerData,
    loadCustomers,
    loadHighRiskCustomers,
    clearDataCache
  }
})
