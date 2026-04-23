<template>
  <main class="content-area"><slot /></main>
</template>

<style scoped>
.content-area {
  grid-area: content; overflow-y: auto;
  padding: var(--content-padding); background: var(--color-bg-white);
}
</style>
