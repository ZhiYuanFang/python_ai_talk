<template>
  <div class="card">
    <div class="card-header">
      <h3 class="card-title">知识库统计信息</h3>
      <button @click="loadStats" class="btn btn-sm btn-primary float-end">刷新</button>
    </div>
    <div class="card-body">
      <div v-if="loading" class="text-center py-4">
        <div class="spinner-border text-primary" role="status"></div>
        <p class="mt-2">加载中...</p>
      </div>

      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div class="card bg-primary text-white">
          <div class="card-body text-center">
            <div class="text-4xl font-bold">{{ stats.total_documents }}</div>
            <div class="text-sm opacity-80">总文档数</div>
          </div>
        </div>
        <div class="card bg-success text-white">
          <div class="card-body text-center">
            <div class="text-4xl font-bold">{{ stats.total_categories }}</div>
            <div class="text-sm opacity-80">分类数量</div>
          </div>
        </div>
        <div class="card bg-info text-white">
          <div class="card-body text-center">
            <div class="text-4xl font-bold">{{ stats.avg_quality_score?.toFixed(2) || '0.00' }}</div>
            <div class="text-sm opacity-80">平均质量分</div>
          </div>
        </div>
        <div class="card bg-warning text-white">
          <div class="card-body text-center">
            <div class="text-4xl font-bold">{{ highQualityCount }}</div>
            <div class="text-sm opacity-80">高质量文档</div>
          </div>
        </div>
      </div>

      <div v-if="stats.categories?.length" class="mt-6">
        <h4 class="mb-3">分类分布</h4>
        <div class="chart-container" style="height: 300px;">
          <canvas id="categoryChart"></canvas>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { knowledgeApi } from '../api/knowledge'

const loading = ref(false)
const stats = ref({})

const highQualityCount = computed(() => {
  if (!stats.value.categories) return 0
  return stats.value.categories.reduce((sum, cat) => sum + cat.count, 0)
})

const loadStats = async () => {
  loading.value = true
  try {
    const response = await knowledgeApi.getStats()
    const data = response.data
    if (data.code === 0) {
      stats.value = data.data
    }
  } catch (error) {
    console.error('加载统计信息失败:', error)
  } finally {
    loading.value = false
    nextTick(() => {
      renderChart()
    })
  }
}

const renderChart = () => {
  if (!stats.value.categories?.length) return

  const ctx = document.getElementById('categoryChart')
  if (!ctx) return

  const labels = stats.value.categories.map(c => c.name)
  const data = stats.value.categories.map(c => c.count)
  const colors = [
    '#667eea', '#764ba2', '#f093fb', '#f5576c',
    '#4facfe', '#00f2fe', '#43e97b', '#38f9d7'
  ]

  if (window.categoryChartInstance) {
    window.categoryChartInstance.destroy()
  }

  const Chart = window.Chart || {}
  if (Chart.defaults) {
    window.categoryChartInstance = new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label: '文档数量',
          data,
          backgroundColor: colors.slice(0, labels.length),
          borderRadius: 8
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              stepSize: 1
            }
          }
        }
      }
    })
  }
}

onMounted(() => {
  loadStats()
})

watch(stats, () => {
  nextTick(() => {
    renderChart()
  })
})
</script>
