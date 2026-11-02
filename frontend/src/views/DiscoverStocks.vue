<template>
  <div class="discover-page">
    <div v-if="unsupportedMarketPreference" class="state-message">
      Your preferred market is Pakistan, but Pakistani stocks are not yet
      available in this catalog. You can currently browse US and UK stocks.
    </div>

    <header class="hero">
      <div>
        <p class="eyebrow">MARKET EXPLORER</p>
        <h1>Discover stocks</h1>
        <p class="hero-copy">
          Explore US and UK listed companies, search by ticker or name,
          and build your own research shortlist.
        </p>
      </div>
      <div class="hero-stat">
        <span>Stocks in catalog</span>
        <strong>{{ universeCount || totalCount }}</strong>
        <small>US and UK markets</small>
      </div>
    </header>

    <section class="market-switcher" aria-label="Choose market">
      <button
        v-for="option in markets"
        :key="option.value"
        type="button"
        :class="{ selected: market === option.value }"
        :aria-pressed="market === option.value"
        @click="selectMarket(option.value)"
      >
        <span>{{ option.label }}</span>
        <small>{{ option.description }}</small>
      </button>
    </section>

    <section class="panel">
      <div class="section-heading">
        <div>
          <p class="eyebrow">START EXPLORING</p>
          <h2>Popular stocks</h2>
          <p class="muted">
            A curated discovery list, not a ranking or recommendation to buy.
          </p>
        </div>
        <span class="count-pill">{{ popularStocks.length }} shown</span>
      </div>

      <p v-if="popularLoading" class="state-message">
        Loading popular stocks…
      </p>

      <p v-else-if="popularError" class="state-message error">
        {{ popularError }}
        <button type="button" class="text-button" @click="loadPopular">
          Try again
        </button>
      </p>

      <p v-else-if="popularStocks.length === 0" class="state-message">
        No curated stocks match this market.
      </p>

      <div v-else class="popular-grid">
        <button
          v-for="stock in popularStocks"
          :key="stock.id"
          type="button"
          class="popular-card"
          @click="openStockResearch(stock.symbol)"
        >
          <span class="popular-card-top">
            <strong>{{ stock.symbol }}</strong>
            <span class="market-tag">{{ stock.market }}</span>
          </span>
          <span class="company-name">{{ stock.company_name }}</span>
          <span class="popular-card-bottom">
            {{ stock.exchange }} · {{ stock.sector || "Sector unavailable" }}
          </span>
          <span class="card-action">Open research →</span>
        </button>
      </div>
    </section>

    <section class="panel catalog-panel" id="stock-catalog">
      <div class="section-heading">
        <div>
          <p class="eyebrow">SEARCH THE UNIVERSE</p>
          <h2>Stock catalog</h2>
          <p class="muted">
            Search symbols, companies, sectors, or industries.
          </p>
        </div>
        <span class="count-pill">
          {{ totalCount }} result{{ totalCount === 1 ? "" : "s" }}
        </span>
      </div>

      <form class="filters" @submit.prevent="applyFilters">
        <label>
          <span>Search stocks</span>
          <input
            v-model="searchInput"
            type="search"
            placeholder="e.g. AAPL, Apple, AstraZeneca"
            autocomplete="off"
          />
        </label>

        <label>
          <span>Exchange</span>
          <select v-model="exchange">
            <option value="">All exchanges</option>
            <option
              v-for="item in availableExchanges"
              :key="item.value"
              :value="item.value"
            >
              {{ item.label }}
            </option>
          </select>
        </label>

        <label>
          <span>Sector or industry</span>
          <input
            v-model.trim="sector"
            type="text"
            placeholder="e.g. Technology, Healthcare"
          />
        </label>

        <div class="filter-actions">
          <button class="primary-button" type="submit" :disabled="loading">
            {{ loading ? "Searching…" : "Search" }}
          </button>
          <button
            class="secondary-button"
            type="button"
            @click="resetFilters"
          >
            Clear
          </button>
        </div>
      </form>

      <div class="results-heading">
        <span>Company</span>
        <span>Market</span>
        <span>Sector</span>
        <span>Industry</span>
      </div>

      <div v-if="loading" class="state-message">
        Loading stock catalog…
      </div>

      <div v-else-if="error" class="state-message error">
        {{ error }}
        <button type="button" class="text-button" @click="loadStocks">
          Try again
        </button>
      </div>

      <div v-else-if="stocks.length === 0" class="empty-state">
        <strong>No matching stocks</strong>
        <p>Try a different name, symbol, exchange, or sector.</p>
        <button
          type="button"
          class="secondary-button"
          @click="resetFilters"
        >
          Clear filters
        </button>
      </div>

      <div v-else class="stock-results">
        <router-link
          v-for="stock in stocks"
          :key="stock.id"
          :to="{ name: 'StockResearch', params: { symbol: stock.symbol } }"
          class="stock-row stock-row-link"
          :aria-label="`Open research for ${stock.symbol} — ${stock.company_name}`"
        >
          <div class="company-cell">
            <span class="symbol-mark">{{ stock.symbol }}</span>
            <span class="company-details">
              <strong>{{ stock.company_name }}</strong>
              <small>{{ stock.exchange }}</small>
            </span>
          </div>

          <span class="market-cell">
            <span class="market-tag">{{ stock.market }}</span>
          </span>

          <span>{{ stock.sector || "—" }}</span>
          <span>{{ stock.industry || "—" }}</span>
        </router-link>
      </div>

      <footer
        v-if="!loading && !error && totalCount > 0"
        class="pagination"
      >
        <span>Page {{ currentPage }} of {{ totalPages || 1 }}</span>
        <div class="pagination-actions">
          <button
            type="button"
            class="secondary-button"
            :disabled="currentPage <= 1"
            @click="changePage(currentPage - 1)"
          >
            ← Previous
          </button>
          <button
            type="button"
            class="secondary-button"
            :disabled="currentPage >= totalPages"
            @click="changePage(currentPage + 1)"
          >
            Next →
          </button>
        </div>
      </footer>

      <p class="data-note">
        This page is a stock-discovery and research tool, not personalised
        financial advice. A catalog entry does not guarantee that recent
        prices, fundamentals, or news are available for that stock.
      </p>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import {
  getStockCatalog,
  getPopularStocks,
  getCurrentUser,
} from "../services/api";

