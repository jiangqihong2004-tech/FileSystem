<template>
  <!-- 整体布局：与 FileManager 主界面一致，左侧侧边栏，右侧对话区 -->
  <div class="app-container">
    <!-- 顶部导航栏（与 Home 保持统一风格） -->
    <div class="top-header">
      <div class="header-logo">
        <div class="logo-icon">📁</div>
        <span>FileManager</span>
      </div>
      <div class="header-title">
        <span class="title-icon">🤖</span>
        <span class="title-text">AI 智能助手</span>
      </div>
      <div class="header-user">
        <el-dropdown @command="handleUserCommand">
          <div style="display:flex;align-items:center;gap:8px;cursor:pointer;">
            <div class="user-avatar">{{ (safeUserInfo.username || 'U').charAt(0).toUpperCase() }}</div>
            <div class="user-name">{{ safeUserInfo.username || '用户' }}</div>
            <el-icon><ArrowDown /></el-icon>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="home">文件管理</el-dropdown-item>
              <el-dropdown-item command="profile">个人中心</el-dropdown-item>
              <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>

    <div class="app-body">
      <!-- 左侧菜单（与 Home 保持一致风格） -->
      <div class="sidebar">
        <div class="sidebar-section">
          <div class="menu-item" @click="gotoView('all')">
            <span class="icon">📂</span><span>全部文件</span>
          </div>
        </div>
        <div class="sidebar-section">
          <div class="sidebar-section-title">文件分类</div>
          <div class="menu-item" @click="gotoView('image')"><span class="icon">🖼️</span><span>图片</span></div>
          <div class="menu-item" @click="gotoView('doc')"><span class="icon">📄</span><span>文档</span></div>
          <div class="menu-item" @click="gotoView('video')"><span class="icon">🎬</span><span>视频</span></div>
          <div class="menu-item" @click="gotoView('audio')"><span class="icon">🎵</span><span>音乐</span></div>
          <div class="menu-item" @click="gotoView('archive')"><span class="icon">🗜️</span><span>压缩包</span></div>
        </div>
        <div class="sidebar-section">
          <div class="sidebar-section-title">其他</div>
          <div class="menu-item" @click="gotoView('recycle')"><span class="icon">🗑️</span><span>回收站</span></div>
          <!-- 当前页面高亮 -->
          <div class="menu-item active" style="font-weight:600;">
            <span class="icon">🤖</span><span>AI智能助手</span>
          </div>
          <div class="menu-item" @click="gotoView('profile')"><span class="icon">👤</span><span>个人中心</span></div>
          <div class="menu-item" v-if="isAdmin" @click="gotoView('admin')"><span class="icon">⚙️</span><span>系统设置</span></div>
        </div>

        <!-- 快捷操作区 -->
        <div class="ai-quick-card">
          <div class="title">💡 试试问我</div>
          <div class="quick-list">
            <div class="quick-item" @click="quickAsk('现在几点了？')">现在几点了？</div>
            <div class="quick-item" @click="quickAsk('今天是什么日期？')">今天是什么日期？</div>
            <div class="quick-item" @click="quickAsk('介绍一下你自己')">介绍一下你自己</div>
            <div class="quick-item" @click="quickAsk('用一句话说明如何管理文件')">文件管理小技巧</div>
          </div>
          <el-button type="danger" plain size="small" @click="clearAll" style="width:100%;margin-top:8px;">
            🗑️ 清空对话历史
          </el-button>
        </div>

        <!-- 知识库管理区 -->
        <div class="kb-card">
          <div class="kb-card-header">
            <div class="title">📚 我的知识库</div>
            <el-button size="small" type="primary" @click="openCreateKbDialog">+ 新建</el-button>
          </div>

          <div class="kb-mode-switch">
            <div
              class="kb-mode-item"
              :class="{ active: chatMode === 'general' }"
              @click="switchChatMode('general')"
            >
              💬 通用助手
            </div>
            <div
              class="kb-mode-item"
              :class="{ active: chatMode === 'kb' }"
              @click="switchChatMode('kb')"
            >
              📚 知识库问答
            </div>
          </div>

          <div class="kb-list-body" v-loading="kbLoading">
            <div v-if="kbList.length === 0" class="kb-empty">
              还没有知识库，点击「新建」创建第一个知识库。
            </div>
            <div
              v-for="kb in kbList"
              :key="'kb-' + kb.id"
              class="kb-item"
              :class="{ active: activeKbId === kb.id && chatMode === 'kb' }"
              @click="selectKb(kb.id)"
            >
              <div class="kb-item-title">{{ kb.name }}</div>
              <div class="kb-item-meta">{{ kb.doc_count }} 文档 · {{ kb.chunk_count }} 片段</div>
              <div class="kb-item-desc" v-if="kb.description">{{ kb.description }}</div>
              <div class="kb-item-actions" v-if="activeKbId === kb.id">
                <el-upload
                  :show-file-list="false"
                  :before-upload="(f) => beforeUploadDoc(f, kb.id)"
                  :http-request="(o) => uploadDoc(o, kb.id)"
                  accept=".doc,.docx,.pdf,.xls,.xlsx,.csv,.txt"
                  multiple
                >
                  <el-button size="small" type="success" :loading="uploadingKbId === kb.id">📄 上传文档</el-button>
                </el-upload>
                <el-button size="small" type="danger" plain @click.stop="deleteKb(kb.id)">删除</el-button>
              </div>
              <div v-if="activeKbId === kb.id" class="kb-doc-list">
                <div
                  v-for="doc in docList"
                  :key="'doc-' + doc.id"
                  class="kb-doc-item"
                >
                  <span class="doc-name">{{ doc.original_name }}</span>
                  <span class="doc-status" :class="'status-' + doc.status">{{ doc.status }}</span>
                  <span class="doc-meta">{{ doc.chunk_count }} 段</span>
                  <el-button size="mini" type="danger" plain @click.stop="deleteDoc(doc.id)">删除</el-button>
                </div>
                <div v-if="docList.length === 0" class="kb-doc-empty">
                  还没有文档，点击上面「上传文档」开始。
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧对话区 -->
      <div class="main-content ai-main">
        <div class="ai-chat-panel">
          <!-- 对话展示区 -->
          <div class="chat-header">
            <div class="chat-title">
              <span class="icon">{{ chatMode === 'kb' ? '📚' : '🤖' }}</span>
              <span>{{ chatMode === 'kb' ? '知识库问答' : '与 AI 助手对话' }}</span>
              <span v-if="chatMode === 'kb' && activeKbName" class="chat-kb-tag">[{{ activeKbName }}]</span>
            </div>
            <div class="chat-tip" v-if="chatMode === 'kb'">
              选择左侧知识库后提问，AI 会基于上传文档中的内容回答。
            </div>
            <div class="chat-tip" v-else>
              支持多轮对话与图片识别。
            </div>
          </div>

          <div ref="chatBodyRef" class="chat-body">
            <!-- 空状态 -->
            <div v-if="currentMessages.length === 0" class="chat-empty">
              <div class="icon">{{ chatMode === 'kb' ? '📚' : '🤖' }}</div>
              <div class="text" v-if="chatMode === 'general'">你好！我是 FileManager AI 助手。</div>
              <div class="text" v-else>
                {{ activeKbId ? '已就绪，可以开始向知识库提问。' : '请先在左侧选择或新建一个知识库。' }}
              </div>
              <div class="sub">{{ chatMode === 'kb' ? '示例：张三的电话是多少？' : '试试发送消息开始对话吧 👋' }}</div>
            </div>

            <!-- 对话消息 -->
            <div
              v-for="(msg, idx) in currentMessages"
              :key="'msg-' + (msg.ts || idx) + '-' + chatMode"
              class="chat-message"
              :class="msg.role === 'user' ? 'is-user' : 'is-assistant'"
            >
              <div class="avatar">{{ msg.role === 'user' ? '👤' : '🤖' }}</div>
              <div class="bubble">
                <div class="role-label">{{ msg.role === 'user' ? '我' : (chatMode === 'kb' ? '知识库 AI' : 'AI 助手') }}</div>
                <div v-if="msg.image" class="msg-image">
                  <img :src="msg.image" :alt="msg.imageName || '图片'" @dblclick="openImagePreview(msg.image)" class="chat-msg-img" />
                </div>
                <div v-if="msg.content" class="content">{{ msg.content }}</div>
                <div v-if="msg.hits && msg.hits.length" class="msg-hits">
                  <div class="hits-title">📖 参考片段：</div>
                  <div v-for="(h, hi) in msg.hits" :key="'hit-' + hi" class="hit-item">
                    <span class="hit-score">[score: {{ h.score }}]</span>
                    <span class="hit-content">{{ String(h.content || '').slice(0, 120) }}{{ String(h.content || '').length > 120 ? '...' : '' }}</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- 加载中提示 -->
            <div v-if="loading" class="chat-message is-assistant">
              <div class="avatar">🤖</div>
              <div class="bubble">
                <div class="role-label">{{ chatMode === 'kb' ? '知识库 AI' : 'AI 助手' }}</div>
                <div class="content typing">
                  <span></span><span></span><span></span> 正在思考中...
                </div>
              </div>
            </div>
          </div>

          <!-- 图片全屏预览遮罩（全局 z-index 很高） -->
          <div
            v-if="previewImage"
            class="image-preview-mask"
            @click="closeImagePreview"
          >
            <img :src="previewImage" class="image-preview-img" @click.stop />
            <div class="image-preview-close" @click="closeImagePreview">×</div>
          </div>

          <!-- 底部输入区 -->
          <div class="chat-input-panel">
            <div v-if="pendingImage" class="pending-image-bar">
              <div class="preview">
                <img :src="pendingImage.dataUrl" :alt="pendingImage.name" />
              </div>
              <div class="meta">
                <div class="name">{{ pendingImage.name }}</div>
                <div class="tip">已选择图片，可在下方输入提问内容，或直接发送以识别图片。</div>
              </div>
              <button class="remove-btn" @click="cancelPendingImage">×</button>
            </div>
            <div class="input-row">
              <!-- 隐藏的原生 file input -->
              <input
                ref="imageFileInput"
                type="file"
                accept="image/jpeg,image/png,image/webp,image/gif,image/bmp"
                style="display:none"
                @change="onImageFileChange"
              />
              <!-- 图片上传按钮 -->
              <button
                type="button"
                class="image-btn"
                :disabled="loading"
                @click="triggerImageSelect"
                title="选择本地图片"
              >
                🖼️
              </button>
              <el-input
                v-model="inputText"
                type="textarea"
                :autosize="{ minRows: 1, maxRows: 4 }"
                :placeholder="pendingImage ? '输入对图片的提问（可不填），回车发送' : '请输入消息，回车发送（Shift+Enter 换行）'"
                maxlength="2000"
                show-word-limit
                @keydown.enter.exact.prevent="handleSend"
                :disabled="loading"
              />
              <el-button type="primary" :loading="loading" @click="handleSend" class="send-btn">
                {{ pendingImage ? '发送图片' : '发送' }}
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- 新建知识库对话框 -->
  <el-dialog v-model="showCreateKbDialog" title="新建知识库" width="460px" append-to-body>
    <el-form :model="createKbForm" label-width="80px">
      <el-form-item label="名称">
        <el-input v-model="createKbForm.name" placeholder="例如：通讯录、产品文档" maxlength="60" show-word-limit />
      </el-form-item>
      <el-form-item label="描述">
        <el-input
          v-model="createKbForm.description"
          type="textarea"
          :rows="3"
          maxlength="300"
          placeholder="选填，简短说明该知识库包含哪些内容"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="showCreateKbDialog = false">取消</el-button>
      <el-button type="primary" @click="onCreateKb">创建</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowDown } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import * as aiApi from '@/api/ai'
