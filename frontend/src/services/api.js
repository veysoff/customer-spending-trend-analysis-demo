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

  // Get AI Insights for a customer
  async getInsights(customerId) {
    const response = await api.get(`/api/customers/${customerId}/insights`)
    return response.data
  },

  // Health check
  async healthCheck() {
    const response = await api.get('/health')
    return response.data
  },

  // ========== Phase 4: UC-3 Fraud Detection API Methods ==========

  // Train fraud detection model
  async trainFraudModel() {
    const response = await api.post('/api/ml/train-fraud-model')
    return response.data
  },

  // Get fraud signals for a customer
  async getFraudSignals(customerId, days = 30, minScore = 0.3, limit = 20) {
    const response = await api.get(`/api/customers/${customerId}/fraud-signals`, {
      params: { days, min_score: minScore, limit }
    })
    return response.data
  },

  // Get fraud signal detail for a specific transaction
  async getFraudTransactionDetail(customerId, txId) {
    const response = await api.get(`/api/customers/${customerId}/fraud-signals/${txId}`)
    return response.data
  },

  // Get high-risk fraud transactions across portfolio
  async getHighRiskFraudTransactions(limit = 50, minScore = 0.5) {
    const response = await api.get('/api/ml/fraud/high-risk-transactions', {
      params: { limit, min_score: minScore }
    })
    return response.data
  }
}

export default api
