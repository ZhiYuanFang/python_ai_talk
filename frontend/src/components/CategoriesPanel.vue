<template>
  <div class="card">
    <div class="card-header">
      <h3 class="card-title">知识分类管理</h3>
      <button @click="loadCategories" class="btn btn-sm btn-primary float-end">刷新</button>
    </div>
    <div class="card-body">
      <div v-if="loading" class="text-center py-4">
        <div class="spinner-border text-primary" role="status"></div>
        <p class="mt-2">加载中...</p>
      </div>

      <div v-else-if="categories.length === 0" class="text-center py-8 text-muted">
        暂无分类
      </div>

      <div v-else class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        <div
          v-for="cat in categories"
          :key="cat.name"
          class="card"
          style="cursor: pointer;"
          @click="selectCategory(cat)"
        >
          <div class="card-body text-center">
            <div class="text-3xl mb-2">{{ getCategoryIcon(cat.name) }}</div>
            <h5 class="card-title">{{ cat.name }}</h5>
            <p class="card-text text-muted">{{ cat.count }} 篇文档</p>
          </div>
        </div>
      </div>

      <div v-if="selectedCategory" class="mt-6">
        <div class="card">
          <div class="card-header">
            <h4>{{ selectedCategory.name }} 分类文档</h4>
            <button @click="selectedCategory = null" class="btn btn-sm btn-outline-secondary float-end">关闭</button>
          </div>
          <div class="card-body">
            <table class="table table-sm">
              <thead>
                <tr>
                  <th>文件名</th>
                  <th>质量分</th>
                  <th>匹配次数</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="doc in categoryDocuments" :key="doc.doc_id">
                  <td>{{ doc.file_name }}</td>
                  <td>{{ doc.quality_score.toFixed(2) }}</td>
                  <td>{{ doc.match_count }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { knowledgeApi } from '../api/knowledge'

const loading = ref(false)
const categories = ref([])
const selectedCategory = ref(null)
const categoryDocuments = ref([])

const getCategoryIcon = (name) => {
  const icons = {
    '喂养指导': '🍼',
    '营养知识': '🥗',
    '发育阶段': '👶',
    '健康护理': '💊',
    '安全防护': '🛡️',
    '未分类': '📄'
  }
  return icons[name] || '📚'
}

const loadCategories = async () => {
  loading.value = true
  try {
    const response = await knowledgeApi.getCategories()
    const data = response.data
    if (data.code === 0) {
      categories.value = data.data
    }
  } catch (error) {
    console.error('加载分类失败:', error)
  } finally {
    loading.value = false
  }
}

const selectCategory = async (category) => {
  selectedCategory.value = category
  try {
    const response = await knowledgeApi.getList({ category: category.name })
    const data = response.data
    if (data.code === 0) {
      categoryDocuments.value = data.data.list
    }
  } catch (error) {
    console.error('加载分类文档失败:', error)
  }
}

onMounted(() => {
  loadCategories()
})
</script>
