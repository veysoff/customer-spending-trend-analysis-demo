<template>
  <div class="card">
    <div class="card-header">
      <h2 class="text-lg font-semibold text-gray-900">Spending Trend & Forecast</h2>
    </div>
    <div class="card-body">
      <div id="trend-chart" style="min-height: 300px"></div>

      <div class="mt-6 grid grid-cols-2 gap-4">
        <div>
          <h3 class="text-sm font-medium text-gray-500">Weekly Spending Trend</h3>
          <p class="text-2xl font-bold mt-1" :class="trendClass">
            {{ (trends.trend_slope_per_month || trends.trend_slope || 0) > 0 ? '+' : '' }}{{ (trends.trend_slope_per_month || trends.trend_slope || 0).toFixed(0) }}
          </p>
          <p class="text-xs text-gray-500 mt-1">AED/month change</p>
        </div>
        <div>
          <h3 class="text-sm font-medium text-gray-500">Seasonality</h3>
          <p class="text-sm text-gray-600 mt-1">
            {{ trends.has_seasonality ? 'Detected' : 'None' }}<br>
            Amplitude: {{ (trends.seasonality_amplitude * 100).toFixed(1) }}%
          </p>
          <p class="text-xs text-gray-500 mt-2">
            Data span: {{ trends.data_span_days || 0 }} days
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import ApexCharts from 'apexcharts'
import { formatAxisValue, formatCurrency } from '@/utils/formatters'  // FIX #5: Formatting
import { detectAnomalies, createAnomalyMarkers } from '@/utils/anomalyDetection'  // FIX #5: Anomaly highlighting

const props = defineProps({
  trends: {
    type: Object,
    required: true
  }
})

const chartInstance = ref(null)

const trendClass = computed(() => {
  const slope = props.trends.trend_slope_per_month ?? props.trends.trend_slope ?? 0
  if (slope > 100) return 'text-green-600'
  if (slope < -100) return 'text-red-600'
  return 'text-gray-600'
})

const renderChart = () => {
  if (!props.trends || !props.trends.trend_data) return

  // Ensure dates are strings (ApexCharts requires string format)
  const dates = props.trends.trend_data.map(d => {
    const dateStr = d.date ? String(d.date).trim() : ''
    return dateStr
  })

  const actuals = props.trends.trend_data.map(d => d.actual ?? null)

  // Find the boundary index where historical data ends and forecast begins
  // Look for the LAST actual value, not the first null (to handle gaps in history correctly)
  let boundaryIdx = -1
  for (let i = props.trends.trend_data.length - 1; i >= 0; i--) {
    if (props.trends.trend_data[i].actual !== null && props.trends.trend_data[i].actual !== undefined) {
      boundaryIdx = i + 1  // forecast starts after last actual
      break
    }
  }
  // If no actual values found at all, use first null
  if (boundaryIdx === -1) {
    boundaryIdx = props.trends.trend_data.findIndex(d => d.actual === null || d.actual === undefined)
  }

  // Forecast line: null during historical period, yhat only from boundary onwards.
  // Include the last actual point as the anchor so the line connects smoothly.
  // This prevents the flat Prophet baseline from cluttering the historical view.
  const lastActualVal = boundaryIdx > 0 ? (actuals[boundaryIdx - 1] ?? null) : null
  const forecasts = props.trends.trend_data.map((d, i) => {
    if (boundaryIdx === -1) return null        // no forecast data at all
    if (i < boundaryIdx - 1) return null       // hide forecast during history (except last actual)
    if (i === boundaryIdx - 1) return lastActualVal  // anchor: last actual value
    return d.forecast ?? null
  })

  // Confidence bands: same approach — only show in forecast window
  const lowerBounds = props.trends.trend_data.map((d, i) => {
    if (boundaryIdx === -1 || i < boundaryIdx) return null
    return d.lower_bound ?? null
  })
  const upperBounds = props.trends.trend_data.map((d, i) => {
    if (boundaryIdx === -1 || i < boundaryIdx) return null
    return d.upper_bound ?? null
  })

  // FIX #5: Detect anomalies
  const anomalies = detectAnomalies(actuals, forecasts)

  const options = {
    chart: {
      type: 'area',
      height: 350,
      toolbar: {
        show: true
      }
    },
    dataLabels: {
      enabled: false
    },
    stroke: {
      curve: 'smooth',
      width: 2
    },
    fill: {
      type: 'gradient',
      gradient: {
        opacityFrom: 0.45,
        opacityTo: 0.05
      }
    },
    xaxis: {
      categories: dates,
      type: 'datetime'
    },
    yaxis: {
      title: {
        text: 'Spending (AED/week)'
      },
      labels: {
        formatter: (val) => formatAxisValue(val)
      }
    },
    legend: {
      position: 'top',
      horizontalAlign: 'right'
    },
    tooltip: {
      x: {
        format: 'MMM dd, yyyy'
      },
      y: {
        formatter: (val) => val ? formatCurrency(val, 2) : 'N/A'
      }
    },
    annotations: {
      points: createAnomalyMarkers(dates, actuals, anomalies)
    }
  }

  const series = [
    {
      name: 'Actual Spending',
      data: actuals.map((val, i) => ({
        x: dates[i],
        y: val,
        fillColor: anomalies[i] ? '#dc2626' : '#0284c7'
      })),
      color: '#0284c7'
    },
    {
      name: 'Forecast',
      data: forecasts.map((val, i) => ({
        x: dates[i],
        y: val
      })),
      color: '#f59e0b'
    },
    {
      name: 'Upper Bound (95% CI)',
      data: upperBounds.map((val, i) => ({
        x: dates[i],
        y: val
      })),
      color: '#e5e7eb',
      type: 'line'
    },
    {
      name: 'Lower Bound (95% CI)',
      data: lowerBounds.map((val, i) => ({
        x: dates[i],
        y: val
      })),
      color: '#e5e7eb',
      type: 'line'
    }
  ]

  const chartElement = document.getElementById('trend-chart')
  if (!chartElement) return

  // Destroy old chart if exists
  if (chartInstance.value) {
    chartInstance.value.destroy()
  }

  chartInstance.value = new ApexCharts(chartElement, { ...options, series })
  chartInstance.value.render()
}

onMounted(renderChart)

// Watch for prop changes and re-render chart
watch(() => props.trends, renderChart, { deep: true })
</script>