const router = useRouter();
const PAGE_SIZE = 24;

const markets = [
  {
    value: "ALL",
    label: "All markets",
    description: "US + UK",
  },
  {
    value: "US",
    label: "United States",
    description: "NASDAQ + NYSE",
  },
  {
    value: "UK",
    label: "United Kingdom",
    description: "London Stock Exchange",
  },
];

const market = ref("ALL");
const unsupportedMarketPreference = ref(false);
const exchange = ref("");
const searchInput = ref("");
const appliedSearch = ref("");
const sector = ref("");

const stocks = ref([]);
const popularStocks = ref([]);

const totalCount = ref(0);
const universeCount = ref(0);
const totalPages = ref(1);
const currentPage = ref(1);

const loading = ref(false);
const popularLoading = ref(false);
const error = ref("");
const popularError = ref("");

const availableExchanges = computed(() => {
  if (market.value === "US") {
    return [
      { value: "NASDAQ", label: "NASDAQ" },
      { value: "NYSE", label: "NYSE" },
    ];
  }

  if (market.value === "UK") {
    return [
      { value: "LSE", label: "London Stock Exchange (LSE)" },
    ];
  }

  return [
    { value: "NASDAQ", label: "NASDAQ" },
    { value: "NYSE", label: "NYSE" },
    { value: "LSE", label: "London Stock Exchange (LSE)" },
  ];
});

async function loadStocks() {
  loading.value = true;
  error.value = "";

  try {
    const result = await getStockCatalog({
      search: appliedSearch.value,
      market: market.value === "ALL" ? "" : market.value,
      exchange: exchange.value,
      sector: sector.value,
      page: currentPage.value,
      pageSize: PAGE_SIZE,
    });

    stocks.value = Array.isArray(result)
      ? result
      : result.results || [];

    totalCount.value = result.count ?? stocks.value.length;
    totalPages.value = result.total_pages ?? 1;
    currentPage.value = result.page ?? currentPage.value;

    if (
      !appliedSearch.value &&
      !sector.value &&
      !exchange.value &&
      market.value === "ALL"
    ) {
      universeCount.value = totalCount.value;
    }
  } catch (requestError) {
    console.error("Failed to load stock catalog:", requestError);
    error.value =
      "Unable to load stocks. Check that the Django API is running.";
    stocks.value = [];
    totalCount.value = 0;
    totalPages.value = 1;
  } finally {
    loading.value = false;
  }
}

