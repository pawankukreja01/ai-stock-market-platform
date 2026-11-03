<template>
  <main class="login-page">
    <div class="login-shell">
      <section class="welcome-panel" aria-label="MarketPulse introduction">
        <RouterLink class="welcome-brand" to="/login" aria-label="MarketPulse login">
          <span class="brand-mark">M</span><span>Market<span class="brand-accent">Pulse</span></span>
        </RouterLink>
        <div class="welcome-copy">
          <span class="eyebrow">INVESTMENT RESEARCH WORKSPACE</span>
          <h2>Research the market with clarity.</h2>
          <p>Explore stocks, review portfolios, and understand the limits of AI forecasts with your own private research workspace.</p>
          <div class="trust-row"><span aria-hidden="true">◉</span> Your account session is verified by the server.</div>
        </div>
        <p class="welcome-footnote">Educational research only. Market forecasts are not guaranteed returns.</p>
      </section>
      <section class="form-panel" aria-labelledby="login-heading">
        <div class="mobile-brand">Market<span>Pulse</span></div>
        <div class="heading-group">
          <div class="sign-in-label">SECURE SIGN IN</div>
          <h1 id="login-heading">Welcome back</h1>
          <p>Sign in to continue to your MarketPulse workspace.</p>
        </div>
        <div v-if="pendingLogout" class="banner warning-banner" role="status">
          <strong>Previous sign-out needs confirmation</strong>
          <p>Your private workspace is locked until the server confirms sign-out or you authenticate again.</p>
          <button type="button" class="retry-button" :disabled="retrying || loading" @click="retryLogout">
            {{ retrying ? "Checking session…" : "Retry sign-out" }}
          </button>
        </div>
        <form class="login-form" @submit.prevent="handleLogin">
          <label for="email">Email address</label>
          <input id="email" v-model.trim="form.email" type="email" name="email"
            placeholder="you@example.com" autocomplete="email" inputmode="email"
            maxlength="254" :disabled="loading" required autofocus />

          <div class="password-label-row">
            <label for="password">Password</label>
            <RouterLink to="/forgot-password">Forgot password?</RouterLink>
          </div>
          <div class="password-field">
            <input id="password" v-model="form.password" name="password"
              :type="showPassword ? 'text' : 'password'" autocomplete="current-password"
              placeholder="Enter your password" :disabled="loading" required
              @keydown="checkCaps" @keyup="checkCaps" />
            <button type="button" class="toggle-password"
              :aria-label="showPassword ? 'Hide password' : 'Show password'"
              :aria-pressed="showPassword" :disabled="loading"
              @click="showPassword = !showPassword">
              {{ showPassword ? "Hide" : "Show" }}
            </button>
          </div>
          <p v-if="capsLock" class="field-note" role="status">Caps Lock is on.</p>
          <p v-if="error" class="banner error-banner" role="alert">{{ error }}</p>
          <p v-if="success" class="banner success-banner" role="status">{{ success }}</p>

          <button class="submit-button" type="submit" :disabled="loading || resending || retrying">
            <span v-if="loading" class="spinner" aria-hidden="true"></span>
            {{ loading ? "Verifying your session…" : "Sign in securely" }}
          </button>
          <button v-if="requiresVerification" type="button" class="verification-button"
            :disabled="resending || loading || !form.email" @click="handleResendVerification">
            {{ resending ? "Sending verification email…" : "Resend verification email" }}
          </button>
        </form>
        <p class="create-account">New to MarketPulse? <RouterLink to="/register">Create an account</RouterLink></p>
        <p class="session-note">For safety, your session expires after 30 minutes without activity and requires a new sign-in after 12 hours.</p>
      </section>
    </div>
  </main>
</template>

<script setup>
import { onBeforeUnmount, onMounted, reactive, ref } from "vue";
import { RouterLink, useRouter } from "vue-router";
import { getCurrentUser, loginUser, resendVerificationEmail } from "../../services/api";
import { confirmServerLogout } from "../../utils/logoutFlow.js";
import {
  clearLogoutPending, logoutPending, recordSessionExpiry,
  sessionIsPastDeadline, PENDING_LOGOUT_KEY,
} from "../../utils/sessionSafety.js";

