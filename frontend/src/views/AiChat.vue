<template>
  <div class="app-container">
    <!-- 顶部导航栏（与首页一致） -->
    <div class="top-header">
      <div class="header-logo">
        <div class="logo-icon">📁</div>
        <span>FileManager</span>
      </div>
      <div class="header-title-bar">
        <span class="page-tag">🤖 AI 智能助手</span>
      </div>
      <div class="header-user">
        <el-dropdown @command="handleUserCommand">
          <div style="display:flex;align-items:center;gap:8px;cursor:pointer;">
            <div class="user-avatar">{{ (userInfo.username || 'U').charAt(0).toUpperCase() }}</div>
            <div class="user-name">{{ userInfo.username }}</div>
            <el-icon><ArrowDown /></el-icon>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="home">返回首页</el-dropdown-item>
              <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>

    <div class="app-body">
      <!-- 左侧菜单（与首页一致，但不含"试试问我"） -->
      <div class="sidebar">
        <div class="sidebar-section">
          <div class="menu-item" @click="goHome('all')">
            <span class="icon">📂</span><span>全部文件</span>
          </div>
        </div>
        <div class="sidebar-section">
          <div class="sidebar-section-title">文件分类</div>
          <div class="menu-item" @click="goHome('image')"><span class="icon">🖼️</span><span>图片</span></div>
          <div class="menu-item" @click="goHome('doc')"><span class="icon">📄</span><span>文档</span></div>
          <div class="menu-item" @click="goHome('video')"><span class="icon">🎬</span><span>视频</span></div>
          <div class="menu-item" @click="goHome('audio')"><span class="icon">🎵</span><span>音乐</span></div>
          <div class="menu-item" @click="goHome('archive')"><span class="icon">🗜️</span><span>压缩包</span></div>
        </div>
        <div class="sidebar-section">
          <div class="sidebar-section-title">其他</div>
          <div class="menu-item" @click="goHome('recycle')"><span class="icon">🗑️</span><span>回收站</span></div>
          <div class="menu-item active"><span class="icon">🤖</span><span>AI智能助手</span></div>
          <div class="menu-item" @click="goToKnowledge"><span class="icon">📚</span><span>知识库</span></div>
          <div class="menu-item" @click="goHome('profile')"><span class="icon">👤</span><span>个人中心</span></div>
          <div class="menu-item" v-if="isAdmin" @click="goHome('admin')"><span class="icon">⚙️</span><span>系统设置</span></div>
        </div>
        <!-- 存储用量（蓝色渐变卡片，与首页风格一致） -->
        <div class="storage-card">
          <div class="title">💾 存储用量</div>
          <div class="bar"><div class="bar-inner" :style="{width: storagePercent + '%'}"></div></div>
          <div class="text">{{ formatSize(stats.totalSize) }} / {{ formatSize(storageQuota) }}</div>
        </div>
      </div>

      <!-- 右侧主内容区：对话区 + 快捷问 -->
      <div class="main-content">
        <div class="chat-layout">
          <!-- 对话主区 -->
          <div class="chat-panel">
            <!-- 对话标题 + 模式切换 -->
            <div class="chat-header">
              <div class="chat-title">
                <span class="title-icon">🤖</span>
                <span>与 AI 助手对话</span>
              </div>
              <div class="mode-switcher">
                <button class="mode-btn" :class="{active: mode==='chat'}" @click="switchMode('chat')">💬 通用助手</button>
                <button class="mode-btn" :class="{active: mode==='kb'}" @click="switchMode('kb')">📚 知识库问答</button>
                <button class="mode-btn clear-btn" @click="onClearChat" title="清除当前模式的对话记录">🗑️ 清除对话</button>
              </div>
            </div>

            <!-- 知识库模式：无需选择知识库，直接搜索全部（移除选择栏） -->

            <!-- 消息列表 -->
            <div ref="msgListRef" class="message-list">
              <div v-for="(msg,i) in currentMessages" :key="'msg-'+i" class="message-row" :class="msg.role">
                <!-- 用户消息：右侧 -->
                <template v-if="msg.role==='user'">
                  <div class="msg-bubble user-bubble">
                    <div v-if="msg.imageUrl" class="msg-image" @click="showImagePreview(msg.imageUrl)">
                      <img :src="msg.imageUrl" :alt="msg.imageName || '图片'" />
                    </div>
                    <div v-if="msg.content" class="msg-text">{{ msg.content }}</div>
                  </div>
                  <div class="msg-avatar avatar-user">{{ (userInfo.username || 'U').charAt(0).toUpperCase() }}</div>
                </template>
                <!-- AI 消息：左侧 -->
                <template v-else>
                  <div class="msg-avatar avatar-ai"><img :src="aiAvatarUrl" alt="AI助手" /></div>
                  <div class="msg-bubble ai-bubble">
                    <div class="ai-label">AI 助手</div>

                    <!-- 正在加载：显示占位动效 -->
                    <div v-if="msg.status==='loading'" class="ai-text thinking">正在思考中<span class="dots-inline" aria-hidden="true"></span></div>

                    <!-- 回答主体 -->
                    <div v-if="msg.content" class="ai-text">{{ msg.content }}</div>

                  </div>
                </template>
              </div>
            </div>

            <!-- 输入区 -->
            <div class="input-area">
              <div class="input-toolbar">
                <button class="tool-btn" @click="triggerImage"><span class="tool-icon">🖼️</span><span>图片</span></button>
                <input type="file" ref="fileInputRef" accept="image/*" style="display:none" @change="onFileChange" />
                <!-- 图片预览（待发送状态） -->
                <div v-if="pendingImage" class="pending-image">
                  <img :src="pendingImage.url" :alt="pendingImage.name" />
                  <div class="pending-image-info">
                    <span class="pending-image-name">{{ pendingImage.name }}</span>
                    <button class="remove-image" @click="removePendingImage" title="移除图片">×</button>
                  </div>
                </div>
              </div>
              <div class="input-wrapper">
                <el-input
                  v-model="inputText"
                  type="textarea"
                  :autosize="{minRows: 2, maxRows: 6}"
                  :placeholder="getPlaceholder()"
                  @keydown.enter.exact.prevent="onSend"
                  @keydown.enter.shift.exact="onNewLine"
                  resize="none"
                  class="chat-input"
                />
                <div class="input-footer">
                  <span class="char-count">{{ (inputText || '').length }} / 2000</span>
                  <button class="send-btn" :disabled="!canSend || loading" @click="onSend">发送</button>
                </div>
              </div>
            </div>
          </div>

          <!-- 右侧快捷问栏 -->
          <div class="quick-panel">
            <div class="quick-header">
              <span class="quick-title-icon">💡</span>
              <span>试试问我</span>
            </div>
            <div class="quick-list">
              <button class="quick-item" @click="sendQuick('现在几点了？')">
                <span class="quick-icon">⏰</span>
                <span class="quick-text">现在几点了？</span>
              </button>
              <button class="quick-item" @click="sendQuick('今天是什么日期？')">
                <span class="quick-icon">📅</span>
                <span class="quick-text">今天是什么日期？</span>
              </button>
              <button class="quick-item" @click="sendQuick('介绍一下你自己')">
                <span class="quick-icon">🤖</span>
                <span class="quick-text">介绍一下你自己</span>
              </button>
              <button class="quick-item" @click="sendQuick('文件管理小贴士')">
                <span class="quick-icon">💡</span>
                <span class="quick-text">文件管理小贴士</span>
              </button>
            </div>
            <div class="quick-tip">
                <div class="tip-icon">✨</div>
                <div class="tip-text">点击快捷问题快速开始对话，或直接输入你的问题</div>
              </div>
            </div>
          </div>
        </div>
      </div>

    <!-- 图片全屏预览遮罩 -->
    <div v-if="showImgPreview" class="image-preview-mask" @click="closeImagePreview">
      <img :src="showImgPreview" class="preview-image" alt="图片预览" />
      <button class="preview-close" @click.stop="closeImagePreview">×</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { formatSize } from '@/utils/format'
