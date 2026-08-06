<template>
  <v-app>
    <!-- 顶栏 App Bar -->
    <v-app-bar color="primary" elevation="2">
      <v-app-bar-title class="font-weight-medium text-white">抖音自动续火花 - 控制台</v-app-bar-title>
    </v-app-bar>

    <!-- 主内容区 Main -->
    <v-main class="bg-background">
      <v-container fluid class="pa-6">
        <v-fade-transition mode="out-in">
          <router-view />
        </v-fade-transition>
      </v-container>
    </v-main>
  </v-app>
</template>

<script setup lang="ts">
// No logic needed here anymore since we removed the sidebar and theme toggle
</script>

<style>
body {
  margin: 0;
  font-family: 'Inter', sans-serif;
}
</style>
