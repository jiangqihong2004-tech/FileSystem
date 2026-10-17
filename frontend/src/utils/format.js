/**
 * 格式化工具函数
 */

export function formatSize(bytes) {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let size = parseFloat(bytes)
  let idx = 0
  while (size >= 1024 && idx < units.length - 1) {
    size /= 1024
    idx++
  }
  return idx === 0 ? `${size} ${units[idx]}` : `${size.toFixed(1)} ${units[idx]}`
}

const IMAGE_EXTS = new Set(['png', 'jpg', 'jpeg', 'gif', 'bmp', 'svg', 'webp', 'ico'])
const VIDEO_EXTS = new Set(['mp4', 'avi', 'mov', 'wmv', 'flv', 'mkv', 'webm', 'm4v'])
const AUDIO_EXTS = new Set(['mp3', 'wav', 'flac', 'aac', 'ogg', 'wma', 'm4a'])
const DOC_EXTS = new Set(['doc', 'docx', 'txt', 'pdf', 'rtf', 'odt', 'md'])
const SHEET_EXTS = new Set(['xls', 'xlsx', 'csv', 'ods'])
const SLIDE_EXTS = new Set(['ppt', 'pptx', 'odp'])
const ARCHIVE_EXTS = new Set(['zip', 'rar', '7z', 'tar', 'gz', 'bz2', 'xz'])

export function getFileCategory(suffix) {
  if (!suffix) return 'other'
  const s = suffix.toLowerCase().replace(/^\./, '')
  if (IMAGE_EXTS.has(s)) return 'image'
  if (VIDEO_EXTS.has(s)) return 'video'
  if (AUDIO_EXTS.has(s)) return 'audio'
  if (DOC_EXTS.has(s)) return 'doc'
  if (SHEET_EXTS.has(s)) return 'sheet'
  if (SLIDE_EXTS.has(s)) return 'slide'
  if (ARCHIVE_EXTS.has(s)) return 'archive'
  return 'other'
}

export function getFileIcon(suffix) {
  const category = getFileCategory(suffix)
  const iconMap = {
    image: '🖼️',
    video: '🎬',
    audio: '🎵',
    doc: '📄',
    sheet: '📊',
    slide: '📈',
    archive: '🗜️',
    other: '📦'
  }
  return iconMap[category] || '📦'
}
