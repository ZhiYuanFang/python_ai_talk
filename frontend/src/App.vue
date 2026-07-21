<template>
  <div class="flex">
    <aside class="sidebar w-64 flex-shrink-0 p-4">
      <h2 class="text-white text-xl font-bold mb-6">母婴知识库</h2>
      <nav class="nav flex-column">
        <button
          v-for="item in menuItems"
          :key="item.key"
          @click="currentView = item.key"
          class="nav-link text-left"
          :class="{ active: currentView === item.key }"
        >
          <span class="me-2">{{ item.icon }}</span>
          {{ item.label }}
        </button>
      </nav>
    </aside>

    <main class="content-area flex-grow p-6">
      <UploadPanel v-if="currentView === 'upload'" @upload-success="handleUploadSuccess" />
      <DocumentList v-else-if="currentView === 'list'" @refresh="refreshList" />
      <StatsPanel v-else-if="currentView === 'stats'" />
      <CategoriesPanel v-else-if="currentView === 'categories'" />
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import UploadPanel from './components/UploadPanel.vue'
import DocumentList from './components/DocumentList.vue'
import StatsPanel from './components/StatsPanel.vue'
import CategoriesPanel from './components/CategoriesPanel.vue'

const currentView = ref('upload')

const menuItems = [
  { key: 'upload', label: '上传知识', icon: '📤' },
  { key: 'list', label: '知识列表', icon: '📋' },
  { key: 'stats', label: '统计信息', icon: '📊' },
  { key: 'categories', label: '分类管理', icon: '🏷️' }
]

const handleUploadSuccess = () => {
  currentView.value = 'list'
}

const refreshList = () => {}
</script>
