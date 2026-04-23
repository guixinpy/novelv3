<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api/client'
import BaseButton from '../components/base/BaseButton.vue'
import BaseInput from '../components/base/BaseInput.vue'

const apiKey = ref('')
const saved = ref(false)
const hasStoredKey = ref(false)

onMounted(async () => {
  const cfg = await api.getConfig()
  hasStoredKey.value = cfg.has_api_key
})

async function save() {
  const nextKey = apiKey.value.trim()
  if (!nextKey) {
    saved.value = true
    setTimeout(() => { saved.value = false }, 2000)
    return
  }
  await api.updateConfig(nextKey)
  hasStoredKey.value = true
  apiKey.value = ''
  saved.value = true
  setTimeout(() => { saved.value = false }, 2000)
}
</script>

<template>
  <div class="settings-view">
    <h1 class="settings-view__title">设置</h1>

    <section class="settings-view__section">
      <h2 class="settings-view__section-title">API 配置</h2>
      <div class="settings-view__row">
        <BaseInput
          v-model="apiKey"
          label="API Key"
          type="password"
          placeholder="sk-..."
        />
      </div>
      <div class="settings-view__row settings-view__row--actions">
        <BaseButton variant="primary" size="sm" @click="save">
          保存配置
        </BaseButton>
        <span v-if="hasStoredKey" class="settings-view__status">已配置</span>
        <span v-if="saved" class="settings-view__saved">已保存</span>
      </div>
    </section>

    <section class="settings-view__section">
      <h2 class="settings-view__section-title">偏好设置</h2>
      <p class="settings-view__placeholder">更多设置项即将推出</p>
    </section>
  </div>
</template>

<style scoped>
.settings-view {
  max-width: 720px;
  margin: 0 auto;
}

.settings-view__title {
  font-size: var(--text-xl);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  margin-bottom: var(--space-8);
}

.settings-view__section {
  margin-bottom: var(--space-8);
}

.settings-view__section-title {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  margin-bottom: var(--space-4);
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--color-border);
}

.settings-view__row {
  margin-bottom: var(--space-4);
}

.settings-view__row--actions {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.settings-view__status {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  font-weight: var(--font-medium);
}

.settings-view__saved {
  font-size: var(--text-sm);
  color: var(--color-success);
  font-weight: var(--font-medium);
}

.settings-view__placeholder {
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
}
</style>
