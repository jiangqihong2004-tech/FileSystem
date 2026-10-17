<template>
  <div class="app-container">
    <!-- 顶部导航栏 -->
    <div class="top-header">
      <div class="header-logo" @click="switchView('all')">
        <div class="logo-icon">📁</div>
        <span>FileManager</span>
      </div>
      <!-- 视图切换：个人中心/系统设置显示蓝色胶囊标签，其他视图保留搜索框 -->
      <template v-if="view === 'profile'">
        <div class="header-title-bar"><span class="page-tag">👤 个人中心</span></div>
      </template>
      <template v-else-if="view === 'admin'">
        <div class="header-title-bar"><span class="page-tag">⚙️ 系统设置</span></div>
      </template>
      <template v-else>
        <div class="header-search">
          <el-input v-model="globalKeyword" placeholder="搜索文件名..." clearable @keyup.enter="handleSearch" @clear="handleSearch">
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
        </div>
      </template>
      <div class="header-user">
        <el-dropdown @command="handleUserCommand">
          <div style="display:flex;align-items:center;gap:8px;cursor:pointer;">
            <div class="user-avatar">{{ (userInfo.username || 'U').charAt(0).toUpperCase() }}</div>
            <div class="user-name">{{ userInfo.username }}</div>
            <el-icon><ArrowDown /></el-icon>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="profile">个人中心</el-dropdown-item>
              <el-dropdown-item v-if="isAdmin" command="admin" divided>系统设置</el-dropdown-item>
              <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>

    <div class="app-body">
      <!-- 左侧菜单 -->
      <div class="sidebar">
        <div class="sidebar-section">
          <div class="menu-item" :class="{active: view==='all'}" @click="switchView('all')">
            <span class="icon">📂</span><span>全部文件</span>
          </div>
        </div>
        <div class="sidebar-section">
          <div class="sidebar-section-title">文件分类</div>
          <div class="menu-item" :class="{active: view==='image'}" @click="switchView('image')"><span class="icon">🖼️</span><span>图片</span></div>
          <div class="menu-item" :class="{active: view==='doc'}" @click="switchView('doc')"><span class="icon">📄</span><span>文档</span></div>
          <div class="menu-item" :class="{active: view==='video'}" @click="switchView('video')"><span class="icon">🎬</span><span>视频</span></div>
          <div class="menu-item" :class="{active: view==='audio'}" @click="switchView('audio')"><span class="icon">🎵</span><span>音乐</span></div>
          <div class="menu-item" :class="{active: view==='archive'}" @click="switchView('archive')"><span class="icon">🗜️</span><span>压缩包</span></div>
        </div>
        <div class="sidebar-section">
          <div class="sidebar-section-title">其他</div>
          <div class="menu-item" :class="{active: view==='recycle'}" @click="switchView('recycle')"><span class="icon">🗑️</span><span>回收站</span></div>
          <div class="menu-item" :class="{active: view==='ai' || $route.path === '/ai-assistant'}" @click="goToAiAssistant"><span class="icon">🤖</span><span>AI智能助手</span></div>
          <div class="menu-item" :class="{active: view==='kb' || $route.path === '/knowledge'}" @click="goToKnowledge"><span class="icon">📚</span><span>知识库</span></div>
          <div class="menu-item" :class="{active: view==='profile'}" @click="switchView('profile')"><span class="icon">👤</span><span>个人中心</span></div>
          <div class="menu-item" v-if="isAdmin" :class="{active: view==='admin'}" @click="switchView('admin')"><span class="icon">⚙️</span><span>系统设置</span></div>
        </div>
        <!-- 存储用量 -->
        <div class="storage-card">
          <div class="title">💾 存储用量</div>
          <div class="bar"><div class="bar-inner" :style="{width: storagePercent + '%'}"></div></div>
          <div class="text">{{ formatSize(stats.totalSize) }} / {{ formatSize(storageQuota) }}</div>
        </div>
      </div>

      <!-- 主内容区 -->
      <div class="main-content">
        <!-- 全部文件 / 分类视图 -->
        <template v-if="['all','image','doc','video','audio','archive'].includes(view)">
          <!-- 统计卡片 -->
          <div class="stats-row">
            <div class="stat-card blue"><div class="stat-icon">📁</div><div class="stat-info"><div class="value">{{ stats.totalFiles }}</div><div class="label">文件总数</div></div></div>
            <div class="stat-card green"><div class="stat-icon">💾</div><div class="stat-info"><div class="value">{{ formatSize(stats.totalSize) }}</div><div class="label">已用空间</div></div></div>
            <div class="stat-card orange"><div class="stat-icon">📂</div><div class="stat-info"><div class="value">{{ stats.totalFolders }}</div><div class="label">文件夹数</div></div></div>
            <div class="stat-card purple"><div class="stat-icon">📊</div><div class="stat-info"><div class="value">{{ stats.todayUploads }}</div><div class="label">今日上传</div></div></div>
          </div>
          <!-- 工具栏 -->
          <div class="toolbar">
            <div class="breadcrumb">
              <span class="crumb" @click="goToFolder(0)">全部文件</span>
              <span v-for="item in breadcrumb" :key="item.id" class="crumb-arrow">/</span>
              <span v-for="item in breadcrumb" :key="'b'+item.id" class="crumb" @click="goToFolder(item.id)">{{ item.name }}</span>
            </div>
            <div class="toolbar-actions">
              <el-button type="primary" @click="showCreateFolder = true">新建文件夹</el-button>
              <el-button type="success" @click="triggerUpload">上传文件</el-button>
              <input type="file" ref="uploadInput" multiple style="display:none" @change="handleUpload">
              <el-button-group>
                <el-button :type="viewMode==='grid'?'primary':''" @click="viewMode='grid'">网格</el-button>
                <el-button :type="viewMode==='list'?'primary':''" @click="viewMode='list'">列表</el-button>
              </el-button-group>
            </div>
          </div>
          <!-- 批量操作栏 -->
          <div class="batch-bar" v-if="selectedIds.length > 0">
            <span>已选择 {{ selectedIds.length }} 项</span>
            <div>
              <el-button size="small" @click="showMoveDialog = true; moveTarget = null">批量移动</el-button>
              <el-button size="small" type="danger" @click="batchDelete">批量删除</el-button>
              <el-button size="small" @click="selectedIds = []">取消</el-button>
            </div>
          </div>
          <!-- 文件列表 -->
          <template v-if="displayList.length > 0">
            <div class="file-grid" v-if="viewMode === 'grid'">
              <div v-for="item in displayList" :key="item.type + '_' + item.id" class="file-card" :class="{selected: isSelected(item), 'folder-card': item.type==='folder'}" @click="handleCardClick(item, $event)">
                <input type="checkbox" class="checkbox" :checked="isSelected(item)" @click.stop="toggleSelect(item)">
                <div class="action-buttons">
                  <el-tooltip content="下载" placement="top" v-if="item.type === 'file'">
                    <div class="action-btn" @click.stop="downloadFile(item)"><el-icon><Download /></el-icon></div>
                  </el-tooltip>
                  <el-tooltip content="重命名" placement="top">
                    <div class="action-btn" @click.stop="openRename(item)"><el-icon><Edit /></el-icon></div>
                  </el-tooltip>
                  <el-tooltip content="移动" placement="top">
                    <div class="action-btn" @click.stop="showMoveDialog = true; moveTarget = item"><el-icon><FolderOpened /></el-icon></div>
                  </el-tooltip>
                  <el-tooltip content="删除" placement="top">
                    <div class="action-btn danger" @click.stop="deleteItem(item)"><el-icon><Delete /></el-icon></div>
                  </el-tooltip>
                </div>
                <div class="file-icon">{{ item.icon }}</div>
                <div class="file-name">{{ item.name }}</div>
                <div class="file-meta">{{ item.type === 'folder' ? item.file_count + ' 个文件' : formatSize(item.file_size) }}</div>
              </div>
            </div>
            <div class="file-table" v-else>
              <table>
                <thead><tr><th style="width:40px;"><input type="checkbox" :checked="allSelected" @change="toggleSelectAll"></th><th>名称</th><th style="width:120px;">大小</th><th style="width:180px;">上传时间</th><th style="width:280px;">操作</th></tr></thead>
                <tbody>
                  <tr v-for="item in displayList" :key="item.type + '_' + item.id" :class="{selected: isSelected(item)}">
                    <td><input type="checkbox" :checked="isSelected(item)" @change="toggleSelect(item)"></td>
                    <td><div class="name-cell"><span class="icon">{{ item.icon }}</span><span class="name" @click="handleCardClick(item)">{{ item.name }}</span></div></td>
                    <td>{{ item.type === 'folder' ? '-' : formatSize(item.file_size) }}</td>
                    <td>{{ item.time }}</td>
                    <td>
                      <div class="action-cell">
                        <el-button v-if="item.type==='file'" size="small" type="primary" plain @click="downloadFile(item)">
                          <el-icon><Download /></el-icon> 下载
                        </el-button>
                        <el-button size="small" type="primary" plain @click="openRename(item)">
                          <el-icon><Edit /></el-icon> 重命名
                        </el-button>
                        <el-button size="small" type="primary" plain @click="showMoveDialog = true; moveTarget = item">
                          <el-icon><FolderOpened /></el-icon> 移动
                        </el-button>
                        <el-button size="small" type="danger" plain @click="deleteItem(item)">
                          <el-icon><Delete /></el-icon> 删除
                        </el-button>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </template>
          <div class="empty-state" v-else>
            <div class="icon">📭</div>
            <div class="text">暂无文件，点击上方按钮上传或新建文件夹</div>
          </div>
        </template>

        <!-- 回收站视图 -->
        <template v-if="view === 'recycle'">
          <div class="toolbar">
            <div class="breadcrumb"><span style="color:#1a3a5c;font-weight:600;">🗑️ 回收站</span></div>
            <div class="toolbar-actions"><el-button type="danger" @click="clearRecycle" :disabled="recycleList.length === 0 && recycleFolderList.length === 0">清空回收站</el-button></div>
          </div>
          <div class="file-table" v-if="recycleList.length > 0 || recycleFolderList.length > 0">
            <table>
              <thead><tr><th>类型</th><th>名称</th><th style="width:120px;">大小</th><th style="width:160px;">原位置</th><th style="width:180px;">删除时间</th><th style="width:160px;">操作</th></tr></thead>
              <tbody>
                <tr v-for="item in [...recycleFolderList.map(f => ({...f, itemType: 'folder'})), ...recycleList.map(f => ({...f, itemType: 'file'}))]" :key="item.itemType + '_' + item.id">
                  <td><span class="icon">{{ item.itemType === 'folder' ? '📁' : (item.icon || '📄') }}</span></td>
                  <td><div class="name-cell"><span>{{ item.itemType === 'folder' ? item.folder_name : item.original_name }}</span></div></td>
                  <td>{{ item.itemType === 'folder' ? '-' : formatSize(item.file_size) }}</td>
                  <td>{{ item.itemType === 'folder' ? (item.parent_id === 0 ? '根目录' : '子目录') : (item.folder_name || '根目录') }}</td>
                  <td>{{ item.delete_time }}</td>
                  <td>
                    <el-button size="small" link type="primary" @click="restoreItem(item)">恢复</el-button>
                    <el-button size="small" link type="danger" @click="permanentDeleteItem(item)">彻底删除</el-button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="empty-state" v-else><div class="icon">🗑️</div><div class="text">回收站为空</div></div>
        </template>

        <!-- AI 智能助手（跳转到独立页面） -->
        <template v-if="view === 'ai'">
          <div class="ai-redirect-tip">
            <el-card>
              <template #header><span style="font-weight:600;color:#1a3a5c;">🤖 AI 智能助手</span></template>
              <p>正在跳转到 AI 智能助手页面...</p>
              <el-button type="primary" @click="goToAiAssistant">立即前往</el-button>
            </el-card>
          </div>
        </template>

        <!-- 个人中心 -->
        <template v-if="view === 'profile'">
          <div style="max-width:600px;margin:0 auto;">
            <el-card>
              <template #header><span style="font-weight:600;color:#1a3a5c;">👤 个人信息</span></template>
              <el-descriptions :column="1" border>
                <el-descriptions-item label="用户名">{{ userInfo.username }}</el-descriptions-item>
                <el-descriptions-item label="邮箱">{{ userInfo.email || '未设置' }}</el-descriptions-item>
                <el-descriptions-item label="角色"><el-tag :type="isAdmin ? 'danger' : 'primary'">{{ isAdmin ? '管理员' : '普通用户' }}</el-tag></el-descriptions-item>
                <el-descriptions-item label="注册时间">{{ userInfo.create_time || '-' }}</el-descriptions-item>
                <el-descriptions-item label="存储配额">{{ formatSize(userInfo.storage_quota || 1073741824) }}</el-descriptions-item>
              </el-descriptions>
            </el-card>
            <el-card style="margin-top:16px;">
              <template #header><span style="font-weight:600;color:#1a3a5c;">🔑 修改密码</span></template>
              <el-form label-width="100px">
                <el-form-item label="原密码"><el-input v-model="pwdForm.old_password" type="password" show-password></el-input></el-form-item>
                <el-form-item label="新密码"><el-input v-model="pwdForm.new_password" type="password" show-password></el-input></el-form-item>
                <el-form-item><el-button type="primary" @click="changePassword">确认修改</el-button></el-form-item>
              </el-form>
            </el-card>
          </div>
        </template>

        <!-- 管理员设置 -->
        <template v-if="view === 'admin'">
          <div style="max-width:800px;margin:0 auto;">
            <el-card>
              <template #header><span style="font-weight:600;color:#1a3a5c;">🌐 基本设置</span></template>
              <el-form label-width="120px">
                <el-form-item label="网站名称"><el-input v-model="settingsForm.site_name"></el-input></el-form-item>
                <el-form-item label="网站地址"><el-input v-model="settingsForm.site_url"></el-input></el-form-item>
                <el-form-item label="联系邮箱"><el-input v-model="settingsForm.contact_email"></el-input></el-form-item>
                <el-form-item label="网站描述"><el-input v-model="settingsForm.site_description" type="textarea"></el-input></el-form-item>
              </el-form>
            </el-card>
            <el-card style="margin-top:16px;">
              <template #header><span style="font-weight:600;color:#1a3a5c;">👥 注册设置</span></template>
              <el-form label-width="120px">
                <el-form-item label="允许注册"><el-switch v-model="settingsForm.allow_register"></el-switch></el-form-item>
                <el-form-item label="注册需审核"><el-switch v-model="settingsForm.register_audit"></el-switch></el-form-item>
                <el-form-item label="默认角色"><el-select v-model="settingsForm.default_role" style="width:200px;"><el-option label="普通用户" value="user"></el-option><el-option label="管理员" value="admin"></el-option></el-select></el-form-item>
                <el-form-item><el-button type="primary" @click="saveSettings">保存设置</el-button></el-form-item>
              </el-form>
            </el-card>
            <el-card style="margin-top:16px;">
              <template #header><span style="font-weight:600;color:#1a3a5c;">📋 用户管理</span></template>
              <el-table :data="userList" stripe>
                <el-table-column prop="id" label="ID" width="60"></el-table-column>
                <el-table-column prop="username" label="用户名"></el-table-column>
                <el-table-column prop="email" label="邮箱"></el-table-column>
                <el-table-column prop="role" label="角色" width="100"><template #default="{row}"><el-tag :type="row.role === 'admin' ? 'danger' : 'primary'">{{ row.role === 'admin' ? '管理员' : '用户' }}</el-tag></template></el-table-column>
                <el-table-column prop="status" label="状态" width="100"><template #default="{row}"><el-tag :type="row.status === 1 ? 'success' : (row.status === 0 ? 'warning' : 'danger')">{{ row.status === 1 ? '正常' : (row.status === 0 ? '待审核' : '禁用') }}</el-tag></template></el-table-column>
                <el-table-column prop="storage_quota" label="存储配额" width="120"><template #default="{row}">{{ formatSize(row.storage_quota || 1073741824) }}</template></el-table-column>
                <el-table-column label="操作" width="260"><template #default="{row}">
                  <el-button v-if="row.status !== 1" size="small" link type="primary" @click="updateUserStatus(row.id, 1)">启用</el-button>
                  <el-button v-if="row.status === 1 && row.role !== 'admin'" size="small" link type="warning" @click="updateUserStatus(row.id, 2)">禁用</el-button>
                  <el-button v-if="row.status === 0" size="small" link type="success" @click="updateUserStatus(row.id, 1)">通过审核</el-button>
                  <el-divider direction="vertical" />
                  <el-button size="small" link type="info" @click="openStorageQuotaDialog(row)">设置配额</el-button>
                </template></el-table-column>
              </el-table>
            </el-card>
          </div>
        </template>
      </div>
    </div>

    <!-- 新建文件夹对话框 -->
    <el-dialog v-model="showCreateFolder" title="新建文件夹" width="400px">
      <el-input v-model="newFolderName" placeholder="请输入文件夹名称" @keyup.enter="createFolder"></el-input>
      <template #footer><el-button @click="showCreateFolder = false">取消</el-button><el-button type="primary" @click="createFolder">确定</el-button></template>
    </el-dialog>

    <!-- 重命名对话框 -->
    <el-dialog v-model="showRename" title="重命名" width="400px">
      <el-input v-model="renameName" placeholder="请输入新名称" @keyup.enter="submitRename"></el-input>
      <template #footer><el-button @click="showRename = false">取消</el-button><el-button type="primary" @click="submitRename">确定</el-button></template>
    </el-dialog>

    <!-- 移动文件对话框 -->
    <el-dialog v-model="showMoveDialog" title="移动到" width="400px">
      <el-select v-model="moveTargetFolderId" placeholder="选择目标文件夹" style="width:100%;">
        <el-option label="根目录" :value="0"></el-option>
        <el-option v-for="f in allFolders" :key="f.id" :label="f.folder_path" :value="f.id"></el-option>
      </el-select>
      <template #footer><el-button @click="showMoveDialog = false">取消</el-button><el-button type="primary" @click="submitMove">确定</el-button></template>
    </el-dialog>

    <!-- 文件预览对话框 -->
    <el-dialog v-model="showPreview" :title="previewFile.name || previewFile.original_name" width="80%" top="5vh">
      <div style="text-align:center;max-height:75vh;overflow:auto;">
        <img v-if="previewCategory === 'image'" :src="previewUrl" style="max-width:100%;max-height:75vh;">
        <video v-else-if="previewCategory === 'video'" :src="previewUrl" controls style="max-width:100%;max-height:75vh;"></video>
        <audio v-else-if="previewCategory === 'audio'" :src="previewUrl" controls style="width:100%;"></audio>
        <iframe v-else-if="previewCategory === 'doc' && previewFile.file_suffix === 'pdf'" :src="previewUrl" style="width:100%;height:75vh;border:none;"></iframe>
        <div v-else style="padding:60px;color:#9ab;">
          <div style="font-size:64px;">{{ previewFile.icon || '📄' }}</div>
          <p style="margin-top:16px;">该文件类型暂不支持在线预览</p>
          <el-button type="primary" style="margin-top:16px;" @click="downloadFile(previewFile)">下载文件</el-button>
        </div>
      </div>
    </el-dialog>

    <!-- 存储配额设置对话框 -->
    <el-dialog v-model="showStorageQuotaDialog" title="设置存储配额" width="400px">
      <el-form label-width="100px">
        <el-form-item label="用户名">
          <span>{{ currentUserForQuota?.username }}</span>
        </el-form-item>
        <el-form-item label="当前配额">
          <span>{{ formatSize(currentUserForQuota?.storage_quota || 1073741824) }}</span>
        </el-form-item>
        <el-form-item label="新配额">
          <el-input-number
            v-model="newStorageQuota"
            :min="1048576"
            :step="1073741824"
            :precision="0"
            style="width: 100%;"
          >
            <template #append>字节</template>
          </el-input-number>
          <div style="margin-top: 8px; font-size: 12px; color: #9ab;">
            常用值：1GB=1073741824, 5GB=5368709120, 10GB=10737418240
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showStorageQuotaDialog = false">取消</el-button>
        <el-button type="primary" @click="submitStorageQuota">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox, ElTooltip } from 'element-plus'
