<template>
  <div class="alerts-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">MONITORING WORKSPACE</p>
        <h1>Alerts & Notifications</h1>
        <p class="subtitle">
          Manage your price and financial-news sentiment alerts.
        </p>
      </div>

      <button
        class="button secondary"
        type="button"
        :disabled="loading"
        @click="loadAll"
      >
        {{ loading ? "Refreshing…" : "Refresh" }}
      </button>
    </header>

    <div class="info-banner">
      <strong>How alert evaluation works</strong>
      <p>
        Rules use your latest stored closing prices or the average sentiment
        of up to 50 recently published, analysed news articles. To evaluate
        them, run
        <code>python manage.py evaluate_alerts</code>
        from your backend directory. Refresh this page to view new events.
      </p>
    </div>

    <div v-if="pageError" class="alert error-alert">
      <strong>Something went wrong</strong>
      <p>{{ pageError }}</p>
    </div>

    <section class="summary-grid">
      <article class="summary-card">
        <span class="summary-label">Total rules</span>
        <strong>{{ rules.length }}</strong>
        <small>Configured alert rules</small>
      </article>

      <article class="summary-card">
        <span class="summary-label">Active rules</span>
        <strong>{{ activeRuleCount }}</strong>
        <small>Eligible for evaluation</small>
      </article>

      <article class="summary-card">
        <span class="summary-label">Unread events</span>
        <strong>{{ unreadEventCount }}</strong>
        <small>Triggered notifications not yet read</small>
      </article>
    </section>

    <section class="panel">
      <div class="panel-heading">
        <div>
          <h2>Create an alert</h2>
          <p>Choose a stock, condition and threshold.</p>
        </div>
      </div>

      <form class="create-form" @submit.prevent="createRule">
        <label class="field">
          <span>Stock</span>
          <select v-model="form.stock_symbol" required>
            <option value="" disabled>Select a stock</option>
            <option
              v-for="stock in stocks"
              :key="stock.id"
              :value="stock.symbol"
            >
              {{ stock.symbol }} — {{ stock.company_name }}
            </option>
          </select>
        </label>

        <label class="field">
          <span>Alert type</span>
          <select v-model="form.alert_type" required>
            <option value="price_above">Price rises above</option>
            <option value="price_below">Price falls below</option>
            <option value="sentiment_above">Sentiment rises above</option>
            <option value="sentiment_below">Sentiment falls below</option>
          </select>
        </label>

        <label class="field">
          <span>{{ thresholdLabel }}</span>
          <input
            v-model="form.threshold"
            type="number"
            :min="isPriceAlert ? '0.000001' : '-1'"
            :max="isPriceAlert ? undefined : '1'"
            step="any"
            required
            :placeholder="thresholdPlaceholder"
          />
        </label>

        <label class="field">
          <span>Rule name (optional)</span>
          <input
            v-model.trim="form.name"
            type="text"
            maxlength="150"
            placeholder="e.g. Alert me on a pullback"
          />
        </label>

        <div class="form-actions">
          <button
            class="button primary"
            type="submit"
            :disabled="saving || !form.stock_symbol"
          >
            {{ saving ? "Creating…" : "Create alert" }}
          </button>
        </div>
      </form>

      <p class="helper-text">
        Price thresholds use USD. Sentiment thresholds range from -1 to 1.
        Alerts are evaluated against stored data rather than live quotes.
      </p>

      <div v-if="formError" class="inline-error">
        {{ formError }}
      </div>

      <div v-if="successMessage" class="success-message">
        {{ successMessage }}
      </div>
    </section>

    <section class="panel">
      <div class="panel-heading rules-heading">
        <div>
          <h2>Alert rules</h2>
          <p>Enable, pause or delete rules.</p>
        </div>

        <label class="filter-field">
          <span>Show</span>
          <select v-model="ruleFilter">
            <option value="all">All rules</option>
            <option value="active">Active only</option>
            <option value="paused">Paused only</option>
          </select>
        </label>
      </div>

      <div v-if="loading" class="state-message">
        Loading alert rules…
      </div>

      <div
        v-else-if="filteredRules.length === 0"
        class="empty-state"
      >
        <h3>No matching alert rules</h3>
        <p>Create a rule above or change the filter.</p>
      </div>

      <div v-else class="table-scroll">
        <table class="data-table">
          <thead>
            <tr>
              <th>Stock</th>
              <th>Rule</th>
              <th>Threshold</th>
              <th>Last observed</th>
              <th>Condition</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>

          <tbody>
            <tr v-for="rule in filteredRules" :key="rule.id">
              <td>
                <strong>{{ rule.stock_symbol }}</strong>
                <small>{{ rule.company_name }}</small>
              </td>

              <td>
                <strong>{{ rule.name || rule.alert_type_label }}</strong>
                <small>{{ rule.alert_type_label }}</small>
              </td>

              <td>{{ formatMetric(rule.alert_type, rule.threshold) }}</td>

              <td>
                {{ formatMetric(rule.alert_type, rule.last_observed_value) }}
                <small>{{ formatDate(rule.last_evaluated_at) }}</small>
              </td>

              <td>
                <span
                  class="status-pill"
                  :class="rule.condition_met ? 'condition-met' : 'condition-clear'"
                >
                  {{ rule.condition_met ? "Condition met" : "Not met" }}
                </span>
              </td>

              <td>
                <span
                  class="status-pill"
                  :class="rule.is_active ? 'active-pill' : 'paused-pill'"
                >
                  {{ rule.is_active ? "Active" : "Paused" }}
                </span>
              </td>

              <td class="actions-cell">
                <button
                  class="mini-button"
                  type="button"
                  :disabled="workingRuleId === rule.id"
                  @click="toggleRule(rule)"
                >
                  {{ workingRuleId === rule.id
                    ? "Saving…"
                    : rule.is_active ? "Pause" : "Enable" }}
                </button>

                <button
                  class="mini-button delete-button"
                  type="button"
                  :disabled="workingRuleId === rule.id"
                  @click="removeRule(rule)"
                >
                  Delete
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="panel">
      <div class="panel-heading events-heading">
        <div>
          <h2>Triggered events</h2>
          <p>Recent alert notifications recorded by the backend.</p>
        </div>

        <label class="filter-field">
          <span>Show</span>
          <select v-model="eventFilter">
            <option value="all">All events</option>
            <option value="unread">Unread only</option>
            <option value="read">Read only</option>
          </select>
        </label>
      </div>

      <div v-if="filteredEvents.length === 0" class="empty-state">
        <h3>No matching events</h3>
        <p>
          When an enabled rule changes from not met to met during evaluation,
          its event will appear here.
        </p>
      </div>

      <div v-else class="event-list">
        <article
          v-for="event in filteredEvents"
          :key="event.id"
          class="event-row"
          :class="{ 'unread-event': !event.is_read }"
        >
          <div class="event-indicator">
            <span :class="event.is_read ? 'read-dot' : 'unread-dot'"></span>
          </div>

          <div class="event-content">
            <div class="event-title">
              <strong>{{ event.stock_symbol }}</strong>
              <span
                class="status-pill"
                :class="event.is_read ? 'read-pill' : 'unread-pill'"
              >
                {{ event.is_read ? "Read" : "Unread" }}
              </span>
            </div>

            <p>{{ event.message }}</p>

            <small>
              {{ event.alert_type_label }}
              <span v-if="event.rule_name"> · {{ event.rule_name }}</span>
              · {{ formatDate(event.triggered_at) }}
            </small>
          </div>

          <button
            v-if="!event.is_read"
            class="mini-button"
            type="button"
            :disabled="workingEventId === event.id"
            @click="markRead(event)"
          >
            {{ workingEventId === event.id ? "Saving…" : "Mark read" }}
          </button>
        </article>
      </div>

      <div v-if="eventsError" class="inline-error">
        {{ eventsError }}
      </div>
    </section>

    <p class="disclaimer">
      Alerts use the stored data available at evaluation time. They are not
      guaranteed to run in real time, and they are not personalised
      investment advice. Scheduled evaluation and email delivery can be
      added after the core workflow is validated.
    </p>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";

