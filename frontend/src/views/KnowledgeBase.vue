<template>
  <div class="app-container">
    <!-- 顶部导航栏（与首页一致） -->
    <div class="top-header">
      <div class="header-logo" @click="goHome">
        <div class="logo-icon">📁</div>
        <span>FileManager</span>
      </div>
      <div class="header-title-bar">
        <span class="page-tag">📚 知识库</span>
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
      <!-- 左侧菜单（与首页一致） -->
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
          <div class="menu-item" @click="goToAi"><span class="icon">🤖</span><span>AI智能助手</span></div>
          <div class="menu-item active"><span class="icon">📚</span><span>知识库</span></div>
          <div class="menu-item" @click="goHome('profile')"><span class="icon">👤</span><span>个人中心</span></div>
          <div class="menu-item" v-if="isAdmin" @click="goHome('admin')"><span class="icon">⚙️</span><span>系统设置</span></div>
        </div>
        <!-- 存储用量（蓝色渐变卡片） -->
        <div class="storage-card">
          <div class="title">💾 存储用量</div>
          <div class="bar"><div class="bar-inner" :style="{width: storagePercent + '%'}"></div></div>
          <div class="text">{{ formatSize(stats.totalSize) }} / {{ formatSize(storageQuota) }}</div>
        </div>
      </div>

      <!-- 右侧主内容区 -->
      <div class="main-content">
        <!-- 顶部统计卡片 -->
        <div class="stats-row">
          <div class="stat-card kb">
            <div class="stat-icon">📚</div>
            <div class="stat-info">
              <div class="value">{{ kbList.length }}</div>
              <div class="label">知识库总数</div>
            </div>
          </div>
          <div class="stat-card doc">
            <div class="stat-icon">📄</div>
            <div class="stat-info">
              <div class="value">{{ totalDocs }}</div>
              <div class="label">文档总数</div>
            </div>
          </div>
          <div class="stat-card chunk">
            <div class="stat-icon">🧩</div>
            <div class="stat-info">
              <div class="value">{{ totalChunks }}</div>
              <div class="label">向量片段</div>
            </div>
          </div>
          <div class="stat-card ai">
            <div class="stat-icon">🤖</div>
            <div class="stat-info">
              <div class="value">
                <span class="action-btn" @click="goToAi">去问答 →</span>
              </div>
              <div class="label">AI 智能问答</div>
            </div>
          </div>
        </div>

        <!-- 主体：知识库列表 + 文档列表 -->
        <div class="content-panels">
          <!-- 左侧：知识库列表 -->
          <div class="kb-panel">
            <div class="panel-header">
              <div class="panel-title">
                <span class="panel-icon">📚</span>
                <span>我的知识库</span>
              </div>
              <button class="action-btn primary" @click="showCreateKb = true">+ 新建</button>
            </div>
            <div class="kb-list" v-loading="kbListLoading">
              <div v-if="kbList.length === 0 && !kbListLoading" class="empty-state">
                <div class="empty-icon">📚</div>
                <div class="empty-text">暂无知识库</div>
                <div class="empty-sub">点击上方"新建"创建第一个知识库</div>
              </div>
              <div
                v-for="kb in kbList"
                :key="'kb-' + kb.id"
                class="kb-item"
                :class="{ active: activeKbId === kb.id }"
                @click="selectKb(kb)"
              >
                <div class="kb-icon">📁</div>
                <div class="kb-info">
                  <div class="kb-name">{{ kb.name }}</div>
                  <div class="kb-desc" v-if="kb.description">{{ kb.description }}</div>
                  <div class="kb-meta">
                    <span class="meta-tag">📄 {{ kb.doc_count }} 文档</span>
                    <span class="meta-tag">🧩 {{ kb.chunk_count }} 片段</span>
                    <span class="meta-tag" v-if="kb.create_time">🕒 {{ formatDate(kb.create_time) }}</span>
                  </div>
                </div>
                <div class="kb-actions" @click.stop>
                  <button class="action-btn sm" @click="onDownloadKb(kb)" title="打包下载">下载</button>
                  <button class="action-btn sm" @click="onRenameKb(kb)" title="重命名">重命名</button>
                  <button
                    class="action-btn sm danger"
                    @click.stop="onDeleteKb(kb.id)"
                    title="删除知识库"
                  >删除</button>
                </div>
              </div>
            </div>
          </div>

          <!-- 右侧：文档列表 -->
          <div class="doc-panel">
            <div class="panel-header" v-if="activeKb">
              <div class="panel-title">
                <span class="panel-icon">📄</span>
                <span>{{ activeKb.name }} - 文档列表</span>
              </div>
              <el-upload
                :show-file-list="false"
                :before-upload="onBeforeDocUpload"
                :http-request="onUploadDoc"
                accept=".doc,.docx,.pdf,.xls,.xlsx,.csv,.txt"
                multiple
                style="display: inline-block"
              >
                <button class="action-btn success">+ 上传文档</button>
              </el-upload>
            </div>
            <div class="panel-header" v-else>
              <div class="panel-title">
                <span class="panel-icon">📄</span>
                <span>请从左侧选择或新建一个知识库</span>
              </div>
            </div>

            <div class="doc-list" v-loading="docListLoading" v-if="activeKbId">
              <div v-if="docList.length === 0 && !docListLoading" class="empty-state">
                <div class="empty-icon">📄</div>
                <div class="empty-text">暂无文档</div>
                <div class="empty-sub">点击右上角"上传文档"添加文档</div>
              </div>
              <div v-for="d in docList" :key="'doc-' + d.id" class="doc-item">
                <div class="doc-icon-wrap" :class="[getFileTypeClass(d.original_name), d.status]">
                  <span class="doc-icon">{{ getFileIcon(d.original_name) }}</span>
                </div>
                <div class="doc-info">
                  <div class="doc-name">{{ d.original_name }}</div>
                  <div class="doc-meta">
                    <span class="meta-item">📦 {{ formatSize(d.file_size) }}</span>
                    <span class="meta-item" v-if="d.status === 'ready'">✅ 已向量化（{{ d.chunk_count || 0 }} 段）</span>
                    <span class="meta-item status-failed" v-else-if="d.status === 'failed'" style="color:#e53935">❌ 解析失败：{{ d.status_msg || '未知错误' }}</span>
                    <span class="meta-item" v-else style="color:#fb8c00">⏳ 处理中...</span>
                    <span class="meta-item" v-if="d.create_time">🕒 {{ formatDate(d.create_time) }}</span>
                  </div>
                </div>
                <div class="doc-actions">
                  <button class="action-btn" @click="onDownloadDoc(d)">下载</button>
                  <button class="action-btn" @click="onRenameDoc(d)">重命名</button>
                  <button class="action-btn" @click="onMoveDoc(d)">移动</button>
                  <button class="action-btn danger" @click="onDeleteDoc(d)">删除</button>
                </div>
              </div>
            </div>

            <!-- 未选择知识库时显示使用指南 -->
            <div class="guide-panel" v-if="!activeKbId">
              <div class="guide-header">
                <div class="guide-icon">📖</div>
                <div class="guide-title">知识库使用指南</div>
              </div>
              <div class="guide-steps">
                <div class="step-item">
                  <div class="step-num">1</div>
                  <div class="step-content">
                    <div class="step-title">创建知识库</div>
                    <div class="step-desc">点击左侧"新建"按钮创建一个知识库（例如：通讯录、产品文档、常见问题等）</div>
                  </div>
                </div>
                <div class="step-item">
                  <div class="step-num">2</div>
                  <div class="step-content">
                    <div class="step-title">上传文档</div>
                    <div class="step-desc">在知识库中上传 doc/docx/pdf/xls/xlsx/csv/txt 等格式的文档</div>
                  </div>
                </div>
                <div class="step-item">
                  <div class="step-num">3</div>
                  <div class="step-content">
                    <div class="step-title">自动向量化</div>
                    <div class="step-desc">文档上传后会自动进行向量化处理，存储到数据库中</div>
                  </div>
                </div>
                <div class="step-item">
                  <div class="step-num">4</div>
                  <div class="step-content">
                    <div class="step-title">智能问答</div>
                    <div class="step-desc">切换到 AI 智能助手页面，选择"知识库问答"模式，即可基于知识库内容进行智能问答</div>
                  </div>
                </div>
                <div class="step-item">
                  <div class="step-num">5</div>
                  <div class="step-content">
                    <div class="step-title">AI 检索回答</div>
                    <div class="step-desc">AI 会根据您的问题检索相关文档片段，并基于这些片段生成答案</div>
                  </div>
                </div>
              </div>
              <div class="guide-footer">
                <button class="action-btn primary" @click="showCreateKb = true">📚 立即创建知识库</button>
                <button class="action-btn" @click="goToAi">🤖 去问答</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 新建知识库对话框 -->
    <el-dialog v-model="showCreateKb" width="460px" custom-class="kb-dialog" :close-on-click-modal="false">
      <template #header>
        <div class="dialog-header">
          <span class="dialog-icon">📚</span>
          <span>新建知识库</span>
        </div>
      </template>
      <div class="dialog-body">
        <div class="form-group">
          <label class="form-label">知识库名称</label>
          <el-input
            v-model="createForm.name"
            placeholder="例如：通讯录、产品手册、常见问题..."
            maxlength="50"
            show-word-limit
            size="large"
            @keyup.enter="onCreateKb"
          />
        </div>
        <div class="form-group">
          <label class="form-label">描述<em class="optional">（可选）</em></label>
          <el-input
            v-model="createForm.description"
            type="textarea"
            :rows="4"
            maxlength="200"
            show-word-limit
            placeholder="简要说明该知识库的内容和用途"
          />
        </div>
      </div>
      <template #footer>
        <div class="dialog-footer">
          <button class="action-btn" @click="showCreateKb = false">取消</button>
          <button class="action-btn primary" @click="onCreateKb">创建</button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { formatSize } from '@/utils/format'
