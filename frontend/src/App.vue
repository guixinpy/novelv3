<template>
  <div class="min-h-screen">
    <nav class="bg-white border-b border-gray-200">
      <div class="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex items-center justify-between h-14">
          <div class="flex items-center gap-2">
            <span class="text-indigo-600 font-bold text-lg">墨舟</span>
            <span class="text-gray-400">|</span>
            <span class="text-gray-600 text-sm">AI Writer</span>
          </div>
          <div class="flex items-center gap-4">
            <router-link
              to="/"
              class="text-sm font-medium text-gray-700 hover:text-indigo-600"
              active-class="text-indigo-600"
            >
              项目列表
            </router-link>
<router-link
              to="/settings"
              class="text-sm font-medium text-gray-700 hover:text-indigo-600"
              active-class="text-indigo-600"
            >
              设置
            </router-link>
          </div>
        </div>
      </div>
    </nav>
    <main class="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <router-view />
    </main>
  </div>
</template>
