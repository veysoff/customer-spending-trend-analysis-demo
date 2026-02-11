/**
 * frontend/src/utils/formatters.js
 * Formatting utilities for spending visualization and charts
 */

/**
 * Format value as AED currency with clean formatting
 * @param {number} value - Value to format
 * @param {number} decimals - Number of decimal places (default: 0)
 * @returns {string} Formatted currency string
 */
export const formatCurrency = (value, decimals = 0) => {
  if (value === null || value === undefined) return 'N/A'

  const num = parseFloat(value)
  if (isNaN(num)) return 'N/A'

  // Use Intl.NumberFormat for locale-aware formatting
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'AED',
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  }).format(num)
}

/**
 * Format axis values for charts (compact format)
 * @param {number} value - Value to format
 * @returns {string} Formatted string (e.g., "400 AED", "1.5K AED")
 */
export const formatAxisValue = (value) => {
  if (value === null || value === undefined) return 'N/A'

  const num = parseFloat(value)
  if (isNaN(num)) return 'N/A'

  if (num >= 1000) {
    return `${(num / 1000).toFixed(1)}K AED`
  }
  return `${Math.round(num)} AED`
}

/**
 * Format percentage with appropriate decimals
 * @param {number} value - Decimal value (e.g., 0.35 for 35%)
 * @param {number} decimals - Number of decimal places (default: 1)
 * @returns {string} Formatted percentage (e.g., "35.0%")
 */
export const formatPercent = (value, decimals = 1) => {
  if (value === null || value === undefined) return 'N/A'

  const num = parseFloat(value)
  if (isNaN(num)) return 'N/A'

  return `${(num * 100).toFixed(decimals)}%`
}

/**
 * Format date for display
 * @param {string|Date} dateStr - Date string or Date object
 * @param {string} format - Format type: 'short' (MM/DD), 'medium' (MMM DD, YYYY), 'long'
 * @returns {string} Formatted date
 */
export const formatDate = (dateStr, format = 'medium') => {
  if (!dateStr) return 'N/A'

  try {
    const date = typeof dateStr === 'string' ? new Date(dateStr) : dateStr

    if (isNaN(date.getTime())) return 'N/A'

    if (format === 'short') {
      return new Intl.DateTimeFormat('en-US', {
        month: '2-digit',
        day: '2-digit'
      }).format(date)
    }

    if (format === 'long') {
      return new Intl.DateTimeFormat('en-US', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      }).format(date)
    }

    // default: 'medium'
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: '2-digit',
      year: 'numeric'
    }).format(date)
  } catch (e) {
    return 'N/A'
  }
}

/**
 * Format number with thousands separator
 * @param {number} value - Value to format
 * @param {number} decimals - Number of decimal places
 * @returns {string} Formatted number
 */
export const formatNumber = (value, decimals = 0) => {
  if (value === null || value === undefined) return 'N/A'

  const num = parseFloat(value)
  if (isNaN(num)) return 'N/A'

  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  }).format(num)
}

/**
 * Format spending with direction indicator
 * @param {number} value - Spending value
 * @param {number} previousValue - Previous period value for comparison
 * @returns {string} Formatted string with arrow (e.g., "450 AED ↑" for increase)
 */
export const formatSpendingWithTrend = (value, previousValue = null) => {
  const formatted = formatCurrency(value, 0)

  if (previousValue === null) return formatted

  const current = parseFloat(value)
  const previous = parseFloat(previousValue)

  if (current > previous) return `${formatted} ↑`
  if (current < previous) return `${formatted} ↓`
  return `${formatted} →`
}

/**
 * Format anomaly detection results
 * @param {number} actual - Actual spending
 * @param {number} forecast - Forecasted spending
 * @returns {object} Object with isAnomaly, deviation, severity
 */
export const formatAnomalyResult = (actual, forecast) => {
  if (actual === null || forecast === null) {
    return { isAnomaly: false, deviation: 0, severity: 'NORMAL' }
  }

  const deviation = Math.abs(actual - forecast) / Math.max(forecast, 1)

  let severity = 'NORMAL'
  if (deviation > 0.5) severity = 'HIGH'
  else if (deviation > 0.2) severity = 'MEDIUM'

  return {
    isAnomaly: deviation > 0.2,
    deviation: formatPercent(deviation, 1),
    severity
  }
}