import * as kbApi from '@/api/kb'

const router = useRouter()
const { state, logout, fetchUserInfo, refreshStorageStats, refreshKbList, refreshKbDocs, selectKb } = useUserStore()

// 用户信息
const userInfo = computed(() => state.userInfo)
const isAdmin = computed(() => userInfo.value.role === 'admin')

// 存储用量（从全局 store 读取，避免路由切换组件重建导致的闪烁）
const stats = computed(() => state.storageStats)
const storageQuota = computed(() => (stats.value.storageQuota || state.userInfo?.storage_quota || 8 * 1024 * 1024 * 1024))
const storagePercent = computed(() => Math.min(100, ((stats.value.totalSize || 0) / storageQuota.value * 100)).toFixed(1))

// 知识库状态（从 store 读取，避免路由切换时的空列表闪烁）
const kbListLoading = ref(false)
const docListLoading = ref(false)
const kbList = computed(() => state.kb.kbList)
const activeKbId = computed(() => state.kb.activeKbId)
const activeKb = computed(() => state.kb.kbList.find(k => k.id === state.kb.activeKbId) || null)
const totalDocs = computed(() => state.kb.kbList.reduce((s, k) => s + (k.doc_count || 0), 0))
const totalChunks = computed(() => state.kb.kbList.reduce((s, k) => s + (k.chunk_count || 0), 0))
const docList = computed(() => {
  const id = state.kb.activeKbId
  if (!id) return []
  return (state.kb.docsMap[id] && state.kb.docsMap[id].docs) || []
})
// 用于移动文档对话框的候选知识库（排除当前知识库）
const otherKbList = computed(() => (state.kb.kbList || []).filter(k => k.id !== state.kb.activeKbId))
// UI 本地状态（不参与缓存）
const showCreateKb = ref(false)
const createForm = ref({ name: '', description: '' })

