<template>
  <main class="auth-page">
    <section class="auth-card">
      <div class="brand">Market<span>Pulse</span></div>

      <template v-if="!registrationComplete">
        <h1>Create your account</h1>
        <p class="subtitle">Create an account to get started with your stock market dashboard.</p>

        <form @submit.prevent="handleRegister">
          <label for="name">Full name</label>
          <input id="name" v-model.trim="form.name" type="text" placeholder="Your full name" autocomplete="name" required />

          <label for="email">Email address</label>
          <input id="email" v-model.trim="form.email" type="email" placeholder="you@example.com" autocomplete="email" required />

          <label for="password">Password</label>
          <input id="password" v-model="form.password" type="password" placeholder="Create a strong password" autocomplete="new-password" required />

          <label for="password-confirm">Confirm password</label>
          <input id="password-confirm" v-model="form.password_confirm" type="password" placeholder="Enter your password again" autocomplete="new-password" required />

          <p v-if="error" class="message error" role="alert">{{ error }}</p>
          <button type="submit" :disabled="loading">{{ loading ? "Creating account..." : "Create account" }}</button>
        </form>

        <p class="footer-text">Already have an account? <RouterLink to="/login">Log in</RouterLink></p>
      </template>

      <template v-else-if="registrationVerified">
        <div class="status-icon success-icon" aria-hidden="true">✓</div>
        <h1>Account created successfully!</h1>
        <p class="subtitle">Your account is verified and ready to use in local development.</p>
        <p class="email-address">{{ form.email }}</p>
        <RouterLink class="primary-link" to="/login">Go to login</RouterLink>
      </template>

      <template v-else>
        <div class="status-icon email-icon" aria-hidden="true">✉</div>
        <h1>Verify your email</h1>
        <p class="subtitle">Your account has been created for:</p>
        <p class="email-address">{{ form.email }}</p>
        <p class="subtitle">{{ registrationMessage }}</p>

        <p v-if="emailSent" class="message success">Check your inbox and spam folder. The verification link expires after 24 hours.</p>
        <p v-else class="message error">The account exists, but the email could not be sent. You can request another link below.</p>
        <p v-if="resendMessage" class="message success" role="status">{{ resendMessage }}</p>
        <p v-if="error" class="message error" role="alert">{{ error }}</p>

        <button type="button" class="secondary-button" :disabled="resending" @click="handleResend">
          {{ resending ? "Sending..." : "Resend verification email" }}
        </button>
        <p class="footer-text">Already verified? <RouterLink to="/login">Go to login</RouterLink></p>
      </template>
    </section>
  </main>
</template>

<script setup>
import { reactive, ref } from "vue";
import { RouterLink } from "vue-router";
import { registerUser, resendVerificationEmail } from "../../services/api";

const form = reactive({ name: "", email: "", password: "", password_confirm: "" });
const loading = ref(false);
const resending = ref(false);
const error = ref("");
const resendMessage = ref("");
const registrationComplete = ref(false);
const registrationVerified = ref(false);
const registrationMessage = ref("");
const emailSent = ref(false);

function formatErrors(data) {
  if (!data || typeof data !== "object") return "Registration failed. Please try again.";
  return Object.entries(data).map(([field, value]) => {
    const messages = Array.isArray(value) ? value.join(" ") : String(value);
    return `${field}: ${messages}`;
  }).join(" ");
}

async function handleRegister() {
  error.value = "";
  if (form.password !== form.password_confirm) {
    error.value = "Your passwords do not match.";
    return;
  }

  loading.value = true;
  try {
    const response = await registerUser(form);
    registrationVerified.value = response?.email_verified === true;
    registrationMessage.value = response?.message || "Your account has been created.";
    emailSent.value = response?.email_sent === true;
    registrationComplete.value = true;
  } catch (err) {
    error.value = formatErrors(err.response?.data);
    if (!err.response) error.value = "Unable to reach the server. Check that Django is running.";
  } finally {
    loading.value = false;
  }
}

async function handleResend() {
  error.value = "";
  resendMessage.value = "";
  resending.value = true;
  try {
    const response = await resendVerificationEmail(form.email);
    resendMessage.value = response?.message || "If an unverified account exists, a verification email will be sent.";
  } catch (err) {
    error.value = err.response?.data?.detail || "Unable to resend the verification email.";
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
button{margin-top:14px;padding:13px;border:0;border-radius:9px;background:#2563eb;color:#fff;font:inherit;font-weight:700;cursor:pointer}
button:disabled{opacity:.65;cursor:not-allowed}.secondary-button{width:100%;border:1px solid #2563eb;background:#fff;color:#2563eb}
.message{margin:8px 0 0;font-size:13px;line-height:1.5}.error{color:#b42318}.success{color:#15803d}
.email-address{padding:12px;margin:18px 0;border-radius:9px;background:#f1f5f9;color:#172033;font-weight:700;overflow-wrap:anywhere;font-size:14px}
.status-icon{display:flex;align-items:center;justify-content:center;width:58px;height:58px;margin-bottom:22px;border-radius:50%;font-size:27px;font-weight:800}.success-icon{background:#dcfce7;color:#15803d}.email-icon{background:#dbeafe;color:#2563eb}
.primary-link{display:inline-block;margin-top:15px;padding:12px 18px;border-radius:9px;background:#2563eb;color:#fff;font-weight:700;text-decoration:none;text-align:center}
.footer-text{margin:24px 0 0;text-align:center;color:#697386;font-size:14px}.footer-text a{color:#2563eb;font-weight:700;text-decoration:none}
@media(max-width:480px){.auth-card{padding:26px 20px}}
</style>
