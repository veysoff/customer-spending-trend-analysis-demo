/**
 * frontend/src/utils/anomalyDetection.js
 * Client-side anomaly detection for spending spikes
 */

/**
 * Detect anomalies: transactions that deviate significantly from forecast
 * Uses statistical approach: anomaly = |actual - forecast| > 2σ
 *
 * @param {array} actuals - Array of actual spending values
 * @param {array} forecasts - Array of forecasted spending values
 * @returns {array} Boolean array where true = anomaly
 */
export const detectAnomalies = (actuals, forecasts) => {
  // Validate inputs
  if (!actuals || !forecasts || actuals.length === 0) return []
  if (actuals.length !== forecasts.length) return []

  // Calculate deviations (actual - forecast)
  const deviations = actuals.map((actual, i) => {
    if (actual === null || actual === undefined) return null
    if (forecasts[i] === null || forecasts[i] === undefined) return null

    return Math.abs(actual - forecasts[i])
  }).filter(d => d !== null)

  if (deviations.length < 3) {
    // Not enough data to detect anomalies statistically
    return actuals.map(() => false)
  }

  // Calculate mean and std of deviations
  const mean = deviations.reduce((a, b) => a + b, 0) / deviations.length
  const variance = deviations.reduce((a, b) => a + (b - mean) ** 2, 0) / deviations.length
  const std = Math.sqrt(variance)

  // Threshold: mean + 2σ (captures ~95% of normal variation)
  const threshold = mean + 2 * std

  // Mark each point as anomaly if deviation exceeds threshold
  return actuals.map((actual, i) => {
    if (actual === null || actual === undefined) return false
    if (forecasts[i] === null || forecasts[i] === undefined) return false

    const deviation = Math.abs(actual - forecasts[i])
    return deviation > threshold
  })
}

/**
 * Calculate anomaly score for individual point
 * Z-score approach: how many standard deviations from forecast?
 *
 * @param {number} actual - Actual spending
 * @param {number} forecast - Forecasted spending
 * @param {number} std - Standard deviation of deviations
 * @returns {number} Anomaly score (0.0-1.0, 1.0 = extreme anomaly)
 */
export const calculateAnomalyScore = (actual, forecast, std) => {
  if (std === 0 || std === null) return 0
  if (actual === null || forecast === null) return 0

  const zscore = Math.abs(actual - forecast) / std

  // Normalize: 3σ = 1.0 (very anomalous), 0σ = 0.0 (normal)
  return Math.min(1.0, zscore / 3)
}

/**
 * Classify anomaly severity
 * @param {number} score - Anomaly score (0.0-1.0)
 * @returns {object} Object with severity level, color, label
 */
export const getAnomalySeverity = (score) => {
  const s = parseFloat(score) || 0

  if (s >= 0.8) {
    return {
      level: 'CRITICAL',
      color: '#dc2626',  // Red
      icon: '🔴',
      description: 'Extreme anomaly'
    }
  }

  if (s >= 0.6) {
    return {
      level: 'HIGH',
      color: '#ea580c',  // Orange
      icon: '🟠',
      description: 'Major anomaly'
    }
  }

  if (s >= 0.4) {
    return {
      level: 'MEDIUM',
      color: '#d97706',  // Amber
      icon: '🟡',
      description: 'Moderate anomaly'
    }
  }

  if (s > 0) {
    return {
      level: 'LOW',
      color: '#eab308',  // Yellow
      icon: '⚠️',
      description: 'Minor anomaly'
    }
  }

  return {
    level: 'NORMAL',
    color: '#10b981',  // Green
    icon: '✓',
    description: 'Normal spending'
  }
}

/**
 * Detect spending spikes (high-value transactions)
 * Uses: mean + 2*std approach
 *
 * @param {array} amounts - Array of spending amounts
 * @returns {array} Boolean array where true = spike detected
 */
export const detectSpikes = (amounts) => {
  if (!amounts || amounts.length === 0) return []

  const validAmounts = amounts.filter(a => a !== null && a !== undefined && !isNaN(a))

  if (validAmounts.length < 3) return amounts.map(() => false)

  const mean = validAmounts.reduce((a, b) => a + b, 0) / validAmounts.length
  const variance = validAmounts.reduce((a, b) => a + (b - mean) ** 2, 0) / validAmounts.length
  const std = Math.sqrt(variance)

  // Threshold: mean + 2*std
  const threshold = mean + 2 * std

  return amounts.map(amount => {
    if (amount === null || amount === undefined) return false
    return amount > threshold
  })
}

/**
 * Detect spending gaps (unusually low activity)
 * @param {array} amounts - Array of spending amounts
 * @param {number} threshold - Percentage threshold (0.0-1.0, default 0.5 = 50% below mean)
 * @returns {array} Boolean array where true = gap detected
 */
export const detectGaps = (amounts, threshold = 0.5) => {
  if (!amounts || amounts.length === 0) return []

  const validAmounts = amounts.filter(a => a !== null && a !== undefined && !isNaN(a) && a > 0)

  if (validAmounts.length < 3) return amounts.map(() => false)

  const mean = validAmounts.reduce((a, b) => a + b, 0) / validAmounts.length
  const gapThreshold = mean * (1 - threshold)  // e.g., mean * 0.5

  return amounts.map(amount => {
    if (amount === null || amount === undefined || amount === 0) return false
    return amount < gapThreshold && amount > 0
  })
}