onMounted(async () => {
  // 进入页面时先尝试从缓存展示，避免组件重建造成数字闪烁
  await loadStats()
  await loadKbList()
  // 若已有缓存选中的知识库，顺便刷新文档列表（缓存也会优先）
  if (state.kb.activeKbId) await refreshKbDocs(state.kb.activeKbId, false)
})

async function loadStats() {
  try { await fetchUserInfo() } catch (e) { console.error(e) }
  try { await refreshStorageStats(false) } catch (e) { console.error(e) }
}

// ============ 导航 ============
function goHome(v) { router.push({ path: '/', query: v ? { view: v } : {} }) }
function goToAi() { router.push('/ai-assistant') }

function handleUserCommand(cmd) {
  if (cmd === 'home') goHome('all')
  else if (cmd === 'logout') { logout(); router.push('/login') }
}

// ============ 知识库列表 ============
async function loadKbList() {
  try {
    kbListLoading.value = true
    await refreshKbList(false)
  } catch (e) { console.error(e) } finally { kbListLoading.value = false }
}

// ============ 文档列表 ============
async function loadDocList(kbId) {
  if (!kbId) return
  try {
    docListLoading.value = true
    await refreshKbDocs(kbId, false)
  } catch (e) { console.error(e) } finally { docListLoading.value = false }
}

