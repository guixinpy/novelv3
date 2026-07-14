/** 项目作用域请求去重 —— 防止旧请求覆盖新数据。
 *
 *  将 4 个 store 中的重复逻辑统一为一个 composable。
 *  每个 project-scoped store 调用 useProjectScope(projectId) 获得去重工具。
 *  项目切换时自动过期所有待处理请求。
 */
import { ref, watch, type Ref } from 'vue'

export interface ScopeTracker {
  snapshot: () => number
  isLatest: (snapshotId: number) => boolean
  expireAll: () => void
}

export function useProjectScope(projectId: Ref<string>): ScopeTracker {
  const currentRequestId = ref(0)

  function snapshot(): number {
    currentRequestId.value++
    return currentRequestId.value
  }

  function isLatest(snapshotId: number): boolean {
    return snapshotId === currentRequestId.value
  }

  function expireAll(): void {
    currentRequestId.value++
  }

  watch(projectId, () => expireAll())

  return { snapshot, isLatest, expireAll }
}
