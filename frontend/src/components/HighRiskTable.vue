<template>
  <div class="card mt-8">
    <div class="card-header flex justify-between items-center">
      <h2 class="text-lg font-semibold text-gray-900">
        High-Risk Customers
        <span class="text-sm font-normal text-gray-500 ml-2">
          {{ customers.length }} customers
        </span>
      </h2>
      <div class="text-sm text-gray-600">
        Showing {{ startIndex + 1 }}-{{ endIndex }} of {{ customers.length }}
      </div>
    </div>
    <div class="card-body">
      <div v-if="customers.length === 0" class="text-center text-gray-500 py-8">
        No high-risk customers detected
      </div>

      <div v-else>
        <div class="overflow-x-auto mb-4">
          <table class="w-full text-sm">
            <thead class="border-b border-gray-200">
              <tr>
                <th class="text-left py-3 px-4 font-semibold text-gray-700">Customer ID</th>
                <th class="text-left py-3 px-4 font-semibold text-gray-700">Churn Risk</th>
                <th class="text-left py-3 px-4 font-semibold text-gray-700">Risk Category</th>
                <th class="text-left py-3 px-4 font-semibold text-gray-700">Primary Signal</th>
                <th class="text-left py-3 px-4 font-semibold text-gray-700">Recommended Action</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-200">
              <tr v-for="customer in paginatedCustomers" :key="customer.customer_id" class="hover:bg-gray-50">
                <td class="py-3 px-4">
                  <code class="text-xs bg-gray-100 px-2 py-1 rounded">{{ customer.customer_id }}</code>
                </td>
                <td class="py-3 px-4">
                  <div class="flex items-center gap-2">
                    <div class="w-24 bg-gray-200 rounded-full h-2">
                      <div
                        class="h-2 rounded-full"
                        :class="getRiskColor(customer.churn_risk)"
                        :style="{ width: (customer.churn_risk * 100) + '%' }"
                      ></div>
                    </div>
                    <span class="font-bold text-sm" :class="getRiskTextColor(customer.churn_risk)">
                      {{ (customer.churn_risk * 100).toFixed(0) }}%
                    </span>
                  </div>
                </td>
                <td class="py-3 px-4">
                  <span :class="'badge ' + getBadgeClass(customer.risk_category)">
                    {{ customer.risk_category }}
                  </span>
                </td>
                <td class="py-3 px-4 text-gray-600">
                  {{ customer.primary_signal }}
                </td>
                <td class="py-3 px-4 text-gray-600">
                  {{ customer.recommended_action }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Pagination Controls -->
        <div class="flex items-center justify-between border-t border-gray-200 pt-4">
          <button
            @click="previousPage"
            :disabled="currentPage === 1"
            class="px-3 py-2 rounded border border-gray-300 text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
          >
            ← Previous
          </button>

          <div class="flex items-center gap-2">
            <span class="text-sm text-gray-600">Page {{ currentPage }} of {{ totalPages }}</span>
            <div class="flex gap-1">
              <button
                v-for="page in visiblePages"
                :key="page"
                @click="goToPage(page)"
                :class="[
                  'px-2 py-1 rounded text-sm font-medium',
                  page === currentPage
                    ? 'bg-blue-600 text-white'
                    : 'border border-gray-300 text-gray-700 hover:bg-gray-50'
                ]"
              >
                {{ page }}
              </button>
            </div>
          </div>

          <button
            @click="nextPage"
            :disabled="currentPage === totalPages"
            class="px-3 py-2 rounded border border-gray-300 text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
          >
            Next →
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  customers: {
    type: Array,
    required: true
  }
})

// Pagination state
const currentPage = ref(1)
const pageSize = ref(10)

// Pagination computed properties
const totalPages = computed(() => Math.ceil(props.customers.length / pageSize.value))

const startIndex = computed(() => (currentPage.value - 1) * pageSize.value)
const endIndex = computed(() => Math.min(currentPage.value * pageSize.value, props.customers.length))

const paginatedCustomers = computed(() => props.customers.slice(startIndex.value, endIndex.value))

const visiblePages = computed(() => {
  const pages = []
  const maxVisible = 5
  let start = Math.max(1, currentPage.value - 2)
  let end = Math.min(totalPages.value, start + maxVisible - 1)
  if (end - start < maxVisible - 1) start = Math.max(1, end - maxVisible + 1)
  for (let i = start; i <= end; i++) pages.push(i)
  return pages
})

// Pagination methods
const nextPage = () => {
  if (currentPage.value < totalPages.value) currentPage.value++
}

const previousPage = () => {
  if (currentPage.value > 1) currentPage.value--
}

const goToPage = (page) => {
  currentPage.value = page
}

// Risk color helpers
const getRiskColor = (risk) => {
  if (risk >= 0.8) return 'bg-red-600'
  if (risk >= 0.6) return 'bg-orange-500'
  if (risk >= 0.4) return 'bg-yellow-500'
  return 'bg-green-500'
}

const getRiskTextColor = (risk) => {
  if (risk >= 0.8) return 'text-red-600'
  if (risk >= 0.6) return 'text-orange-600'
  if (risk >= 0.4) return 'text-yellow-600'
  return 'text-green-600'
}

const getBadgeClass = (category) => {
  if (category === 'CRITICAL') return 'badge-critical'
  if (category === 'HIGH') return 'badge-high'
  if (category === 'MEDIUM') return 'badge-medium'
  return 'badge-low'
}
</script>