// ============ 创建知识库 ============
async function onCreateKb() {
  const name = (createForm.value.name || '').trim()
  if (!name) { ElMessage.warning('请输入知识库名称'); return }
  try {
    const res = await kbApi.createKnowledgeBase(name, createForm.value.description || '')
    if (res && res.code === 200) {
      ElMessage.success('知识库创建成功')
      createForm.value = { name: '', description: '' }
      showCreateKb.value = false
      await refreshKbList(true) // 强制刷新，保证新库可见
      if (res.data && res.data.id) selectKb({ id: res.data.id, ...res.data })
    }
  } catch (e) { ElMessage.error('创建知识库失败') }
}

// ============ 删除知识库 ============
async function onDeleteKb(kbId) {
  try {
    await ElMessageBox.confirm('确认删除该知识库？所有文档和向量化片段都会被删除', '提示', { type: 'warning' })
    const res = await kbApi.deleteKnowledgeBase(kbId)
    if (res && res.code === 200) {
      ElMessage.success('已删除')
      // 清理被删除库的文档缓存
      if (state.kb.docsMap[kbId]) delete state.kb.docsMap[kbId]
      if (state.kb.activeKbId === kbId) {
        state.kb.activeKbId = null
      }
      await refreshKbList(true) // 强制刷新列表
    }
  } catch (e) { if (e !== 'cancel') ElMessage.error('删除失败') }
}

// ============ 下载知识库（打包下载所有文档） ============
async function onDownloadKb(kb) {
  try {
    const res = await kbApi.downloadKbAll(kb.id, (kb.name || 'knowledge_base') + '.zip')
    if (res && res.ok !== false) ElMessage.success('已开始下载知识库「' + (kb.name || '') + '」')
  } catch (e) { ElMessage.error('下载失败') }
}

// ============ 重命名知识库 ============
async function onRenameKb(kb) {
  try {
    const { value } = await ElMessageBox.prompt('请输入新的知识库名称', '重命名知识库', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      inputValue: kb.name || '',
      inputPlaceholder: '请输入新的知识库名称',
    })
    const newName = (value || '').trim()
    if (!newName) return
    const res = await kbApi.renameKnowledgeBase(kb.id, newName, kb.description || '')
    if (res && res.code === 200) {
      ElMessage.success('重命名成功')
      await refreshKbList(true)
    }
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') ElMessage.error('重命名失败')
  }
}

// ============ 文档上传 ============
function onBeforeDocUpload(file) {
  if (!state.kb.activeKbId) { ElMessage.warning('请先选择一个知识库'); return false }
  const isOk = /\.(doc|docx|pdf|xls|xlsx|csv|txt)$/i.test(file.name)
  if (!isOk) { ElMessage.warning('仅支持 doc/docx/pdf/xls/xlsx/csv/txt 格式'); return false }
  if (file.size > 20 * 1024 * 1024) { ElMessage.warning('文件大小不能超过 20MB'); return false }
  return true
}

