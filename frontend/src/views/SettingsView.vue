<template>
  <div class="settings-view">
    <section class="settings-view__intro">
      <p class="settings-view__eyebrow">Settings</p>
      <div class="space-y-3">
        <h1 class="settings-view__title">把模型密钥放在同一套创作壳层里管理。</h1>
        <p class="settings-view__copy">
          设置页不该像另一套系统。这里保留最少但关键的配置入口，让你确认模型可用，再回到写作工作区继续推进。
        </p>
      </div>

      <div class="settings-view__notes">
        <article class="settings-view__note">
          <span class="settings-view__note-title">当前职责</span>
          <p class="settings-view__note-copy">只处理 DeepSeek API Key 的保存，不顺手扩散到别的系统配置。</p>
        </article>
        <article class="settings-view__note">
          <span class="settings-view__note-title">风险控制</span>
          <p class="settings-view__note-copy">危险操作降到页面尾部，避免把高频配置和低频破坏性动作摆在一起。</p>
        </article>
      </div>
    </section>

    <section class="settings-view__main">
      <div class="settings-view__card settings-view__card--form">
        <div class="settings-view__card-head">
          <p class="settings-view__card-eyebrow">模型接入</p>
          <h2 class="settings-view__card-title">DeepSeek API Key</h2>
        </div>

        <label class="settings-view__field">
          <span class="settings-view__field-label">API Key</span>
          <input
            v-model="apiKey"
            type="password"
            placeholder="sk-..."
            class="settings-view__input"
          />
        </label>

        <div class="settings-view__actions">
          <button class="settings-view__primary" @click="save">
            保存配置
          </button>
          <span v-if="saved" class="settings-view__saved">已保存</span>
        </div>
      </div>

      <div class="settings-view__card settings-view__card--danger">
        <div class="settings-view__card-head">
          <p class="settings-view__card-eyebrow">危险操作</p>
          <h2 class="settings-view__card-title">保持低优先级展示</h2>
        </div>
        <p class="settings-view__danger-copy">
          当前界面不提供一键清库、重置历史或删除生成记录。真要做破坏性操作，应该在后续明确补全 API 和确认流程后再开放。
        </p>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api/client'

const apiKey = ref('')
const saved = ref(false)

onMounted(async () => {
  const cfg = await api.getConfig()
  if (cfg.has_api_key) apiKey.value = '********'
})

async function save() {
  await api.updateConfig(apiKey.value)
  saved.value = true
  setTimeout(() => {
    saved.value = false
  }, 2000)
}
</script>

<style scoped>
.settings-view {
  display: grid;
  gap: 1.5rem;
}

.settings-view__intro,
.settings-view__card {
  border: 1px solid rgba(111, 69, 31, 0.16);
  border-radius: 1.9rem;
  padding: 1.35rem;
  box-shadow:
    0 20px 38px rgba(83, 57, 29, 0.1),
    inset 0 1px 0 rgba(255, 251, 242, 0.8);
}

.settings-view__intro {
  display: grid;
  gap: 1rem;
  background:
    linear-gradient(135deg, rgba(255, 249, 237, 0.96) 0%, rgba(240, 230, 209, 0.9) 100%);
}

.settings-view__eyebrow,
.settings-view__card-eyebrow {
  color: var(--accent-strong);
  font-size: 0.76rem;
  font-weight: 700;
  letter-spacing: 0.22em;
  text-transform: uppercase;
}

.settings-view__title,
.settings-view__card-title {
  color: var(--ink-strong);
  font-family: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", serif;
  line-height: 1.08;
}

.settings-view__title {
  font-size: clamp(2rem, 4vw, 3.2rem);
}

.settings-view__card-title {
  font-size: 1.5rem;
}

.settings-view__copy,
.settings-view__note-copy,
.settings-view__danger-copy {
  color: var(--ink-muted);
  font-size: 0.96rem;
  line-height: 1.7;
}

.settings-view__notes,
.settings-view__main {
  display: grid;
  gap: 1rem;
}

.settings-view__note {
  border: 1px solid rgba(111, 69, 31, 0.12);
  border-radius: 1.2rem;
  padding: 0.95rem 1rem;
  background: rgba(255, 249, 237, 0.68);
}

.settings-view__note-title,
.settings-view__field-label {
  color: var(--ink-muted);
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.settings-view__card {
  display: grid;
  gap: 1rem;
}

.settings-view__card--form {
  background:
    linear-gradient(180deg, rgba(255, 252, 246, 0.98) 0%, rgba(251, 248, 240, 0.96) 100%);
}

.settings-view__card--danger {
  background:
    linear-gradient(180deg, rgba(249, 242, 233, 0.8) 0%, rgba(243, 235, 225, 0.72) 100%);
}

.settings-view__card-head,
.settings-view__field {
  display: grid;
  gap: 0.45rem;
}

.settings-view__input {
  width: 100%;
  border: 1px solid rgba(111, 69, 31, 0.18);
  border-radius: 1rem;
  padding: 0.95rem 1rem;
  background: rgba(255, 255, 252, 0.92);
  color: var(--ink-strong);
  font-size: 0.96rem;
  outline: none;
}

.settings-view__input:focus {
  border-color: rgba(111, 69, 31, 0.34);
  box-shadow: 0 0 0 3px rgba(141, 93, 49, 0.12);
}

.settings-view__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem;
}

.settings-view__primary {
  border: 1px solid rgba(111, 69, 31, 0.18);
  border-radius: 1rem;
  padding: 0.85rem 1rem;
  background: linear-gradient(180deg, rgba(150, 101, 55, 0.96) 0%, rgba(112, 72, 34, 0.98) 100%);
  color: #fff8ed;
  font-size: 0.95rem;
  font-weight: 700;
}

.settings-view__saved {
  color: #2f6b3a;
  font-size: 0.9rem;
  font-weight: 700;
}

@media (min-width: 1100px) {
  .settings-view {
    grid-template-columns: minmax(18rem, 0.92fr) minmax(0, 1.08fr);
    align-items: start;
  }
}
</style>
