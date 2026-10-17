/**
 * AI 智能助手前端接口封装
 * 对接后端 FastAPI 的 /ai/* 路由
 * 支持两种模式：general（通用助手） 和 kb（知识库问答）
 * 对话历史持久化到数据库，刷新页面和登录后都能恢复
 */

import request from './index'

/**
 * 发送一条消息并获取 AI 回复
 * @param {{ mode?: 'general'|'kb', content: string }} data
 */
export const sendChatMessage = (data) => {
  // 兼容旧的调用方式：传 { session_id: xxx, content: xxx }
  const payload = Object.assign({}, data)
  // 如果未指定 mode，自动补为 general（kb 模式走 /kb/ask-all）
  if (!payload.mode) payload.mode = 'general'
  // 去掉旧接口的 session_id（后端现在用 token 识别用户）
  delete payload.session_id
  return request.post('/ai/chat', payload)
}

/**
 * 加载当前登录用户的历史对话（按 mode 区分）
 * @param {'general'|'kb'} mode
 */
export const getChatHistory = (mode = 'general') =>
  request.get('/ai/history', { params: { mode } })

/**
 * 清空当前登录用户的对话记录（按 mode 区分）
 * @param {'general'|'kb'} mode
 */
export const clearChatSession = (mode = 'general') =>
  request.delete('/ai/clear', { params: { mode } })

/**
 * 上传图片并让 AI 助手识别与解释（仅 general 模式）
 * @param {File} file   图片文件
 * @param {string} prompt 用户对图片的提问（可为空）
 */
export const sendChatImage = (file, prompt = '') => {
  const formData = new FormData()
  formData.append('file', file)
  if (prompt && String(prompt).trim()) {
    formData.append('prompt', String(prompt).trim())
  }
  return request.post('/ai/image', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 180000
  })
}

/**
 * 上传图片（预留接口，当前版本仅返回提示信息）
 * @deprecated 请使用 sendChatImage
 */
export const uploadChatImage = (sessionId, formData) =>
  request.post('/ai/image', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    params: { session_id: sessionId }
  })
