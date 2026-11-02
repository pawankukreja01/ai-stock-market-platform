<template>
  <main class="auth-page">
    <section class="auth-card">
      <div class="brand">Market<span>Pulse</span></div>
      <h1>{{ heading }}</h1>
      <p class="subtitle" role="status">{{ message }}</p>
      <p v-if="error" class="message error" role="alert">{{ error }}</p>
      <RouterLink v-if="finished" class="primary-link" to="/login">Go to login</RouterLink>
    </section>
  </main>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { RouterLink, useRoute } from "vue-router";
import { verifyEmail } from "../../services/api";

const route = useRoute();
const heading = ref("Verifying your email...");
const message = ref("Please wait while we verify your email address.");
const error = ref("");
const finished = ref(false);

onMounted(async () => {
  const token = route.query.token;
  if (typeof token !== "string" || !token) {
    heading.value = "Verification link is incomplete";
    message.value = "Open the full verification link from your email.";
    finished.value = true;
    return;
  }

  try {
    const response = await verifyEmail(token);
    heading.value = "Email verified";
    message.value = response?.message || "Your email has been verified. You can now log in.";
  } catch (err) {
    heading.value = "Email verification failed";
    error.value = err.response?.data?.detail || "The verification link is invalid or has expired.";
    message.value = "Request a fresh verification link or contact support.";
  } finally {
    finished.value = true;
  }
});
</script>

<style scoped>
.auth-page{min-height:100vh;display:flex;align-items:center;justify-content:center;padding:32px 16px;background:#f4f7fb;color:#172033}
.auth-card{width:100%;max-width:440px;padding:36px;background:#fff;border:1px solid #e4e9f1;border-radius:18px;box-shadow:0 16px 45px rgba(25,42,70,.08)}
.brand{margin-bottom:28px;font-size:23px;font-weight:800;letter-spacing:-.8px}.brand span{color:#2563eb}
h1{margin:0 0 12px;font-size:28px}.subtitle{color:#697386;line-height:1.6;font-size:14px}.message{font-size:13px;line-height:1.5}.error{color:#b42318}
.primary-link{display:inline-block;margin-top:18px;padding:12px 18px;border-radius:9px;background:#2563eb;color:#fff;font-weight:700;text-decoration:none}
</style>
