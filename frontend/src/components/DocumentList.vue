<template>
  <div class="card">
    <div class="card-header">
      <div class="d-flex justify-content-between align-items-center">
        <h3 class="card-title">知识文档列表</h3>
        <div class="d-flex gap-2">
          <select v-model="categoryFilter" class="form-select form-select-sm">
            <option value="">全部分类</option>
            <option v-for="cat in categories" :key="cat.name" :value="cat.name">
              {{ cat.name }} ({{ cat.count }})
            </option>
          </select>
          <button @click="loadDocuments" class="btn btn-sm btn-primary">
            刷新
          </button>
        </div>
      </div>
    </div>
    <div class="card-body">
      <div v-if="loading" class="text-center py-4">
        <div class="spinner-border text-primary" role="status"></div>
        <p class="mt-2">加载中...</p>
      </div>

      <table v-else class="table table-striped">
        <thead>
          <tr>
            <th>文件名</th>
            <th>分类</th>
            <th>质量分</th>
            <th>匹配次数</th>
            <th>有用次数</th>
            <th>创建时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="doc in documents" :key="doc.doc_id">
            <td>
              <button @click="viewDocument(doc)" class="btn btn-link p-0 text-primary">
                {{ doc.file_name }}
              </button>
            </td>
            <td>{{ doc.category }}</td>
            <td>
              <span :class="getQualityClass(doc.quality_score)" class="quality-badge">
                {{ doc.quality_score.toFixed(2) }}
              </span>
            </td>
            <td>{{ doc.match_count }}</td>
            <td>{{ doc.helpful_count }}</td>
            <td>{{ formatTime(doc.created_at) }}</td>
            <td>
              <div class="d-flex gap-1">
                <button @click="viewDocument(doc)" class="btn btn-sm btn-outline-primary">
                  查看
                </button>
                <button @click="deleteDocument(doc)" class="btn btn-sm btn-outline-danger">
                  删除
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="!loading && documents.length === 0" class="text-center py-8 text-muted">
        暂无文档
      </div>

      <nav v-if="!loading && total > pageSize" class="mt-4">
        <ul class="pagination justify-content-center">
          <li class="page-item" :class="{ disabled: page === 1 }">
            <button @click="page--; loadDocuments()" class="page-link">上一页</button>
          </li>
          <li class="page-item active">
            <span class="page-link">{{ page }}</span>
          </li>
          <li class="page-item" :class="{ disabled: page >= totalPages }">
            <button @click="page++; loadDocuments()" class="page-link">下一页</button>
          </li>
        </ul>
        <p class="text-center text-sm text-muted mt-2">
          共 {{ total }} 条记录，第 {{ page }} / {{ totalPages }} 页
        </p>
      </nav>
    </div>
  </div>

  <div v-if="showModal" class="modal show d-block" tabindex="-1">
    <div class="modal-dialog modal-lg">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">{{ currentDoc?.file_name || '文档详情' }}</h5>
          <button @click="showModal = false" class="btn-close"></button>
        </div>
        <div class="modal-body">
          <div v-if="currentDoc" class="space-y-4">
            <div class="row">
              <div class="col-md-6">
                <label class="form-label">文档 ID</label>
                <input :value="currentDoc.doc_id" class="form-control" readonly />
              </div>
              <div class="col-md-6">
                <label class="form-label">分类</label>
                <input :value="currentDoc.category" class="form-control" readonly />
              </div>
            </div>
            <div class="row">
              <div class="col-md-4">
                <label class="form-label">质量分</label>
                <input :value="currentDoc.quality_score.toFixed(2)" class="form-control" readonly />
              </div>
              <div class="col-md-4">
                <label class="form-label">匹配次数</label>
                <input :value="currentDoc.match_count" class="form-control" readonly />
              </div>
              <div class="col-md-4">
                <label class="form-label">有用次数</label>
                <input :value="currentDoc.helpful_count" class="form-control" readonly />
              </div>
            </div>
            <div>
              <label class="form-label">文档内容</label>
              <pre class="form-control" style="height: 300px; white-space: pre-wrap">{{ currentDoc.content }}</pre>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button @click="showModal = false" class="btn btn-secondary">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { knowledgeApi } from '../api/knowledge'

const emit = defineEmits(['refresh'])

const loading = ref(false)
const documents = ref([])
const categories = ref([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const categoryFilter = ref('')
const showModal = ref(false)
const currentDoc = ref(null)

const totalPages = computed(() => Math.ceil(total.value / pageSize.value))

const getQualityClass = (score) => {
  if (score >= 0.7) return 'quality-high'
  if (score >= 0.4) return 'quality-medium'
  return 'quality-low'
}

const formatTime = (timeStr) => {
  if (!timeStr) return ''
  return new Date(timeStr).toLocaleString('zh-CN')
}

const loadDocuments = async () => {
  loading.value = true
  try {
    const params = {
      page: page.value,
      page_size: pageSize.value
    }
    if (categoryFilter.value) {
      params.category = categoryFilter.value
    }
    const response = await knowledgeApi.getList(params)
    const data = response.data
    if (data.code === 0) {
      documents.value = data.data.list
      total.value = data.data.total
      page.value = data.data.page
    }
  } catch (error) {
    console.error('加载文档列表失败:', error)
  } finally {
    loading.value = false
  }
}

const loadCategories = async () => {
  try {
    const response = await knowledgeApi.getCategories()
    const data = response.data
    if (data.code === 0) {
      categories.value = data.data
    }
  } catch (error) {
    console.error('加载分类失败:', error)
  }
}

const viewDocument = async (doc) => {
  try {
    const response = await knowledgeApi.getDetail(doc.doc_id)
    const data = response.data
    if (data.code === 0) {
      currentDoc.value = data.data
      showModal.value = true
    }
  } catch (error) {
    console.error('查看文档失败:', error)
  }
}

const deleteDocument = async (doc) => {
  if (!confirm(`确定要删除文档 "${doc.file_name}" 吗？`)) return
  try {
    const response = await knowledgeApi.delete(doc.doc_id)
    const data = response.data
    if (data.code === 0) {
      loadDocuments()
      emit('refresh')
    }
  } catch (error) {
    console.error('删除文档失败:', error)
  }
}

onMounted(() => {
  loadDocuments()
  loadCategories()
})
</script>
