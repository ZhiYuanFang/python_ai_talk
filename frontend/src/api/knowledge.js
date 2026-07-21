import axios from 'axios'

const baseURL = '/v1/knowledge'

export const knowledgeApi = {
  uploadFile(file, category) {
    const formData = new FormData()
    formData.append('file', file)
    if (category) {
      formData.append('category', category)
    }
    return axios.post(`${baseURL}/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  },

  getList(params) {
    return axios.get(`${baseURL}/list`, { params })
  },

  getDetail(docId) {
    return axios.get(`${baseURL}/${docId}`)
  },

  update(docId, content, category) {
    return axios.put(`${baseURL}/${docId}`, null, {
      params: { content, category }
    })
  },

  delete(docId) {
    return axios.delete(`${baseURL}/${docId}`)
  },

  getStats() {
    return axios.get(`${baseURL}/stats`)
  },

  getCategories() {
    return axios.get(`${baseURL}/categories`)
  }
}