import * as kbApi from '@/api/kb'

const router = useRouter()
const { state, logout } = useUserStore()
const userInfo = computed(() => state.userInfo)
// 安全的 userInfo：确保永远不会是 null/undefined，避免模板中 `?.` 失败
const safeUserInfo = computed(() => {
  const ui = userInfo.value
  if (ui && typeof ui === 'object') return ui
  try {
    const raw = localStorage.getItem('fm_user_info')
    if (raw) {
      const parsed = JSON.parse(raw)
      if (parsed && typeof parsed === 'object') return parsed
    }
  } catch (_) {}
  return { id: null, username: '', email: '', role: 'user', create_time: '' }
})
const isAdmin = computed(() => safeUserInfo.value.role === 'admin')

// 会话模式：general=通用助手，kb=知识库问答
const chatMode = ref('general')
// 两种模式的消息列表互相隔离
const messagesGeneral = ref([])
const messagesKb = ref([])
const messages = computed(() => (chatMode.value === 'kb' ? messagesKb.value : messagesGeneral.value))
const inputText = ref('')
const loading = ref(false)
const chatBodyRef = ref(null)

// 图片上传相关
const imageFileInput = ref(null) // 隐藏 file input 的 DOM 引用
const pendingImage = ref(null)   // 已选择但尚未发送的图片 { name, dataUrl }
const previewImage = ref(null)   // 当前正在全屏预览的图片 dataUrl

