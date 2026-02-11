<template>
  <div class="ai-insights-panel bg-white rounded-lg shadow-md p-6 border-l-4" :class="borderColorClass">
    <!-- Header -->
    <div v-if="summary" class="flex items-center justify-between mb-6">
      <div class="flex items-center gap-3">
        <span class="text-3xl">{{ summary.summary_icon }}</span>
        <div>
          <h2 class="text-2xl font-bold text-gray-900">AI Insights</h2>
          <p class="text-sm text-gray-600">Professional Analysis & Recommendations</p>
        </div>
      </div>
      <div class="text-right">
        <div class="text-3xl font-bold" :class="summaryColorClass">
          {{ summary.summary }}
        </div>
        <p class="text-xs text-gray-500 mt-1">Confidence: {{ (summary.confidence_score * 100).toFixed(0) }}%</p>
      </div>
    </div>

    <div v-if="loading" class="text-center py-8">
      <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      <p class="text-gray-600 mt-2">Generating insights...</p>
    </div>

    <div v-else-if="error" class="bg-red-50 border border-red-200 rounded-md p-4 mb-6">
      <p class="text-red-800 text-sm">{{ error }}</p>
    </div>

    <div v-else-if="summary">
      <!-- Key Findings Section -->
      <section class="mb-8">
        <h3 class="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <span>🔍</span> Key Findings
        </h3>
        <div class="space-y-3">
          <div
            v-for="(finding, index) in summary.key_findings"
            :key="index"
            class="flex gap-3 p-3 bg-gray-50 rounded-md"
          >
            <span class="text-blue-600 font-bold flex-shrink-0">{{ index + 1 }}.</span>
            <p class="text-gray-700 text-sm leading-relaxed">{{ finding }}</p>
          </div>
        </div>
      </section>

      <!-- Business Advice Section -->
      <section class="mb-8">
        <h3 class="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <span>🎯</span> Business Advice
        </h3>
        <div class="bg-gradient-to-r from-blue-50 to-indigo-50 border-l-4 border-blue-500 p-4 rounded-r-md">
          <p class="text-gray-800 text-sm leading-relaxed whitespace-pre-line">
            {{ summary.business_advice }}
          </p>
        </div>
      </section>

      <!-- Technical Evidence (Collapsible) -->
      <section>
        <button
          @click="showEvidence = !showEvidence"
          class="flex items-center gap-2 text-sm font-semibold text-gray-700 hover:text-gray-900 transition-colors mb-3"
        >
          <span v-if="!showEvidence">▶</span>
          <span v-else>▼</span>
          📊 Technical Evidence (Advanced)
        </button>

        <div v-if="showEvidence && summary.technical_evidence" class="bg-gray-50 border border-gray-200 rounded-md p-4 text-xs font-mono">
          <!-- Churn Probability -->
          <div class="mb-4 pb-4 border-b border-gray-200">
            <p class="text-gray-600 mb-2"><span class="font-bold">Churn Probability:</span> {{ (summary.technical_evidence.churn_probability * 100).toFixed(1) }}%</p>
            <div class="w-full bg-gray-200 rounded-full h-2">
              <div
                class="bg-red-500 h-2 rounded-full transition-all"
                :style="{ width: (summary.technical_evidence.churn_probability * 100) + '%' }"
              ></div>
            </div>
          </div>

          <!-- Top SHAP Factors with Explanations -->
          <div v-if="summary.technical_evidence && summary.technical_evidence.top_shap_factors && Object.keys(summary.technical_evidence.top_shap_factors).length > 0" class="mb-4 pb-4 border-b border-gray-200">
            <p class="font-bold text-gray-900 mb-3">⚡ Key Risk Drivers (SHAP Analysis):</p>
            <div class="space-y-3">
              <div
                v-for="[factor, value] in Object.entries(summary.technical_evidence.top_shap_factors).slice(0, 5)"
                :key="factor"
                class="bg-gray-50 p-3 rounded-md border-l-4"
                :class="{ 'border-red-500': value > 0, 'border-green-500': value < 0, 'border-gray-300': value === 0 }"
              >
                <div class="flex justify-between items-start mb-2">
                  <span class="font-semibold text-gray-900">{{ formatFactorName(factor) }}</span>
                  <span
                    class="font-bold text-sm px-2 py-1 rounded"
                    :class="{
                      'text-red-700 bg-red-100': value > 0,
                      'text-green-700 bg-green-100': value < 0,
                      'text-gray-700 bg-gray-100': value === 0
                    }"
                  >
                    {{ formatShapValue(value) }}
                  </span>
                </div>
                <p class="text-xs text-gray-600 leading-relaxed">
                  {{ getShapExplanation(factor, value) }}
                </p>
              </div>
            </div>
          </div>
          <div v-else class="mb-4 pb-4 border-b border-gray-200 text-xs text-gray-500">
            <p>SHAP analysis not available for this customer.</p>
          </div>

          <!-- Key Metrics -->
          <div v-if="summary.technical_evidence && summary.technical_evidence.key_metrics && Object.keys(summary.technical_evidence.key_metrics).length > 0" class="pb-4 border-b border-gray-200">
            <p class="font-bold text-gray-900 mb-2">Key Metrics:</p>
            <div class="space-y-1 text-gray-700">
              <div
                v-for="(value, metric) in summary.technical_evidence.key_metrics"
                :key="metric"
                class="flex justify-between"
              >
                <span>{{ formatMetricName(metric) }}:</span>
                <span class="font-mono">{{ formatMetricValue(metric, value) }}</span>
              </div>
            </div>
          </div>

          <!-- Status Notes -->
          <div class="text-gray-600 space-y-1">
            <p v-if="summary.technical_evidence.dormancy_status">
              💤 {{ summary.technical_evidence.dormancy_status }}
            </p>
            <p v-if="summary.technical_evidence.trend_status">
              📉 {{ summary.technical_evidence.trend_status }}
            </p>
          </div>

          <!-- Cache Info -->
          <div class="mt-4 text-gray-500 text-xs">
            <p>Model: {{ summary.technical_evidence.model }}</p>
            <p>Generated: {{ new Date(summary.generated_at).toLocaleString() }}</p>
            <p v-if="summary.cached">✓ Cached result (expires in 7 days)</p>
          </div>
        </div>
      </section>
    </div>

    <div v-else class="text-center py-8 text-gray-500">
      <p>Select a customer to view AI insights</p>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch } from 'vue'