async function loadPopular() {
  popularLoading.value = true;
  popularError.value = "";

  try {
    const result = await getPopularStocks({
      market: market.value === "ALL" ? "" : market.value,
      pageSize: 100,
    });

    popularStocks.value = Array.isArray(result)
      ? result
      : result.results || [];
  } catch (requestError) {
    console.error("Failed to load popular stocks:", requestError);
    popularError.value = "Unable to load the popular list.";
    popularStocks.value = [];
  } finally {
    popularLoading.value = false;
  }
}

function selectMarket(value) {
  market.value = value;
  unsupportedMarketPreference.value = false;
  exchange.value = "";
  currentPage.value = 1;

  loadStocks();
  loadPopular();
}

function applyFilters() {
  appliedSearch.value = searchInput.value.trim();
  currentPage.value = 1;
  loadStocks();
}

function resetFilters() {
  searchInput.value = "";
  appliedSearch.value = "";
  sector.value = "";
  exchange.value = "";
  currentPage.value = 1;

  loadStocks();
}

function changePage(page) {
  if (page < 1 || page > totalPages.value || loading.value) return;

  currentPage.value = page;
  loadStocks();
}

function openStockResearch(symbol) {
  const normalizedSymbol = String(symbol || "").trim().toUpperCase();
  if (!normalizedSymbol) return;

  router.push({
    name: "StockResearch",
    params: { symbol: normalizedSymbol },
  });
}

function searchPopular(stock) {
  market.value = stock.market || "ALL";
  unsupportedMarketPreference.value = false;
  exchange.value = "";
  searchInput.value = stock.symbol;
  appliedSearch.value = stock.symbol;
  sector.value = "";
  currentPage.value = 1;

  loadStocks();

  document
    .getElementById("stock-catalog")
    ?.scrollIntoView({ behavior: "smooth", block: "start" });
}

onMounted(async () => {
  try {
    const response = await getCurrentUser();
    const user = response.user || response;

    const preferredMarket = user.preferred_market || "global";
    const preferredSectors = Array.isArray(user.preferred_sectors)
      ? user.preferred_sectors
      : [];

    if (preferredMarket === "us") {
      market.value = "US";
    } else if (preferredMarket === "uk") {
      market.value = "UK";
    } else if (preferredMarket === "pakistan") {
      market.value = "ALL";
      unsupportedMarketPreference.value = true;
    } else {
      market.value = "ALL";
    }

    sector.value = preferredSectors.join(", ");
  } catch (requestError) {
    console.warn(
      "Unable to load profile preferences:",
      requestError
    );
  }

  await Promise.all([loadStocks(), loadPopular()]);
});
</script>