import { Download, Edit, FolderOpened, Delete } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import { formatSize, getFileIcon, getFileCategory } from '@/utils/format'
import * as authApi from '@/api/auth'
import * as fileApi from '@/api/file'
import * as folderApi from '@/api/folder'
import * as settingsApi from '@/api/settings'
import * as aiApi from '@/api/ai'
import * as kbApi from '@/api/kb'
const router = useRouter()
const route = useRoute()
const {
  state, logout, fetchUserInfo, refreshStorageStats, refreshRecycle, resetRecycleCache,
  refreshViewFiles, refreshViewFolders, refreshAllFolders, refreshView, resetView, resetAllViews,
} = useUserStore()

// 用户信息
const userInfo = computed(() => state.userInfo)
const isAdmin = computed(() => userInfo.value.role === 'admin')

// 视图状态（首次渲染即决定正确视图，避免先渲染"全部文件"造成闪现）
const VALID_VIEWS = ['all', 'image', 'doc', 'video', 'audio', 'archive', 'recycle', 'profile', 'admin', 'ai']
const initialQueryView = (() => {
  try {
    const qv = new URLSearchParams(window.location.search).get('view')
    return qv && VALID_VIEWS.includes(qv) ? qv : null
  } catch (e) {
    return null
  }
})()
const view = ref(initialQueryView || 'all')
const viewMode = ref('grid')
const currentFolderId = ref(0)
const breadcrumb = ref([])
const globalKeyword = ref('')

