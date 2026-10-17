/**
 * 知识库前端 API 封装
 * 对接后端 FastAPI /kb/*  路由
 * 所有接口依赖登录 token（axios 拦截器自动附加）
 */

import request from './index'

/** 知识库列表 */
export const listKnowledgeBases = () =>
  request.get('/kb/list')

/** 创建知识库 */
export const createKnowledgeBase = (name, description = '') =>
  request.post('/kb/create', { name, description })

/** 删除知识库 */
export const deleteKnowledgeBase = (kbId) =>
  request.delete(`/kb/${kbId}`)

/** 重命名/更新知识库 */
export const renameKnowledgeBase = (kbId, name, description = null) =>
  request.put(`/kb/${kbId}`, { name, description })

/** 知识库文档列表 */
export const listKbDocuments = (kbId) =>
  request.get(`/kb/${kbId}/documents`)

/** 上传文档（multipart/form-data）并完成向量化入库 */
export const uploadKbDocument = (kbId, file, onUploadProgress) => {
  const formData = new FormData()
  formData.append('file', file)
  return request.post(`/kb/${kbId}/upload`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 180000,
    onUploadProgress: onUploadProgress || undefined,
  })
}

/** 删除文档 */
export const deleteKbDocument = (docId) =>
  request.delete(`/kb/document/${docId}`)

/** 重命名文档 */
export const renameKbDocument = (docId, name) =>
  request.put(`/kb/document/${docId}`, { name })

/** 将文档移动到另一个知识库 */
export const moveKbDocument = (docId, targetKbId) =>
  request.post(`/kb/document/${docId}/move`, { target_kb_id: targetKbId })

/** 下载单个文档（二进制文件） */
export const downloadKbDocument = (docId, originalName = 'document.txt') => {
  return request.get(`/kb/document/${docId}/download`, {
    responseType: 'blob',
  }).then((res) => {
    // 触发浏览器下载
    const url = URL.createObjectURL(new Blob([res]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', originalName || 'download')
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
    return { ok: true }
  })
}

/** 打包下载整个知识库的文档（ZIP） */
export const downloadKbAll = (kbId, name = 'knowledge_base.zip') => {
  return request.get(`/kb/${kbId}/download`, {
    responseType: 'blob',
  }).then((res) => {
    const url = URL.createObjectURL(new Blob([res]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', name || 'knowledge_base.zip')
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
    return { ok: true }
  })
}

/** 余弦相似度检索片段（指定知识库） */
export const searchKb = (kbId, question, topK = 8) =>
  request.post('/kb/search', { kb_id: kbId, question, top_k: topK })

/** 知识库问答（RAG） - 单个知识库 */
export const askKb = (kbId, question) =>
  request.post('/kb/ask', { kb_id: kbId, question })

/** 跨所有知识库问答（全局 RAG，无需选择知识库）
 *  后端会自动将问答记录持久化到 chat_message(mode="kb")，
 *  以便刷新页面或重新登录后恢复历史。
 */
export const askKbAll = (question) =>
  request.post('/kb/ask-all', { question })

/** 跨所有知识库余弦相似度检索 */
export const searchKbAll = (question, topK = 8) =>
  request.post('/kb/search-all', { question, top_k: topK })