<style scoped>
.discover-page {
  display: grid;
  gap: 22px;
  color: var(--text-primary, #e8eef8);
  padding-bottom: 32px;
}

.hero {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 24px;
  padding: 28px;
  border: 1px solid var(--border-color, #26364b);
  border-radius: 18px;
  background:
    radial-gradient(
      circle at 85% 10%,
      rgba(65, 190, 148, 0.14),
      transparent 36%
    ),
    var(--surface-card, #111b2b);
}

.eyebrow {
  margin: 0 0 9px;
  color: #64d9ad;
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.13em;
}

h1,
h2,
p {
  margin-top: 0;
}

h1 {
  margin-bottom: 10px;
  font-size: clamp(1.7rem, 3vw, 2.45rem);
  letter-spacing: -0.04em;
}

h2 {
  margin-bottom: 7px;
  font-size: 1.25rem;
  letter-spacing: -0.025em;
}

.hero-copy,
.muted {
  color: var(--text-muted, #99a9bd);
  line-height: 1.6;
}

.hero-copy {
  max-width: 650px;
  margin-bottom: 0;
}

.hero-stat {
  min-width: 150px;
  padding: 16px;
  display: grid;
  gap: 5px;
  border: 1px solid rgba(100, 217, 173, 0.22);
  border-radius: 13px;
  background: rgba(10, 25, 37, 0.6);
}

.hero-stat span,
.hero-stat small {
  color: var(--text-muted, #99a9bd);
  font-size: 0.8rem;
}

.hero-stat strong {
  color: #64d9ad;
  font-size: 2rem;
}

.market-switcher {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.market-switcher button {
  display: grid;
  gap: 5px;
  text-align: left;
  padding: 15px 17px;
  border: 1px solid var(--border-color, #26364b);
  border-radius: 12px;
  background: var(--surface-card, #111b2b);
  color: inherit;
  cursor: pointer;
  transition: border-color 0.18s ease, background 0.18s ease;
}

.market-switcher button:hover,
.market-switcher button.selected {
  border-color: #4bc69b;
  background: rgba(39, 151, 115, 0.11);
}

.market-switcher button span {
  font-weight: 750;
}

.market-switcher button small {
  color: var(--text-muted, #99a9bd);
}

.panel {
  min-width: 0;
  padding: 23px;
  border: 1px solid var(--border-color, #26364b);
  border-radius: 16px;
  background: var(--surface-card, #111b2b);
}

.section-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 20px;
}

.section-heading .muted {
  margin-bottom: 0;
  font-size: 0.88rem;
}

.count-pill,
.market-tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: fit-content;
  white-space: nowrap;
  padding: 5px 9px;
  border: 1px solid var(--border-color, #304158);
  border-radius: 100px;
  background: rgba(100, 116, 139, 0.12);
  color: var(--text-muted, #bdc8d6);
  font-size: 0.75rem;
  font-weight: 700;
}

.popular-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 11px;
}

.popular-card {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 9px;
  min-width: 0;
  padding: 15px;
  text-align: left;
  border: 1px solid var(--border-color, #26364b);
  border-radius: 12px;
  background: var(--surface-raised, #142135);
  color: inherit;
  cursor: pointer;
  transition: transform 0.18s ease, border-color 0.18s ease;
}

.popular-card:hover {
  transform: translateY(-2px);
  border-color: #4bc69b;
}

.popular-card-top,
.popular-card-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.popular-card-top strong {
  overflow-wrap: anywhere;
  font-size: 1rem;
  color: #64d9ad;
}

.company-name {
  font-size: 0.86rem;
  font-weight: 650;
  line-height: 1.45;
  min-height: 2.5em;
}

.popular-card-bottom {
  justify-content: flex-start;
  flex-wrap: wrap;
  color: var(--text-muted, #99a9bd);
  font-size: 0.74rem;
}

.card-action {
  margin-top: 3px;
  color: #64d9ad;
  font-size: 0.78rem;
  font-weight: 750;
}

.filters {
  display: grid;
  grid-template-columns:
    minmax(220px, 1.6fr)
    minmax(160px, 0.8fr)
    minmax(160px, 0.9fr)
    auto;
  align-items: end;
  gap: 12px;
  margin-bottom: 24px;
}

.filters label {
  display: grid;
  gap: 7px;
  min-width: 0;
}

.filters label > span {
  color: var(--text-muted, #99a9bd);
  font-size: 0.8rem;
  font-weight: 700;
}

.filters input,
.filters select {
  box-sizing: border-box;
  width: 100%;
  min-width: 0;
  min-height: 42px;
  padding: 10px 12px;
  border: 1px solid var(--border-color, #304158);
  border-radius: 9px;
  outline: none;
  background: var(--surface-raised, #142135);
  color: inherit;
  font: inherit;
}

.filters input:focus,
.filters select:focus {
  border-color: #4bc69b;
  box-shadow: 0 0 0 3px rgba(75, 198, 155, 0.13);
}

.filter-actions,
.pagination-actions {
  display: flex;
  gap: 8px;
}

.primary-button,
.secondary-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 40px;
  padding: 9px 13px;
  border: 1px solid transparent;
  border-radius: 9px;
  font: inherit;
  font-size: 0.84rem;
  font-weight: 750;
  cursor: pointer;
  white-space: nowrap;
}

.primary-button {
  background: #54d3a4;
  color: #062b21;
}

.secondary-button {
  border-color: var(--border-color, #304158);
  background: transparent;
  color: inherit;
}

.primary-button:disabled,
.secondary-button:disabled {
  opacity: 0.42;
  cursor: not-allowed;
}

.results-heading,
.stock-row {
  display: grid;
  grid-template-columns:
    minmax(200px, 1.55fr)
    0.65fr
    1fr
    1.1fr;
  gap: 14px;
  align-items: center;
}

.results-heading {
  padding: 11px 13px;
  border-bottom: 1px solid var(--border-color, #304158);
  color: var(--text-muted, #99a9bd);
  font-size: 0.75rem;
  font-weight: 800;
}

.stock-results {
  display: grid;
}

.stock-row {
  padding: 14px 13px;
  border-bottom: 1px solid var(--border-color, #26364b);
  font-size: 0.84rem;
}

.stock-row:last-child {
  border-bottom: 0;
}

.stock-row > span:not(.market-cell) {
  overflow-wrap: anywhere;
  color: var(--text-muted, #bdc8d6);
}

.company-cell {
  display: flex;
  align-items: center;
  gap: 11px;
  min-width: 0;
}

.symbol-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 54px;
  min-height: 37px;
  padding: 0 7px;
  box-sizing: border-box;
  border-radius: 8px;
  background: rgba(75, 198, 155, 0.1);
  color: #64d9ad;
  font-weight: 850;
  font-size: 0.78rem;
  overflow-wrap: anywhere;
}

.company-details {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.company-details strong {
  line-height: 1.4;
  overflow-wrap: anywhere;
}

.company-details small {
  color: var(--text-muted, #99a9bd);
}

.market-cell {
  display: flex;
  align-items: center;
}

.state-message,
.empty-state {
  padding: 24px 12px;
  color: var(--text-muted, #99a9bd);
  text-align: center;
}

.empty-state strong {
  display: block;
  margin-bottom: 6px;
  color: inherit;
}

.empty-state p {
  margin-bottom: 14px;
}

.error {
  color: #f3a3a3;
}

.text-button {
  margin-left: 8px;
  padding: 3px 6px;
  border: 0;
  background: transparent;
  color: #64d9ad;
  font: inherit;
  font-weight: 750;
  cursor: pointer;
}

.pagination {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
  padding-top: 17px;
  border-top: 1px solid var(--border-color, #26364b);
  color: var(--text-muted, #99a9bd);
  font-size: 0.83rem;
}

.data-note {
  margin: 20px 0 0;
  padding: 13px 14px;
  border-radius: 9px;
  background: rgba(100, 116, 139, 0.09);
  color: var(--text-muted, #99a9bd);
  font-size: 0.79rem;
  line-height: 1.6;
}

@media (max-width: 1100px) {
  .popular-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .filters {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .filter-actions {
    align-self: end;
  }
}

@media (max-width: 760px) {
  .hero {
    flex-direction: column;
    padding: 21px;
  }

  .hero-stat {
    width: auto;
    min-width: 0;
    align-self: stretch;
  }

  .market-switcher {
    grid-template-columns: 1fr;
  }

  .popular-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .panel {
    padding: 16px;
  }

  .section-heading {
    flex-direction: column;
  }

  .filters {
    grid-template-columns: 1fr;
  }

  .results-heading {
    display: none;
  }

  .stock-row {
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 10px;
    padding: 15px 5px;
  }

  .stock-row > span:nth-child(3),
  .stock-row > span:nth-child(4) {
    grid-column: 1 / -1;
    font-size: 0.78rem;
  }

  .stock-row > span:nth-child(3)::before {
    content: "Sector: ";
    color: var(--text-muted, #99a9bd);
  }

  .stock-row > span:nth-child(4)::before {
    content: "Industry: ";
    color: var(--text-muted, #99a9bd);
  }

  .market-cell {
    justify-content: flex-end;
  }

  .pagination {
    align-items: flex-start;
    flex-direction: column;
  }

  .popular-card {
    padding: 12px;
  }
}

@media (max-width: 420px) {
  .popular-grid {
    grid-template-columns: 1fr;
  }

  .filter-actions {
    flex-wrap: wrap;
  }
}
.stock-row-link {
  color: inherit;
  text-decoration: none;
  cursor: pointer;
  transition: background 140ms ease, box-shadow 140ms ease;
}

.stock-row-link:hover {
  background: rgba(75, 198, 155, 0.07);
}

.stock-row-link:focus-visible,
.popular-card:focus-visible {
  outline: 3px solid rgba(75, 198, 155, 0.45);
  outline-offset: 2px;
}

</style>
