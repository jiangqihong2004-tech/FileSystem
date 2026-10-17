/**
 * 用户状态管理（轻量级，使用 Vue3 reactive）
 */
import { reactive } from 'vue'
import { getToken, setToken, removeToken, getUserInfo, setUserInfo, removeUserInfo } from '@/utils/storage'
import { getMe } from '@/api/auth'
import { getStats } from '@/api/settings'
import * as kbApi from '@/api/kb'
import * as fileApi from '@/api/file'
import * as folderApi from '@/api/folder'

// 全局共享的默认配额（用户未登录时回退到此值）
const DEFAULT_QUOTA = 8 * 1024 * 1024 * 1024

const state = reactive({
  token: getToken() || '',
  userInfo: getUserInfo() || { id: null, username: '', email: '', role: 'user', create_time: '', storage_quota: DEFAULT_QUOTA },
  // 共享的存储用量：避免在 Home / AiChat / KnowledgeBase 三个视图之间切换时，
  // 不会因为组件重建导致的 "0 → 正确值" 闪烁
  storageStats: {
    totalFiles: 0,
    totalSize: 0,
    totalFolders: 0,
    recycleCount: 0,
    todayUploads: 0,
    categoryStats: {},
    storageQuota: DEFAULT_QUOTA,
    storageUsed: 0,
    storagePercent: 0,
    // 是否已加载过一次：已加载过的情况下进入页面不再闪烁
    loadedAt: 0,
  },
  // 知识库共享缓存（进入 /knowledge 路由不再从空列表起步）
  kb: {
    kbList: [],
    kbListLoadedAt: 0,
    activeKbId: null,
    // docsMap[kbId] = { loadedAt: Number, docs: Array }
    docsMap: {},
  },
  // 回收站共享缓存（组件切换保持，避免从空数组起步产生闪烁）
  recycle: { files: [], folders: [], loadedAt: 0 },
  // 文件/文件夹视图共享缓存：按 view 缓存，避免菜单切换时的空列表跳变
  // views[view] = { files: Array, folders: Array, currentFolderId: Number, loadedAt: Number }
  views: {},
  // 全局文件夹列表（左侧面包屑等）
  allFolders: { items: [], loadedAt: 0 },
})

