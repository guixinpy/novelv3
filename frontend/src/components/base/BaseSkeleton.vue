<script setup lang="ts">
defineProps<{
  width?: string
  height?: string
  rounded?: 'sm' | 'md' | 'lg' | 'full'
}>()
</script>

<template>
  <div
    class="base-skeleton"
    :style="{ width: width || '100%', height: height || '1rem' }"
    :class="[rounded ? `base-skeleton--rounded-${rounded}` : '']"
    aria-hidden="true"
  />
</template>

<style scoped>
.base-skeleton {
  background: linear-gradient(
    90deg,
    var(--color-bg-tertiary) 25%,
    var(--color-bg-secondary) 50%,
    var(--color-bg-tertiary) 75%
  );
  background-size: 200% 100%;
  animation: base-skeleton-pulse 1.5s ease-in-out infinite;
  border-radius: var(--radius-sm);
}

.base-skeleton--rounded-sm { border-radius: var(--radius-sm); }
.base-skeleton--rounded-md { border-radius: var(--radius-md); }
.base-skeleton--rounded-lg { border-radius: var(--radius-lg); }
.base-skeleton--rounded-full { border-radius: var(--radius-full); }

@keyframes base-skeleton-pulse {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
</style>
