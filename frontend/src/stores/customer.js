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
  async function generateData(n_customers = 1000, months = 12) {
    loading.value = true
    error.value = null
    try {
      const result = await apiService.generateData(n_customers, months)
      dataGenerated.value = true

      // Generate sample customer list (IDs only)
      customers.value = Array.from({ length: 50 }, (_, i) => ({
        customer_id: `customer_${String(i).padStart(6, '0')}`,
        name: `Customer ${i + 1}`,
        status: 'active'
      }))

      selectedCustomerId.value = customers.value[0].customer_id
      return result
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function selectCustomer(customerId) {
    selectedCustomerId.value = customerId
    await loadCustomerData(customerId)
  }

  async function loadCustomerData(customerId) {
    loading.value = true
    error.value = null
    try {
      const [profile, trends, anomalies] = await Promise.all([
        apiService.getCustomerProfile(customerId),
        apiService.getCustomerTrends(customerId),
        apiService.getCustomerAnomalies(customerId)
      ])

      customerProfile.value = profile
      customerTrends.value = trends
      customerAnomalies.value = anomalies
    } catch (err) {
      error.value = err.message
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
    generateData,
    selectCustomer,
    loadCustomerData,
    loadHighRiskCustomers
  }
})