async function onUploadDoc(opt) {
  if (!state.kb.activeKbId) return
  try {
    const res = await kbApi.uploadKbDocument(state.kb.activeKbId, opt.file)
    if (res && res.code === 200) {
      const doc = res.data || {}
      if (doc.status === 'ready') {
        ElMessage.success(`「${doc.original_name || opt.file.name}」上传成功，已完成向量化（${doc.chunk_count || 0} 段）`)
      } else if (doc.status === 'failed') {
        ElMessage.warning(`「${doc.original_name || opt.file.name}」上传成功但解析失败：${doc.status_msg || ''}`)
      } else {
        ElMessage.success(`「${doc.original_name || opt.file.name}」上传成功，正在处理...`)
      }
      // 强制刷新，使用户看到最新文档
      await refreshKbDocs(state.kb.activeKbId, true)
      await refreshKbList(true)
    } else {
      const errMsg = (res && (res.message || res.msg)) || '未知错误，请检查网络'
      ElMessage.error(`文档上传失败：${errMsg}`)
    }
  } catch (e) {
    const errDetail = (e && e.message) || (e && e.response && e.response.data && (e.response.data.detail || e.response.data.message)) || '网络异常'
    ElMessage.error(`文档上传失败：${errDetail}`)
  }
}

async function onDeleteDoc(d) {
  try {
    await ElMessageBox.confirm('确认删除文档「' + (d.original_name || '') + '」？', '提示', { type: 'warning' })
    const res = await kbApi.deleteKbDocument(d.id)
    if (res && res.code === 200) {
      ElMessage.success('已删除')
      await refreshKbDocs(state.kb.activeKbId, true)
      await refreshKbList(true)
    }
  } catch (e) { if (e !== 'cancel') ElMessage.error('删除失败') }
}

// ============ 下载文档 ============
async function onDownloadDoc(d) {
  try {
    const res = await kbApi.downloadKbDocument(d.id, d.original_name)
    if (res && res.ok !== false) ElMessage.success('已开始下载「' + (d.original_name || '文档') + '」')
  } catch (e) { ElMessage.error('下载失败') }
}

// ============ 重命名文档 ============
async function onRenameDoc(d) {
  try {
    const { value } = await ElMessageBox.prompt('请输入新的文件名', '重命名', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      inputValue: d.original_name || '',
      inputPlaceholder: '请输入新的文件名',
    })
    const newName = (value || '').trim()
    if (!newName) return
    const res = await kbApi.renameKbDocument(d.id, newName)
    if (res && res.code === 200) {
      ElMessage.success('重命名成功')
      await refreshKbDocs(state.kb.activeKbId, true)
    }
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') ElMessage.error('重命名失败')
  }
}

// ============ 移动文档到其他知识库 ============
async function onMoveDoc(d) {
  try {
    if (!otherKbList.value || otherKbList.value.length === 0) {
      ElMessage.warning('当前没有可移动到的知识库，请先创建其他知识库')
      return
    }
    // 使用 ElementPlus 的 select 对话框——这里用简化版：弹一个 prompt 让用户输入 kb id
    // 为了更易用，我们改成显示选项对话框（ElMessageBox 支持自定义选项）
    const options = otherKbList.value.map(k => ({ label: k.name, value: k.id }))
    // 为了简单、可用、易实现，使用 ElMessageBox 选择对话框的替代：使用 ElMessage 提示 + ElInput 选择
    // 这里直接使用 ElMessageBox.prompt + 列表提示的简化版
    const promptText =
      '可用知识库（输入目标知识库 ID）：\n' + options.slice(0, 10).map(o => `  ${o.value} - ${o.label}`).join('\n')
    const { value } = await ElMessageBox.prompt(promptText, '移动到哪个知识库？', {
      confirmButtonText: '移动',
      cancelButtonText: '取消',
      inputPlaceholder: '例如：' + (options[0] && options[0].value),
    })
    const targetKbId = parseInt((value || '').trim(), 10)
    if (!targetKbId) return
    const res = await kbApi.moveKbDocument(d.id, targetKbId)
    if (res && res.code === 200) {
      ElMessage.success('已移动到目标知识库')
      // 强制刷新两个知识库的文档列表
      await refreshKbDocs(state.kb.activeKbId, true)
      await refreshKbList(true)
    }
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') ElMessage.error('移动失败')
  }
}