const router = useRouter();
const form = reactive({ email: "", password: "" });
const loading = ref(false);
const resending = ref(false);
const retrying = ref(false);
const pendingLogout = ref(logoutPending());
const error = ref("");
const success = ref("");
const requiresVerification = ref(false);
const showPassword = ref(false);
const capsLock = ref(false);

function checkCaps(event) {
  if (typeof event.getModifierState === "function") {
    capsLock.value = event.getModifierState("CapsLock");
  }
}

function onStorage(event) {
  if (event.key === PENDING_LOGOUT_KEY) pendingLogout.value = logoutPending();
}

async function retryLogout() {
  if (retrying.value || loading.value) return;
  retrying.value = true;
  error.value = "";
  try {
    const confirmed = await confirmServerLogout();
    pendingLogout.value = !confirmed;
    if (!confirmed) {
      error.value = "Unable to confirm sign-out. Keep this page locked or sign in again.";
    } else {
      success.value = "Your previous session is now signed out.";
    }
  } catch {
    pendingLogout.value = true;
    error.value = "Server unavailable. Protected pages remain locked.";
  } finally {
    retrying.value = false;
  }
}

async function handleLogin() {
  if (loading.value || retrying.value) return;
  error.value = "";
  success.value = "";
  requiresVerification.value = false;
  loading.value = true;
  try {
    const email = form.email.trim().toLowerCase();
    await loginUser({ email, password: form.password });
    // Never unlock the dashboard based on the login response alone.
    const verified = await getCurrentUser();
    if (!verified?.user || !verified?.session?.expires_at ||
        sessionIsPastDeadline(verified.session.expires_at)) {
      throw new Error("Server did not confirm an active session.");
    }
    recordSessionExpiry(verified.session.expires_at);
    clearLogoutPending();
    pendingLogout.value = false;
    form.password = "";
    await router.replace("/");
  } catch (err) {
    const data = err?.response?.data;
    requiresVerification.value = data?.email_verification_required === true;
    if (err?.response?.status === 429) {
      error.value = "Too many attempts. Please try again later.";
    } else if (data?.detail) {
      error.value = String(data.detail);
    } else {
      error.value = "We could not verify your session. Check your connection and try again.";
    }
  } finally {
    loading.value = false;
  }
}

async function handleResendVerification() {
  if (resending.value) return;
  error.value = "";
  success.value = "";
  resending.value = true;
  try {
    const result = await resendVerificationEmail(form.email.trim().toLowerCase());
    success.value = result?.message || "If an unverified account exists, a verification email will be sent.";
  } catch {
    error.value = "Could not request verification email. Please try again.";
  } finally {
    resending.value = false;
  }
}

onMounted(() => window.addEventListener("storage", onStorage));
onBeforeUnmount(() => {
  window.removeEventListener("storage", onStorage);
  form.password = "";
});
</script>