// 数据
// 文件夹 / 文件列表从全局 store 读取，按 view 缓存——
// 在左侧菜单 "全部文件 / 图片 / 文档 / 视频 / 音乐 / 压缩包" 切换时，
// 先显示已缓存的内容，不会出现先空再填的闪烁。
const folderList = computed(() => {
  const v = state.views[view.value]
  return v ? v.folders : []
})
const fileList = computed(() => {
  const v = state.views[view.value]
  return v ? v.files : []
})
const allFolders = computed(() => state.allFolders.items)

// 回收站数据从全局 store 读取——进入 /?view=recycle 时，若已加载过就直接显示，不再空列表起步
const recycleList = computed(() => state.recycle.files)
const recycleFolderList = computed(() => state.recycle.folders)
// 存储用量（从全局 store 读取，避免路由切换组件重建导致的 0→正确值 闪烁）
const stats = computed(() => state.storageStats)
const storageQuota = computed(() => (stats.value.storageQuota || state.userInfo?.storage_quota || 8 * 1024 * 1024 * 1024))

// 选择
const selectedIds = ref([])

// 对话框
const showCreateFolder = ref(false)
const newFolderName = ref('')
const showRename = ref(false)
const renameName = ref('')
const renameTarget = ref(null)
const showMoveDialog = ref(false)
const moveTargetFolderId = ref(0)
const moveTarget = ref(null)
const showPreview = ref(false)
const previewFile = ref({})
const previewUrl = ref('')
const previewCategory = ref('')

