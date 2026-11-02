<template>
  <main class="auth-page">
    <section class="auth-card">
      <div class="brand">Market<span>Pulse</span></div>
      <h1>Set a new password</h1>
      <p class="subtitle">Choose a new password for your MarketPulse account.</p>

      <form @submit.prevent="handleSubmit">
        <label for="password">New password</label>
        <input id="password" v-model="password" type="password" autocomplete="new-password" required />

        <label for="password-confirm">Confirm new password</label>
        <input id="password-confirm" v-model="passwordConfirm" type="password" autocomplete="new-password" required />

        <p v-if="error" class="message error" role="alert">{{ error }}</p>
        <p v-if="success" class="message success" role="status">{{ success }}</p>

        <button type="submit" :disabled="loading || !validLink || Boolean(success)">
          {{ loading ? "Updating..." : "Reset password" }}
        </button>
      </form>

      <p class="footer-text"><RouterLink to="/login">Back to login</RouterLink></p>
    </section>
  </main>
</template>

<script setup>
import { computed, ref } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";
import { confirmPasswordReset } from "../../services/api";

const route = useRoute();
const router = useRouter();
const password = ref("");
const passwordConfirm = ref("");
const loading = ref(false);
const error = ref("");
const success = ref("");

const uid = computed(() => route.params.uid);
const token = computed(() => route.params.token);
const validLink = computed(() => Boolean(uid.value && token.value));

function formatErrors(data) {
  if (!data || typeof data !== "object") return "Unable to reset your password. Please try again.";
  return Object.values(data).flatMap((value) => Array.isArray(value) ? value : [value]).filter((value) => typeof value === "string").join(" ");
}

async function handleSubmit() {
  error.value = "";
  if (!validLink.value) {
    error.value = "The password reset link is incomplete.";
    return;
  }
  if (password.value !== passwordConfirm.value) {
    error.value = "Your passwords do not match.";
    return;
  }

  loading.value = true;
  try {
    const response = await confirmPasswordReset({
      uid: uid.value,
      token: token.value,
      password: password.value,
      password_confirm: passwordConfirm.value,
    });
    success.value = response?.message || "Your password has been reset successfully.";
    window.setTimeout(() => router.replace("/login"), 1800);
  } catch (err) {
    error.value = formatErrors(err.response?.data);
    if (!err.response) error.value = "Unable to reach the server. Check that Django is running.";
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.auth-page{min-height:100vh;display:flex;align-items:center;justify-content:center;padding:32px 16px;background:#f4f7fb;color:#172033}
.auth-card{width:100%;max-width:440px;padding:36px;background:#fff;border:1px solid #e4e9f1;border-radius:18px;box-shadow:0 16px 45px rgba(25,42,70,.08)}
.brand{margin-bottom:28px;font-size:23px;font-weight:800;letter-spacing:-.8px}.brand span{color:#2563eb}
h1{margin:0 0 8px;font-size:28px}.subtitle{margin:0 0 26px;color:#697386;line-height:1.6;font-size:14px}
form{display:flex;flex-direction:column;gap:10px}label{margin-top:8px;font-size:13px;font-weight:600}
input{width:100%;box-sizing:border-box;padding:12px 13px;border:1px solid #d6dce7;border-radius:9px;font:inherit;font-size:14px;outline:none}
input:focus{border-color:#2563eb;box-shadow:0 0 0 3px rgba(37,99,235,.12)}
button{margin-top:14px;padding:13px;border:0;border-radius:9px;background:#2563eb;color:#fff;font:inherit;font-weight:700;cursor:pointer}button:disabled{opacity:.65;cursor:not-allowed}
.message{font-size:13px;line-height:1.5}.error{color:#b42318}.success{color:#15803d}.footer-text{margin:24px 0 0;text-align:center;font-size:14px}.footer-text a{color:#2563eb;font-weight:700;text-decoration:none}
</style>
