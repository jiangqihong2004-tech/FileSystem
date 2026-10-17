import request from './index'

export const getStats = () => request.get('/stats/overview')
export const getSettings = () => request.get('/settings')
export const updateSettings = (data) => request.put('/settings', data)
export const getUserList = () => request.get('/user/list')
export const updateUserStatus = (data) => request.put('/user/status', data)
export const getStorageDetail = () => request.get('/stats/storage')
export const updateStorageQuota = (data) => request.put('/user/storage_quota', data)