// 存储配额对话框
const showStorageQuotaDialog = ref(false)
const currentUserForQuota = ref(null)
const newStorageQuota = ref(1073741824)

// 管理员
const userList = ref([])
const settingsForm = reactive({ site_name: '', site_url: 'http://localhost:' + '8000', contact_email: '', site_description: '', allow_register: true, register_audit: false, default_role: 'user' })

// 密码
const pwdForm = reactive({ old_password: '', new_password: '' })

// 上传
const uploadInput = ref(null)

// Computed
const storagePercent = computed(() => Math.min(100, ((stats.value.totalSize || 0) / storageQuota.value * 100)).toFixed(1))
const displayList = computed(() => {
  const folders = folderList.value.map(f => ({ type: 'folder', id: f.id, name: f.folder_name, icon: '📁', file_count: f.file_count, file_size: f.total_size, time: f.create_time, raw: f }))
  const files = fileList.value.map(f => ({ type: 'file', id: f.id, name: f.original_name, icon: f.icon, file_size: f.file_size, file_suffix: f.file_suffix, category: f.category, time: f.upload_time, raw: f }))
  return [...folders, ...files]
})
const allSelected = computed(() => displayList.value.length > 0 && selectedIds.value.length === displayList.value.length)

// Methods
function checkLogin() {
  if (!state.token) { router.push('/login'); return false }
  return true
}

