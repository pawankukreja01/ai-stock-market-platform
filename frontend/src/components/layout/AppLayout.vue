<template>
  <div class="app-layout">
    <aside class="sidebar">
      <router-link
        to="/"
        class="brand brand-link"
        aria-label="AI Stock home"
      >
        <h2>AI Stock</h2>
        <span>Market Intelligence</span>
      </router-link>

      <nav class="navigation">
        <router-link
          to="/"
          exact-active-class="router-link-exact-active"
        >
          Dashboard
        </router-link>

        <router-link
          to="/portfolio"
          exact-active-class="router-link-exact-active"
        >
          Portfolio
        </router-link>

        <router-link
          to="/screener"
          exact-active-class="router-link-exact-active"
        >
          Stock Screener
        </router-link>

        <router-link
          to="/investment-simulator"
          exact-active-class="router-link-exact-active"
        >
          Investment Simulator
        </router-link>

        <router-link
          to="/alerts"
          class="alerts-nav-link"
          exact-active-class="router-link-exact-active"
        >
          <span>Alerts &amp; Notifications</span>

          <span
            v-if="unreadAlertCount > 0"
            class="unread-count"
            :aria-label="`${unreadAlertCount} unread alerts`"
          >
            {{ unreadAlertCount > 99 ? "99+" : unreadAlertCount }}
          </span>
        </router-link>
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

<script setup>
import { onBeforeUnmount, onMounted, ref } from "vue";
import { getAlertEvents } from "../../services/api";

const unreadAlertCount = ref(0);

let refreshIntervalId = null;
let requestInProgress = false;

async function refreshUnreadAlertCount() {
  if (requestInProgress) return;

  requestInProgress = true;

  try {
    const response = await getAlertEvents({
      unread: "true",
      limit: 1,
    });

    unreadAlertCount.value = Math.max(
      0,
      Number(response?.count ?? 0)
    );
  } catch (error) {
    // Keep the last known count if the API is temporarily unavailable.
    console.error("Unable to refresh unread alert count:", error);
  } finally {
    requestInProgress = false;
  }
}

onMounted(() => {
  refreshUnreadAlertCount();

  refreshIntervalId = window.setInterval(
    refreshUnreadAlertCount,
    60_000
  );
});

onBeforeUnmount(() => {
  if (refreshIntervalId !== null) {
    window.clearInterval(refreshIntervalId);
    refreshIntervalId = null;
  }
});
</script>

<style scoped>
.app-layout {
  min-height: 100vh;
  background: #f5f7fa;
}

.sidebar {
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  width: 240px;
  height: 100vh;
  overflow-y: auto;
  background: #111827;
  color: white;
  padding: 24px 16px;
  box-sizing: border-box;
  z-index: 1000;
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

.brand-link {
  display: block;
  color: white;
  text-decoration: none;
  border-radius: 8px;
}

.brand-link:hover h2 {
  color: #dbeafe;
}

.navigation {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.navigation a {
  display: block;
  padding: 11px 12px;
  border-radius: 8px;
  color: #d1d5db;
  text-decoration: none;
  font-size: 15px;
  transition: background 0.15s ease, color 0.15s ease;
}

.navigation a:hover,
.navigation a.router-link-exact-active {
  background: #1f2937;
  color: white;
}

.navigation a.alerts-nav-link {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.unread-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 22px;
  height: 22px;
  padding: 0 6px;
  border-radius: 999px;
  background: #dc2626;
  color: #fff;
  font-size: 11px;
  font-weight: 800;
  line-height: 1;
  flex-shrink: 0;
}

.main-area {
  margin-left: 240px;
  width: calc(100% - 240px);
  min-width: 0;
  min-height: 100vh;
}

.topbar {
  min-height: 70px;
  background: white;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 30px;
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

@media (max-width: 640px) {
  .sidebar {
    width: 170px;
    padding: 20px 10px;
  }

  .brand {
    padding: 0 8px 24px;
  }

  .main-area {
    margin-left: 170px;
    width: calc(100% - 170px);
  }

  .content {
    padding: 14px;
  }

  .topbar {
    padding: 16px;
  }

  .topbar h1 {
    font-size: 17px;
  }

  .navigation a {
    font-size: 13px;
  }
}
</style>