import * as aiApi from '@/api/ai'
import * as kbApi from '@/api/kb'
import aiAvatar from '@/assets/ai-avatar.svg'

const router = useRouter()
const { state, logout, fetchUserInfo, refreshStorageStats } = useUserStore()

const aiAvatarUrl = aiAvatar

// 用户信息
const userInfo = computed(() => state.userInfo)
const isAdmin = computed(() => userInfo.value.role === 'admin')

// 存储用量（从全局 store 读取，避免路由切换组件重建导致的 0→正确值 闪烁）
const stats = computed(() => state.storageStats)
const storageQuota = computed(() => (stats.value.storageQuota || state.userInfo?.storage_quota || 8 * 1024 * 1024 * 1024))
const storagePercent = computed(() => Math.min(100, ((stats.value.totalSize || 0) / storageQuota.value * 100)).toFixed(1))

// AI 助手状态
const mode = ref('chat')
const inputText = ref('')
const loading = ref(false)

const messagesChat = ref([])
const messagesKb = ref([])
const kbList = ref([])
const msgListRef = ref(null)
const fileInputRef = ref(null)
// 图片相关
const pendingImage = ref(null)
const showImgPreview = ref(null)

// ============ AI 消息封装 ============
// 发送消息时立刻 push 一个占位的 AI 消息，状态 status：
//   - loading：等待 API 返回中；返回后设置 content，status 变为 null
// ⚠️ 关键：必须返回响应式数组中 Vue 包装的 Proxy 对象，而非原始 msg
//    Vue 3 的 ref/reactive 数组会自动包装 push 进来的对象为 Proxy；
//    返回原始 msg 时，后续修改 msg.content 不会触发 Proxy 的 set trap，
//    导致模板不会重新渲染 → 一直卡在"正在思考中"。
function appendAssistantMsg(listRef) {
  listRef.value.push({
    role: 'assistant',
    status: 'loading',
    ts: Date.now(),
    content: '',
    hits: null,
  })
  // 从响应式数组中取出 Vue 包装的 Proxy 对象，后续修改其属性会触发重渲染
  return listRef.value[listRef.value.length - 1]
}