function switchView(v) {
  // 若当前路由不是首页（如 AI 助手页），先跳回首页并携带视图参数
  if (route.path !== '/') {
    if (v === 'all') {
      router.push({ path: '/' })
    } else {
      router.push({ path: '/', query: { view: v } })
    }
    return
  }
  // 切换视图：先更新内部状态，同步 URL，并强制刷新对应视图的数据
  view.value = v
  syncUrlQuery(v)
  // 关键：每次点击菜单项都重新加载，保证系统设置、个人中心第一次进入就能显示最新数据
  triggerViewLoad(v)
}

// 把当前视图同步到 URL query，方便刷新和分享
function syncUrlQuery(v) {
  try {
    if (v === 'all') {
      router.replace({ path: '/', query: {} })
    } else {
      router.replace({ path: '/', query: { view: v } })
    }
  } catch (e) { /* ignore */ }
}

function loadCurrentView() {
  if (['all','image','doc','video','audio','archive'].includes(view.value)) {
    // 进入文件视图：先从 store 缓存读取，立即显示已有内容，避免闪烁
    refreshView(view.value, { force: false, folderId: currentFolderId.value, keyword: globalKeyword.value })
  }
}

async function getFolders() {
  await refreshViewFolders(view.value, { force: false, folderId: currentFolderId.value, keyword: globalKeyword.value })
}

async function getAllFolders() {
  await refreshAllFolders(false)
}

async function getBreadcrumb() {
  if (currentFolderId.value === 0) { breadcrumb.value = []; return }
  try {
    const res = await folderApi.getBreadcrumb({ folder_id: currentFolderId.value })
    if (res.code === 200) breadcrumb.value = res.data
  } catch (e) { console.error(e) }
}

async function createFolder() {
  if (!newFolderName.value.trim()) { ElMessage.warning('请输入文件夹名称'); return }
  try {
    const res = await folderApi.createFolder({ folder_name: newFolderName.value, parent_id: currentFolderId.value })
    if (res.code === 200) {
      ElMessage.success('创建成功')
      showCreateFolder.value = false
      newFolderName.value = ''
      // 创建文件夹后：重置所有视图缓存，确保全部文件、图片、文档等所有分类栏都能看到新文件夹
      resetAllViews()
      // 同时刷新当前视图和全局文件夹列表，保证立即展示
      await Promise.all([
        refreshView(view.value, { force: true, folderId: currentFolderId.value, keyword: '' }),
        refreshAllFolders(true),
      ])
      refreshStats()
    }
  } catch (e) { console.error(e) }
}

function goToFolder(folderId) {
  currentFolderId.value = folderId
  selectedIds.value = []
  getBreadcrumb()
  // 进入新的文件夹层级，强制刷新
  refreshView(view.value, { force: true, folderId, keyword: '' })
}

async function getFiles() {
  await refreshViewFiles(view.value, { force: false, folderId: currentFolderId.value, keyword: globalKeyword.value })
}

function triggerUpload() { uploadInput.value?.click() }

async function handleUpload(e) {
  const files = e.target.files
  if (!files || files.length === 0) return
  const formData = new FormData()
  for (const f of files) formData.append('files', f)
  try {
    ElMessage.info('上传中...')
    const res = await fileApi.uploadFile(currentFolderId.value, formData)
    if (res.code === 200) {
      ElMessage.success(res.msg)
      // 上传文件后：重置所有视图缓存，确保全部文件、图片、文档等所有分类栏都能看到新文件
      resetAllViews()
      await Promise.all([
        refreshView(view.value, { force: true, folderId: currentFolderId.value, keyword: globalKeyword.value }),
        refreshAllFolders(true),
      ])
      refreshStats()
    }
  } catch (err) { console.error(err) } finally { if (uploadInput.value) uploadInput.value.value = '' }
}

async function downloadFile(item) {
  try {
    const res = await fileApi.downloadFile(item.id)
    const url = window.URL.createObjectURL(res)
    const a = document.createElement('a')
    a.href = url; a.download = item.name || item.original_name
    document.body.appendChild(a); a.click(); document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
  } catch (e) { console.error(e) }
}

async function openPreview(item) {
  previewFile.value = item
  previewCategory.value = item.category
  try {
    const res = await fileApi.previewFile(item.id)
    const blob = new Blob([res])
    previewUrl.value = URL.createObjectURL(blob)
    showPreview.value = true
  } catch (e) {
    ElMessage.error('预览加载失败')
    console.error(e)
  }
}

function openRename(item) {
  renameTarget.value = item
  renameName.value = item.type === 'folder' ? item.name : item.name.replace(/\.[^.]+$/, '')
  showRename.value = true
}

async function submitRename() {
  if (!renameName.value.trim()) { ElMessage.warning('名称不能为空'); return }
  try {
    const res = await (renameTarget.value.type === 'folder' ? folderApi.renameFolder(renameTarget.value.id, { new_name: renameName.value }) : fileApi.renameFile(renameTarget.value.id, { new_name: renameName.value }))
    if (res.code === 200) {
      ElMessage.success('重命名成功')
      showRename.value = false
      // 重命名后：重置所有视图缓存，确保全部文件、图片、文档等所有分类栏都同步刷新
      resetAllViews()
      await Promise.all([
        refreshView(view.value, { force: true, folderId: currentFolderId.value, keyword: globalKeyword.value }),
        refreshAllFolders(true),
      ])
    }
  } catch (e) { console.error(e) }
}

async function submitMove() {
  const targetId = moveTargetFolderId.value
  try {
    if (selectedIds.value.length > 0) {
      const fileIds = selectedIds.value.filter(k => k.startsWith('file_')).map(k => parseInt(k.replace('file_', '')))
      if (fileIds.length > 0) await fileApi.batchMoveFiles({ id_list: fileIds, target_folder_id: targetId })
    } else if (moveTarget.value && moveTarget.value.type === 'file') {
      await fileApi.moveFile(moveTarget.value.id, { target_folder_id: targetId })
    }
    ElMessage.success('移动成功')
    showMoveDialog.value = false; moveTarget.value = null; selectedIds.value = []; moveTargetFolderId.value = 0
    // 移动后：重置所有视图缓存，确保全部文件、图片、文档等所有分类栏都同步刷新
    resetAllViews()
    await Promise.all([
      refreshView(view.value, { force: true, folderId: currentFolderId.value, keyword: globalKeyword.value }),
      refreshAllFolders(true),
    ])
  } catch (e) { console.error(e) }
}