// ============ 工具函数 ============
function getFileIcon(name) {
  if (!name) return '📄'
  const ext = (name.split('.').pop() || '').toLowerCase()
  const map = { pdf: '📕', doc: '📘', docx: '📘', xls: '📊', xlsx: '📊', csv: '📊', txt: '📝' }
  return map[ext] || '📄'
}
function getFileTypeClass(name) {
  if (!name) return 'file-default'
  const ext = (name.split('.').pop() || '').toLowerCase()
  const map = { pdf: 'file-pdf', doc: 'file-doc', docx: 'file-doc', xls: 'file-xls', xlsx: 'file-xls', csv: 'file-xls', txt: 'file-txt' }
  return map[ext] || 'file-default'
}
function formatDate(s) {
  if (!s) return ''
  const d = new Date(s)
  if (isNaN(d.getTime())) return s
  const pad = (n) => String(n).padStart(2, '0')
  return (
    d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()) +
    ' ' + pad(d.getHours()) + ':' + pad(d.getMinutes())
  )
}
</script>

<style scoped>
/* ============ 基础容器（与首页一致） ============ */
.app-container { display: flex; flex-direction: column; height: 100vh; }

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
.header-title-bar { flex: 1; display: flex; align-items: center; justify-content: center; }
.page-tag {
  padding: 8px 20px;
  background: linear-gradient(135deg, #4facfe 0%, #2196f3 100%);
  color: #fff;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(33, 150, 243, 0.2);
}
.header-user { margin-left: auto; display: flex; align-items: center; gap: 16px; }
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
.user-name { font-size: 14px; color: #1a3a5c; font-weight: 500; }

/* ============ 主体布局 ============ */
.app-body { flex: 1; display: flex; overflow: hidden; }

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
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}

/* ============ 顶部统计卡片（与首页风格一致） ============ */
.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
}
.stat-card {
  background: #fff;
  border-radius: 12px;
  padding: 18px 20px;
  display: flex;
  align-items: center;
  gap: 14px;
  box-shadow: 0 2px 8px rgba(33, 150, 243, 0.05);
  transition: all 0.2s;
}
.stat-card:hover { transform: translateY(-2px); box-shadow: 0 4px 14px rgba(33, 150, 243, 0.12); }
.stat-card .stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
}
.stat-card .stat-info .value { font-size: 22px; font-weight: 700; color: #1a3a5c; }
.stat-card .stat-info .label { font-size: 12px; color: #9ab; margin-top: 2px; }
.stat-card.kb .stat-icon { background: #e3f2fd; color: #2196f3; }
.stat-card.doc .stat-icon { background: #e8f5e9; color: #66bb6a; }
.stat-card.chunk .stat-icon { background: #fff3e0; color: #ff9800; }
.stat-card.ai .stat-icon { background: #f3e5f5; color: #9c27b0; }

.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 7px 16px;
  font-size: 13px;
  background: #fff;
  border: 1px solid #e3eefb;
  border-radius: 8px;
  cursor: pointer;
  color: #4a5c6e;
  font-weight: 500;
  transition: all 0.2s;
}
.action-btn:hover { background: #f0f7ff; border-color: #bbdefb; color: #2196f3; transform: translateY(-1px); }
.action-btn.primary {
  background: linear-gradient(135deg, #4facfe 0%, #2196f3 100%);
  border-color: transparent;
  color: #fff;
  box-shadow: 0 2px 8px rgba(33, 150, 243, 0.25);
}
.action-btn.primary:hover { transform: translateY(-1px); box-shadow: 0 4px 14px rgba(33, 150, 243, 0.35); }
.action-btn.success {
  background: linear-gradient(135deg, #81c784 0%, #66bb6a 100%);
  border-color: transparent;
  color: #fff;
  box-shadow: 0 2px 8px rgba(102, 187, 106, 0.25);
}
.action-btn.success:hover { transform: translateY(-1px); box-shadow: 0 4px 14px rgba(102, 187, 106, 0.35); }
.action-btn.danger {
  background: linear-gradient(135deg, #ff8a80 0%, #f44336 100%);
  border-color: transparent;
  color: #fff;
  box-shadow: 0 2px 8px rgba(244, 67, 54, 0.2);
}
.action-btn.danger:hover { transform: translateY(-1px); box-shadow: 0 4px 14px rgba(244, 67, 54, 0.3); }

/* ============ 内容面板容器 ============ */
.content-panels {
  flex: 1;
  display: flex;
  gap: 16px;
  min-height: 0;
}

/* ============ 知识库 / 文档 面板（统一卡片风格） ============ */
.kb-panel {
  width: 320px;
  flex-shrink: 0;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(33, 150, 243, 0.05);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.doc-panel {
  flex: 1;
  min-width: 0;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(33, 150, 243, 0.05);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-header {
  padding: 16px 20px;
  border-bottom: 1px solid #e3eefb;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.panel-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 15px;
  font-weight: 600;
  color: #1a3a5c;
}
.panel-icon {
  width: 28px;
  height: 28px;
  background: #e3f2fd;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
}

/* ============ 知识库列表 ============ */
.kb-list {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  background: #fafdff;
}
.kb-item {
  padding: 14px;
  background: #fff;
  border: 1px solid #e3eefb;
  border-radius: 10px;
  margin-bottom: 10px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 12px;
  transition: all 0.2s;
}
.kb-item:hover {
  background: #f0f7ff;
  border-color: #bbdefb;
  transform: translateX(3px);
  box-shadow: 0 2px 8px rgba(33, 150, 243, 0.08);
}
.kb-item.active {
  background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
  border-color: #2196f3;
  box-shadow: 0 2px 12px rgba(33, 150, 243, 0.15);
}
.kb-icon {
  width: 40px;
  height: 40px;
  background: linear-gradient(135deg, #4facfe 0%, #2196f3 100%);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  color: #fff;
  flex-shrink: 0;
}
.kb-item.active .kb-icon { background: #fff; color: #2196f3; }
.kb-actions {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex-shrink: 0;
}
.kb-actions .action-btn.sm {
  padding: 4px 10px;
  font-size: 12px;
  min-width: 60px;
}
.kb-info { flex: 1; min-width: 0; }
.kb-name { font-weight: 600; font-size: 14px; color: #1a3a5c; margin-bottom: 4px; }
.kb-desc { font-size: 12px; color: #789; margin-bottom: 6px; line-height: 1.4; }
.kb-meta { display: flex; gap: 6px; flex-wrap: wrap; }
.meta-tag { font-size: 11px; color: #5a6c7d; background: #f0f7ff; padding: 2px 6px; border-radius: 4px; }
.kb-item.active .meta-tag { background: rgba(255,255,255,0.6); color: #1565c0; }
.delete-btn {
  width: 28px;
  height: 28px;
  border: none;
  background: #ffebee;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.15s;
  flex-shrink: 0;
}
.delete-btn:hover { background: #f44336; transform: scale(1.15); }

/* ============ 文档列表 ============ */
.doc-list {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
}
.doc-item {
  padding: 16px;
  background: #fff;
  border: 1px solid #e3eefb;
  border-radius: 10px;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 14px;
  transition: all 0.2s;
}
.doc-item:hover {
  background: #fafdff;
  border-color: #bbdefb;
  box-shadow: 0 2px 10px rgba(33, 150, 243, 0.08);
}
.doc-icon-wrap {
  width: 48px;
  height: 48px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.doc-icon-wrap.file-pdf { background: #ffebee; }
.doc-icon-wrap.file-doc { background: #e3f2fd; }
.doc-icon-wrap.file-xls { background: #e8f5e9; }
.doc-icon-wrap.file-txt { background: #fff3e0; }
.doc-icon-wrap.file-default { background: #f3e5f5; }
.doc-icon { font-size: 22px; }

.doc-info { flex: 1; min-width: 0; }
.doc-name {
  font-size: 14px;
  font-weight: 600;
  color: #1a3a5c;
  margin-bottom: 6px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.doc-meta { display: flex; gap: 12px; flex-wrap: wrap; }
.meta-item { font-size: 12px; color: #789; display: flex; align-items: center; gap: 3px; }
.doc-actions { display: flex; gap: 6px; flex-shrink: 0; }

/* ============ 空状态 ============ */
.empty-state {
  text-align: center;
  padding: 60px 20px;
}
.empty-icon { font-size: 48px; margin-bottom: 12px; opacity: 0.6; }
.empty-text { font-size: 15px; color: #4a5c6e; font-weight: 600; margin-bottom: 6px; }
.empty-sub { font-size: 13px; color: #9ab; }

/* ============ 使用指南面板 ============ */
.guide-panel {
  flex: 1;
  padding: 30px 36px;
  overflow-y: auto;
  background: linear-gradient(135deg, #fafdff 0%, #f0f7ff 100%);
}
.guide-header {
  text-align: center;
  margin-bottom: 30px;
}
.guide-icon {
  font-size: 54px;
  margin-bottom: 10px;
}
.guide-title {
  font-size: 22px;
  font-weight: 700;
  color: #1a3a5c;
}
.guide-steps {
  display: flex;
  flex-direction: column;
  gap: 14px;
  max-width: 700px;
  margin: 0 auto 28px auto;
}
.step-item {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 18px 22px;
  background: #fff;
  border: 1px solid #e3eefb;
  border-radius: 12px;
  transition: all 0.2s;
}
.step-item:hover { border-color: #bbdefb; transform: translateX(3px); box-shadow: 0 2px 10px rgba(33, 150, 243, 0.08); }
.step-num {
  width: 36px;
  height: 36px;
  background: linear-gradient(135deg, #4facfe 0%, #2196f3 100%);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 16px;
  font-weight: 700;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(33, 150, 243, 0.2);
}
.step-title { font-size: 15px; font-weight: 600; color: #1a3a5c; margin-bottom: 4px; }
.step-desc { font-size: 13px; color: #5a6c7d; line-height: 1.6; }
.guide-footer {
  display: flex;
  gap: 12px;
  justify-content: center;
}
.guide-footer .action-btn { padding: 10px 24px; font-size: 14px; }

/* ============ 对话框美化 ============ */
.dialog-header {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 16px;
  font-weight: 600;
  color: #1a3a5c;
}
.dialog-icon { font-size: 22px; }
.dialog-body { padding: 4px 0; }
.form-group { margin-bottom: 18px; }
.form-label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #4a5c6e;
  margin-bottom: 8px;
}
.form-label .optional { font-style: normal; color: #9ab; font-weight: 400; font-size: 12px; margin-left: 4px; }
.dialog-footer { display: flex; justify-content: flex-end; gap: 10px; }
.dialog-footer .action-btn { padding: 8px 22px; font-size: 14px; }

/* ============ 滚动条（统一风格） ============ */
.kb-list::-webkit-scrollbar,
.doc-list::-webkit-scrollbar,
.main-content::-webkit-scrollbar,
.sidebar::-webkit-scrollbar,
.guide-panel::-webkit-scrollbar {
  width: 6px;
}
.kb-list::-webkit-scrollbar-thumb,
.doc-list::-webkit-scrollbar-thumb,
.main-content::-webkit-scrollbar-thumb,
.sidebar::-webkit-scrollbar-thumb,
.guide-panel::-webkit-scrollbar-thumb {
  background: #bbdefb;
  border-radius: 3px;
}
.kb-list::-webkit-scrollbar-thumb:hover,
.doc-list::-webkit-scrollbar-thumb:hover,
.main-content::-webkit-scrollbar-thumb:hover,
.sidebar::-webkit-scrollbar-thumb:hover,
.guide-panel::-webkit-scrollbar-thumb:hover {
  background: #90caf9;
}
.kb-list::-webkit-scrollbar-track,
.doc-list::-webkit-scrollbar-track,
.main-content::-webkit-scrollbar-track,
.sidebar::-webkit-scrollbar-track,
.guide-panel::-webkit-scrollbar-track {
  background: transparent;
}

/* ============ 响应式 ============ */
@media (max-width: 1200px) {
  .stats-row { grid-template-columns: repeat(2, 1fr); }
  .kb-panel { width: 280px; }
}
@media (max-width: 900px) {
  .content-panels { flex-direction: column; }
  .kb-panel { width: 100%; max-height: 300px; }
}
</style>
