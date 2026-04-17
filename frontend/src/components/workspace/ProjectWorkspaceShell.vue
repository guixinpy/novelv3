<template>
  <div class="workspace-shell">
    <section class="workspace-shell__chat">
      <slot name="chat" />
    </section>
    <aside class="workspace-shell__inspector">
      <slot name="inspector" />
    </aside>
  </div>
</template>

<style scoped>
.workspace-shell {
  display: grid;
  gap: 1rem;
  min-height: calc(100svh - 7.5rem);
}

.workspace-shell__chat,
.workspace-shell__inspector {
  min-height: 24rem;
}

@media (min-width: 1024px) {
  .workspace-shell {
    grid-template-columns: minmax(0, 1.72fr) minmax(22rem, 1fr);
    height: calc(100svh - 8.5rem);
  }

  .workspace-shell__chat,
  .workspace-shell__inspector {
    min-height: 0;
  }
}
</style>