const currentMessages = computed(() => mode.value === 'chat' ? messagesChat.value : messagesKb.value)

const canSend = computed(() => {
  if (loading.value) return false
  // 通用助手：文本或图片均可发送
  if (mode.value === 'chat') {
    if (pendingImage.value) return true
    return !!(inputText.value && inputText.value.trim())
  }
  // 知识库问答：只需有文本即可（自动搜索所有知识库）
  return !!(inputText.value && inputText.value.trim())
})

// ============ 初始化 ============
onMounted(async () => {
  // 进入页面时先尝试从缓存展示，避免组件重建造成数字闪烁
  await loadStats()
  // 首次进入：加载两种模式的对话历史（从数据库持久化恢复）
  await loadHistory('chat')
  await loadHistory('kb')
  // 默认模式是通用助手
  mode.value = 'chat'
  // 加载完历史后滚动到最新消息（需要等 DOM 渲染完成）
  scrollToBottom()
})

// ============ 加载历史对话（从后端数据库读取并保存到本地 messagesChat / messagesKb） ============
// ============ 清洗从数据库返回的历史消息（兼容之前的脏数据）
function cleanHistoryContent(raw, role) {
  if (!raw) return ''
  let text = String(raw)
  if (role === 'user') {
    // 用户消息：剔除 "[知识库] 用户问题：XXX" 前缀以及其后的内部上下文
    text = text
      .replace(/^\s*\[知识库\]\s*用户问题[：:]\s*/i, '')
      .replace(/\n[^\n]*相关内容[：:].*$/s, '')
      .replace(/\[相关片段\s*\d+\][^\n]*\n?/g, '')
      .trim()
  } else {
    // AI 消息：保持原样（模型回复通常是干净的；若有 [模型未返回] 等占位符可以保留）
  }
  return text
}

async function loadHistory(targetMode) {
  try {
    const backendMode = targetMode === 'kb' ? 'kb' : 'general'
    const res = await aiApi.getChatHistory(backendMode)
    if (res && res.code === 200 && res.data && Array.isArray(res.data.messages)) {
      const messages = res.data.messages.map(m => {
        const role = (m.role || 'user')
        const isAi = role === 'assistant'
        const cleanContent = cleanHistoryContent(m.content, role)
        return {
          role: isAi ? 'assistant' : 'user',
          status: null,
          content: cleanContent,
          ts: Date.now(),
          hits: null,
        }
      })
      if (targetMode === 'kb') {
        messagesKb.value = messages
      } else {
        messagesChat.value = messages
      }
    }
  } catch (e) {
    // 加载历史失败：静默处理，不打扰用户（避免连续弹「网络错误」）
    console.warn('[AI助手] 加载历史对话失败，已忽略：', e && e.message ? e.message : e)
  }
}

