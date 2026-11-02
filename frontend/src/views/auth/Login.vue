<template>
  <main class="auth-page">
    <section class="auth-card">
      <div class="brand">Market<span>Pulse</span></div>
      <h1>Welcome back</h1>
      <p class="subtitle">Log in to access your stock market dashboard.</p>

      <form @submit.prevent="handleLogin">
        <label for="email">Email address</label>
        <input
          id="email"
          v-model.trim="form.email"
          type="email"
          placeholder="you@example.com"
          autocomplete="email"
          required
        />

        <label for="password">Password</label>
        <input
          id="password"
          v-model="form.password"
          type="password"
          placeholder="Enter your password"
          autocomplete="current-password"
          required
        />

        <div class="forgot-row">
          <RouterLink to="/forgot-password">Forgot password?</RouterLink>
        </div>

        <p v-if="error" class="message error" role="alert">{{ error }}</p>
        <p v-if="success" class="message success" role="status">{{ success }}</p>

        <button type="submit" :disabled="loading">
          {{ loading ? "Logging in..." : "Log in" }}
        </button>

        <button
          v-if="requiresVerification"
          type="button"
          class="secondary-button"
          :disabled="resending || !form.email"
          @click="handleResendVerification"
        >
          {{ resending ? "Sending..." : "Resend verification email" }}
        </button>
      </form>

      <p class="footer-text">
        Don't have an account? <RouterLink to="/register">Create an account</RouterLink>
      </p>
    </section>
  </main>
</template>

<script setup>
import { reactive, ref } from "vue";
import { RouterLink, useRouter } from "vue-router";
import { loginUser, resendVerificationEmail } from "../../services/api";

const router = useRouter();
const form = reactive({ email: "", password: "" });
const loading = ref(false);
const resending = ref(false);
const error = ref("");
const success = ref("");
const requiresVerification = ref(false);

async function handleLogin() {
  error.value = "";
  success.value = "";
  requiresVerification.value = false;
  loading.value = true;

  try {
    await loginUser(form);
    await router.replace("/");
  } catch (err) {
    const data = err.response?.data;
    error.value = data?.detail || "Login failed. Check your email and password.";
    requiresVerification.value = data?.email_verification_required === true;

    if (!data && !err.response) {
      error.value = "Unable to reach the server. Check that Django is running.";
    }
  } finally {
    loading.value = false;
  }
}

async function handleResendVerification() {
  error.value = "";
  success.value = "";
  resending.value = true;

  try {
    const response = await resendVerificationEmail(form.email);
    success.value = response?.message || "If the account needs verification, an email will be sent.";
  } catch (err) {
    error.value = err.response?.data?.detail || "Unable to send the verification email. Please try again.";
  } finally {
    resending.value = false;
  }
}
</script>

<style scoped>
.auth-page{min-height:100vh;display:flex;align-items:center;justify-content:center;padding:32px 16px;background:#f4f7fb;color:#172033}
.auth-card{width:100%;max-width:440px;padding:36px;background:#fff;border:1px solid #e4e9f1;border-radius:18px;box-shadow:0 16px 45px rgba(25,42,70,.08)}
.brand{margin-bottom:28px;font-size:23px;font-weight:800;letter-spacing:-.8px}.brand span{color:#2563eb}
h1{margin:0 0 8px;font-size:28px;letter-spacing:-.8px}.subtitle{margin:0 0 26px;color:#697386;line-height:1.6;font-size:14px}
form{display:flex;flex-direction:column;gap:10px}label{margin-top:8px;font-size:13px;font-weight:600}
input{width:100%;box-sizing:border-box;padding:12px 13px;border:1px solid #d6dce7;border-radius:9px;font:inherit;font-size:14px;outline:none}
input:focus{border-color:#2563eb;box-shadow:0 0 0 3px rgba(37,99,235,.12)}
.forgot-row{text-align:right;font-size:13px}.forgot-row a,.footer-text a{color:#2563eb;font-weight:700;text-decoration:none}
button{margin-top:14px;padding:13px;border:0;border-radius:9px;background:#2563eb;color:#fff;font:inherit;font-weight:700;cursor:pointer}
.secondary-button{margin-top:4px;border:1px solid #2563eb;background:#fff;color:#2563eb}
button:disabled{opacity:.65;cursor:not-allowed}.message{margin:8px 0 0;font-size:13px;line-height:1.5}.error{color:#b42318}.success{color:#15803d}
.footer-text{margin:24px 0 0;text-align:center;color:#697386;font-size:14px}
@media(max-width:480px){.auth-card{padding:26px 20px}}
</style>