import {
  getStocks,
  getAlertRules,
  createAlertRule,
  updateAlertRule,
  deleteAlertRule,
  getAlertEvents,
  markAlertEventRead,
} from "../services/api";

const stocks = ref([]);
const rules = ref([]);
const events = ref([]);

const loading = ref(false);
const saving = ref(false);
const workingRuleId = ref(null);
const workingEventId = ref(null);

const pageError = ref("");
const formError = ref("");
const eventsError = ref("");
const successMessage = ref("");

const ruleFilter = ref("all");
const eventFilter = ref("all");

const form = reactive({
  stock_symbol: "",
  alert_type: "price_above",
  threshold: "",
  name: "",
});

const isPriceAlert = computed(
  () => form.alert_type.startsWith("price_")
);

const thresholdLabel = computed(() =>
  isPriceAlert.value
    ? "Price threshold (USD)"
    : "Sentiment threshold (-1 to 1)"
);

const thresholdPlaceholder = computed(() =>
  isPriceAlert.value ? "e.g. 350" : "e.g. 0.2"
);

const activeRuleCount = computed(
  () => rules.value.filter((rule) => rule.is_active).length
);

const unreadEventCount = computed(
  () => events.value.filter((event) => !event.is_read).length
);

const filteredRules = computed(() => {
  if (ruleFilter.value === "active") {
    return rules.value.filter((rule) => rule.is_active);
  }

  if (ruleFilter.value === "paused") {
    return rules.value.filter((rule) => !rule.is_active);
  }

  return rules.value;
});