// ============ 清除当前模式对话（调用后端删除数据库记录） ============
async function onClearChat() {
  try {
    await ElMessageBox.confirm(
      '确认清除当前模式的所有对话记录？此操作会同时删除服务器端的持久化记录。',
      '提示',
      { type: 'warning' }
    )
    const backendMode = mode.value === 'kb' ? 'kb' : 'general'
    const res = await aiApi.clearChatSession(backendMode)
    if (res && res.code === 200) {
      if (mode.value === 'kb') messagesKb.value = []
      else messagesChat.value = []
      ElMessage.success('对话记录已清除')
    } else {
      ElMessage.error('清除失败')
    }
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') ElMessage.error('清除失败')
  }
}

async function loadStats() {
  try { await fetchUserInfo() } catch (e) { console.error(e) }
  try { await refreshStorageStats(false) } catch (e) { console.error(e) }
}

// ============ 导航 ============
function goHome(v) { router.push({ path: '/', query: v ? { view: v } : {} }) }
function goToKnowledge() { router.push('/knowledge') }

function handleUserCommand(cmd) {
  if (cmd === 'home') goHome('all')
  else if (cmd === 'logout') handleLogout()
}

function handleLogout() {
  logout()
  router.push('/login')
}

// ============ 模式切换 ============
function switchMode(next) {
  if (mode.value === next) return
  mode.value = next
  scrollToBottom()
}

// ============ 知识库 ============
async function loadKbList() {
  try {
    const res = await kbApi.listKnowledgeBases()
    if (res && res.code === 200 && Array.isArray(res.data)) kbList.value = res.data
  } catch (e) { console.error(e) }
}

function onKbChange() { scrollToBottom() }

// ============ 发送消息 ============
function onSend() {
  if (!canSend.value) return
  const q = inputText.value.trim()
  // 限制总长度（图片不占文本长度）
  if (q.length > 2000) { ElMessage.warning('消息不能超过 2000 字'); return }

  if (mode.value === 'chat') {
    // 通用助手：支持图片
    sendChatMessage(q)
  } else {
    // 知识库问答：仅文本（图片不适用）
    sendKbMessage(q)
  }
}

function onNewLine(e) {
  // Shift+Enter 处理：el-input 的 textarea 默认不阻止换行
  // 但我们的 @keydown.enter.prevent 可能会冲突，这里显式允许换行
  // 通过只在 @keydown.enter.exact.prevent 时发送，
  // @keydown.enter.shift.exact 不阻止默认行为，浏览器会自动插入换行
}

function sendQuick(q) {
  inputText.value = q
  if (mode.value !== 'chat') mode.value = 'chat'
  nextTick(() => onSend())
}

// ============ 图片上传 ============
function triggerImage() {
  if (fileInputRef.value) fileInputRef.value.click()
}

// 在组件作用域内暂存真实的 File 对象，避免把 base64 再次上传造成体积膨胀
let _pendingImageFile = null

function onFileChange(e) {
  const file = e.target.files[0]
  if (!file) return
  // 简单的 MIME 检查
  if (!file.type.startsWith('image/')) {
    ElMessage.warning('请选择图片文件')
    return
  }
  // 大小限制：10MB
  if (file.size > 10 * 1024 * 1024) {
    ElMessage.warning('图片大小不能超过 10MB')
    return
  }
  // 读取为 base64 仅用于本地预览，真正上传时会用下方的 _pendingImageFile
  const reader = new FileReader()
  reader.onload = () => {
    pendingImage.value = {
      url: reader.result,
      name: file.name,
      size: file.size,
    }
    _pendingImageFile = file
  }
  reader.onerror = () => ElMessage.error('图片读取失败')
  reader.readAsDataURL(file)
  // 重置 input，允许再次选择同一文件
  if (fileInputRef.value) fileInputRef.value.value = ''
}

function removePendingImage() {
  pendingImage.value = null
  _pendingImageFile = null
}

function showImagePreview(url) {
  // 简单全屏预览：使用浏览器原生图片查看
  showImgPreview.value = url
}

