<template>
  <section class="matrix-hero">
    <div class="matrix-hero__content">
      <p class="matrix-hero__eyebrow">Project Matrix</p>
      <div class="space-y-3">
        <h1 class="matrix-hero__title">先找最该继续的项目，再进工作区。</h1>
        <p class="matrix-hero__summary">
          {{ summary }}
        </p>
      </div>
      <div class="matrix-hero__markers">
        <span class="matrix-hero__marker">{{ totalProjects }} 个项目</span>
        <span class="matrix-hero__marker">{{ totalWords.toLocaleString('zh-CN') }} 字累计产出</span>
        <span v-if="focusProjectName" class="matrix-hero__marker">当前焦点：{{ focusProjectName }}</span>
      </div>
    </div>

    <div class="matrix-hero__actions">
      <button
        class="matrix-hero__toggle"
        type="button"
        @click="composerOpen = !composerOpen"
      >
        {{ composerOpen ? '收起创建入口' : '新建项目' }}
      </button>

      <form v-if="composerOpen" class="matrix-hero__composer" @submit.prevent="submit">
        <label class="matrix-hero__field">
          <span class="matrix-hero__field-label">项目名</span>
          <input
            v-model.trim="name"
            class="matrix-hero__input"
            placeholder="例如：盐风档案"
            :disabled="submitting"
          />
        </label>

        <label class="matrix-hero__field">
          <span class="matrix-hero__field-label">题材</span>
          <input
            v-model.trim="genre"
            class="matrix-hero__input"
            placeholder="悬疑 / 仙侠 / 科幻"
            :disabled="submitting"
          />
        </label>

        <button
          class="matrix-hero__submit"
          type="submit"
          :disabled="submitting || !name"
        >
          {{ submitting ? '创建中...' : '创建并加入矩阵' }}
        </button>
      </form>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  summary: string
  totalProjects: number
  totalWords: number
  focusProjectName?: string
  submitting?: boolean
}>()

const emit = defineEmits<{
  create: [payload: { name: string; genre: string }]
}>()

const composerOpen = ref(false)
const name = ref('')
const genre = ref('')

function submit() {
  if (!name.value || props.submitting) return
  emit('create', { name: name.value, genre: genre.value })
  name.value = ''
  genre.value = ''
  composerOpen.value = false
}
</script>

<style scoped>
.matrix-hero {
  display: grid;
  gap: 1.5rem;
  border: 1px solid rgba(111, 69, 31, 0.18);
  border-radius: 2rem;
  padding: 1.5rem;
  background:
    linear-gradient(135deg, rgba(255, 249, 237, 0.96) 0%, rgba(241, 231, 209, 0.9) 100%);
  box-shadow:
    0 24px 48px rgba(75, 51, 26, 0.12),
    inset 0 1px 0 rgba(255, 251, 241, 0.82);
}

.matrix-hero__content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.matrix-hero__eyebrow {
  color: var(--accent-strong);
  font-family: "Palatino Linotype", "Book Antiqua", serif;
  font-size: 0.76rem;
  font-weight: 700;
  letter-spacing: 0.28em;
  text-transform: uppercase;
}

.matrix-hero__title {
  color: var(--ink-strong);
  font-family: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", serif;
  font-size: clamp(2rem, 5vw, 3.6rem);
  line-height: 0.95;
}

.matrix-hero__summary {
  max-width: 44rem;
  color: var(--ink-muted);
  font-size: 1rem;
  line-height: 1.7;
}

.matrix-hero__markers {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.matrix-hero__marker {
  border: 1px solid rgba(111, 69, 31, 0.14);
  border-radius: 999px;
  padding: 0.45rem 0.85rem;
  background: rgba(255, 249, 236, 0.72);
  color: var(--ink-muted);
  font-size: 0.82rem;
}

.matrix-hero__actions {
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
  align-self: stretch;
}

.matrix-hero__toggle,
.matrix-hero__submit {
  border: 1px solid rgba(111, 69, 31, 0.18);
  border-radius: 1rem;
  padding: 0.9rem 1rem;
  font-size: 0.95rem;
  font-weight: 700;
  transition:
    transform 180ms ease,
    border-color 180ms ease,
    box-shadow 180ms ease;
}

.matrix-hero__toggle {
  background: rgba(255, 248, 233, 0.8);
  color: var(--accent-strong);
}

.matrix-hero__submit {
  background: linear-gradient(180deg, rgba(150, 101, 55, 0.96) 0%, rgba(112, 72, 34, 0.98) 100%);
  color: #fff8ed;
}

.matrix-hero__toggle:hover,
.matrix-hero__submit:hover:not(:disabled) {
  transform: translateY(-1px);
  border-color: rgba(111, 69, 31, 0.28);
  box-shadow: 0 16px 28px rgba(83, 56, 28, 0.12);
}

.matrix-hero__submit:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.matrix-hero__composer {
  display: grid;
  gap: 0.85rem;
  border: 1px solid rgba(111, 69, 31, 0.14);
  border-radius: 1.4rem;
  padding: 1rem;
  background: rgba(252, 248, 239, 0.84);
}

.matrix-hero__field {
  display: grid;
  gap: 0.35rem;
}

.matrix-hero__field-label {
  color: var(--ink-muted);
  font-size: 0.78rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.matrix-hero__input {
  width: 100%;
  border: 1px solid rgba(111, 69, 31, 0.18);
  border-radius: 0.95rem;
  padding: 0.85rem 0.95rem;
  background: rgba(255, 252, 245, 0.92);
  color: var(--ink-strong);
  font-size: 0.96rem;
  outline: none;
}

.matrix-hero__input:focus {
  border-color: rgba(111, 69, 31, 0.34);
  box-shadow: 0 0 0 3px rgba(141, 93, 49, 0.12);
}

@media (min-width: 960px) {
  .matrix-hero {
    grid-template-columns: minmax(0, 1.5fr) minmax(20rem, 0.85fr);
    align-items: start;
    padding: 1.9rem 2rem;
  }
}
</style>
