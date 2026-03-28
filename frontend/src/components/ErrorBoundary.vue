<template>
  <div v-if="hasError" class="p-6 bg-red-50 border border-red-200 rounded-lg">
    <div class="flex items-start gap-4">
      <span class="text-3xl">⚠️</span>
      <div class="flex-1">
        <h3 class="text-lg font-semibold text-red-900 mb-2">{{ title }}</h3>
        <p class="text-red-800 mb-4">{{ errorMessage }}</p>
        <div class="flex gap-2">
          <button
            @click="retry"
            class="px-4 py-2 bg-red-600 text-white rounded-lg font-semibold hover:bg-red-700 transition-colors"
          >
            🔄 Retry
          </button>
          <button
            @click="dismiss"
            class="px-4 py-2 bg-red-200 text-red-900 rounded-lg font-semibold hover:bg-red-300 transition-colors"
          >
            Dismiss
          </button>
        </div>
      </div>
    </div>
  </div>
  <div v-else>
    <slot></slot>
  </div>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  title: {
    type: String,
    default: 'Something went wrong'
  },
  errorMessage: {
    type: String,
    default: 'Please try again or contact support'
  }
})

const emit = defineEmits(['retry', 'dismiss'])

const hasError = ref(false)

function setError(show = true) {
  hasError.value = show
}

function retry() {
  hasError.value = false
  emit('retry')
}

function dismiss() {
  hasError.value = false
  emit('dismiss')
}

defineExpose({ setError })
</script>
