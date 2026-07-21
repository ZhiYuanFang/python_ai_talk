<template>
  <div class="card">
    <div class="card-header">
      <h3 class="card-title">上传知识文档</h3>
    </div>
    <div class="card-body">
      <div class="mb-4">
        <label for="category" class="form-label">知识分类</label>
        <select v-model="category" id="category" class="form-select">
          <option value="未分类">未分类</option>
          <option value="喂养指导">喂养指导</option>
          <option value="营养知识">营养知识</option>
          <option value="发育阶段">发育阶段</option>
          <option value="健康护理">健康护理</option>
          <option value="安全防护">安全防护</option>
        </select>
      </div>

      <div
        class="upload-area"
        :class="{ dragover: isDragover }"
        @dragover.prevent="isDragover = true"
        @dragleave="isDragover = false"
        @drop.prevent="handleDrop"
        @click="triggerFileInput"
      >
        <input
          ref="fileInput"
          type="file"
          accept=".md,.txt"
          class="d-none"
          @change="handleFileSelect"
        />
        <div class="mb-3">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="mx-auto text-secondary">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="17 8 12 3 7 8"></polyline>
            <line x1="12" y1="3" x2="12" y2="15"></line>
          </svg>
        </div>
        <p class="text-secondary mb-1">点击或拖拽文件到此处上传</p>
        <p class="text-sm text-muted">支持 .md 和 .txt 格式的文件</p>
      </div>

      <div v-if="uploading" class="mt-4">
        <div class="progress">
          <div class="progress-bar progress-bar-striped progress-bar-animated" style="width: 100%"></div>
        </div>
        <p class="text-center text-sm text-muted mt-2">正在上传中...</p>
      </div>

      <div v-if="uploadResult" class="mt-4">
        <div :class="['alert', uploadResult.success ? 'alert-success' : 'alert-danger']">
          {{ uploadResult.message }}
          <span v-if="uploadResult.data">
            <br />文档 ID: {{ uploadResult.data.doc_id }}
            <br />生成向量: {{ uploadResult.data.vector_count }} 个
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { knowledgeApi } from '../api/knowledge'

const emit = defineEmits(['upload-success'])

const fileInput = ref(null)
const isDragover = ref(false)
const category = ref('未分类')
const uploading = ref(false)
const uploadResult = ref(null)

const triggerFileInput = () => {
  fileInput.value.click()
}

const handleFileSelect = (event) => {
  const file = event.target.files[0]
  if (file) {
    uploadFile(file)
  }
}

const handleDrop = (event) => {
  isDragover.value = false
  const file = event.dataTransfer.files[0]
  if (file && (file.name.endsWith('.md') || file.name.endsWith('.txt'))) {
    uploadFile(file)
  }
}

const uploadFile = async (file) => {
  uploading.value = true
  uploadResult.value = null

  try {
    const response = await knowledgeApi.uploadFile(file, category.value)
    const data = response.data
    uploadResult.value = {
      success: data.code === 0,
      message: data.message,
      data: data.data
    }
    if (data.code === 0) {
      emit('upload-success')
    }
  } catch (error) {
    uploadResult.value = {
      success: false,
      message: error.response?.data?.detail || '上传失败'
    }
  } finally {
    uploading.value = false
    if (fileInput.value) {
      fileInput.value.value = ''
    }
  }
}
</script>