<style scoped>
.login-page{min-height:100vh;display:flex;align-items:center;justify-content:center;padding:26px;background:#f0f4fa;color:#17243a}
.login-shell{display:grid;grid-template-columns:minmax(0,1.04fr) minmax(0,.96fr);width:min(1020px,100%);min-height:640px;background:#fff;border:1px solid #dce5ef;border-radius:22px;overflow:hidden;box-shadow:0 24px 75px rgb(24 46 86 / 10%)}
.welcome-panel{background:radial-gradient(circle at 95% 0%,#2861b9 0,transparent 38%),linear-gradient(135deg,#0b1830,#133c76);color:#fff;padding:44px;display:flex;flex-direction:column;justify-content:space-between}
.welcome-brand{display:flex;gap:12px;align-items:center;color:#fff;text-decoration:none;font-size:24px;font-weight:800;letter-spacing:-.04em}
.brand-mark{display:grid;place-items:center;border:1px solid #79a8fa;background:#2563eb;border-radius:13px;width:43px;height:43px;font-size:23px}
.brand-accent,.mobile-brand span{color:#94c5ff}
.welcome-copy h2{font-size:clamp(32px,4vw,46px);letter-spacing:-.05em;line-height:1.12;margin:15px 0 18px;max-width:470px}
.welcome-copy p{font-size:15px;color:#d6e4f6;line-height:1.8;max-width:440px}
.eyebrow,.sign-in-label{font-size:11px;font-weight:800;letter-spacing:.15em;color:#9ac9ff}
.trust-row{margin-top:27px;padding:14px 17px;border:1px solid rgb(255 255 255 / 18%);border-radius:11px;color:#e2eaf5;font-size:13px}
.trust-row span{margin-right:8px;color:#73d7b0}
.welcome-footnote{font-size:12px;line-height:1.6;color:#afc5de}
.form-panel{display:flex;flex-direction:column;justify-content:center;padding:55px clamp(24px,5vw,64px)}
.mobile-brand{display:none;font-size:21px;font-weight:800}
.sign-in-label{color:#2563eb}
.heading-group h1{font-size:clamp(27px,3vw,36px);letter-spacing:-.04em;margin:12px 0 8px}
.heading-group p{font-size:14px;line-height:1.6;color:#64748b;margin:0 0 27px}
.login-form{display:flex;flex-direction:column;gap:11px}
label{font-size:13px;font-weight:750}
input{width:100%;border:1px solid #cbd5e1;border-radius:10px;padding:13px 14px;font-size:15px;font-family:inherit;background:#fff;color:#17243a;box-sizing:border-box}
input:focus-visible,button:focus-visible,a:focus-visible{outline:3px solid #93c5fd;outline-offset:2px}
.password-label-row{display:flex;align-items:center;justify-content:space-between;margin-top:5px;gap:14px}
.password-label-row a,.create-account a{color:#1d4ed8;font-weight:750;font-size:13px;text-decoration:none}
.password-label-row a:hover,.create-account a:hover{text-decoration:underline}
.password-field{position:relative}
.password-field input{padding-right:74px}
.toggle-password{position:absolute;right:9px;top:50%;transform:translateY(-50%);border:0;background:none;color:#1d4ed8;font-size:12px;font-weight:800;padding:8px;cursor:pointer}
.submit-button{display:flex;align-items:center;justify-content:center;gap:10px;width:100%;background:#1d4ed8;color:#fff;border:0;border-radius:10px;padding:14px;font-size:14px;font-weight:800;cursor:pointer;margin-top:12px}
.submit-button:hover{background:#1e40af}
button:disabled{opacity:.55;cursor:not-allowed}
.verification-button,.retry-button{border:1px solid #b7cdf2;background:#eff6ff;color:#1d4ed8;padding:10px 12px;border-radius:9px;font-weight:750;cursor:pointer}
.create-account{margin:25px 0 10px;font-size:13px;text-align:center;color:#64748b}
.session-note{text-align:center;font-size:11px;line-height:1.55;color:#8290a3}
.banner{padding:12px 14px;border-radius:9px;font-size:13px;line-height:1.5;margin:8px 0}
.banner p{margin:5px 0 10px}
.error-banner{background:#fff1f2;border:1px solid #fecdd3;color:#9f1239}
.warning-banner{background:#fffbeb;border:1px solid #fde68a;color:#92400e}
.success-banner{background:#ecfdf5;border:1px solid #a7f3d0;color:#047857}
.field-note{font-size:12px;color:#a16207;margin:0}
.spinner{width:14px;height:14px;border:2px solid #9bbffa;border-top-color:#fff;border-radius:50%;animation:spin .7s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
@media(max-width:800px){.login-shell{grid-template-columns:1fr;max-width:560px;min-height:0}.welcome-panel{display:none}.form-panel{padding:38px}.mobile-brand{display:block;margin-bottom:28px}.mobile-brand span{color:#2563eb}}
@media(max-width:460px){.login-page{padding:10px}.login-shell{border-radius:15px}.form-panel{padding:27px 22px}}
@media(prefers-reduced-motion:reduce){.spinner{animation:none}}
</style>