const filteredEvents = computed(() => {
  if (eventFilter.value === "unread") {
    return events.value.filter((event) => !event.is_read);
  }

  if (eventFilter.value === "read") {
    return events.value.filter((event) => event.is_read);
  }

  return events.value;
});

function asList(response) {
  if (Array.isArray(response)) return response;
  if (Array.isArray(response?.results)) return response.results;
  return [];
}

function errorMessage(error) {
  const data = error?.response?.data;

  if (typeof data === "string") return data;
  if (data?.detail) return String(data.detail);
  if (data?.error) return String(data.error);

  if (data && typeof data === "object") {
    return Object.entries(data)
      .map(([field, message]) => (
        `${field}: ${Array.isArray(message) ? message.join(", ") : String(message)}`
      ))
      .join(" | ");
  }

  return error?.message || "An unexpected error occurred.";
}

function formatMetric(type, value) {
  if (value == null || !Number.isFinite(Number(value))) {
    return "Not evaluated";
  }

  const number = Number(value);

  if (type.startsWith("price_")) {
    return number.toLocaleString(undefined, {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }

  return number.toFixed(4);
}

function formatDate(value) {
  if (!value) return "Never";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return String(value);
  }

  return date.toLocaleString();
}

async function loadAll() {
  loading.value = true;
  pageError.value = "";
  eventsError.value = "";

  try {
    const [stockData, ruleData, eventData] = await Promise.all([
      getStocks(),
      getAlertRules(),
      getAlertEvents({ limit: 100 }),
    ]);

    stocks.value = asList(stockData).filter(
      (stock) => stock.is_active !== false
    );

    rules.value = asList(ruleData);
    events.value = asList(eventData?.results);

    if (!form.stock_symbol && stocks.value.length) {
      form.stock_symbol = stocks.value.some(
        (stock) => stock.symbol === "AAPL"
      )
        ? "AAPL"
        : stocks.value[0].symbol;
    }
  } catch (error) {
    pageError.value = errorMessage(error);
  } finally {
    loading.value = false;
  }
}

async function reloadRulesAndEvents() {
  const [ruleData, eventData] = await Promise.all([
    getAlertRules(),
    getAlertEvents({ limit: 100 }),
  ]);

  rules.value = asList(ruleData);
  events.value = asList(eventData?.results);
}

async function createRule() {
  formError.value = "";
  pageError.value = "";
  successMessage.value = "";

  if (!form.stock_symbol) {
    formError.value = "Choose a stock.";
    return;
  }

  const threshold = Number(form.threshold);

  if (!Number.isFinite(threshold)) {
    formError.value = "Enter a valid numeric threshold.";
    return;
  }

  if (isPriceAlert.value && threshold <= 0) {
    formError.value = "Price thresholds must be greater than zero.";
    return;
  }

  if (
    !isPriceAlert.value &&
    (threshold < -1 || threshold > 1)
  ) {
    formError.value = "Sentiment thresholds must be between -1 and 1.";
    return;
  }

  saving.value = true;

  try {
    await createAlertRule({
      stock_symbol: form.stock_symbol,
      name: form.name.trim(),
      alert_type: form.alert_type,
      threshold: String(threshold),
      is_active: true,
    });

    successMessage.value =
      "Alert rule created. Evaluate alerts from your backend to check whether its condition is met.";

    form.name = "";
    form.threshold = "";

    await reloadRulesAndEvents();
  } catch (error) {
    formError.value = errorMessage(error);
  } finally {
    saving.value = false;
  }
}

async function toggleRule(rule) {
  workingRuleId.value = rule.id;
  pageError.value = "";
  successMessage.value = "";

  try {
    await updateAlertRule(rule.id, {
      is_active: !rule.is_active,
    });

    await reloadRulesAndEvents();
  } catch (error) {
    pageError.value = errorMessage(error);
  } finally {
    workingRuleId.value = null;
  }
}

async function removeRule(rule) {
  const confirmed = window.confirm(
    `Delete the ${rule.stock_symbol} alert "${rule.name || rule.alert_type_label}" and its event history?`
  );

  if (!confirmed) return;

  workingRuleId.value = rule.id;
  pageError.value = "";

  try {
    await deleteAlertRule(rule.id);
    await reloadRulesAndEvents();
  } catch (error) {
    pageError.value = errorMessage(error);
  } finally {
    workingRuleId.value = null;
  }
}

async function markRead(event) {
  workingEventId.value = event.id;
  eventsError.value = "";

  try {
    await markAlertEventRead(event.id, true);
    await reloadRulesAndEvents();
  } catch (error) {
    eventsError.value = errorMessage(error);
  } finally {
    workingEventId.value = null;
  }
}

onMounted(loadAll);
</script>

<style scoped>
.alerts-page {
  max-width: 1600px;
  margin: 0 auto;
  padding: 28px clamp(16px, 3vw, 36px) 40px;
  display: flex;
  flex-direction: column;
  gap: 22px;
  color: #111827;
}

.page-header,
.panel-heading,
.rules-heading,
.events-heading {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.eyebrow {
  margin: 0 0 7px;
  color: #64748b;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: .13em;
}

h1 {
  margin: 0;
  font-size: clamp(27px, 3vw, 36px);
  letter-spacing: -.04em;
}

h2 {
  margin: 0;
  font-size: 18px;
  letter-spacing: -.02em;
}

.subtitle,
.panel-heading p {
  margin: 8px 0 0;
  color: #64748b;
  font-size: 14px;
  line-height: 1.55;
}

.panel,
.summary-card {
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  background: #fff;
  box-shadow: 0 3px 12px rgb(15 23 42 / 3%);
}

.panel {
  overflow: hidden;
}

.button {
  min-height: 39px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 0 13px;
  background: #fff;
  color: #334155;
  cursor: pointer;
  font: inherit;
  font-size: 13px;
  font-weight: 700;
}

.button:disabled,
.mini-button:disabled {
  cursor: not-allowed;
  opacity: .5;
}

.primary {
  border-color: #172554;
  background: #172554;
  color: #fff;
}

.primary:hover:not(:disabled) {
  background: #1e3a8a;
}

.secondary:hover:not(:disabled) {
  background: #f8fafc;
}

.info-banner {
  border: 1px solid #dbeafe;
  border-radius: 12px;
  padding: 15px 17px;
  background: #eff6ff;
  color: #1e40af;
  font-size: 13px;
  line-height: 1.6;
}

.info-banner p {
  margin: 6px 0 0;
  color: #475569;
}

.info-banner code {
  font-size: 12px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.summary-card {
  display: flex;
  flex-direction: column;
  min-height: 115px;
  padding: 18px 20px;
  gap: 9px;
}

.summary-label {
  color: #64748b;
  font-size: 12px;
  font-weight: 650;
}

.summary-card strong {
  font-size: 27px;
  letter-spacing: -.03em;
}

.summary-card small {
  color: #94a3b8;
  font-size: 12px;
}

.panel-heading {
  padding: 20px 22px;
  border-bottom: 1px solid #eef2f7;
}

.create-form {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 15px;
  padding: 20px 22px 16px;
}

.field,
.filter-field {
  display: flex;
  flex-direction: column;
  min-width: 0;
  gap: 7px;
}

.field span,
.filter-field span {
  color: #475569;
  font-size: 12px;
  font-weight: 650;
}

.field input,
.field select,
.filter-field select {
  width: 100%;
  min-width: 0;
  height: 40px;
  border: 1px solid #dbe3ed;
  border-radius: 8px;
  outline: none;
  padding: 0 10px;
  background: #fff;
  color: #0f172a;
  font: inherit;
  font-size: 13px;
}

.field input:focus,
.field select:focus,
.filter-field select:focus {
  border-color: #64748b;
  box-shadow: 0 0 0 3px rgb(100 116 139 / 12%);
}

.form-actions {
  display: flex;
  align-items: end;
}

.form-actions .button {
  width: 100%;
  min-height: 40px;
}

.helper-text {
  margin: 0;
  padding: 0 22px 18px;
  color: #94a3b8;
  font-size: 12px;
  line-height: 1.6;
}

.inline-error,
.success-message {
  margin: 0 22px 16px;
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 12px;
  line-height: 1.5;
}

.inline-error,
.error-alert {
  border: 1px solid #fecaca;
  background: #fef2f2;
  color: #b91c1c;
}

.success-message {
  border: 1px solid #bbf7d0;
  background: #f0fdf4;
  color: #166534;
}

.alert {
  border-radius: 10px;
  padding: 14px 16px;
  font-size: 13px;
}

.alert p {
  margin: 5px 0 0;
  line-height: 1.5;
}

.rules-heading,
.events-heading {
  align-items: center;
}

.filter-field {
  min-width: 145px;
}

.filter-field select {
  height: 36px;
}

.table-scroll {
  width: 100%;
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  white-space: nowrap;
  font-size: 13px;
}

.data-table th {
  padding: 13px 12px;
  background: #f8fafc;
  color: #64748b;
  font-size: 11px;
  font-weight: 750;
  text-align: left;
}

.data-table th:first-child,
.data-table td:first-child {
  padding-left: 22px;
}

.data-table td {
  padding: 14px 12px;
  border-top: 1px solid #eef2f7;
  color: #334155;
  vertical-align: middle;
}

.data-table tbody tr:hover {
  background: #fbfdff;
}

.data-table td strong,
.data-table td small {
  display: block;
}

.data-table td strong {
  color: #0f172a;
}

.data-table td small {
  margin-top: 5px;
  color: #94a3b8;
  font-size: 11px;
}

.status-pill {
  display: inline-block;
  border: 1px solid #e2e8f0;
  border-radius: 999px;
  padding: 5px 8px;
  font-size: 11px;
  font-weight: 700;
}

.condition-met,
.unread-pill {
  border-color: #fed7aa;
  background: #fff7ed;
  color: #c2410c;
}

.condition-clear {
  background: #f8fafc;
  color: #64748b;
}

.active-pill {
  border-color: #bbf7d0;
  background: #f0fdf4;
  color: #166534;
}

.paused-pill,
.read-pill {
  background: #f1f5f9;
  color: #64748b;
}

.actions-cell {
  min-width: 150px;
}

.mini-button {
  margin: 2px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 6px 8px;
  background: #fff;
  color: #334155;
  cursor: pointer;
  font: inherit;
  font-size: 11px;
  font-weight: 650;
}

.delete-button {
  border-color: #fecaca;
  color: #b91c1c;
}

.state-message,
.empty-state {
  padding: 30px 20px;
  text-align: center;
  color: #64748b;
  font-size: 13px;
}

.empty-state h3 {
  margin: 0 0 8px;
  color: #334155;
  font-size: 15px;
}

.empty-state p {
  margin: 0;
  line-height: 1.6;
}

.event-list {
  display: flex;
  flex-direction: column;
}

.event-row {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 18px 22px;
  border-top: 1px solid #eef2f7;
}

.event-row:first-child {
  border-top: 0;
}

.unread-event {
  background: #fbfdff;
}

.event-indicator {
  padding-top: 5px;
}

.unread-dot,
.read-dot {
  display: block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.unread-dot {
  background: #2563eb;
}

.read-dot {
  background: #cbd5e1;
}

.event-content {
  flex: 1;
  min-width: 0;
}

.event-title {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 9px;
}

.event-content p {
  margin: 7px 0;
  color: #334155;
  font-size: 13px;
  line-height: 1.6;
}

.event-content small {
  color: #94a3b8;
  font-size: 11px;
  line-height: 1.5;
}

.disclaimer {
  margin: -5px 0 0;
  color: #94a3b8;
  font-size: 12px;
  line-height: 1.6;
}

@media (max-width: 900px) {
  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 650px) {
  .alerts-page {
    padding: 20px 12px 30px;
    gap: 16px;
  }

  .page-header {
    align-items: flex-start;
  }

  .create-form {
    grid-template-columns: 1fr;
    padding: 16px;
  }

  .panel-heading {
    padding: 16px;
  }

  .helper-text {
    padding: 0 16px 16px;
  }

  .inline-error,
  .success-message {
    margin: 0 16px 16px;
  }

  .rules-heading,
  .events-heading {
    align-items: flex-start;
  }

  .event-row {
    padding: 16px;
  }

  .event-row .mini-button {
    flex-shrink: 0;
  }
}

@media (max-width: 420px) {
  .summary-grid {
    grid-template-columns: 1fr;
  }

  .summary-card {
    min-height: 100px;
  }

  .page-header {
    flex-direction: column;
  }
}
</style>