// ============ 知识库相关 ============
const kbList = ref([])
const kbLoading = ref(false)
const activeKbId = ref(null)
const docList = ref([])
const uploadingKbId = ref(null)
const showCreateKbDialog = ref(false)
const createKbForm = ref({ name: '', description: '' })

const activeKbName = computed(() => {
  const kb = (kbList.value || []).find(k => k.id === activeKbId.value)
  return kb ? kb.name : ''
})

// 会话 id：以当前登录用户 id 为基础，实现用户之间隔离
// 若 userInfo.id 尚未加载（刷新瞬间 pinia 未填充），则尝试从本地缓存读取
// 仍拿不到则 fallback 为 'anonymous'，保证组件挂载不中断
function getSessionId() {
  try {
    // 优先：响应式 userInfo
    if (safeUserInfo.value && safeUserInfo.value.id) {
      return `user_${String(safeUserInfo.value.id)}`
    }
    // 回退：localStorage
    const raw = localStorage.getItem('fm_user_info')
    if (raw) {
      const ui = JSON.parse(raw)
      if (ui && ui.id) return `user_${String(ui.id)}`
    }
  } catch (_) {}
  return 'anonymous'
}
function ensureSessionId() {
  return getSessionId()
}

// 自动滚动到底部
function scrollToBottom() {
  nextTick(() => {
    if (chatBodyRef.value) {
      chatBodyRef.value.scrollTop = chatBodyRef.value.scrollHeight
    }
  })
}

watch([messagesGeneral, messagesKb, chatMode], () => scrollToBottom(), { deep: true })

// ============ 根据模式操作的当前消息 ref ============
function currentMessagesRef() {
  return chatMode.value === 'kb' ? messagesKb : messagesGeneral
}
function pushMessage(msg) {
  const ref = currentMessagesRef()
  try {
    ref.value.push(msg)
  } catch (_) {
    ref.value = [msg]
  }
}

// ============ 图片持久化（防止导航切换 / 刷新后图片消失） ============
// 图片 dataUrl 仅在前端保存到 localStorage（按用户隔离），
// 后端历史接口仅返回 role/content。加载时按后端返回消息的「顺序 + 角色」
// 合并前端缓存的图片，并在发送图片时同时写入缓存。
function _imgStoreKey() {
  return `fm_ai_images_${getSessionId() || 'guest'}`
}
function _loadImageCache() {
  try {
    const raw = localStorage.getItem(_imgStoreKey())
    if (!raw) return []
    const data = JSON.parse(raw)
    return Array.isArray(data) ? data : []
  } catch (e) {
    console.warn('图片缓存读取失败，已重置:', e)
    try {
      localStorage.removeItem(_imgStoreKey())
    } catch (_) {}
    return []
  }
}
function _saveImageCache(list) {
  try {
    // 最多保留最近 20 张图片，避免超出配额
    const trimmed = (list || []).slice(-20)
    // 单张图片超过 2MB 就不写入缓存（可在消息框内展示，但不持久化）
    const filtered = trimmed.filter(item => {
      if (!item || !item.image) return false
      // data:image/...;base64,xxx 大约是原大小的 4/3
      if (typeof item.image === 'string' && item.image.length > 2.8 * 1024 * 1024) {
        return false
      }
      return true
    })
    localStorage.setItem(_imgStoreKey(), JSON.stringify(filtered))
  } catch (e) {
    console.warn('图片缓存写入失败（可能超出配额），已清空旧缓存:', e)
    try {
      localStorage.removeItem(_imgStoreKey())
    } catch (_) {}
  }
}
function _appendImageToCache(msgImage) {
  if (!msgImage || !msgImage.image) return
  const list = _loadImageCache()
  list.push(msgImage)
  _saveImageCache(list)
}
function _clearImageCache() {
  try {
    localStorage.removeItem(_imgStoreKey())
  } catch (e) {
    console.warn('图片缓存清空失败:', e)
  }
}
// 图片缓存合并逻辑已迁移到 _mergeImagesIntoCache（异步路径，避免阻塞首次渲染）
// 此处保留空函数以防历史代码直接引用（无副作用）
function _mergeImagesIntoMessages(serverMessages) {
  if (!Array.isArray(serverMessages)) return []
  return serverMessages
}

// ============ 图片双击预览 ============
function openImagePreview(dataUrl) {
  if (!dataUrl) return
  previewImage.value = dataUrl
  // 阻止背景滚动
  document.body.style.overflow = 'hidden'
}
function closeImagePreview() {
  previewImage.value = null
  document.body.style.overflow = ''
}
// ESC 键关闭预览
function _onKeydown(e) {
  if (e.key === 'Escape' && previewImage.value) {
    closeImagePreview()
  }
}

