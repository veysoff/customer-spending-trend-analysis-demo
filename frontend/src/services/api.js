import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  }
})

export const apiService = {
  // Generate synthetic data
  async generateData(n_customers = 1000, months = 12) {
    const response = await api.post('/api/data/generate', {
      n_customers,
      months,
      patterns: ['normal', 'silent_churn', 'lifestyle_shift']
    })
    return response.data
  },

  // Get customer profile
  async getCustomerProfile(customerId) {
    const response = await api.get(`/api/customers/${customerId}`)
    return response.data
  },

  // Get customer trends
  async getCustomerTrends(customerId) {
    const response = await api.get(`/api/customers/${customerId}/trends`)
    return response.data
  },

  // Get customer anomalies
  async getCustomerAnomalies(customerId) {
    const response = await api.get(`/api/customers/${customerId}/anomalies`)
    return response.data
  },

  // Get high-risk customers
  async getHighRiskCustomers() {
    const response = await api.get('/api/customers/risk/high')
    return response.data
  },

  // Get all customers from database
  async getAllCustomers() {
    const response = await api.get('/api/customers')
    return response.data
  },

  // Get personas
  async getPersonas() {
    const response = await api.get('/api/personas')
    return response.data
  },

  // ========== Phase 5D: Churn Prediction API Methods ==========

  // Train/retrain churn model
  async trainChurnModel() {
    const response = await api.post('/api/ml/train-churn-model')
    return response.data
  },

  // Get single customer churn prediction with SHAP explanation
  async getChurnPrediction(customerId) {
    const response = await api.get(`/api/customers/${customerId}/churn-prediction`)
    return response.data
  },

  // Get batch churn predictions for all customers
  async predictAllChurn() {
    const response = await api.post('/api/ml/predict-all-churn')
    return response.data
  },

  // Get feature importance ranking from trained model
  async getFeatureImportance() {
    const response = await api.get('/api/ml/churn-model/feature-importance')
    return response.data
  },

  // Health check
  async healthCheck() {
    const response = await api.get('/health')
    return response.data
  }
}

export default api