/**
 * Get color for trend direction
 * @param {string} direction - "INCREASING", "STABLE", "DECREASING"
 * @returns {string} CSS color class or hex color
 */
export const getTrendColor = (direction) => {
  const colors = {
    'INCREASING': '#10b981',    // Green
    'STABLE': '#6b7280',         // Gray
    'DECREASING': '#ef4444',     // Red
    'INSUFFICIENT_DATA': '#9ca3af'  // Light gray
  }

  return colors[direction] || '#6b7280'
}

/**
 * Get risk level badge color
 * @param {number} riskScore - Risk score (0.0-1.0)
 * @returns {object} Object with color, backgroundColor, label
 */
export const getRiskLevelColor = (riskScore) => {
  const score = parseFloat(riskScore)

  if (score >= 0.8) {
    return {
      color: '#dc2626',
      backgroundColor: '#fee2e2',
      label: 'CRITICAL',
      icon: '🔴'
    }
  }

  if (score >= 0.6) {
    return {
      color: '#ea580c',
      backgroundColor: '#fed7aa',
      label: 'HIGH',
      icon: '🟠'
    }
  }

  if (score >= 0.4) {
    return {
      color: '#d97706',
      backgroundColor: '#fef3c7',
      label: 'MEDIUM',
      icon: '🟡'
    }
  }

  return {
    color: '#10b981',
    backgroundColor: '#d1fae5',
    label: 'LOW',
    icon: '🟢'
  }
}

/**
 * Format confidence interval display
 * @param {number} lower - Lower bound
 * @param {number} upper - Upper bound
 * @returns {string} Formatted CI (e.g., "300-500 AED")
 */
export const formatConfidenceInterval = (lower, upper) => {
  if (lower === null || upper === null) return 'N/A'

  const lowerFormatted = Math.max(0, Math.round(lower))
  const upperFormatted = Math.round(upper)

  return `${lowerFormatted}-${upperFormatted} AED`
}

/**
 * Get seasonality badge text
 * @param {boolean} hasSeasonality - Whether seasonality was detected
 * @param {number} amplitude - Seasonality amplitude (0.0-1.0)
 * @returns {string} Formatted badge text
 */
export const getSeasonalityBadge = (hasSeasonality, amplitude = 0) => {
  if (!hasSeasonality) return 'No Seasonality'

  const percent = (amplitude * 100).toFixed(1)
  if (amplitude > 0.3) return `Strong (${percent}%)`
  if (amplitude > 0.1) return `Moderate (${percent}%)`
  return `Weak (${percent}%)`
}

/**
 * Format trend slope explanation
 * @param {number} slopePerMonth - Slope in AED/month
 * @param {number} confidence - Confidence (0.0-1.0)
 * @returns {string} Human-readable explanation
 */
export const formatTrendExplanation = (slopePerMonth, confidence = 0) => {
  const slope = Math.abs(slopePerMonth)
  const direction = slopePerMonth > 0 ? 'UP' : 'DOWN'
  const confStr = confidence > 0 ? ` (${Math.round(confidence * 100)}% confidence)` : ''

  if (slope > 100) {
    return `Strong ${direction} trend: ${Math.round(slopePerMonth)} AED/month${confStr}`
  } else if (slope > 50) {
    return `Moderate ${direction} trend: ${Math.round(slopePerMonth)} AED/month${confStr}`
  } else if (slope > 0) {
    return `Slight ${direction} trend: ${Math.round(slopePerMonth)} AED/month${confStr}`
  } else {
    return `Stable: minimal trend${confStr}`
  }
}

/**
 * Batch format multiple values
 * @param {array} values - Array of values to format
 * @param {string} type - Format type: 'currency', 'percent', 'number'
 * @returns {array} Formatted values
 */
export const formatBatch = (values, type = 'currency') => {
  const formatter = {
    'currency': (v) => formatCurrency(v, 0),
    'percent': (v) => formatPercent(v, 1),
    'number': (v) => formatNumber(v, 0),
    'date': (v) => formatDate(v, 'short')
  }[type] || ((v) => String(v))

  return (values || []).map((v) => {
    try {
      return formatter(v)
    } catch (e) {
      return 'N/A'
    }
  })
}