/**
 * Get statistical summary of anomalies
 * @param {array} actuals - Actual spending array
 * @param {array} forecasts - Forecasted spending array
 * @returns {object} Summary with count, percentage, mean, etc.
 */
export const getAnomalySummary = (actuals, forecasts) => {
  if (!actuals || !forecasts || actuals.length === 0) {
    return {
      totalPoints: 0,
      anomalies: 0,
      anomalyPercent: 0,
      meanDeviation: 0,
      maxDeviation: 0
    }
  }

  const anomalies = detectAnomalies(actuals, forecasts)
  const anomalyCount = anomalies.filter(a => a).length

  // Calculate deviations
  const deviations = actuals.map((actual, i) => {
    if (actual === null || forecasts[i] === null) return null
    return Math.abs(actual - forecasts[i])
  }).filter(d => d !== null)

  const meanDeviation = deviations.length > 0
    ? deviations.reduce((a, b) => a + b, 0) / deviations.length
    : 0

  const maxDeviation = deviations.length > 0
    ? Math.max(...deviations)
    : 0

  return {
    totalPoints: actuals.length,
    anomalies: anomalyCount,
    anomalyPercent: (anomalyCount / actuals.length) * 100,
    meanDeviation: Math.round(meanDeviation),
    maxDeviation: Math.round(maxDeviation),
    recommendation: getAnomalyRecommendation(anomalyCount / actuals.length)
  }
}

/**
 * Get business recommendation based on anomaly rate
 * @param {number} anomalyRate - Percentage of anomalies (0.0-1.0)
 * @returns {string} Recommendation text
 */
export const getAnomalyRecommendation = (anomalyRate) => {
  if (anomalyRate > 0.3) {
    return '⚠️ High anomaly rate: Spending highly erratic (investigate patterns)'
  } else if (anomalyRate > 0.1) {
    return '🟡 Moderate anomalies: Some unusual spending (monitor closely)'
  } else if (anomalyRate > 0.05) {
    return '✓ Low anomaly rate: Mostly normal spending (occasional spikes expected)'
  } else {
    return '✅ Very stable: Predictable spending pattern'
  }
}

/**
 * Create ApexCharts annotation markers for anomalies
 * @param {array} dates - Array of date strings
 * @param {array} actuals - Array of actual values
 * @param {array} anomalies - Boolean array from detectAnomalies()
 * @returns {array} ApexCharts points array
 */
export const createAnomalyMarkers = (dates, actuals, anomalies) => {
  if (!dates || !actuals || !anomalies || dates.length === 0) return []

  const markers = []

  dates.forEach((date, i) => {
    // Ensure date is a valid string (ApexCharts needs string format)
    if (!date || typeof date !== 'string') return
    if (anomalies[i] && actuals[i] !== null && actuals[i] !== undefined) {
      markers.push({
        x: date,  // Ensure this is a string
        y: actuals[i],
        marker: {
          size: 8,
          fillColor: '#dc2626',  // Red
          strokeColor: '#7f1d1d',
          radius: 2
        },
        label: {
          borderColor: '#dc2626',
          offsetY: 0,
          style: {
            color: '#fff',
            background: '#dc2626'
          },
          text: '⚠️ Anomaly'
        }
      })
    }
  })

  return markers
}

/**
 * Filter data to show only anomalies
 * @param {array} dates - Date array
 * @param {array} actuals - Actual values
 * @param {array} forecasts - Forecast values
 * @param {array} anomalies - Boolean array
 * @returns {object} Object with filtered dates, actuals, forecasts, scores
 */
export const filterToAnomalies = (dates, actuals, forecasts, anomalies) => {
  const filtered = {
    dates: [],
    actuals: [],
    forecasts: [],
    deviations: [],
    scores: []
  }

  if (!dates || !actuals || !anomalies) return filtered

  dates.forEach((date, i) => {
    if (anomalies[i]) {
      const dev = Math.abs(actuals[i] - forecasts[i])
      const score = calculateAnomalyScore(actuals[i], forecasts[i], Math.sqrt(dev))

      filtered.dates.push(date)
      filtered.actuals.push(actuals[i])
      filtered.forecasts.push(forecasts[i])
      filtered.deviations.push(dev)
      filtered.scores.push(score)
    }
  })

  return filtered
}

/**
 * Export anomaly data for analysis/reporting
 * @param {object} trendData - Trend data with actuals, forecasts, etc.
 * @returns {string} CSV-formatted string
 */
export const exportAnomaliesAsCSV = (trendData) => {
  if (!trendData || !trendData.trend_data) return ''

  const anomalies = detectAnomalies(
    trendData.trend_data.map(d => d.actual),
    trendData.trend_data.map(d => d.forecast)
  )

  const anomalyRows = trendData.trend_data
    .map((d, i) => ({ ...d, isAnomaly: anomalies[i] }))
    .filter(row => row.isAnomaly)

  if (anomalyRows.length === 0) return 'No anomalies detected'

  // CSV header
  const header = 'Date,Actual,Forecast,Deviation,Lower Bound,Upper Bound\n'

  // CSV rows
  const rows = anomalyRows.map(row => {
    const deviation = Math.abs(row.actual - row.forecast).toFixed(2)
    return `${row.date},${row.actual.toFixed(2)},${row.forecast.toFixed(2)},${deviation},${row.lower_bound.toFixed(2)},${row.upper_bound.toFixed(2)}`
  }).join('\n')

  return header + rows
}