function closeImagePreview() {
  showImgPreview.value = null
}

// ============ 聊天消息发送（千问式思考：先显示气泡 → 半透明推理 → 完成后折叠 → 显示最终答案）
async function sendChatMessage(q) {
  const hasImage = !!pendingImage.value
  const fileToSend = _pendingImageFile
  messagesChat.value.push({
    role: 'user',
    content: q,
    imageUrl: hasImage ? pendingImage.value.url : null,
    imageName: hasImage ? pendingImage.value.name : null,
    ts: Date.now(),
  })
  pendingImage.value = null
  _pendingImageFile = null
  inputText.value = ''
  loading.value = true

  // 立即 push 一个占位 AI 消息
  const aiMsg = appendAssistantMsg(messagesChat)
  scrollToBottom()

  try {
    let reply = null
    if (hasImage && fileToSend) {
      const res = await aiApi.sendChatImage(fileToSend, q || '')
      if (res && res.code === 200 && res.data) {
        reply = res.data.reply || null
      }
    } else {
      const res = await aiApi.sendChatMessage({ session_id: 'user_chat', content: q })
      if (res && res.code === 200 && res.data) {
        reply = res.data.reply || null
      }
    }
    if (!reply) reply = '抱歉，AI 暂时无法回答，请稍后再试。'
    aiMsg.content = reply
    aiMsg.status = null
    scrollToBottom()
  } catch (e) {
    aiMsg.content = '连接 AI 失败，请检查网络或稍后再试。'
    aiMsg.status = null
    scrollToBottom()
  } finally {
    loading.value = false
  }
}

// ==================== 知识库问答 ====================
async function sendKbMessage(q) {
  messagesKb.value.push({ role: 'user', content: q, ts: Date.now() })
  inputText.value = ''
  loading.value = true

  const aiMsg = appendAssistantMsg(messagesKb)
  scrollToBottom()

  try {
    const res = await kbApi.askKbAll(q)
    let reply = null
    if (res && res.code === 200 && res.data) {
      reply = res.data.answer || null
    }
    if (!reply) reply = '抱歉，AI 暂时无法回答，请稍后再试。'
    aiMsg.content = reply
    aiMsg.status = null
    scrollToBottom()
  } catch (e) {
    aiMsg.content = '连接 AI 失败，请检查网络或稍后再试。'
    aiMsg.status = null
    scrollToBottom()
  } finally {
    loading.value = false
  }
}

function getPlaceholder() {
  if (mode.value === 'chat') return '请输入消息，Enter 发送 · Shift+Enter 换行'
  return '基于知识库提问，Enter 发送 · Shift+Enter 换行'
}

function scrollToBottom() {
  // 使用 nextTick + requestAnimationFrame 多次尝试，确保 DOM 已完全渲染后再滚动
  // 特别是刷新后加载多条历史消息时，单次 nextTick 可能不够
  const tryScroll = (attempt) => {
    if (attempt > 5) return  // 最多尝试 5 次
    nextTick(() => {
      if (msgListRef.value) {
        msgListRef.value.scrollTop = msgListRef.value.scrollHeight
      }
      // 下一帧再确认一次（消息内容可能含换行/图片，高度会变）
      requestAnimationFrame(() => {
        if (msgListRef.value) {
          const list = msgListRef.value
          // 只有当尚未到底时才继续尝试（避免重复操作造成性能浪费）
          if (list.scrollTop + list.clientHeight < list.scrollHeight - 2) {
            list.scrollTop = list.scrollHeight
            setTimeout(() => tryScroll(attempt + 1), 50)
          }
        }
      })
    })
  }
  tryScroll(0)
}
</script>

<style scoped>
/* ============ 容器（与首页一致） ============ */
.app-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

/* ============ 顶部导航栏（与首页一致的白色风格） ============ */
.top-header {
  height: 60px;
  background: #fff;
  box-shadow: 0 2px 8px rgba(33, 150, 243, 0.08);
  display: flex;
  align-items: center;
  padding: 0 24px;
  z-index: 10;
}

.header-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 18px;
  font-weight: 700;
  color: #1a3a5c;
  min-width: 220px;
  cursor: pointer;
}

