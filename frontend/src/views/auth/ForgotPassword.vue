
<template>
  <main class="auth-page">
    <section class="auth-card">
      <div class="brand">Market<span>Pulse</span></div>

      <h1>Forgot password?</h1>

      <p class="subtitle">
        Enter your registered email address to reset your password.
      </p>

      <form @submit.prevent="handleSubmit">
        <label for="email">Email address</label>

        <input
          id="email"
          v-model.trim="email"
          type="email"
          autocomplete="email"
          placeholder="you@example.com"
          required
        />

        <p v-if="error" class="message error">
          {{ error }}
        </p>

        <p v-if="success" class="message success">
          {{ success }}
        </p>

        <button type="submit" :disabled="loading">
          {{ loading ? "Generating reset link..." : "Reset password" }}
        </button>
      </form>

      <!-- Local development reset link -->
      <div v-if="devResetUrl" class="development-link">
        <h3>Development password reset</h3>

        <p>
          Your reset link is ready. Click below to open the password
          reset page directly.
        </p>

        <a :href="devResetUrl">
          Open password reset page
        </a>
      </div>

      <p class="footer-text">
        Remember your password?
        <RouterLink to="/login">Back to login</RouterLink>
      </p>
    </section>
  </main>
</template>

<script setup>
import { ref } from "vue";
import { RouterLink } from "vue-router";
import { requestPasswordReset } from "../../services/api";

const email = ref("");
const loading = ref(false);
const error = ref("");
const success = ref("");
const devResetUrl = ref("");

async function handleSubmit() {
  error.value = "";
  success.value = "";
  devResetUrl.value = "";

  loading.value = true;

  try {
    const response = await requestPasswordReset(email.value);

    success.value =
      response?.message ||
      "If an account exists, a reset link will be sent.";

    // Available only when the local development backend enables it.
    devResetUrl.value = response?.dev_reset_url || "";

  } catch (err) {
    error.value =
      err.response?.data?.detail ||
      "Unable to process your request. Please try again.";

  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px 16px;
  background: #f4f7fb;
  color: #172033;
}

.auth-card {
  width: 100%;
  max-width: 440px;
  padding: 36px;
  background: #ffffff;
  border: 1px solid #e4e9f1;
  border-radius: 18px;
  box-shadow: 0 16px 45px rgba(25, 42, 70, 0.08);
}

.brand {
  margin-bottom: 28px;
  font-size: 23px;
  font-weight: 800;
  letter-spacing: -0.8px;
}

.brand span {
  color: #2563eb;
}

h1 {
  margin: 0 0 8px;
  font-size: 28px;
}

.subtitle {
  margin: 0 0 26px;
  color: #697386;
  line-height: 1.6;
  font-size: 14px;
}

form {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

label {
  margin-top: 8px;
  font-size: 13px;
  font-weight: 600;
}

input {
  width: 100%;
  box-sizing: border-box;
  padding: 12px 13px;
  border: 1px solid #d6dce7;
  border-radius: 9px;
  font: inherit;
  font-size: 14px;
  outline: none;
}

input:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
}

button {
  margin-top: 14px;
  padding: 13px;
  border: 0;
  border-radius: 9px;
  background: #2563eb;
  color: white;
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}

button:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.message {
  font-size: 13px;
  line-height: 1.5;
}

.error {
  color: #b42318;
}

.success {
  color: #15803d;
}

.development-link {
  margin-top: 24px;
  padding: 18px;
  border: 1px solid #bfdbfe;
  border-radius: 10px;
  background: #eff6ff;
}

.development-link h3 {
  margin: 0 0 8px;
  color: #1e40af;
  font-size: 15px;
}

.development-link p {
  color: #475569;
  font-size: 13px;
  line-height: 1.5;
}

.development-link a {
  display: block;
  margin-top: 12px;
  color: #2563eb;
  font-weight: 700;
  text-decoration: none;
}

.footer-text {
  margin: 24px 0 0;
  text-align: center;
  color: #697386;
  font-size: 14px;
}

.footer-text a {
  color: #2563eb;
  font-weight: 700;
  text-decoration: none;
}
</style>
