<template>
  <div>
    <nav style="padding: 1rem; border-bottom: 1px solid #ccc;">
      <router-link to="/">项目列表</router-link> |
      <router-link to="/chat">对话</router-link> |
      <router-link to="/settings">设置</router-link>
    </nav>
    <main style="padding: 1rem;">
      <router-view />
    </main>
  </div>
</template>
