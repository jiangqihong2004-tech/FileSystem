<template>
  <div class="login-page">
    <div class="login-card">
      <!-- 左侧品牌区 -->
      <div class="brand-side">
        <div class="brand-logo">
          <div class="logo-icon">📁</div>
          <span>FileManager</span>
        </div>
        <div class="brand-slogan">
          <h2>轻量级<br>文件管理系统</h2>
          <p>安全可靠的个人云端存储，<br>随时随地管理您的文件。</p>
        </div>
        <div class="brand-features">
          <div class="brand-feature"><span class="dot"></span>支持多格式文件上传与下载</div>
          <div class="brand-feature"><span class="dot"></span>文件分类管理与回收站</div>
          <div class="brand-feature"><span class="dot"></span>在线预览图片/视频/文档</div>
          <div class="brand-feature"><span class="dot"></span>个人独立存储空间隔离</div>
        </div>
      </div>
      <!-- 右侧表单区 -->
      <div class="form-side">
        <div class="form-title">{{ isLogin ? '欢迎回来' : '创建账号' }}</div>
        <div class="form-subtitle">{{ isLogin ? '请登录您的账号继续使用' : '填写信息完成注册' }}</div>
        <div class="tab-switch">
          <div class="tab" :class="{active: isLogin}" @click="isLogin = true">登录</div>
          <div class="tab" :class="{active: !isLogin}" @click="isLogin = false">注册</div>
        </div>
        <!-- 登录表单 -->
        <template v-if="isLogin">
          <div class="form-item">
            <label>用户名</label>
            <input class="form-input" v-model="loginForm.username" placeholder="请输入用户名" @keyup.enter="handleLogin" />
          </div>
          <div class="form-item">
            <label>密码</label>
            <input class="form-input" type="password" v-model="loginForm.password" placeholder="请输入密码" @keyup.enter="handleLogin" />
          </div>
          <button class="submit-btn" :disabled="loginLoading" @click="handleLogin">
            {{ loginLoading ? '登录中...' : '登 录' }}
          </button>
        </template>
        <!-- 注册表单 -->
        <template v-else>
          <div class="form-item">
            <label>用户名</label>
            <input class="form-input" v-model="registerForm.username" placeholder="至少3位" />
          </div>
          <div class="form-item">
            <label>邮箱（选填）</label>
            <input class="form-input" v-model="registerForm.email" placeholder="请输入邮箱" />
          </div>
          <div class="form-item">
            <label>密码</label>
            <input class="form-input" type="password" v-model="registerForm.password" placeholder="至少6位" />
          </div>
          <div class="form-item">
            <label>确认密码</label>
            <input class="form-input" type="password" v-model="registerForm.confirmPassword" placeholder="请再次输入密码" @keyup.enter="handleRegister" />
          </div>
          <button class="submit-btn" :disabled="registerLoading" @click="handleRegister">
            {{ registerLoading ? '注册中...' : '注 册' }}
          </button>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { login as loginApi, register as registerApi } from '@/api/auth'
import { useUserStore } from '@/stores/user'
import { getToken } from '@/utils/storage'

const router = useRouter()
const { setLoginData } = useUserStore()

const isLogin = ref(true)
const loginLoading = ref(false)
const registerLoading = ref(false)
const loginForm = ref({ username: '', password: '' })
const registerForm = ref({ username: '', email: '', password: '', confirmPassword: '' })

onMounted(() => {
  if (getToken()) {
    router.push('/')
  }
})

async function handleLogin() {
  const f = loginForm.value
  if (!f.username || !f.password) {
    ElMessage.warning('请填写用户名和密码')
    return
  }
  loginLoading.value = true
  try {
    const res = await loginApi({ username: f.username, password: f.password })
    if (res.code === 200) {
      setLoginData(res.data.token, res.data)
      ElMessage.success('登录成功')
      router.push('/')
    }
  } catch (err) {
    // 错误已在拦截器处理
  } finally {
    loginLoading.value = false
  }
}