export function useUserStore() {
  function setLoginData(token, userInfo) {
    state.token = token
    state.userInfo = { ...state.userInfo, ...userInfo }
    setToken(token)
    setUserInfo(state.userInfo)
  }

  function logout() {
    state.token = ''
    state.userInfo = { id: null, username: '', email: '', role: 'user', create_time: '', storage_quota: DEFAULT_QUOTA }
    // 登出时清空缓存的存储用量与知识库，避免显示旧用户的数据
    resetStorageStats()
    resetKbCache()
    removeToken()
    removeUserInfo()
  }

  function resetStorageStats() {
    state.storageStats.totalFiles = 0
    state.storageStats.totalSize = 0
    state.storageStats.totalFolders = 0
    state.storageStats.recycleCount = 0
    state.storageStats.todayUploads = 0
    state.storageStats.categoryStats = {}
    state.storageStats.storageQuota = DEFAULT_QUOTA
    state.storageStats.storageUsed = 0
    state.storageStats.storagePercent = 0
    state.storageStats.loadedAt = 0
  }

  function resetKbCache() {
    state.kb.kbList = []
    state.kb.kbListLoadedAt = 0
    state.kb.activeKbId = null
    state.kb.docsMap = {}
  }

  async function refreshRecycle(force = false) {
    const now = Date.now()
    const ONE_MINUTE = 60 * 1000
    if (!force && state.recycle.loadedAt && now - state.recycle.loadedAt < ONE_MINUTE) {
      return true
    }
    try {
      const [fileRes, folderRes] = await Promise.all([
        fileApi.getRecycleList(),
        folderApi.getRecycleFolderList(),
      ])
      if (fileRes.code === 200) state.recycle.files = fileRes.data
      if (folderRes.code === 200) state.recycle.folders = folderRes.data
      state.recycle.loadedAt = now
    } catch (e) { console.error('获取回收站数据失败:', e) }
    return false
  }

  function resetRecycleCache() {
    state.recycle.files = []
    state.recycle.folders = []
    state.recycle.loadedAt = 0
  }

  // ---------- 文件与文件夹视图共享缓存 ----------
  // 保证：在全部文件 / 图片 / 文档 / 视频 / 音乐 / 压缩包之间切换时，
  // 先显示已缓存的内容，不出现空列表跳变。
  // 后台异步刷新最新数据，刷新完成后自动更新（响应式）。

  function _ensureView(view) {
    if (!state.views[view]) {
      state.views[view] = { files: [], folders: [], currentFolderId: 0, loadedAt: 0 }
    }
    return state.views[view]
  }

  /**
   * 刷新文件列表（仅 'all' 视图需要 folderId）。
   * @param {string} view - 'all' | 'image' | 'doc' | 'video' | 'audio' | 'archive'
   * @param {{force?: boolean, folderId?: number, keyword?: string}} opts
   */
  async function refreshViewFiles(view, opts = {}) {
    const { force = false, folderId = 0, keyword = '' } = opts
    const cache = _ensureView(view)
    const now = Date.now()
    const SHORT_CACHE = 30 * 1000
    if (!force && cache.loadedAt && now - cache.loadedAt < SHORT_CACHE) return true
    try {
      const params = {
        page: 1, size: 200,
        keyword: keyword || '',
      }
      if (view === 'all') params.folder_id = folderId
      else params.category = view
      const res = await fileApi.getFileList(params)
      if (res.code === 200) cache.files = res.data?.list || (Array.isArray(res.data) ? res.data : [])
      cache.loadedAt = now
      cache.currentFolderId = folderId
    } catch (e) { console.error(`刷新文件列表失败[${view}]:`, e) }
    return false
  }

  /**
   * 刷新文件夹列表（仅 'all' 视图有）。
   */
  async function refreshViewFolders(view, opts = {}) {
    const { force = false, folderId = 0, keyword = '' } = opts
    const cache = _ensureView(view)
    if (view !== 'all') { cache.folders = []; return true }
    const now = Date.now()
    const SHORT_CACHE = 30 * 1000
    if (!force && cache.loadedAt && now - cache.loadedAt < SHORT_CACHE) return true
    try {
      const res = await folderApi.getFolderList({ parent_id: folderId, keyword: keyword || '' })
      if (res.code === 200) cache.folders = res.data || []
      cache.loadedAt = now
      cache.currentFolderId = folderId
    } catch (e) { console.error(`刷新文件夹列表失败[${view}]:`, e) }
    return false
  }

  /**
   * 刷新全部文件夹（用于面包屑等场景）。
   */
  async function refreshAllFolders(force = false) {
    const now = Date.now()
    const SHORT_CACHE = 60 * 1000
    if (!force && state.allFolders.loadedAt && now - state.allFolders.loadedAt < SHORT_CACHE) return true
    try {
      const res = await folderApi.getFolderList({ keyword: '' })
      if (res.code === 200) state.allFolders.items = res.data || []
      state.allFolders.loadedAt = now
    } catch (e) { console.error('刷新全部文件夹失败:', e) }
    return false
  }

  /**
   * 一次调用刷新当前视图的文件+文件夹+全局文件夹列表。
   */
  async function refreshView(view, opts = {}) {
    const { force = false, folderId = 0, keyword = '' } = opts
    return Promise.all([
      refreshViewFiles(view, { force, folderId, keyword }),
      refreshViewFolders(view, { force, folderId, keyword }),
      refreshAllFolders(force),
    ])
  }

  /**
   * 重置某一视图缓存（例如上传、删除、重命名后）。
   */
  function resetView(view) {
    if (state.views[view]) {
      state.views[view].files = []
      state.views[view].folders = []
      state.views[view].loadedAt = 0
    }
  }

  function resetAllViews() {
    state.views = {}
    state.allFolders = { items: [], loadedAt: 0 }
  }

  async function fetchUserInfo() {
    try {
      const res = await getMe()
      if (res.code === 200) {
        state.userInfo = { ...state.userInfo, ...res.data }
        setUserInfo(state.userInfo)
      }
    } catch (e) {
      console.error('获取用户信息失败:', e)
    }
  }

  /**
   * 刷新共享的存储用量。
   * - force=true 时强制执行一次网络请求，用于上传 / 删除 / 恢复等操作后立即更新；
   * - force=false 时，仅在 5 分钟内还没加载过才发起请求，避免路由切换时的闪烁。
   */
  async function refreshStorageStats(force = false) {
    const now = Date.now()
    const FIVE_MINUTES = 5 * 60 * 1000
    if (!force && state.storageStats.loadedAt && now - state.storageStats.loadedAt < FIVE_MINUTES) {
      // 直接使用缓存的已存在的值，不重新发起请求
      return
    }
    try {
      const res = await getStats()
      if (res.code === 200) {
        const data = res.data || {}
        Object.assign(state.storageStats, data)
        state.storageStats.storageQuota = data.storageQuota || state.storageStats.storageQuota || DEFAULT_QUOTA
        state.storageStats.loadedAt = now
      }
    } catch (e) {
      console.error('获取存储用量失败:', e)
    }
  }

  /**
   * 刷新知识库列表（缓存优先）。
   * 返回 true 表示已使用缓存（路由切换无闪烁），false 表示触发了网络请求。
   */
  async function refreshKbList(force = false) {
    const now = Date.now()
    const FIVE_MINUTES = 5 * 60 * 1000
    if (!force && state.kb.kbListLoadedAt && now - state.kb.kbListLoadedAt < FIVE_MINUTES) {
      // 使用已有缓存，无需请求
      return true
    }
    try {
      const res = await kbApi.listKnowledgeBases()
      if (res && res.code === 200 && Array.isArray(res.data)) {
        state.kb.kbList = res.data
        // 如果当前没有选中的知识库，自动选择第一个
        if (!state.kb.activeKbId && state.kb.kbList.length > 0) {
          state.kb.activeKbId = state.kb.kbList[0].id
        }
      }
      state.kb.kbListLoadedAt = now
    } catch (e) {
      console.error('获取知识库列表失败:', e)
    }
    return false
  }

  /**
   * 刷新指定知识库的文档列表（缓存优先）。
   */
  async function refreshKbDocs(kbId, force = false) {
    if (!kbId) return true
    const now = Date.now()
    const FIVE_MINUTES = 5 * 60 * 1000
    const cached = state.kb.docsMap[kbId]
    if (!force && cached && cached.loadedAt && now - cached.loadedAt < FIVE_MINUTES) {
      return true
    }
    try {
      const res = await kbApi.listKbDocuments(kbId)
      const list = (res && res.code === 200 && Array.isArray(res.data)) ? res.data : []
      state.kb.docsMap[kbId] = { loadedAt: now, docs: list }
    } catch (e) {
      console.error('获取文档列表失败:', e)
      state.kb.docsMap[kbId] = { loadedAt: now, docs: [] }
    }
    return false
  }

  /**
   * 选择知识库（同时刷新该知识库的文档缓存）。
   */
  function selectKb(kb) {
    if (!kb) return
    state.kb.activeKbId = kb.id
    refreshKbDocs(kb.id, false)
  }

  return {
    state,
    setLoginData,
    logout,
    fetchUserInfo,
    refreshStorageStats,
    resetStorageStats,
    refreshKbList,
    refreshKbDocs,
    selectKb,
    resetKbCache,
    refreshRecycle,
    resetRecycleCache,
    refreshViewFiles,
    refreshViewFolders,
    refreshAllFolders,
    refreshView,
    resetView,
    resetAllViews,
  }
}