async function deleteItem(item) {
  try { await ElMessageBox.confirm(`确定要删除「${item.name}」吗？${item.type === 'folder' ? '文件夹内文件将移入回收站。' : '文件将移入回收站。'}`, '提示', { type: 'warning' }) } catch { return }
  try {
    const res = item.type === 'folder' ? await folderApi.deleteFolder(item.id) : await fileApi.deleteFile(item.id)
    if (res.code === 200) {
      ElMessage.success(res.msg)
      // 删除后：重置所有视图缓存，确保全部文件、图片、文档等所有分类栏都同步刷新
      resetAllViews()
      await Promise.all([
        refreshView(view.value, { force: true, folderId: currentFolderId.value, keyword: globalKeyword.value }),
        refreshAllFolders(true),
      ])
      refreshStats()
    }
  } catch (e) { console.error(e) }
}

async function batchDelete() {
  if (selectedIds.value.length === 0) return
  try { await ElMessageBox.confirm(`确定要删除选中的 ${selectedIds.value.length} 项吗？`, '提示', { type: 'warning' }) } catch { return }
  const folderIds = selectedIds.value.filter(k => k.startsWith('folder_')).map(k => parseInt(k.replace('folder_', '')))
  const fileIds = selectedIds.value.filter(k => k.startsWith('file_')).map(k => parseInt(k.replace('file_', '')))
  try {
    if (fileIds.length > 0) await fileApi.batchDeleteFiles({ id_list: fileIds })
    for (const fid of folderIds) await folderApi.deleteFolder(fid)
    ElMessage.success('批量删除完成')
    selectedIds.value = []
    // 删除后：重置所有视图缓存，确保全部文件、图片、文档等所有分类栏都同步刷新
    resetAllViews()
    await Promise.all([
      refreshView(view.value, { force: true, folderId: currentFolderId.value, keyword: globalKeyword.value }),
      refreshAllFolders(true),
    ])
    refreshStats()
  } catch (e) { console.error(e) }
}

async function loadRecycle() {
  // 使用共享缓存：短时间内进入回收站直接显示已有数据，不再产生"空列表 → 真实数据"的闪跳
  await refreshRecycle(false)
}

async function restoreItem(item) {
  try {
    const res = item.itemType === 'folder'
      ? await folderApi.restoreFolder(item.id)
      : await fileApi.restoreFile(item.id)
    if (res.code === 200) {
      ElMessage.success('已恢复')
      // 恢复后：重置所有视图缓存，确保全部文件、图片、文档、视频、音乐、压缩包都能看到恢复的内容
      resetAllViews()
      await Promise.all([
        refreshRecycle(true),
        refreshView(view.value, { force: true, folderId: currentFolderId.value, keyword: '' }),
        refreshAllFolders(true),
      ])
      refreshStats()
    }
  } catch (e) { console.error(e) }
}

async function permanentDeleteItem(item) {
  try { await ElMessageBox.confirm('彻底删除后无法恢复，确定继续？', '警告', { type: 'warning' }) } catch { return }
  try {
    const res = item.itemType === 'folder'
      ? await folderApi.permanentDeleteFolder(item.id)
      : await fileApi.permanentDeleteFile(item.id)
    if (res.code === 200) {
      ElMessage.success('已彻底删除')
      await refreshRecycle(true) // 删除后强制刷新缓存
      refreshStats()
    }
  } catch (e) { console.error(e) }
}

async function clearRecycle() {
  try { await ElMessageBox.confirm('将永久删除回收站内所有文件和文件夹，确定继续？', '警告', { type: 'warning' }) } catch { return }
  try {
    const [fileRes, folderRes] = await Promise.all([
      fileApi.clearRecycle(),
      clearRecycleFolders()
    ])
    if (fileRes.code === 200 || folderRes?.code === 200) {
      ElMessage.success('已清空回收站')
      await refreshRecycle(true) // 清空后强制刷新缓存
      refreshStats()
    }
  } catch (e) { console.error(e) }
}

async function clearRecycleFolders() {
  for (const folder of recycleFolderList.value) {
    await folderApi.permanentDeleteFolder(folder.id)
  }
  return { code: 200 }
}

async function refreshStats() {
  // 上传/删除/恢复后强制刷新存储用量
  try { await fetchUserInfo() } catch (e) { console.error(e) }
  try { await refreshStorageStats(true) } catch (e) { console.error(e) }
}

async function loadProfile() { await fetchUserInfo() }

async function changePassword() {
  if (!pwdForm.old_password || !pwdForm.new_password) { ElMessage.warning('请填写完整'); return }
  if (pwdForm.new_password.length < 6) { ElMessage.warning('新密码至少6位'); return }
  try { const res = await authApi.changePassword(pwdForm); if (res.code === 200) { ElMessage.success('密码修改成功'); pwdForm.old_password = ''; pwdForm.new_password = '' } } catch (e) { console.error(e) }
}

async function loadAdmin() {
  try {
    // 同时刷新用户信息（存储配额）与系统管理数据
    const [statsRes, settingsRes, usersRes] = await Promise.all([settingsApi.getStats(), settingsApi.getSettings(), settingsApi.getUserList()])
    if (statsRes.code === 200) {
      Object.assign(state.storageStats, statsRes.data)
      state.storageStats.loadedAt = Date.now()
    }
    if (usersRes.code === 200) userList.value = usersRes.data
    if (settingsRes.code === 200) {
      const s = settingsRes.data.values || settingsRes.data
      console.log('从后端加载的设置:', s)
      // 更健壮的布尔值判断：支持 'true', 'True', 'TRUE', true, 1 等格式
      const parseBool = (val) => val === true || val === 'true' || val === 'True' || val === 'TRUE' || val === '1' || val === 1
      Object.assign(settingsForm, {
        site_name: s.site_name || '',
        site_url: s.site_url || '',
        contact_email: s.contact_email || '',
        site_description: s.site_description || '',
        allow_register: parseBool(s.allow_register),
        register_audit: parseBool(s.register_audit),
        default_role: s.default_role || 'user'
      })
      console.log('更新后的表单:', settingsForm)
    }
    // 确保管理员页面也能拿到最新的存储配额（解决首次或二次点击才显示的问题）
    fetchUserInfo()
  } catch (e) {
    console.error('加载管理员数据失败:', e)
  }
}

