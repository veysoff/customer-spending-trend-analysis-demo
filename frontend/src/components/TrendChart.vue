<template>
  <div class="card">
    <div class="card-header">
      <h2 class="text-lg font-semibold text-gray-900">Spending Trend & Forecast</h2>
    </div>
    <div class="card-body">
      <div id="trend-chart" style="min-height: 300px"></div>

      <div class="mt-6 grid grid-cols-2 gap-4">
        <div>
          <h3 class="text-sm font-medium text-gray-500">Trend Slope</h3>
          <p class="text-2xl font-bold mt-1" :class="trendClass">
            {{ trends.trend_slope.toFixed(2) }} /month
          </p>
        </div>
        <div>
          <h3 class="text-sm font-medium text-gray-500">Seasonality</h3>
          <p class="text-sm text-gray-600 mt-1">
            {{ trends.seasonality_pattern }}<br>
            Amplitude: {{ (trends.seasonality_amplitude * 100).toFixed(0) }}%
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import ApexCharts from 'apexcharts'

const props = defineProps({
  trends: {
    type: Object,
    required: true
  }
})

const chartInstance = ref(null)

const trendClass = computed(() => {
  if (props.trends.trend_slope > 50) return 'text-green-600'
  if (props.trends.trend_slope < -50) return 'text-red-600'
  return 'text-gray-600'
})

const renderChart = () => {
  if (!props.trends || !props.trends.trend_data) return

  const dates = props.trends.trend_data.map(d => d.date)
  const actuals = props.trends.trend_data.map(d => d.actual || null)
  const forecasts = props.trends.trend_data.map(d => d.forecast)
  const lowerBounds = props.trends.trend_data.map(d => d.lower_bound)
  const upperBounds = props.trends.trend_data.map(d => d.upper_bound)

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
      width: [2, 1, 1]
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
        text: 'Spending (AED)'
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
        formatter: (val) => val ? 'AED ' + val.toFixed(2) : 'N/A'
      }
    }
  }

  const series = [
    {
      name: 'Actual Spending',
      data: actuals,
      color: '#0284c7'
    },
    {
      name: 'Forecast',
      data: forecasts,
      color: '#f59e0b'
    },
    {
      name: 'Confidence Interval',
      data: lowerBounds.map((l, i) => ({
        x: dates[i],
        y: [(l + upperBounds[i]) / 2, l, upperBounds[i]]
      })),
      color: '#e5e7eb'
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