.header-logo .logo-icon {
  width: 36px;
  height: 36px;
  background: linear-gradient(135deg, #4facfe 0%, #2196f3 100%);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  color: #fff;
}

.header-title-bar {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.page-tag {
  padding: 8px 20px;
  background: linear-gradient(135deg, #4facfe 0%, #2196f3 100%);
  color: #fff;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(33, 150, 243, 0.2);
}

.header-user {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 16px;
}

.user-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, #4facfe 0%, #2196f3 100%);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
}

.user-name {
  font-size: 14px;
  color: #1a3a5c;
  font-weight: 500;
}

/* ============ 主体布局 ============ */
.app-body {
  flex: 1;
  display: flex;
  overflow: hidden;
}

/* ============ 左侧菜单（与首页一致） ============ */
.sidebar {
  width: 220px;
  background: #fff;
  border-right: 1px solid #e3eefb;
  padding: 16px 0;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

.sidebar-section { padding: 8px 0; }
.sidebar-section-title { font-size: 11px; color: #9ab; padding: 8px 24px; letter-spacing: 1px; }

.menu-item {
  padding: 11px 24px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 12px;
  color: #4a5c6e;
  font-size: 14px;
  transition: all 0.2s;
  border-left: 3px solid transparent;
}
.menu-item:hover { background: #f0f7ff; color: #2196f3; }
.menu-item.active { background: #e3f2fd; color: #2196f3; border-left-color: #2196f3; font-weight: 600; }
.menu-item .icon { font-size: 16px; width: 18px; text-align: center; }

.storage-card {
  margin: 16px;
  padding: 16px;
  background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
  border-radius: 12px;
}
.storage-card .title { font-size: 13px; color: #1565c0; font-weight: 600; margin-bottom: 8px; }
.storage-card .bar { height: 8px; background: rgba(255,255,255,0.6); border-radius: 4px; overflow: hidden; margin-bottom: 8px; }
.storage-card .bar-inner { height: 100%; background: linear-gradient(90deg, #2196f3, #4facfe); border-radius: 4px; transition: width 0.3s; }
.storage-card .text { font-size: 12px; color: #1565c0; }

/* ============ 主内容区 ============ */
.main-content {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
  background: #f0f7ff;
}

/* ============ 对话布局（左侧对话 + 右侧快捷问） ============ */
.chat-layout {
  display: flex;
  gap: 16px;
  height: calc(100vh - 60px - 48px);
  min-height: 500px;
}

/* ============ 对话主区 ============ */
.chat-panel {
  flex: 1;
  min-width: 0;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(33, 150, 243, 0.08);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* 对话头部 */
.chat-header {
  padding: 16px 24px;
  border-bottom: 1px solid #e3eefb;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.chat-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 16px;
  font-weight: 700;
  color: #1a3a5c;
}

.title-icon {
  width: 32px;
  height: 32px;
  background: linear-gradient(135deg, #4facfe 0%, #2196f3 100%);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  color: #fff;
}

.mode-switcher { display: flex; gap: 6px; }
.mode-btn {
  padding: 7px 16px;
  font-size: 13px;
  background: #fff;
  border: 1px solid #e3eefb;
  border-radius: 8px;
  cursor: pointer;
  color: #4a5c6e;
  transition: all 0.2s;
}
.mode-btn:hover { background: #f0f7ff; color: #2196f3; border-color: #bbdefb; }
.mode-btn.active {
  background: linear-gradient(135deg, #4facfe 0%, #2196f3 100%);
  border-color: transparent;
  color: #fff;
  box-shadow: 0 2px 8px rgba(33, 150, 243, 0.25);
}
.mode-btn.danger {
  color: #e53935;
  border-color: transparent;
  background: #ffebee;
}
.mode-btn.danger:hover {
  background: #ffcdd2;
  color: #c62828;
  border-color: transparent;
  box-shadow: 0 2px 8px rgba(244, 67, 54, 0.2);
}

/* 清除对话按钮：与整体蓝白风格一致，但带淡蓝色警示 */
.mode-btn.clear-btn {
  background: #fff;
  color: #4a5c6e;
  border: 1px solid #e3eefb;
}
.mode-btn.clear-btn:hover {
  background: #e8f4ff;
  color: #1565c0;
  border-color: #bbdefb;
  box-shadow: 0 2px 8px rgba(33, 150, 243, 0.15);
}

/* 知识库选择栏 */
.kb-select-bar {
  padding: 10px 24px;
  background: #e3f2fd;
  border-bottom: 1px solid #bbdefb;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
}
.kb-label { font-weight: 600; color: #1565c0; }
.kb-select { min-width: 220px; }

/* 消息列表 */
.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  background: #fafdff;
}

.message-row {
  display: flex;
  margin-bottom: 20px;
  align-items: flex-start;
  gap: 12px;
}
.message-row.user { justify-content: flex-end; }
.message-row.assistant { justify-content: flex-start; }

.msg-avatar {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  flex-shrink: 0;
  font-weight: 600;
}

.avatar-user {
  background: linear-gradient(135deg, #4facfe 0%, #2196f3 100%);
  color: #fff;
}

.avatar-ai {
  background: #ffffff;
  padding: 0;
  overflow: hidden;
  border: 1px solid #e3eefb;
  box-shadow: 0 2px 6px rgba(33, 150, 243, 0.15);
}
.avatar-ai img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.msg-bubble {
  max-width: 65%;
  padding: 14px 18px;
  border-radius: 12px;
  line-height: 1.7;
  font-size: 14px;
  word-wrap: break-word;
}

.user-bubble {
  background: linear-gradient(135deg, #4facfe 0%, #2196f3 100%);
  color: #fff;
  border-radius: 12px 2px 12px 12px;
  box-shadow: 0 2px 8px rgba(33, 150, 243, 0.25);
}

.ai-bubble {
  background: #fff;
  border: 1px solid #e3eefb;
  color: #1a3a5c;
  border-radius: 2px 12px 12px 12px;
  box-shadow: 0 2px 6px rgba(33, 150, 243, 0.06);
}

.ai-label {
  font-size: 11px;
  color: #66bb6a;
  font-weight: 600;
  margin-bottom: 4px;
}

.ai-text {
  white-space: pre-wrap;
  word-break: break-word;
  animation: ai-text-appear 0.35s ease;
}

@keyframes ai-text-appear {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ============ 加载中小动画（省略号跳动） ============ */
.dots-inline {
  display: inline-block;
  width: 18px;
  text-align: left;
}
.dots-inline::after {
  content: '...';
  animation: dots-ellipsis 1.4s steps(4, end) infinite;
}
@keyframes dots-ellipsis {
  0% { content: ''; }
  25% { content: '.'; }
  50% { content: '..'; }
  75% { content: '...'; }
  100% { content: ''; }
}


/* 输入区 */
.input-area {
  border-top: 1px solid #e3eefb;
  background: #fff;
  padding: 12px 24px 16px;
}

.input-toolbar {
  display: flex;
  gap: 6px;
  margin-bottom: 8px;
}

.tool-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: #f0f7ff;
  border: 1px solid transparent;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  color: #4a5c6e;
  transition: all 0.2s;
}
.tool-btn:hover { background: #e3f2fd; border-color: #bbdefb; color: #2196f3; }
.tool-icon { font-size: 14px; }

.input-wrapper { }

.chat-input :deep(.el-textarea__inner) {
  border: 1px solid #e3eefb;
  resize: none;
  padding: 12px 14px;
  font-size: 14px;
  line-height: 1.7;
  border-radius: 10px;
  background: #fafdff;
  color: #1a3a5c;
}
.chat-input :deep(.el-textarea__inner:focus) {
  border-color: #4facfe;
  background: #fff;
  box-shadow: 0 0 0 3px rgba(79, 172, 254, 0.15);
}

.input-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0 0 0;
}
.char-count { font-size: 12px; color: #9ab; }
.send-btn {
  padding: 8px 28px;
  background: linear-gradient(135deg, #4facfe 0%, #2196f3 100%);
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 2px 8px rgba(33, 150, 243, 0.25);
}
.send-btn:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(33, 150, 243, 0.35); }
.send-btn:disabled { background: #bbdefb; cursor: not-allowed; box-shadow: none; opacity: 0.8; }

/* ============ 右侧快捷问面板 ============ */
.quick-panel {
  width: 240px;
  flex-shrink: 0;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(33, 150, 243, 0.08);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.quick-header {
  padding: 16px 20px;
  background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 15px;
  font-weight: 700;
  color: #1565c0;
  border-bottom: 1px solid #bbdefb;
}

.quick-title-icon { font-size: 18px; }

.quick-list {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.quick-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  background: #fafdff;
  border: 1px solid #e3eefb;
  border-radius: 10px;
  cursor: pointer;
  font-size: 13px;
  color: #4a5c6e;
  text-align: left;
  transition: all 0.2s;
}
.quick-item:hover {
  background: #e3f2fd;
  border-color: #4facfe;
  color: #2196f3;
  transform: translateX(3px);
  box-shadow: 0 2px 8px rgba(33, 150, 243, 0.15);
}

.quick-icon { font-size: 16px; }
.quick-text { flex: 1; }

/* 底部提示 */
.quick-tip {
  padding: 14px 16px;
  background: #fff8e1;
  border-top: 1px solid #ffe082;
  display: flex;
  gap: 8px;
  font-size: 12px;
  color: #795548;
  line-height: 1.5;
}
.tip-icon { font-size: 14px; flex-shrink: 0; }

/* ============ 滚动条（统一风格） ============ */
.message-list::-webkit-scrollbar,
.sidebar::-webkit-scrollbar,
.quick-list::-webkit-scrollbar,
.main-content::-webkit-scrollbar {
  width: 6px;
}
.message-list::-webkit-scrollbar-thumb,
.sidebar::-webkit-scrollbar-thumb,
.quick-list::-webkit-scrollbar-thumb,
.main-content::-webkit-scrollbar-thumb {
  background: #bbdefb;
  border-radius: 3px;
}
.message-list::-webkit-scrollbar-thumb:hover,
.sidebar::-webkit-scrollbar-thumb:hover,
.quick-list::-webkit-scrollbar-thumb:hover,
.main-content::-webkit-scrollbar-thumb:hover {
  background: #90caf9;
}
.message-list::-webkit-scrollbar-track,
.sidebar::-webkit-scrollbar-track,
.quick-list::-webkit-scrollbar-track,
.main-content::-webkit-scrollbar-track {
  background: transparent;
}

/* ============ 响应式 ============ */
@media (max-width: 960px) {
  .chat-layout { flex-direction: column; height: auto; }
  .quick-panel { width: 100%; max-height: 280px; }
  .msg-bubble { max-width: 80%; }
}

/* ============ 图片上传与预览 ============ */
.pending-image {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 12px;
  padding: 10px;
  background: #fafdff;
  border: 1px solid #e3eefb;
  border-radius: 10px;
}
.pending-image img {
  width: 64px;
  height: 64px;
  object-fit: cover;
  border-radius: 8px;
  border: 1px solid #e3eefb;
}
.pending-image-info {
  display: flex;
  flex: 1;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.pending-image-name {
  font-size: 13px;
  color: #4a5c6e;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.remove-image {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #ffcdd2;
  color: #c62828;
  border: none;
  font-size: 18px;
  line-height: 1;
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
}
.remove-image:hover { background: #ef9a9a; color: #fff; }

/* 消息中的图片显示 */
.msg-image {
  margin-bottom: 8px;
  cursor: pointer;
}
.msg-image img {
  max-width: 240px;
  max-height: 240px;
  border-radius: 10px;
  display: block;
  border: 2px solid rgba(255, 255, 255, 0.5);
  transition: transform 0.2s;
}
.msg-image img:hover { transform: scale(1.02); }
.msg-text { line-height: 1.6; word-break: break-word; }

/* 图片全屏预览遮罩 */
.image-preview-mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 35, 65, 0.9);
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: zoom-out;
  padding: 40px;
}
.preview-image {
  max-width: 90vw;
  max-height: 90vh;
  object-fit: contain;
  border-radius: 8px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.4);
}
.preview-close {
  position: absolute;
  top: 24px;
  right: 24px;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.95);
  color: #1a3a5c;
  border: none;
  font-size: 28px;
  line-height: 1;
  cursor: pointer;
  transition: all 0.2s;
  z-index: 1;
}
.preview-close:hover { background: #fff; transform: rotate(90deg); }

/* 更新：输入区 tip-text 和输入栏样式 */
.tip-text {
  font-size: 11px;
  color: #9ab;
}
</style>
