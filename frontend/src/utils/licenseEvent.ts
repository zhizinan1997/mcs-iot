/**
 * 简单的事件发射器，用于授权状态更新的跨组件通信
 */

type LicenseEventCallback = () => void

const listeners: Set<LicenseEventCallback> = new Set()

/**
 * 订阅授权状态更新事件
 */
export function onLicenseUpdate(callback: LicenseEventCallback): () => void {
  listeners.add(callback)
  // 返回取消订阅函数
  return () => {
    listeners.delete(callback)
  }
}

/**
 * 触发授权状态更新事件
 */
export function emitLicenseUpdate(): void {
  listeners.forEach((callback) => {
    try {
      callback()
    } catch (error) {
      console.error('License event callback error:', error)
    }
  })
}
