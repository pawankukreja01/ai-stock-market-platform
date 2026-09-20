<template>
  <div class="dashboard">
    <div class="page-header">
      <div>
        <h1>Stock Market Dashboard</h1>
        <p>
          AI-powered market analysis, forecasting, and risk assessment.
        </p>
      </div>

      <div class="market-status">
        <span class="status-dot"></span>
        API Connected
      </div>
    </div>

    <div class="stats-grid">
      <div class="stat-card">
        <span class="stat-label">Tracked Stocks</span>
        <strong class="stat-value">{{ stocks.length }}</strong>
      </div>

      <div class="stat-card">
        <span class="stat-label">Market</span>
        <strong class="stat-value">US Equities</strong>
      </div>

      <div class="stat-card">
        <span class="stat-label">Data Source</span>
        <strong class="stat-value">Django API</strong>
      </div>
    </div>

    <section class="stocks-section">
      <div class="section-header">
        <div>
          <h2>Tracked Stocks</h2>
          <p>Stocks currently stored in the platform.</p>
        </div>
      </div>

      <div v-if="loading" class="message">
        Loading stocks...
      </div>

      <div v-else-if="error" class="message error">
        {{ error }}
      </div>

      <div v-else-if="stocks.length === 0" class="message">
        No stocks found.
      </div>

      <div v-else class="stock-list">
        <div
          v-for="stock in stocks"
          :key="stock.id"
          class="stock-row"
        >
          <div>
            <strong>{{ stock.symbol }}</strong>
            <span>{{ stock.company_name }}</span>
          </div>

          <div class="stock-meta">
            <span>{{ stock.exchange || "—" }}</span>
            <span>{{ stock.sector || "Sector unavailable" }}</span>
          </div>
        </div>
      </div>
    </section>

    <StockPriceChart
      v-if="stocks.length > 0"
      :stock-id="stocks[0].id"
      :symbol="stocks[0].symbol"
    />
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";

import { getStocks } from "../services/api";
import StockPriceChart from "../components/charts/StockPriceChart.vue";

const stocks = ref([]);
const loading = ref(true);
const error = ref("");

const loadStocks = async () => {
  try {
    loading.value = true;
    error.value = "";

    stocks.value = await getStocks();
  } catch (err) {
    console.error("Failed to load stocks:", err);

    error.value =
      "Unable to connect to the Django API. Make sure the backend is running.";
  } finally {
    loading.value = false;
  }
};

onMounted(loadStocks);
</script>

<style scoped>
.dashboard {
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 30px;
}

.page-header h1 {
  margin: 0;
  font-size: 30px;
}

.page-header p {
  margin: 8px 0 0;
  color: #6b7280;
}

.market-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #ecfdf5;
  color: #047857;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #10b981;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  margin-bottom: 30px;
}

.stat-card {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 22px;
}

.stat-label {
  display: block;
  color: #6b7280;
  font-size: 14px;
  margin-bottom: 10px;
}

.stat-value {
  display: block;
  font-size: 26px;
  color: #111827;
}

.stocks-section {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  overflow: hidden;
}

.section-header {
  padding: 22px;
  border-bottom: 1px solid #e5e7eb;
}

.section-header h2 {
  margin: 0;
  font-size: 20px;
}

.section-header p {
  margin: 6px 0 0;
  color: #6b7280;
  font-size: 14px;
}

.stock-list {
  display: flex;
  flex-direction: column;
}

.stock-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 22px;
  border-bottom: 1px solid #f3f4f6;
}

.stock-row:last-child {
  border-bottom: none;
}

.stock-row strong {
  display: block;
  font-size: 17px;
}

.stock-row span {
  display: block;
  margin-top: 4px;
  color: #6b7280;
  font-size: 13px;
}

.stock-meta {
  display: flex;
  gap: 25px;
  text-align: right;
}

.stock-meta span {
  margin: 0;
}

.message {
  padding: 30px;
  text-align: center;
  color: #6b7280;
}

.message.error {
  color: #b91c1c;
  background: #fef2f2;
}

@media (max-width: 800px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }

  .page-header {
    flex-direction: column;
  }

  .stock-row {
    align-items: flex-start;
    flex-direction: column;
    gap: 12px;
  }

  .stock-meta {
    text-align: left;
    flex-wrap: wrap;
  }
}
</style>