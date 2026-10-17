import request from './index'

export const createFolder = (data) => request.post('/folder/create', data)
export const getFolderList = (params) => request.get('/folder/list', { params })
export const getBreadcrumb = (params) => request.get('/folder/breadcrumb', { params })
export const renameFolder = (folderId, data) => request.put(`/folder/rename/${folderId}`, data)
export const deleteFolder = (folderId) => request.delete(`/folder/${folderId}`)
export const getRecycleFolderList = () => request.get('/folder/recycle/list')
export const restoreFolder = (folderId) => request.post(`/folder/recycle/restore/${folderId}`)
export const permanentDeleteFolder = (folderId) => request.delete(`/folder/recycle/permanent/${folderId}`)
