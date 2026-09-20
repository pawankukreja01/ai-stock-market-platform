<template>
  <div class="app-layout">
    <aside class="sidebar">
      <div class="brand">
        <h2>AI Stock</h2>
        <span>Market Intelligence</span>
      </div>

      <nav class="navigation">
        <router-link to="/">Dashboard</router-link>
      </nav>
    </aside>

    <div class="main-area">
      <header class="topbar">
        <div>
          <h1>Market Intelligence</h1>
        </div>

        <div class="topbar-right">
          <span>US Markets</span>
        </div>
      </header>

      <main class="content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<style scoped>
.app-layout {
  min-height: 100vh;
  display: flex;
  background: #f5f7fa;
}

.sidebar {
  width: 240px;
  min-height: 100vh;
  background: #111827;
  color: white;
  padding: 24px 16px;
  box-sizing: border-box;
}

.brand {
  padding: 0 12px 30px;
}

.brand h2 {
  margin: 0;
  font-size: 22px;
}

.brand span {
  display: block;
  margin-top: 5px;
  font-size: 12px;
  color: #9ca3af;
}

.navigation {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.navigation a {
  padding: 11px 12px;
  border-radius: 8px;
  color: #d1d5db;
  text-decoration: none;
}

.navigation a:hover,
.navigation a.router-link-active {
  background: #1f2937;
  color: white;
}

.main-area {
  flex: 1;
  min-width: 0;
}

.topbar {
  height: 70px;
  background: white;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 30px;
  box-sizing: border-box;
}

.topbar h1 {
  margin: 0;
  font-size: 20px;
}

.topbar-right {
  font-size: 14px;
  color: #6b7280;
}

.content {
  padding: 30px;
}
</style>