async function saveSettings() {
  try {
    // 将布尔值转换为小写字符串，与后端保持一致
    const payload = {
      ...settingsForm,
      allow_register: settingsForm.allow_register ? 'true' : 'false',
      register_audit: settingsForm.register_audit ? 'true' : 'false'
    }
    console.log('保存设置:', payload)
    const res = await settingsApi.updateSettings(payload)
    if (res.code === 200) {
      ElMessage.success('保存成功')
      // 重新加载设置，确保前端显示与数据库一致
      await loadAdmin()
    }
  } catch (e) {
    console.error(e)
    ElMessage.error('保存失败')
  }
}

async function updateUserStatus(userId, status) {
  try { const res = await settingsApi.updateUserStatus({ user_id: userId, status }); if (res.code === 200) { ElMessage.success('更新成功'); loadAdmin() } } catch (e) { console.error(e) }
}

function openStorageQuotaDialog(user) {
  currentUserForQuota.value = user
  newStorageQuota.value = user.storage_quota || 1073741824
  showStorageQuotaDialog.value = true
}

async function submitStorageQuota() {
  if (!currentUserForQuota.value) return
  try {
    const res = await settingsApi.updateStorageQuota({
      user_id: currentUserForQuota.value.id,
      storage_quota: newStorageQuota.value
    })
    if (res.code === 200) {
      ElMessage.success('存储配额更新成功')
      showStorageQuotaDialog.value = false
      // 刷新系统设置页用户列表与统计
      loadAdmin()
      // 如果修改的是当前登录用户，则同步刷新 userInfo（个人中心）与侧边栏存储用量
      if (currentUserForQuota.value.id === userInfo.value.id) {
        await fetchUserInfo()
        refreshStats()
      }
    }
  } catch (e) {
    console.error(e)
    ElMessage.error('更新失败')
  }
}

function handleUserCommand(cmd) {
  if (cmd === 'profile') switchView('profile')
  else if (cmd === 'admin') switchView('admin')
  else if (cmd === 'logout') handleLogout()
}

function handleLogout() { logout(); router.push('/login') }
function handleSearch() {
  // 搜索时，强制刷新当前视图（关键词改变后数据不同）
  if (['all','image','doc','video','audio','archive'].includes(view.value)) {
    refreshView(view.value, { force: true, folderId: currentFolderId.value, keyword: globalKeyword.value })
  }
}
function goToAiAssistant() { router.push('/ai-assistant') }
function goToKnowledge() { router.push('/knowledge') }

function handleCardClick(item, event) {
  if (item.type === 'folder') { goToFolder(item.id) }
  else {
    if (['image', 'video', 'audio'].includes(item.category) || (item.category === 'doc' && item.file_suffix === 'pdf')) { openPreview(item) }
    else { toggleSelect(item) }
  }
}

function isSelected(item) { return selectedIds.value.includes(item.type + '_' + item.id) }
function toggleSelect(item) { const key = item.type + '_' + item.id; const idx = selectedIds.value.indexOf(key); if (idx >= 0) selectedIds.value.splice(idx, 1); else selectedIds.value.push(key) }
function toggleSelectAll(e) { if (e.target.checked) selectedIds.value = displayList.value.map(i => i.type + '_' + i.id); else selectedIds.value = [] }

// 根据视图类型加载对应的数据（view 变化或 onMounted 时调用）
function triggerViewLoad(v) {
  selectedIds.value = []
  if (v === 'recycle') loadRecycle()
  else if (v === 'profile') {
    // 进入个人中心时同时刷新 userInfo（存储配额）与侧边栏存储用量
    fetchUserInfo()
    refreshStats()
  }
  else if (v === 'admin') loadAdmin()
  else {
    if (v !== 'all') { currentFolderId.value = 0; breadcrumb.value = [] }
    loadCurrentView()
  }
}

onMounted(() => {
  if (!checkLogin()) return
  // 统一从后端刷新用户信息（含 storage_quota），避免登录后仅靠 localStorage 的旧数据
  fetchUserInfo()
  refreshStats()
  // view 已由 window.location.search 初始化，加载对应视图数据
  triggerViewLoad(view.value)
})

// 监听 URL query view 变化（例如从 AI 助手页跳转过来时，路由完成后需要同步视图）
// 注意：如果 URL query 与当前 view 相同，说明是在当前页面内部触发的路由更新，不要重复刷新数据
watch(
  () => route.query.view,
  (nv) => {
    const next = nv && VALID_VIEWS.includes(String(nv)) ? String(nv) : 'all'
    if (next === view.value) return
    view.value = next
    refreshStats()
    triggerViewLoad(next)
  }
)
</script>

