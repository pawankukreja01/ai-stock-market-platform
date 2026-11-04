<template>
  <div class="onboarding">
    <header class="intro">
      <span class="eyebrow">WELCOME TO MARKETPULSE</span>
      <h1>Start with evidence, not predictions.</h1>
      <p>Use this guided path to understand the US and UK stock research workspace. These tools are educational and do not place trades or guarantee returns.</p>
    </header>
    <div class="steps">
      <article>
        <span class="number">01</span>
        <div><h2>Check the available data</h2>
          <p>Begin with Research Health. Missing or stale data is a reason to investigate, not a signal to buy or sell.</p>
          <router-link to="/research-health">Check research health</router-link>
        </div>
      </article>
      <article>
        <span class="number">02</span>
        <div><h2>Research a company</h2>
          <p>Discover stocks and inspect historical performance, technical indicators, news context and benchmark-relative risks.</p>
          <router-link to="/discover">Discover stocks</router-link>
        </div>
      </article>
      <article>
        <span class="number">03</span>
        <div><h2>Review model evidence</h2>
          <p>Predictions are experimental. Compare their errors against simple no-change assumptions and examine uncertainty.</p>
          <router-link to="/forecast-performance">See prospective performance</router-link>
        </div>
      </article>
      <article>
        <span class="number">04</span>
        <div><h2>Explore your own scenarios</h2>
          <p>Create sample portfolios, study allocations and explore historical hypothetical investments; none of these actions place actual orders.</p>
          <router-link to="/portfolio">Open portfolios</router-link>
        </div>
      </article>
    </div>
    <section class="caution">
      <h2>Before you rely on a number</h2>
      <p>Confirm its date, currency, source and whether it is a past observation or an unverified forecast. London prices may originate in GBp and display in GBP. Comparing GBP and USD totals requires reliable FX conversion. Fees, taxes and dividends may be excluded.</p>
      <p><strong>Forecast quality is an open research question.</strong> Earlier historical tests did not consistently beat simple baselines. Prospective validation requires new real-world outcomes.</p>
    </section>
  </div>
</template>
<style scoped>
.onboarding{max-width:1080px;margin:auto;color:#14233c}
.intro{padding:35px;border-radius:18px;background:linear-gradient(115deg,#fff,#eef5ff);border:1px solid #dce6f4}
.intro .eyebrow{font-size:11px;font-weight:800;letter-spacing:.13em;color:#1d4ed8}
.intro h1{font-size:clamp(28px,4vw,45px);letter-spacing:-.04em;line-height:1.1;margin:15px 0}
.intro p,.steps p,.caution p{color:#58677c;line-height:1.7}
.steps{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;margin:22px 0}
.steps article{display:flex;gap:15px;background:#fff;padding:22px;border:1px solid #e2e8f0;border-radius:14px}
.steps h2{font-size:20px;margin:0}
.steps a{display:inline-block;padding:10px 13px;border:1px solid #b4c8f4;background:#eff6ff;border-radius:8px;text-decoration:none;color:#1d4ed8;font-size:13px;font-weight:800}
.number{display:block;font-size:22px;font-weight:800;color:#64748b}
.caution{padding:24px;border-radius:14px;background:#f1f5f9;margin-bottom:25px}
.caution h2{margin:0}
@media(max-width:720px){.steps{grid-template-columns:1fr}.intro{padding:22px}}
</style>
