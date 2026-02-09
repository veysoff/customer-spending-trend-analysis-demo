<template>
  <div class="card">
    <div class="card-header">
      <h2 class="text-lg font-semibold text-gray-900">
        Detected Anomalies
        <span class="text-sm font-normal text-gray-500 ml-2">
          {{ anomalies.anomalies.length }} found
        </span>
      </h2>
    </div>
    <div class="card-body">
      <div v-if="anomalies.anomalies.length === 0" class="text-center text-gray-500 py-8">
        No anomalies detected
      </div>

      <div v-else class="space-y-4">
        <div
          v-for="(anomaly, idx) in anomalies.anomalies"
          :key="idx"
          class="border rounded-lg p-4"
          :class="{
            'border-red-300 bg-red-50': anomaly.anomaly_score > 0.8,
            'border-orange-300 bg-orange-50': anomaly.anomaly_score > 0.6 && anomaly.anomaly_score <= 0.8,
            'border-yellow-300 bg-yellow-50': anomaly.anomaly_score <= 0.6
          }"
        >
          <div class="flex justify-between items-start">
            <div class="flex-1">
              <h3 class="font-semibold text-gray-900">
                {{ anomaly.anomaly_type }}
              </h3>
              <p class="text-sm text-gray-600 mt-1">{{ anomaly.date }}</p>
            </div>
            <span
              class="text-right"
              :class="{
                'text-red-600 font-bold': anomaly.anomaly_score > 0.8,
                'text-orange-600 font-bold': anomaly.anomaly_score > 0.6,
                'text-yellow-600 font-bold': anomaly.anomaly_score <= 0.6
              }"
            >
              {{ (anomaly.anomaly_score * 100).toFixed(0) }}%
            </span>
          </div>

          <!-- Top Drivers -->
          <div v-if="anomaly.explanation.top_drivers.length > 0" class="mt-3">
            <p class="text-xs font-medium text-gray-600 uppercase">Contributing Factors:</p>
            <ul class="mt-1 space-y-1">
              <li v-for="(driver, i) in anomaly.explanation.top_drivers" :key="i" class="text-sm text-gray-700">
                • {{ driver }}
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  anomalies: {
    type: Object,
    required: true
  }
})
</script>