<style scoped>
.app-container { display: flex; flex-direction: column; height: 100vh; }
.top-header { height: 60px; background: #fff; box-shadow: 0 2px 8px rgba(33,150,243,0.08); display: flex; align-items: center; padding: 0 24px; z-index: 10; }
.header-logo { display: flex; align-items: center; gap: 10px; font-size: 18px; font-weight: 700; color: #1a3a5c; min-width: 220px; cursor: pointer; }
.header-logo .logo-icon { width: 36px; height: 36px; background: linear-gradient(135deg, #4facfe 0%, #2196f3 100%); border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 20px; color: #fff; }
.header-title-bar { flex: 1; display: flex; align-items: center; justify-content: center; }
.header-title-bar .page-tag { padding: 8px 20px; background: linear-gradient(135deg, #4facfe 0%, #2196f3 100%); color: #fff; border-radius: 20px; font-size: 14px; font-weight: 600; box-shadow: 0 2px 8px rgba(33, 150, 243, 0.2); }
.header-search { flex: 1; max-width: 480px; margin: 0 32px; }
.header-user { margin-left: auto; display: flex; align-items: center; gap: 16px; }
.user-avatar { width: 36px; height: 36px; border-radius: 50%; background: linear-gradient(135deg, #4facfe 0%, #2196f3 100%); color: #fff; display: flex; align-items: center; justify-content: center; font-size: 14px; font-weight: 600; }
.user-name { font-size: 14px; color: #1a3a5c; font-weight: 500; }
.app-body { flex: 1; display: flex; overflow: hidden; }
.sidebar { width: 220px; background: #fff; border-right: 1px solid #e3eefb; padding: 16px 0; display: flex; flex-direction: column; overflow-y: auto; }
.sidebar-section { padding: 8px 0; }
.sidebar-section-title { font-size: 11px; color: #9ab; padding: 8px 24px; letter-spacing: 1px; }
.menu-item { padding: 11px 24px; cursor: pointer; display: flex; align-items: center; gap: 12px; color: #4a5c6e; font-size: 14px; transition: all 0.2s; border-left: 3px solid transparent; }
.menu-item:hover { background: #f0f7ff; color: #2196f3; }
.menu-item.active { background: #e3f2fd; color: #2196f3; border-left-color: #2196f3; font-weight: 600; }
.menu-item .icon { font-size: 16px; width: 18px; text-align: center; }
.storage-card { margin: 16px; padding: 16px; background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%); border-radius: 12px; }
.storage-card .title { font-size: 13px; color: #1565c0; font-weight: 600; margin-bottom: 8px; }
.storage-card .bar { height: 8px; background: rgba(255,255,255,0.6); border-radius: 4px; overflow: hidden; margin-bottom: 8px; }
.storage-card .bar-inner { height: 100%; background: linear-gradient(90deg, #2196f3, #4facfe); border-radius: 4px; transition: width 0.3s; }
.storage-card .text { font-size: 12px; color: #1565c0; }
.main-content { flex: 1; padding: 24px; overflow-y: auto; }
.stats-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; margin-bottom: 20px; }
.stat-card { background: #fff; border-radius: 12px; padding: 18px 20px; display: flex; align-items: center; gap: 14px; box-shadow: 0 2px 8px rgba(33,150,243,0.05); transition: all 0.2s; }
.stat-card:hover { transform: translateY(-2px); box-shadow: 0 4px 14px rgba(33, 150, 243, 0.12); }
.stat-card .stat-icon { width: 48px; height: 48px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 22px; }
.stat-card .stat-info .value { font-size: 22px; font-weight: 700; color: #1a3a5c; }
.stat-card .stat-info .label { font-size: 12px; color: #9ab; margin-top: 2px; }
.stat-card.blue .stat-icon { background: #e3f2fd; color: #2196f3; }
.stat-card.green .stat-icon { background: #e8f5e9; color: #4caf50; }
.stat-card.orange .stat-icon { background: #fff3e0; color: #ff9800; }
.stat-card.purple .stat-icon { background: #f3e5f5; color: #9c27b0; }
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 12px; }
.breadcrumb { display: flex; align-items: center; gap: 4px; flex-wrap: wrap; }
.crumb { color: #2196f3; cursor: pointer; font-size: 14px; }
.crumb:hover { text-decoration: underline; }
.crumb-arrow { color: #9ab; font-size: 14px; }
.toolbar-actions { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.batch-bar { position: sticky; top: 0; background: #e3f2fd; border-radius: 10px; padding: 10px 16px; margin-bottom: 16px; display: flex; align-items: center; justify-content: space-between; font-size: 13px; color: #1565c0; z-index: 5; }
.file-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 14px; }
.file-card { background: #fff; border-radius: 12px; padding: 16px 12px; text-align: center; cursor: pointer; transition: all 0.2s; border: 2px solid transparent; position: relative; }
.file-card:hover { box-shadow: 0 6px 18px rgba(33,150,243,0.12); transform: translateY(-2px); }
.file-card.selected { border-color: #2196f3; background: #f0f7ff; }
.file-card .file-icon { font-size: 48px; line-height: 1; margin-bottom: 10px; }
.file-card .file-name { font-size: 13px; color: #1a3a5c; font-weight: 500; word-break: break-all; line-height: 1.4; height: 36px; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
.file-card .file-meta { font-size: 11px; color: #9ab; margin-top: 6px; }
.file-card .checkbox { position: absolute; top: 8px; left: 8px; opacity: 0; transition: opacity 0.2s; }
.file-card:hover .checkbox, .file-card.selected .checkbox { opacity: 1; }
.file-card .action-buttons { position: absolute; top: 8px; right: 8px; display: flex; gap: 6px; opacity: 0; transition: opacity 0.2s; z-index: 2; }
.file-card:hover .action-buttons { opacity: 1; }
.file-card .action-btn { width: 28px; height: 28px; border-radius: 6px; background: rgba(255,255,255,0.95); box-shadow: 0 2px 8px rgba(0,0,0,0.1); display: flex; align-items: center; justify-content: center; cursor: pointer; transition: all 0.2s; color: #5a6c7d; }
.file-card .action-btn:hover { background: #2196f3; color: #fff; transform: scale(1.1); }
.file-card .action-btn.danger:hover { background: #f44336; }
.file-card .more-btn { display: none; }
.file-table { background: #fff; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(33,150,243,0.05); }
.file-table table { width: 100%; border-collapse: collapse; }
.file-table th { padding: 14px 16px; text-align: left; font-size: 13px; color: #5a6c7d; font-weight: 600; border-bottom: 1px solid #e3eefb; background: #f8fbff; }
.file-table td { padding: 12px 16px; font-size: 13px; color: #1a3a5c; border-bottom: 1px solid #f0f4fa; vertical-align: middle; }
.file-table tr:hover td { background: #f8fbff; }
.file-table tr.selected td { background: #e3f2fd; }
.file-table .action-cell { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.file-table .action-cell .el-button { margin: 0; white-space: nowrap; min-width: 70px; }
.file-table .name-cell { display: flex; align-items: center; gap: 10px; }
.file-table .name-cell .icon { font-size: 22px; }
.file-table .name-cell .name { cursor: pointer; }
.file-table .name-cell .name:hover { color: #2196f3; }
.empty-state { text-align: center; padding: 60px 20px; color: #9ab; }
.empty-state .icon { font-size: 64px; opacity: 0.5; }
.empty-state .text { font-size: 14px; margin-top: 12px; }

.ai-redirect-tip { padding: 40px 20px; text-align: center; }
</style>