async function handleRegister() {
  const f = registerForm.value
  if (!f.username || f.username.length < 3) {
    ElMessage.warning('用户名至少3位')
    return
  }
  if (!f.password || f.password.length < 6) {
    ElMessage.warning('密码至少6位')
    return
  }
  if (f.password !== f.confirmPassword) {
    ElMessage.warning('两次密码不一致')
    return
  }
  registerLoading.value = true
  try {
    const res = await registerApi({ username: f.username, password: f.password, email: f.email || null })
    if (res.code === 200) {
      ElMessage.success(res.msg)
      isLogin.value = true
      loginForm.value.username = f.username
      loginForm.value.password = ''
      registerForm.value = { username: '', email: '', password: '', confirmPassword: '' }
    }
  } catch (err) {
    // 错误已在拦截器处理
  } finally {
    registerLoading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 50%, #90caf9 100%);
  position: relative;
  overflow: hidden;
}
.login-page::before, .login-page::after {
  content: ''; position: absolute; border-radius: 50%;
  background: rgba(255, 255, 255, 0.35); pointer-events: none;
}
.login-page::before { width: 480px; height: 480px; top: -160px; right: -120px; }
.login-page::after { width: 360px; height: 360px; bottom: -120px; left: -100px; }

.login-card {
  width: 880px; max-width: 94vw; min-height: 520px;
  background: #fff; border-radius: 18px;
  box-shadow: 0 20px 60px rgba(33, 150, 243, 0.18);
  display: flex; overflow: hidden; position: relative; z-index: 1;
}
.brand-side {
  flex: 1;
  background: linear-gradient(160deg, #4facfe 0%, #2196f3 60%, #1976d2 100%);
  color: #fff; padding: 56px 44px;
  display: flex; flex-direction: column; justify-content: space-between;
  position: relative; overflow: hidden;
}
.brand-side::before {
  content: ''; position: absolute; width: 320px; height: 320px;
  border-radius: 50%; background: rgba(255,255,255,0.12); top: -100px; right: -100px;
}
.brand-side::after {
  content: ''; position: absolute; width: 220px; height: 220px;
  border-radius: 50%; background: rgba(255,255,255,0.08); bottom: -80px; left: -60px;
}
.brand-logo { display: flex; align-items: center; gap: 10px; font-size: 18px; font-weight: 700; position: relative; z-index: 1; }
.brand-logo .logo-icon { width: 36px; height: 36px; background: rgba(255,255,255,0.2); border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 20px; }
.brand-slogan { position: relative; z-index: 1; }
.brand-slogan h2 { font-size: 28px; font-weight: 700; margin-bottom: 16px; line-height: 1.4; }
.brand-slogan p { font-size: 14px; line-height: 1.8; opacity: 0.92; }
.brand-features { position: relative; z-index: 1; display: flex; flex-direction: column; gap: 12px; }
.brand-feature { display: flex; align-items: center; gap: 10px; font-size: 13px; opacity: 0.95; }
.brand-feature .dot { width: 6px; height: 6px; background: #fff; border-radius: 50%; }

.form-side { width: 420px; padding: 48px 44px; display: flex; flex-direction: column; justify-content: center; }
.form-title { font-size: 24px; font-weight: 700; color: #1a3a5c; margin-bottom: 8px; }
.form-subtitle { font-size: 13px; color: #8aa0b6; margin-bottom: 32px; }
.tab-switch { display: flex; gap: 24px; margin-bottom: 28px; border-bottom: 1px solid #e3eefb; }
.tab-switch .tab { padding: 10px 0; font-size: 15px; color: #8aa0b6; cursor: pointer; position: relative; transition: color 0.2s; }
.tab-switch .tab.active { color: #2196f3; font-weight: 600; }
.tab-switch .tab.active::after { content: ''; position: absolute; left: 0; right: 0; bottom: -1px; height: 2px; background: #2196f3; border-radius: 2px; }
.form-item { margin-bottom: 18px; }
.form-item label { display: block; font-size: 13px; color: #5a6c7d; margin-bottom: 6px; }
.form-input { width: 100%; height: 44px; border: 1px solid #d0d5dd; border-radius: 10px; padding: 0 14px; font-size: 14px; color: #1a3a5c; transition: all 0.2s; outline: none; background: #f8fbff; }
.form-input:focus { border-color: #2196f3; background: #fff; box-shadow: 0 0 0 3px rgba(33,150,243,0.1); }
.submit-btn { width: 100%; height: 44px; background: linear-gradient(135deg, #4facfe 0%, #2196f3 100%); color: #fff; border: none; border-radius: 10px; font-size: 15px; font-weight: 600; cursor: pointer; transition: all 0.2s; margin-top: 8px; }
.submit-btn:hover { transform: translateY(-1px); box-shadow: 0 6px 20px rgba(33,150,243,0.3); }
.submit-btn:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }

@media (max-width: 768px) {
  .login-card { flex-direction: column; width: 94vw; }
  .brand-side { padding: 32px 28px; min-height: 180px; }
  .form-side { width: 100%; padding: 32px 28px; }
}
</style>