import api from '../services/api'

export default {
  name: 'AIInsightsPanel',
  props: {
    customerId: {
      type: String,
      required: true
    }
  },
  setup(props) {
    const summary = ref(null)
    const loading = ref(false)
    const error = ref(null)
    const showEvidence = ref(false)

    // Computed properties
    const summaryColorClass = computed(() => {
      if (!summary.value) return 'text-gray-600'
      const s = summary.value.summary
      if (s === 'CRITICAL') return 'text-red-600'
      if (s === 'WARNING') return 'text-orange-600'
      if (s === 'MEDIUM') return 'text-yellow-600'
      return 'text-green-600'
    })

    const borderColorClass = computed(() => {
      if (!summary.value) return 'border-gray-300'
      const s = summary.value.summary
      if (s === 'CRITICAL') return 'border-red-500'
      if (s === 'WARNING') return 'border-orange-500'
      if (s === 'MEDIUM') return 'border-yellow-500'
      return 'border-green-500'
    })

    // Methods
    const fetchInsights = async () => {
      loading.value = true
      error.value = null

      try {
        const response = await api.get(`/api/customers/${props.customerId}/insights`)
        summary.value = response.data
        showEvidence.value = false // Close evidence by default
      } catch (err) {
        console.error('Error fetching AI insights:', err)
        error.value = err.response?.data?.detail || 'Failed to generate insights'
      } finally {
        loading.value = false
      }
    }

    const formatMetricName = (metric) => {
      if (!metric) return ''
      return String(metric)
        .replace(/_/g, ' ')
        .split(' ')
        .map(w => w.charAt(0).toUpperCase() + w.slice(1))
        .join(' ')
    }

    const formatMetricValue = (metric, value) => {
      // Safety check
      if (value === null || value === undefined || isNaN(value)) {
        return 'N/A'
      }

      const metricStr = String(metric).toLowerCase()

      if (metricStr.includes('ratio') || metricStr.includes('score')) {
        return (value * 100).toFixed(1) + '%'
      }
      if (metricStr.includes('days') || metricStr.includes('months')) {
        return Math.round(value) + 'd'
      }
      if (metricStr.includes('slope')) {
        return (value > 0 ? '+' : '') + value.toFixed(0) + ' AED/mo'
      }
      return value.toFixed(2)
    }

    const formatShapValue = (value) => {
      // Handle NaN, null, undefined
      if (value === null || value === undefined || isNaN(value)) {
        return 'N/A'
      }
      // Convert to percentage
      const percentage = value * 100
      if (isNaN(percentage)) {
        return 'N/A'
      }
      // Format with sign and percentage
      return (value > 0 ? '+' : '') + percentage.toFixed(1) + '%'
    }

    const formatFactorName = (factor) => {
      if (!factor) return 'Unknown Factor'
      try {
        return String(factor)
          .replace(/_/g, ' ')
          .split(' ')
          .map(w => w.charAt(0).toUpperCase() + w.slice(1))
          .join(' ')
      } catch (e) {
        return 'Unknown Factor'
      }
    }

    const getShapExplanation = (factor, value) => {
      // Safety checks
      if (!factor || typeof factor !== 'string') {
        return 'Unable to generate explanation for this factor.'
      }
      if (value === null || value === undefined || isNaN(value)) {
        return 'Value data unavailable.'
      }

      const explanations = {
        'dormancy_days': {
          positive: `Customer inactive for ${Math.abs(value * 100).toFixed(0)}% contribution to churn. Long periods without transactions indicate potential abandonment.`,
          negative: 'Recent activity reduces churn risk. Customer engagement is protective.',
          zero: 'Activity level is neutral - not a major churn indicator.'
        },
        'trend_slope': {
          positive: 'Spending increases reduce churn. Growing value suggests loyalty.',
          negative: `Declining spending (${Math.abs(value * 100).toFixed(0)}% factor) is a strong churn signal. Budget cuts or switching detected.`,
          zero: 'Stable spending patterns - neutral churn indicator.'
        },
        'inactive_months_count': {
          positive: `${Math.abs(value * 100).toFixed(0)}% contribution: Multiple inactive months. Strong predictor of churn.`,
          negative: 'Active every month. Consistent engagement protects against churn.',
          zero: 'Engagement consistency is neutral.'
        },
        'payment_delay_score': {
          positive: `Late payments (${Math.abs(value * 100).toFixed(0)}% factor) signal financial stress and churn risk.`,
          negative: 'Perfect payment history. Reliable customers have lower churn.',
          zero: 'Payment behavior is neutral.'
        },
        'support_sentiment_score': {
          positive: 'High support issues increase churn. Dissatisfied customers leave.',
          negative: `Positive support experience (${Math.abs(value * 100).toFixed(0)}% protective) strongly reduces churn.`,
          zero: 'Support interactions are neutral.'
        },
        'campaign_engagement_score': {
          positive: 'High engagement indicates retention. Active customers are less likely to churn.',
          negative: `Low engagement (${Math.abs(value * 100).toFixed(0)}% factor) means customer is disconnecting. High churn risk.`,
          zero: 'Campaign engagement is neutral.'
        },
        'utilization_ratio': {
          positive: 'High credit utilization. Customer depends on account.',
          negative: 'Low utilization suggests customer not using account. Churn risk.',
          zero: 'Credit usage is neutral.'
        },
        'spending_volatility': {
          positive: 'High transaction variability. Customer shopping patterns changing.',
          negative: 'Stable spending protects against churn.',
          zero: 'Spending patterns are consistent.'
        },
        'account_age_months': {
          positive: 'Long-standing customer. Loyalty reduces churn.',
          negative: 'New account. Early-stage customers have higher churn.',
          zero: 'Account age is neutral.'
        },
        'balance_to_spending_ratio': {
          positive: 'High balance relative to spending. May indicate dormancy.',
          negative: 'Low balance suggests active account use.',
          zero: 'Balance ratio is neutral.'
        }
      }

      const factor_key = String(factor).toLowerCase()
      const explanation = explanations[factor_key]

      if (!explanation) {
        if (value > 0) {
          return `This factor contributes ${(value * 100).toFixed(1)}% toward increased churn risk.`
        } else if (value < 0) {
          return `This factor contributes ${Math.abs(value * 100).toFixed(1)}% toward reducing churn risk.`
        } else {
          return 'This factor has minimal impact on churn prediction.'
        }
      }

      if (value > 0.01) {
        return explanation.positive
      } else if (value < -0.01) {
        return explanation.negative
      } else {
        return explanation.zero
      }
    }

    // Watchers
    watch(() => props.customerId, () => {
      if (props.customerId) {
        fetchInsights()
      }
    }, { immediate: true })

    return {
      summary,
      loading,
      error,
      showEvidence,
      summaryColorClass,
      borderColorClass,
      fetchInsights,
      formatMetricName,
      formatMetricValue,
      formatShapValue,
      formatFactorName,
      getShapExplanation
    }
  }
}
</script>

<style scoped>
.ai-insights-panel {
  transition: all 0.3s ease-in-out;
}

.ai-insights-panel:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.animate-spin {
  animation: spin 1s linear infinite;
}
</style>