// ============ 发送消息 ============
async function handleSend() {
  // 有图片则走图片发送流程
  if (pendingImage.value) {
    await handleSendImage()
    return
  }

  const text = (inputText.value || '').trim()
  if (!text) {
    try { ElMessage.warning('请输入消息内容') } catch (_) {}
    return
  }
  if (chatMode.value === 'kb' && !activeKbId.value) {
    ElMessage.warning('请先在左侧选择或新建一个知识库')
    return
  }
  if (loading.value) return

  pushMessage({ role: 'user', content: text, ts: Date.now() })
  inputText.value = ''
  loading.value = true

  try {
    if (chatMode.value === 'kb') {
      // 知识库问答模式
      const res = await kbApi.askKb(activeKbId.value, text)
      if (res && res.code === 200 && res.data) {
        pushMessage({
          role: 'assistant',
          content: res.data.answer || '',
          hits: Array.isArray(res.data.hits) ? res.data.hits.slice(0, 3) : [],
          ts: Date.now(),
        })
      } else {
        pushMessage({
          role: 'assistant',
          content: '（服务返回异常：' + ((res && res.message) || '未知') + '）',
          hits: [],
          ts: Date.now(),
        })
      }
    } else {
      // 通用助手模式
      const res = await aiApi.sendChatMessage({ session_id: getSessionId(), content: text })
      if (res && res.code === 200 && res.data) {
        pushMessage({ role: 'assistant', content: res.data.reply || '', ts: Date.now() })
      } else {
        pushMessage({
          role: 'assistant',
          content: '（服务返回异常：' + ((res && res.message) || '未知') + '）',
          ts: Date.now(),
        })
      }
    }
  } catch (e) {
    console.error(e)
    pushMessage({
      role: 'assistant',
      content: '（网络或服务异常，请稍后重试。）',
      ts: Date.now(),
    })
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

// ============ 图片选择与发送 ============
function triggerImageSelect() {
  if (loading.value) return
  const el = imageFileInput.value
  if (el && el.$el && el.$el.querySelector) {
    // Element Plus el-upload 模式
  }
  if (el && el.click) {
    el.click()
  } else if (el && el.$el && el.$el.click) {
    el.$el.click()
  }
}

function onImageFileChange(event) {
  const file = event.target.files && event.target.files[0]
  if (!file) return
  // 校验类型
  const allowed = /^image\/(jpeg|png|webp|gif|bmp|jpg)$/i
  if (!allowed.test(file.type)) {
    ElMessage.warning('仅支持 jpg/png/webp/gif/bmp 格式图片')
    event.target.value = ''
    return
  }
  // 大小限制 10MB
  if (file.size > 10 * 1024 * 1024) {
    ElMessage.warning('图片大小不能超过 10MB')
    event.target.value = ''
    return
  }
  const reader = new FileReader()
  reader.onload = (e) => {
    pendingImage.value = {
      name: file.name,
      dataUrl: e.target.result,
      file
    }
    scrollToBottom()
  }
  reader.readAsDataURL(file)
  event.target.value = ''
}

function cancelPendingImage() {
  pendingImage.value = null
}

async function handleSendImage() {
  if (!pendingImage.value) return
  if (loading.value) return

  // 仅在「通用助手」模式下支持图片（知识库问答聚焦文本内容）
  if (chatMode.value !== 'general') {
    ElMessage.info('知识库问答暂不支持图片上传；已自动切换到通用助手模式')
    chatMode.value = 'general'
  }

  const text = (inputText.value || '').trim()
  const now = Date.now()

  // 构造图片消息并推入消息列表（带预览、ts）
  const userMsg = {
    role: 'user',
    content: text || '',
    image: pendingImage.value.dataUrl,
    imageName: pendingImage.value.name,
    ts: now
  }
  pushMessage(userMsg)

  // 关键：将图片写入前端缓存（带内容签名，便于加载历史时恢复）
  try {
    _appendImageToCache({
      image: pendingImage.value.dataUrl,
      imageName: pendingImage.value.name,
      content: text,
      prefix: '[图片]',
      ts: now
    })
  } catch (e) {
    console.warn('图片缓存写入失败（忽略）:', e)
  }

  const file = pendingImage.value.file
  pendingImage.value = null
  inputText.value = ''
  loading.value = true
  scrollToBottom()

  try {
    const res = await aiApi.sendChatImage(file, text)
    if (res && res.code === 200 && res.data) {
      pushMessage({
        role: 'assistant',
        content: res.data.reply || '',
        ts: Date.now()
      })
    } else {
      pushMessage({
        role: 'assistant',
        content: '（服务返回异常：' + ((res && res.message) || '未知') + '）',
        ts: Date.now()
      })
    }
  } catch (e) {
    console.error(e)
    pushMessage({
      role: 'assistant',
      content: '（网络或服务异常，请稍后重试。图片识别请求可能超时，请重试或换一张更小的图片。）',
      ts: Date.now()
    })
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

// ============ 加载历史对话 ============
async function loadHistory() {
  // 1) 确保 messagesGeneral / messagesKb 永远是数组，避免渲染报错
  try {
    if (!Array.isArray(messagesGeneral.value)) messagesGeneral.value = []
    if (!Array.isArray(messagesKb.value)) messagesKb.value = []
  } catch (_) {
    messagesGeneral.value = []
    messagesKb.value = []
  }

  // 2) 读取后端「通用助手」文本历史（允许失败）
  let serverMsgs = []
  try {
    const res = await aiApi.getChatHistory(getSessionId())
    if (res && res.code === 200 && res.data && Array.isArray(res.data.messages)) {
      serverMsgs = res.data.messages
    } else if (res && res.data && Array.isArray(res.data.messages)) {
      serverMsgs = res.data.messages
    } else if (Array.isArray(res && res.messages)) {
      serverMsgs = res.messages
    } else {
      serverMsgs = []
    }
    serverMsgs = (serverMsgs || []).map((m, i) => {
      if (!m || typeof m !== 'object') return { role: 'assistant', content: '', ts: Date.now() + i }
      return Object.assign({ ts: Date.now() + i, role: 'assistant', content: '' }, m)
    })
  } catch (err) {
    console.warn('加载 AI 历史对话失败（忽略）:', err)
    serverMsgs = []
  }

  // 3) 把文本历史写入通用助手消息列表
  try {
    messagesGeneral.value = serverMsgs
  } catch (e) {
    console.warn('messagesGeneral 赋值异常:', e)
    messagesGeneral.value = []
  }

  // 4) 异步合并图片缓存（延迟到下一个事件循环，避免大 base64 解析阻塞首次渲染）
  try {
    setTimeout(() => {
      try {
        const cache = _loadImageCache()
        if (!cache || !cache.length) {
          scrollToBottom()
          return
        }
        const merged = _mergeImagesIntoCache(messagesGeneral.value, cache)
        if (merged && Array.isArray(merged)) messagesGeneral.value = merged
      } catch (imgErr) {
        console.warn('图片缓存合并失败，已忽略:', imgErr)
      }
      scrollToBottom()
    }, 30)
  } catch (e) {
    console.warn('图片缓存读取异常:', e)
  }
}

// 将图片缓存与已渲染的 messages 合并（不阻塞主线程）
function _mergeImagesIntoCache(serverMessages, cache) {
  if (!Array.isArray(serverMessages) || !cache.length) return null

  const result = serverMessages.slice()
  let cursor = 0
  let changed = false
  for (let i = 0; i < result.length; i++) {
    const m = result[i]
    if (m.role !== 'user') continue
    if (cursor >= cache.length) break
    const cached = cache[cursor]
    const expected = (cached.prefix || '[图片]') + (cached.content || '')
    const matchExact = m.content === cached.content
    const matchExpected = m.content === expected
    const matchEmpty = cached.content === '' && /^\[图片\]/.test(m.content)
    if (matchExact || matchExpected || matchEmpty) {
      result[i] = Object.assign({}, m, {
        image: cached.image,
        imageName: cached.imageName,
        ts: m.ts || cached.ts || Date.now() + i
      })
      cursor += 1
      changed = true
    } else {
      // 全局搜索匹配（兜底）
      let foundIdx = -1
      for (let j = cursor; j < cache.length; j++) {
        const cj = cache[j]
        const expectedJ = (cj.prefix || '[图片]') + (cj.content || '')
        if (m.content === cj.content || m.content === expectedJ) {
          foundIdx = j
          break
        }
      }
      if (foundIdx >= 0) {
        const cj = cache[foundIdx]
        result[i] = Object.assign({}, m, {
          image: cj.image,
          imageName: cj.imageName,
          ts: m.ts || cj.ts || Date.now() + i
        })
        cursor = foundIdx + 1
        changed = true
      }
    }
  }
  return changed ? result : null
}

// ============ 快捷提问 ============
function quickAsk(q) {
  inputText.value = q
  nextTick(() => handleSend())
}

// ============ 清空对话 ============
async function clearAll() {
  const modeLabel = chatMode.value === 'kb' ? '知识库问答对话' : '通用助手对话'
  try {
    await ElMessageBox.confirm(`确认清空${modeLabel}的历史？此操作不可恢复。`, '提示', {
      confirmButtonText: '确定清空',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  try {
    if (chatMode.value === 'kb') {
      // 知识库问答的对话仅在前端页面维护，切换即消失
      messagesKb.value = []
    } else {
      const sid = ensureSessionId()
      await aiApi.clearChatSession(sid)
      messagesGeneral.value = []
      _clearImageCache() // 同时清空本地图片缓存
    }
    ElMessage.success('对话历史已清空')
  } catch (e) {
    console.error(e)
    ElMessage.error('清空失败')
  }
}

// ============ 知识库业务函数 ============
function switchChatMode(next) {
  if (!next) return
  if (next === chatMode.value) return
  chatMode.value = next
  scrollToBottom()
}

async function loadKnowledgeBases() {
  try {
    kbLoading.value = true
    const res = await kbApi.listKnowledgeBases()
    if (res && res.code === 200 && Array.isArray(res.data)) {
      kbList.value = res.data
      // 如果还没有选择的，选中第一个
      if (!activeKbId.value && kbList.value.length > 0) {
        selectKb(kbList.value[0].id)
      }
    } else {
      kbList.value = []
    }
  } catch (e) {
    console.error(e)
    kbList.value = []
  } finally {
    kbLoading.value = false
  }
}

async function selectKb(id) {
  activeKbId.value = id
  // 加载对应文档列表
  try {
    const res = await kbApi.listKbDocuments(id)
    if (res && res.code === 200 && Array.isArray(res.data)) {
      docList.value = res.data
    } else {
      docList.value = []
    }
  } catch (e) {
    console.error(e)
    docList.value = []
  }
}

function openCreateKbDialog() {
  createKbForm.value = { name: '', description: '' }
  showCreateKbDialog.value = true
}

async function onCreateKb() {
  const name = (createKbForm.value.name || '').trim()
  if (!name) {
    ElMessage.warning('请输入知识库名称')
    return
  }
  try {
    const res = await kbApi.createKnowledgeBase(name, (createKbForm.value.description || '').trim())
    if (res && res.code === 200) {
      showCreateKbDialog.value = false
      ElMessage.success('知识库创建成功')
      await loadKnowledgeBases()
      if (res.data && res.data.id) {
        // 选中新创建的
        await selectKb(res.data.id)
      }
    } else {
      ElMessage.error('创建失败')
    }
  } catch (e) {
    console.error(e)
    ElMessage.error('创建失败')
  }
}

async function deleteKb(id) {
  try {
    await ElMessageBox.confirm('确认删除该知识库？（文档与向量化数据将一并删除）', '提示', {
      type: 'warning',
    })
  } catch {
    return
  }
  try {
    const res = await kbApi.deleteKnowledgeBase(id)
    if (res && res.code === 200) {
      ElMessage.success('删除成功')
      if (activeKbId.value === id) {
        activeKbId.value = null
        docList.value = []
        messagesKb.value = []
      }
      await loadKnowledgeBases()
    }
  } catch (e) {
    console.error(e)
    ElMessage.error('删除失败')
  }
}

function beforeUploadDoc(file, kbId) {
  if (!file) return false
  const max = 20 * 1024 * 1024
  if (file.size > max) {
    ElMessage.warning('文件大小不能超过 20MB')
    return false
  }
  return true
}

async function uploadDoc(opt, kbId) {
  if (!opt || !opt.file) return
  if (!kbId) return
  uploadingKbId.value = kbId
  try {
    const res = await kbApi.uploadKbDocument(kbId, opt.file)
    if (res && res.code === 200) {
      ElMessage.success('文档已上传并向量化')
      await selectKb(kbId)
      await loadKnowledgeBases()
    } else {
      ElMessage.error('上传或向量化失败')
    }
  } catch (e) {
    console.error(e)
    ElMessage.error('上传或向量化失败')
  } finally {
    uploadingKbId.value = null
  }
}

async function deleteDoc(docId) {
  try {
    await ElMessageBox.confirm('确认删除该文档？（对应的向量化片段也会删除）', '提示', { type: 'warning' })
  } catch {
    return
  }
  try {
    const res = await kbApi.deleteKbDocument(docId)
    if (res && res.code === 200) {
      ElMessage.success('删除成功')
      if (activeKbId.value) await selectKb(activeKbId.value)
      await loadKnowledgeBases()
    }
  } catch (e) {
    console.error(e)
    ElMessage.error('删除失败')
  }
}

// ============ 顶栏下拉菜单 ============
function handleUserCommand(cmd) {
  if (cmd === 'home') router.push('/')
  else if (cmd === 'profile') router.push({ path: '/', query: { view: 'profile' } })
  else if (cmd === 'logout') handleLogout()
}

function handleLogout() {
  logout()
  router.push('/login')
}

// 跳转到文件管理主页的指定视图
function gotoView(view) {
  if (view === 'all') router.push('/')
  else router.push({ path: '/', query: { view } })
}

onMounted(() => {
  // 关键：先把 messages 置为数组，确保组件立即能渲染骨架，然后再做耗时的异步加载
  try {
    if (!Array.isArray(messagesGeneral.value)) messagesGeneral.value = []
    if (!Array.isArray(messagesKb.value)) messagesKb.value = []
  } catch (_) {
    messagesGeneral.value = []
    messagesKb.value = []
  }

  // 未登录则跳转
  if (!state.token) {
    try { router.push('/login') } catch (_) {}
    return
  }

  // ESC 关闭图片预览
  window.addEventListener('keydown', _onKeydown)

  // 延迟执行 loadHistory，让页面先完成首次渲染
  setTimeout(() => loadHistory(), 50)
  // 异步加载知识库列表
  setTimeout(() => loadKnowledgeBases(), 100)
})

onUnmounted(() => {
  try {
    window.removeEventListener('keydown', _onKeydown)
  } catch (_) {}
  // 组件卸载时确保恢复 body 滚动状态
  try { document.body.style.overflow = '' } catch (_) {}
})
</script>

<style scoped>
/* ============ 整体布局（与 Home.vue 保持一致） ============ */
.app-container { display: flex; flex-direction: column; height: 100vh; }
.top-header {
  height: 60px; background: #fff; box-shadow: 0 2px 8px rgba(33,150,243,0.08);
  display: flex; align-items: center; padding: 0 24px; z-index: 10;
}
.header-logo { display: flex; align-items: center; gap: 10px; font-size: 18px; font-weight: 700; color: #1a3a5c; min-width: 220px; }
.header-logo .logo-icon { width: 36px; height: 36px; background: linear-gradient(135deg,#4facfe 0%,#2196f3 100%); border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 20px; color: #fff; }
.header-title { flex: 1; display: flex; align-items: center; gap: 10px; font-size: 15px; color: #1565c0; font-weight: 600; padding-left: 12px; }
.header-title .title-icon { font-size: 22px; }
.header-user { margin-left: auto; display: flex; align-items: center; gap: 16px; }
.user-avatar { width: 36px; height: 36px; border-radius: 50%; background: linear-gradient(135deg,#4facfe 0%,#2196f3 100%); color: #fff; display: flex; align-items: center; justify-content: center; font-size: 14px; font-weight: 600; }
.user-name { font-size: 14px; color: #1a3a5c; font-weight: 500; }

.app-body { flex: 1; display: flex; overflow: hidden; }

/* ============ 侧边栏 ============ */
.sidebar { width: 220px; background: #fff; border-right: 1px solid #e3eefb; padding: 16px 0; display: flex; flex-direction: column; overflow-y: auto; }
.sidebar-section { padding: 8px 0; }
.sidebar-section-title { font-size: 11px; color: #9ab; padding: 8px 24px; letter-spacing: 1px; }
.menu-item { padding: 11px 24px; cursor: pointer; display: flex; align-items: center; gap: 12px; color: #4a5c6e; font-size: 14px; transition: all 0.2s; border-left: 3px solid transparent; }
.menu-item:hover { background: #f0f7ff; color: #2196f3; }
.menu-item.active { background: #e3f2fd; color: #2196f3; border-left-color: #2196f3; font-weight: 600; }
.menu-item .icon { font-size: 16px; width: 18px; text-align: center; }

/* ============ 快捷卡片 ============ */
.ai-quick-card { margin: 16px; padding: 16px; background: linear-gradient(135deg,#e3f2fd 0%,#bbdefb 100%); border-radius: 12px; }
.ai-quick-card .title { font-size: 13px; color: #1565c0; font-weight: 600; margin-bottom: 10px; }
.quick-list { display: flex; flex-direction: column; gap: 6px; }
.quick-item {
  font-size: 12px; color: #1565c0; padding: 8px 10px; border-radius: 8px; cursor: pointer;
  background: rgba(255,255,255,0.6); transition: all 0.2s;
}
.quick-item:hover { background: #fff; transform: translateX(4px); box-shadow: 0 2px 6px rgba(33,150,243,0.15); }

/* ============ 主内容区 ============ */
.main-content { flex: 1; padding: 24px; overflow: hidden; background: #f5f9ff; }
.ai-main { display: flex; align-items: stretch; justify-content: center; }
.ai-chat-panel {
  width: 100%; max-width: 960px; background: #fff; border-radius: 16px;
  box-shadow: 0 4px 20px rgba(33,150,243,0.08);
  display: flex; flex-direction: column; overflow: hidden;
}

/* 头部 */
.chat-header {
  padding: 18px 24px; border-bottom: 1px solid #e3eefb;
  display: flex; justify-content: space-between; align-items: center;
}
.chat-title { display: flex; align-items: center; gap: 10px; font-size: 16px; font-weight: 700; color: #1a3a5c; }
.chat-title .icon { font-size: 22px; }
.chat-tip { font-size: 12px; color: #7a8c9e; }

/* 对话展示区 */
.chat-body {
  flex: 1; overflow-y: auto; padding: 24px; background: linear-gradient(180deg,#f8fbff 0%,#ffffff 100%);
}
.chat-empty { text-align: center; padding: 80px 20px; color: #9ab; }
.chat-empty .icon { font-size: 64px; opacity: 0.6; margin-bottom: 16px; }
.chat-empty .text { font-size: 15px; color: #1a3a5c; font-weight: 500; }
.chat-empty .sub { font-size: 13px; margin-top: 6px; }

.chat-message { display: flex; gap: 12px; margin-bottom: 20px; align-items: flex-start; }
.chat-message .avatar {
  width: 40px; height: 40px; border-radius: 50%; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center; font-size: 20px;
  background: #e3f2fd;
}
.chat-message.is-user { flex-direction: row-reverse; }
.chat-message.is-user .avatar { background: linear-gradient(135deg,#4facfe,#2196f3); color: #fff; }

.chat-message .bubble {
  max-width: 72%; padding: 12px 16px; border-radius: 12px;
  background: #f0f7ff; border: 1px solid #e3eefb;
}
.chat-message.is-user .bubble {
  background: linear-gradient(135deg,#4facfe,#2196f3); color: #fff; border: none;
}
.chat-message .role-label {
  font-size: 11px; font-weight: 600; margin-bottom: 4px; opacity: 0.7;
}
.chat-message.is-user .bubble .role-label { color: rgba(255,255,255,0.85); }
.chat-message .bubble .content { font-size: 14px; line-height: 1.7; white-space: pre-wrap; word-break: break-word; }

.chat-message .bubble .content.typing { color: #7a8c9e; font-style: italic; }
.chat-message .bubble .content.typing span {
  display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: #7a8c9e;
  margin: 0 2px; animation: blink 1.2s infinite both;
}
.chat-message .bubble .content.typing span:nth-child(2) { animation-delay: 0.2s; }
.chat-message .bubble .content.typing span:nth-child(3) { animation-delay: 0.4s; }
@keyframes blink { 0%,80%,100% { opacity: 0.3; transform: scale(0.8); } 40% { opacity: 1; transform: scale(1); } }

/* 输入区 */
.chat-input-panel {
  padding: 16px 24px 20px;
  border-top: 1px solid #e3eefb;
  background: #fff;
}
.pending-image-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  background: #f0f7ff;
  border: 1px solid #d6e9fb;
  border-radius: 10px;
  margin-bottom: 12px;
}
.pending-image-bar .preview {
  width: 56px;
  height: 56px;
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
  border: 1px solid #d6e9fb;
  flex-shrink: 0;
}
.pending-image-bar .preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.pending-image-bar .meta {
  flex: 1;
  min-width: 0;
}
.pending-image-bar .name {
  font-size: 13px;
  color: #1a3a5c;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pending-image-bar .tip {
  font-size: 12px;
  color: #7a8c9e;
  margin-top: 2px;
}
.pending-image-bar .remove-btn {
  background: transparent;
  border: none;
  cursor: pointer;
  color: #7a8c9e;
  font-size: 22px;
  line-height: 1;
  padding: 6px 8px;
  border-radius: 6px;
  transition: all 0.2s;
}
.pending-image-bar .remove-btn:hover {
  background: #ffe4e4;
  color: #f56c6c;
}

.input-row {
  display: flex;
  align-items: flex-end;
  gap: 10px;
}
.image-btn {
  width: 44px;
  height: 44px;
  border-radius: 8px;
  border: 1px solid #d6e9fb;
  background: #f5faff;
  font-size: 20px;
  cursor: pointer;
  flex-shrink: 0;
  transition: all 0.2s;
}
.image-btn:hover:not(:disabled) {
  background: #e3f2fd;
  border-color: #2196f3;
}
.image-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.send-btn {
  height: 48px;
  min-width: 100px;
  flex-shrink: 0;
  font-weight: 600;
}
.input-tip {
  font-size: 11px;
  color: #9ab;
  margin-top: 8px;
  text-align: right;
}

/* 消息中的图片预览 */
.msg-image {
  margin: 4px 0 8px 0;
  max-width: 320px;
  border-radius: 10px;
  overflow: hidden;
  background: #fff;
  border: 1px solid #e3eefb;
}
.msg-image img.chat-msg-img {
  width: 100%;
  height: auto;
  display: block;
  max-height: 360px;
  object-fit: contain;
  cursor: zoom-in;
  transition: opacity 0.15s ease;
  background: #f7fbff;
}
.msg-image img.chat-msg-img:hover {
  opacity: 0.92;
}

/* ============ 图片全屏预览遮罩 ============ */
.image-preview-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.88);
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: zoom-out;
}
.image-preview-img {
  max-width: 92vw;
  max-height: 90vh;
  object-fit: contain;
  border-radius: 6px;
  background: #000;
  cursor: default;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
}
.image-preview-close {
  position: fixed;
  top: 20px;
  right: 28px;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.15);
  color: #fff;
  font-size: 28px;
  line-height: 36px;
  text-align: center;
  cursor: pointer;
  user-select: none;
  transition: background 0.15s ease;
}
.image-preview-close:hover {
  background: rgba(255, 255, 255, 0.3);
}

/* ============ 知识库模式头栏 ============ */
.chat-mode-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 24px;
  background: #f5faff;
  border-bottom: 1px solid #e3eefb;
}
.chat-mode-switcher {
  display: inline-flex;
  background: #fff;
  border: 1px solid #d6e9fb;
  border-radius: 20px;
  padding: 3px;
}
.chat-mode-tab {
  padding: 6px 16px;
  border-radius: 17px;
  font-size: 13px;
  color: #556;
  cursor: pointer;
  transition: all 0.18s ease;
}
.chat-mode-tab.active {
  background: linear-gradient(135deg, #2196f3, #1976d2);
  color: #fff;
  box-shadow: 0 2px 6px rgba(33, 150, 243, 0.25);
}
.chat-mode-hint {
  font-size: 12px;
  color: #7a8c9e;
}

/* ============ 知识库管理侧栏 ============ */
.kb-side-panel {
  width: 300px;
  border-right: 1px solid #e3eefb;
  background: #fbfdff;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}
.kb-section-title {
  padding: 12px 18px;
  font-size: 13px;
  font-weight: 600;
  color: #1a3a5c;
  background: linear-gradient(180deg, #fff, #f5faff);
  border-bottom: 1px solid #e3eefb;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.kb-section-title .kb-total-badge {
  font-size: 12px;
  color: #2196f3;
  background: #e3f2fd;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 500;
}
.kb-section-action {
  font-size: 12px;
  color: #2196f3;
  cursor: pointer;
  user-select: none;
}
.kb-section-action:hover {
  color: #1976d2;
  text-decoration: underline;
}
.kb-list {
  flex: 1;
  overflow-y: auto;
  padding: 10px 12px;
}
.kb-list::-webkit-scrollbar { width: 6px; }
.kb-list::-webkit-scrollbar-thumb { background: #cfd8e3; border-radius: 3px; }
.kb-list::-webkit-scrollbar-track { background: transparent; }
.kb-item {
  padding: 10px 12px;
  background: #fff;
  border: 1px solid #e3eefb;
  border-radius: 10px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: all 0.15s ease;
  position: relative;
}
.kb-item:hover {
  border-color: #2196f3;
  box-shadow: 0 2px 6px rgba(33, 150, 243, 0.12);
}
.kb-item.active {
  border-color: #2196f3;
  background: #e3f2fd;
  box-shadow: 0 2px 8px rgba(33, 150, 243, 0.15);
}
.kb-item-name {
  font-size: 13px;
  font-weight: 600;
  color: #1a3a5c;
  margin-bottom: 4px;
  word-break: break-all;
}
.kb-item-meta {
  font-size: 11px;
  color: #7a8c9e;
}
.kb-item-del {
  position: absolute;
  top: 6px;
  right: 8px;
  color: #c0c8d0;
  cursor: pointer;
  padding: 2px 6px;
  font-size: 14px;
  border-radius: 4px;
}
.kb-item-del:hover {
  color: #f56c6c;
  background: #ffe9e9;
}
.kb-empty {
  padding: 30px 20px;
  text-align: center;
  font-size: 12px;
  color: #9ab;
}
.kb-empty .icon { font-size: 32px; margin-bottom: 8px; display: block; }

.kb-doc-panel {
  border-top: 1px solid #e3eefb;
  background: #fff;
  max-height: 220px;
  overflow-y: auto;
}
.kb-doc-panel-title {
  padding: 10px 18px;
  font-size: 12px;
  font-weight: 600;
  color: #1a3a5c;
  background: #f5faff;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.kb-doc-list {
  padding: 6px 12px 12px;
}
.kb-doc-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  background: #fbfdff;
  border: 1px solid #e3eefb;
  border-radius: 8px;
  margin-bottom: 6px;
  font-size: 12px;
}
.kb-doc-item .doc-name {
  color: #1a3a5c;
  word-break: break-all;
  flex: 1;
  margin-right: 8px;
}
.kb-doc-item .doc-meta {
  color: #7a8c9e;
  font-size: 11px;
  margin-right: 6px;
}
.kb-doc-del {
  color: #c0c8d0;
  cursor: pointer;
  font-size: 14px;
  padding: 2px 6px;
  border-radius: 4px;
}
.kb-doc-del:hover {
  color: #f56c6c;
  background: #ffe9e9;
}
.kb-doc-upload {
  padding: 10px 12px;
  border-top: 1px dashed #d6e9fb;
  text-align: center;
}
.kb-upload-btn {
  display: inline-block;
  padding: 8px 18px;
  background: linear-gradient(135deg, #2196f3, #1976d2);
  color: #fff;
  border-radius: 20px;
  font-size: 12px;
  cursor: pointer;
  font-weight: 500;
  box-shadow: 0 2px 6px rgba(33, 150, 243, 0.25);
  transition: all 0.15s ease;
}
.kb-upload-btn:hover {
  box-shadow: 0 4px 10px rgba(33, 150, 243, 0.3);
  transform: translateY(-1px);
}
.kb-upload-btn.disabled {
  background: #c0c8d0;
  cursor: not-allowed;
  box-shadow: none;
}
.kb-doc-upload-tip {
  font-size: 11px;
  color: #9ab;
  margin-top: 6px;
}

/* 参考片段样式（知识库模式 AI 回复） */
.kb-ref-block {
  margin-top: 10px;
  padding: 10px 12px;
  background: #f5faff;
  border-left: 3px solid #2196f3;
  border-radius: 6px;
}
.kb-ref-title {
  font-size: 12px;
  font-weight: 600;
  color: #1a3a5c;
  margin-bottom: 6px;
}
.kb-ref-item {
  font-size: 12px;
  color: #556;
  padding: 4px 0;
  line-height: 1.5;
  border-top: 1px dashed #d6e9fb;
}
.kb-ref-item:first-child { border-top: none; }
.kb-ref-score {
  font-size: 11px;
  color: #2196f3;
  margin-left: 6px;
}
</style>
