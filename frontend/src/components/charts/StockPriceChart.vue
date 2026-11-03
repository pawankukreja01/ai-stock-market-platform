<template>
  <section class="chart-card">
    <div class="chart-header">
      <div>
        <h2>{{ symbol }} Price History</h2>

        <p>
          OHLC candlestick chart with moving averages, Bollinger Bands,
          volume, RSI, MACD, Stochastic, ATR, ROC, OBV, ADX, +DI, -DI,
          Support & Resistance, Golden Cross, Death Cross, Market Regime,
          Performance Analysis, Benchmark Comparison, Fundamentals and Risk Analysis
        </p>
      </div>

      <div class="period-buttons">
        <button
          v-for="period in periods"
          :key="period.value"
          type="button"
          :class="{ active: selectedPeriod === period.value }"
          @click="changePeriod(period.value)"
        >
          {{ period.label }}
        </button>
      </div>
    </div>

    <!-- =====================================================
         STEP 13 - MARKET REGIME
    ====================================================== -->

    <div v-if="marketRegime" class="regime-panel">
      <div class="regime-header">
        <div>
          <span class="regime-title">
            Market Regime
          </span>

          <span class="regime-subtitle">
            Quantitative trend analysis for
            {{ selectedPeriodLabel }}
          </span>
        </div>

        <div
          class="regime-badge"
          :class="regimeClass"
        >
          {{ marketRegime.trend }}
        </div>
      </div>

      <div class="regime-grid">
        <div class="regime-item">
          <span class="regime-label">
            Trend
          </span>

          <strong>
            {{ marketRegime.trend }}
          </strong>
        </div>

        <div class="regime-item">
          <span class="regime-label">
            Strength
          </span>

          <strong>
            {{ marketRegime.strength }}
          </strong>
        </div>

        <div class="regime-item">
          <span class="regime-label">
            ADX
          </span>

          <strong>
            {{ formatIndicator(marketRegime.adx) }}
          </strong>
        </div>

        <div class="regime-item">
          <span class="regime-label">
            +DI
          </span>

          <strong>
            {{ formatIndicator(marketRegime.plusDI) }}
          </strong>
        </div>

        <div class="regime-item">
          <span class="regime-label">
            -DI
          </span>

          <strong>
            {{ formatIndicator(marketRegime.minusDI) }}
          </strong>
        </div>

        <div class="regime-item">
          <span class="regime-label">
            SMA Alignment
          </span>

          <strong>
            {{ marketRegime.smaAlignment }}
          </strong>
        </div>

        <div class="regime-item">
          <span class="regime-label">
            Price vs SMA 200
          </span>

          <strong>
            {{ marketRegime.priceVsSMA200 }}
          </strong>
        </div>

        <div class="regime-item">
          <span class="regime-label">
            Data Points
          </span>

          <strong>
            {{ marketRegime.dataPoints }}
          </strong>
        </div>
      </div>

      <div class="regime-description">
        {{ marketRegime.description }}
      </div>
    </div>

    <!-- =====================================================
         STEP 14 - PERFORMANCE ANALYSIS
    ====================================================== -->

    <div
      v-if="performanceMetrics"
      class="performance-panel"
    >
      <div class="performance-header">
        <div>
          <span class="performance-title">
            Performance Analysis
          </span>

          <span class="performance-subtitle">
            Historical performance for
            {{ selectedPeriodLabel }}
          </span>
        </div>

        <div
          class="performance-return"
          :class="performanceReturnClass"
        >
          {{
            formatSignedPercentage(
              performanceMetrics.totalReturn
            )
          }}
        </div>
      </div>

      <div class="performance-grid">
        <div class="performance-item">
          <span class="performance-label">
            Total Return
          </span>

          <strong
            :class="
              returnValueClass(
                performanceMetrics.totalReturn
              )
            "
          >
            {{
              formatSignedPercentage(
                performanceMetrics.totalReturn
              )
            }}
          </strong>
        </div>

        <div class="performance-item">
          <span class="performance-label">
            Annualised Return
          </span>

          <strong
            :class="
              returnValueClass(
                performanceMetrics.annualizedReturn
              )
            "
          >
            {{
              formatSignedPercentage(
                performanceMetrics.annualizedReturn
              )
            }}
          </strong>
        </div>

        <div class="performance-item">
          <span class="performance-label">
            Annualised Volatility
          </span>

          <strong>
            {{
              formatPercentage(
                performanceMetrics.annualizedVolatility
              )
            }}
          </strong>
        </div>

        <div class="performance-item">
          <span class="performance-label">
            Maximum Drawdown
          </span>

          <strong class="negative-value">
            {{
              formatSignedPercentage(
                performanceMetrics.maxDrawdown
              )
            }}
          </strong>
        </div>

        <div class="performance-item">
          <span class="performance-label">
            Best Day
          </span>

          <strong class="positive-value">
            {{
              formatSignedPercentage(
                performanceMetrics.bestDay
              )
            }}
          </strong>
        </div>

        <div class="performance-item">
          <span class="performance-label">
            Worst Day
          </span>

          <strong class="negative-value">
            {{
              formatSignedPercentage(
                performanceMetrics.worstDay
              )
            }}
          </strong>
        </div>

        <div class="performance-item">
          <span class="performance-label">
            Positive Days
          </span>

          <strong class="positive-value">
            {{
              formatPercentage(
                performanceMetrics.positiveDays
              )
            }}
          </strong>
        </div>

        <div class="performance-item">
          <span class="performance-label">
            Negative Days
          </span>

          <strong class="negative-value">
            {{
              formatPercentage(
                performanceMetrics.negativeDays
              )
            }}
          </strong>
        </div>

        <div class="performance-item">
          <span class="performance-label">
            Starting Price
          </span>

          <strong>
            {{
              formatPrice(
                performanceMetrics.startPrice
              )
            }}
          </strong>
        </div>

        <div class="performance-item">
          <span class="performance-label">
            Ending Price
          </span>

          <strong>
            {{
              formatPrice(
                performanceMetrics.endPrice
              )
            }}
          </strong>
        </div>

        <div class="performance-item">
          <span class="performance-label">
            Price Change
          </span>

          <strong
            :class="
              returnValueClass(
                performanceMetrics.priceChange
              )
            "
          >
            {{
              formatSignedPrice(
                performanceMetrics.priceChange
              )
            }}
          </strong>
        </div>

        <div class="performance-item">
          <span class="performance-label">
            Trading Days
          </span>

          <strong>
            {{
              performanceMetrics.tradingDays
            }}
          </strong>
        </div>
      </div>

      <div class="performance-description">
        {{ performanceMetrics.description }}
      </div>
    </div>

    <!-- =====================================================
         STEP 15 - BENCHMARK COMPARISON
    ====================================================== -->

    <div
      v-if="benchmarkMetrics"
      class="benchmark-panel"
    >
      <div class="benchmark-header">
        <div>
          <span class="benchmark-title">
            Benchmark Comparison
          </span>

          <span class="benchmark-subtitle">
            Historical comparison for
            {{ selectedPeriodLabel }}
          </span>
        </div>
      </div>

      <div
        v-if="benchmarkLoading"
        class="benchmark-loading"
      >
        Loading benchmark data...
      </div>

      <div
        v-else-if="benchmarkError"
        class="benchmark-error"
      >
        {{ benchmarkError }}
      </div>

      <template v-else>
        <div class="benchmark-table-wrapper">
          <table class="benchmark-table">
            <thead>
              <tr>
                <th>Metric</th>
                <th>{{ symbol }}</th>
                <th>{{ benchmarkMetrics.primaryName }}</th>
                <th>{{ benchmarkMetrics.secondaryName }}</th>
                <th>
                  {{
                    benchmarkMetrics.sectorName
                  }}
                </th>
              </tr>
            </thead>

            <tbody>
              <tr>
                <td>Total Return</td>

                <td
                  :class="
                    returnValueClass(
                      benchmarkMetrics.stock.totalReturn
                    )
                  "
                >
                  {{
                    formatSignedPercentage(
                      benchmarkMetrics.stock.totalReturn
                    )
                  }}
                </td>

                <td
                  :class="
                    returnValueClass(
                      benchmarkMetrics.sp500.totalReturn
                    )
                  "
                >
                  {{
                    formatSignedPercentage(
                      benchmarkMetrics.sp500.totalReturn
                    )
                  }}
                </td>

                <td
                  :class="
                    returnValueClass(
                      benchmarkMetrics.nasdaq100.totalReturn
                    )
                  "
                >
                  {{
                    formatSignedPercentage(
                      benchmarkMetrics.nasdaq100.totalReturn
                    )
                  }}
                </td>

                <td
                  :class="
                    returnValueClass(
                      benchmarkMetrics.sector.totalReturn
                    )
                  "
                >
                  {{
                    formatSignedPercentage(
                      benchmarkMetrics.sector.totalReturn
                    )
                  }}
                </td>
              </tr>

              <tr>
                <td>Annualised Return</td>

                <td>
                  {{
                    formatSignedPercentage(
                      benchmarkMetrics.stock.annualizedReturn
                    )
                  }}
                </td>

                <td>
                  {{
                    formatSignedPercentage(
                      benchmarkMetrics.sp500.annualizedReturn
                    )
                  }}
                </td>

                <td>
                  {{
                    formatSignedPercentage(
                      benchmarkMetrics.nasdaq100.annualizedReturn
                    )
                  }}
                </td>

                <td>
                  {{
                    formatSignedPercentage(
                      benchmarkMetrics.sector.annualizedReturn
                    )
                  }}
                </td>
              </tr>

              <tr>
                <td>Annualised Volatility</td>

                <td>
                  {{
                    formatPercentage(
                      benchmarkMetrics.stock.annualizedVolatility
                    )
                  }}
                </td>

                <td>
                  {{
                    formatPercentage(
                      benchmarkMetrics.sp500.annualizedVolatility
                    )
                  }}
                </td>

                <td>
                  {{
                    formatPercentage(
                      benchmarkMetrics.nasdaq100.annualizedVolatility
                    )
                  }}
                </td>

                <td>
                  {{
                    formatPercentage(
                      benchmarkMetrics.sector.annualizedVolatility
                    )
                  }}
                </td>
              </tr>

              <tr>
                <td>Correlation</td>

                <td>1.00</td>

                <td>
                  {{
                    formatCorrelation(
                      benchmarkMetrics.sp500.correlation
                    )
                  }}
                </td>

                <td>
                  {{
                    formatCorrelation(
                      benchmarkMetrics.nasdaq100.correlation
                    )
                  }}
                </td>

                <td>
                  {{
                    formatCorrelation(
                      benchmarkMetrics.sector.correlation
                    )
                  }}
                </td>
              </tr>

              <tr>
                <td>Relative Return</td>

                <td>—</td>

                <td
                  :class="
                    returnValueClass(
                      benchmarkMetrics.relative.sp500
                    )
                  "
                >
                  {{
                    formatSignedPercentage(
                      benchmarkMetrics.relative.sp500
                    )
                  }}
                </td>

                <td
                  :class="
                    returnValueClass(
                      benchmarkMetrics.relative.nasdaq100
                    )
                  "
                >
                  {{
                    formatSignedPercentage(
                      benchmarkMetrics.relative.nasdaq100
                    )
                  }}
                </td>

                <td
                  :class="
                    returnValueClass(
                      benchmarkMetrics.relative.sector
                    )
                  "
                >
                  {{
                    formatSignedPercentage(
                      benchmarkMetrics.relative.sector
                    )
                  }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div
          v-if="benchmarkChartHasData && !benchmarkChartRenderError"
          ref="benchmarkChartElement"
          class="benchmark-chart"
          role="img"
          :aria-label="`Historical performance comparison for ${symbol} and available benchmarks`"
        ></div>
        <p v-else class="benchmark-chart-empty">
          {{
            benchmarkChartRenderError ||
            "Historical chart data is unavailable for this period. The comparison table remains available."
          }}
        </p>

        <div class="benchmark-description">
          {{ benchmarkMetrics.description }}
        </div>
      </template>
    </div>

    <!-- =====================================================
         STEP 16 - FUNDAMENTALS
    ====================================================== -->

    <div class="fundamentals-panel">
      <div class="fundamentals-header">
        <div>
          <span class="fundamentals-title">
            Fundamentals
          </span>

          <span class="fundamentals-subtitle">
            Financial and valuation metrics for
            {{ symbol }}
          </span>
        </div>

        <div class="fundamentals-period-buttons">
          <button
            type="button"
            :class="{
              active: fundamentalsPeriod === 'annual'
            }"
            @click="changeFundamentalsPeriod('annual')"
          >
            Annual
          </button>

          <button
            type="button"
            :class="{
              active: fundamentalsPeriod === 'quarterly'
            }"
            @click="changeFundamentalsPeriod('quarterly')"
          >
            Quarterly
          </button>
        </div>
      </div>

      <div
        v-if="fundamentalsLoading"
        class="fundamentals-loading"
      >
        Loading fundamental data...
      </div>

      <div
        v-else-if="fundamentalsError"
        class="fundamentals-error"
      >
        {{ fundamentalsError }}
      </div>

      <div
        v-else-if="!latestFundamental"
        class="fundamentals-empty"
      >
        No fundamental data available for this period.
      </div>

      <template v-else>
        <div class="fundamentals-period">
          {{ fundamentalsPeriod === 'annual' ? 'Annual' : 'Quarterly' }} report:
          {{ formatFundamentalDate(latestFundamental.period_end) }}
        </div>

        <div class="fundamentals-grid">
          <div class="fundamental-item"><span>Revenue</span><strong>{{ formatFundamentalCurrency(latestFundamental.revenue) }}</strong></div>
          <div class="fundamental-item"><span>Gross Profit</span><strong>{{ formatFundamentalCurrency(latestFundamental.gross_profit) }}</strong></div>
          <div class="fundamental-item"><span>Operating Income</span><strong>{{ formatFundamentalCurrency(latestFundamental.operating_income) }}</strong></div>
          <div class="fundamental-item"><span>Net Income</span><strong>{{ formatFundamentalCurrency(latestFundamental.net_income) }}</strong></div>
          <div class="fundamental-item"><span>EPS</span><strong>{{ formatFundamentalCurrency(latestFundamental.eps) }}</strong></div>
          <div class="fundamental-item"><span>Free Cash Flow</span><strong>{{ formatFundamentalCurrency(latestFundamental.free_cash_flow) }}</strong></div>
          <div class="fundamental-item"><span>ROE</span><strong>{{ formatFundamentalPercentage(latestFundamental.roe) }}</strong></div>
          <div class="fundamental-item"><span>ROA</span><strong>{{ formatFundamentalPercentage(latestFundamental.roa) }}</strong></div>
          <div class="fundamental-item"><span>Gross Margin</span><strong>{{ formatFundamentalPercentage(latestFundamental.gross_margin) }}</strong></div>
          <div class="fundamental-item"><span>Operating Margin</span><strong>{{ formatFundamentalPercentage(latestFundamental.operating_margin) }}</strong></div>
          <div class="fundamental-item"><span>Profit Margin</span><strong>{{ formatFundamentalPercentage(latestFundamental.profit_margin) }}</strong></div>
          <div class="fundamental-item"><span>Debt / Equity</span><strong>{{ formatFundamentalNumber(latestFundamental.debt_to_equity) }}</strong></div>
          <div class="fundamental-item"><span>Current Ratio</span><strong>{{ formatFundamentalNumber(latestFundamental.current_ratio) }}</strong></div>
          <div class="fundamental-item"><span>P / E Ratio</span><strong>{{ formatFundamentalNumber(latestFundamental.pe_ratio) }}</strong></div>
          <div class="fundamental-item"><span>Forward P / E</span><strong>{{ formatFundamentalNumber(latestFundamental.forward_pe) }}</strong></div>
          <div class="fundamental-item"><span>PEG Ratio</span><strong>{{ formatFundamentalNumber(latestFundamental.peg_ratio) }}</strong></div>
          <div class="fundamental-item"><span>Price / Sales</span><strong>{{ formatFundamentalNumber(latestFundamental.price_to_sales) }}</strong></div>
          <div class="fundamental-item"><span>Price / Book</span><strong>{{ formatFundamentalNumber(latestFundamental.price_to_book) }}</strong></div>
          <div class="fundamental-item"><span>Dividend / Share</span><strong>{{ formatFundamentalCurrency(latestFundamental.dividend_per_share) }}</strong></div>
          <div class="fundamental-item"><span>Dividend Yield</span><strong>{{ formatFundamentalPercentage(latestFundamental.dividend_yield) }}</strong></div>
        </div>
      </template>
    </div>

    <!-- =====================================================
         STEP 17.2 - RISK ANALYSIS UI
    ====================================================== -->

    <div class="risk-panel">
      <div class="risk-header">
        <div>
          <span class="risk-title">
            Risk Analysis
          </span>

          <span class="risk-subtitle">
            Historical risk metrics for
            {{ selectedPeriodLabel }}
          </span>
        </div>

        <div
          v-if="riskMetrics && riskMetrics.benchmark"
          class="risk-benchmark-badge"
        >
          Benchmark: {{ riskMetrics.benchmark }}
        </div>
      </div>

      <div
        v-if="riskLoading"
        class="risk-loading"
      >
        Loading risk metrics...
      </div>

      <div
        v-else-if="riskError"
        class="risk-error"
      >
        {{ riskError }}
      </div>

      <div
        v-else-if="!riskMetrics"
        class="risk-empty"
      >
        No risk metrics available for this period.
      </div>

      <template v-else>
        <div class="risk-period">
          Historical risk analysis from
          {{ formatRiskDate(riskPeriod?.startDate) }}
          to
          {{ formatRiskDate(riskPeriod?.endDate) }}
          using {{ formatRiskObservations(riskMetrics.observations) }} observations.
        </div>

        <div class="risk-grid">
          <div class="risk-item">
            <span class="risk-label">
              Annualised Return
            </span>
            <strong
              :class="returnValueClass(
                toPercentageValue(riskMetrics.annualised_return)
              )"
            >
              {{ formatRiskPercentage(riskMetrics.annualised_return) }}
            </strong>
            <span class="risk-help">
              Compounded historical return rate for the selected period.
            </span>
          </div>

          <div class="risk-item">
            <span class="risk-label">
              Annualised Volatility
            </span>
            <strong>
              {{ formatRiskPercentage(riskMetrics.annualised_volatility) }}
            </strong>
            <span class="risk-help">
              Annualised standard deviation of daily returns.
            </span>
          </div>

          <div class="risk-item">
            <span class="risk-label">
              Maximum Drawdown
            </span>
            <strong class="negative-value">
              {{ formatRiskPercentage(riskMetrics.maximum_drawdown) }}
            </strong>
            <span class="risk-help">
              Largest historical peak-to-trough decline.
            </span>
          </div>

          <div class="risk-item">
            <span class="risk-label">
              Sharpe Ratio
            </span>
            <strong>
              {{ formatRiskRatio(riskMetrics.sharpe_ratio) }}
            </strong>
            <span class="risk-help">
              Historical return relative to total variability.
            </span>
          </div>

          <div class="risk-item">
            <span class="risk-label">
              Sortino Ratio
            </span>
            <strong>
              {{ formatRiskRatio(riskMetrics.sortino_ratio) }}
            </strong>
            <span class="risk-help">
              Historical return relative to downside variability.
            </span>
          </div>

          <div class="risk-item">
            <span class="risk-label">
              Downside Deviation
            </span>
            <strong>
              {{ formatRiskPercentage(riskMetrics.downside_deviation) }}
            </strong>
            <span class="risk-help">
              Annualised variability from returns below the minimum acceptable return.
            </span>
          </div>

          <div class="risk-item">
            <span class="risk-label">
              VaR (95%)
            </span>
            <strong class="negative-value">
              {{ formatRiskPercentage(riskMetrics.var_95) }}
            </strong>
            <span class="risk-help">
              Historical 5th-percentile daily return.
            </span>
          </div>

          <div class="risk-item">
            <span class="risk-label">
              Expected Shortfall (95%)
            </span>
            <strong class="negative-value">
              {{ formatRiskPercentage(riskMetrics.expected_shortfall_95) }}
            </strong>
            <span class="risk-help">
              Average historical daily return in the worst 5% tail.
            </span>
          </div>

          <div class="risk-item">
            <span class="risk-label">
              Historical Loss Frequency
            </span>
            <strong>
              {{ formatRiskPercentage(riskMetrics.historical_loss_frequency) }}
            </strong>
            <span class="risk-help">
              Share of observed trading days with a negative return.
            </span>
          </div>

          <div class="risk-item">
            <span class="risk-label">
              Beta vs S&amp;P 500
            </span>
            <strong>
              {{ formatRiskRatio(riskMetrics.beta) }}
            </strong>
            <span class="risk-help">
              Sensitivity of the stock's daily returns to the S&amp;P 500.
            </span>
          </div>

          <div class="risk-item">
            <span class="risk-label">
              S&amp;P 500 Correlation
            </span>
            <strong>
              {{ formatRiskCorrelation(riskMetrics.benchmark_correlation) }}
            </strong>
            <span class="risk-help">
              Pearson correlation between stock and benchmark daily returns.
            </span>
          </div>

          <div class="risk-item">
            <span class="risk-label">
              Observations
            </span>
            <strong>
              {{ formatRiskObservations(riskMetrics.observations) }}
            </strong>
            <span class="risk-help">
              Number of historical closing-price observations used.
            </span>
          </div>
        </div>

        <div class="risk-note">
          These are historical measurements derived from the selected data period.
          They are not forecasts and do not represent a guaranteed future outcome.
        </div>

        <!-- =====================================================
             STEP 17.3 - RISK VISUALISATION & INTERPRETATION
        ====================================================== -->

        <div class="risk-visual-section">
          <div class="risk-section-heading">
            <div>
              <span class="risk-section-title">
                Risk Visualisation
              </span>

              <span class="risk-section-subtitle">
                Historical return, drawdown and daily-loss distribution for
                {{ selectedPeriodLabel }}
              </span>
            </div>
          </div>

          <div class="risk-visual-grid">
            <div class="risk-visual-card">
              <div class="risk-visual-card-header">
                <span class="risk-visual-card-title">
                  Risk–Return Profile
                </span>
                <span class="risk-visual-card-subtitle">
                  Annualised return vs annualised volatility
                </span>
              </div>
              <div
                ref="riskReturnChartElement"
                class="risk-return-chart"
              ></div>
            </div>

            <div class="risk-visual-card">
              <div class="risk-visual-card-header">
                <span class="risk-visual-card-title">
                  Historical Drawdown
                </span>
                <span class="risk-visual-card-subtitle">
                  Percentage decline from the running peak
                </span>
              </div>
              <div
                ref="riskDrawdownChartElement"
                class="risk-drawdown-chart"
              ></div>
            </div>

            <div class="risk-visual-card risk-distribution-card">
              <div class="risk-visual-card-header">
                <span class="risk-visual-card-title">
                  Daily Return Distribution
                </span>
                <span class="risk-visual-card-subtitle">
                  Historical daily returns with VaR and Expected Shortfall
                </span>
              </div>
              <div
                ref="riskDistributionChartElement"
                class="risk-distribution-chart"
              ></div>
            </div>
          </div>
        </div>

        <div class="risk-interpretation-panel">
          <div class="risk-section-heading">
            <div>
              <span class="risk-section-title">
                Risk Interpretation
              </span>

              <span class="risk-section-subtitle">
                Plain-language interpretation of the measured historical statistics
              </span>
            </div>
          </div>

          <div class="risk-interpretation-grid">
            <div class="risk-interpretation-item">
              <span class="risk-interpretation-label">
                Return & Volatility
              </span>
              <p>
                {{ riskInterpretation.returnVolatility }}
              </p>
            </div>

            <div class="risk-interpretation-item">
              <span class="risk-interpretation-label">
                Drawdown
              </span>
              <p>
                {{ riskInterpretation.drawdown }}
              </p>
            </div>

            <div class="risk-interpretation-item">
              <span class="risk-interpretation-label">
                Tail Loss
              </span>
              <p>
                {{ riskInterpretation.tailRisk }}
              </p>
            </div>

            <div class="risk-interpretation-item">
              <span class="risk-interpretation-label">
                Benchmark Relationship
              </span>
              <p>
                {{ riskInterpretation.benchmark }}
              </p>
            </div>
          </div>

          <div class="risk-interpretation-note">
            Interpretation is based only on the historical observations shown in this analysis.
            It is descriptive rather than a forecast or investment recommendation.
          </div>
        </div>
      </template>
    </div>

    <!-- =====================================================
         STEP 18.7 - ML RETURN PREDICTION DASHBOARD
    ====================================================== -->

    <div class="ml-prediction-panel">
      <div class="ml-prediction-header">
        <div>
          <span class="ml-prediction-title">
            ML Return Prediction
          </span>

          <span class="ml-prediction-subtitle">
            Machine-learning estimate of future return with an empirical prediction range
          </span>
        </div>

        <div class="ml-prediction-controls">
          <div class="ml-control-group">
            <span class="ml-control-label">Model</span>
            <div class="ml-control-buttons">
              <button
                v-for="model in mlModels"
                :key="model.value"
                type="button"
                :class="{ active: mlModel === model.value }"
                @click="changeMLModel(model.value)"
              >
                {{ model.label }}
              </button>
            </div>
          </div>

          <div class="ml-control-group">
            <span class="ml-control-label">Horizon</span>
            <div class="ml-control-buttons">
              <button
                v-for="horizon in mlHorizons"
                :key="horizon.value"
                type="button"
                :class="{ active: mlHorizon === horizon.value }"
                @click="changeMLHorizon(horizon.value)"
              >
                {{ horizon.label }}
              </button>
            </div>
          </div>
        </div>
        <button
          type="button"
          class="ml-generate-button"
          :disabled="mlLoading"
          @click="loadMLPrediction"
        >
          {{ mlLoading ? "Generating…" : "Generate prediction" }}
        </button>
      </div>

      <div
        v-if="mlLoading"
        class="ml-prediction-loading"
      >
        Training {{ mlModelLabel }} and generating prediction...
      </div>

      <div
        v-else-if="mlError"
        class="ml-prediction-error"
      >
        {{ mlError }}
      </div>

      <div
        v-else-if="!mlPrediction"
        class="ml-prediction-empty"
      >
        Select a model and horizon, then click <strong>Generate prediction</strong>.
        Forecasts are experimental and trained only when requested to avoid
        repeated backend training and request limits.
      </div>

      <template v-else>
        <div class="ml-prediction-period">
          {{ mlPrediction.model_name }} prediction for
          {{ mlPrediction.horizon_label }} using historical data through
          {{ formatMLDate(mlPrediction.historical_period?.end_date) }}.
        </div>

        <div
          v-if="mlPrediction.evidence"
          class="ml-evidence-box"
          :class="mlPrediction.evidence.status === 'limited_evidence' ? 'ml-evidence-warning' : 'ml-evidence-preliminary'"
          role="status"
        >
          <strong>
            {{ mlPrediction.evidence.status === "limited_evidence"
              ? "Limited forecasting evidence"
              : "Promising single-period holdout — not live-trading ready" }}
          </strong>
          <p>
            Model held-out error: {{ formatMLPercentage(mlPrediction.evidence.model_mae) }}.
            Zero-return baseline: {{ formatMLPercentage(mlPrediction.evidence.baselines?.zero_return?.mae) }}.
            Historical-mean baseline: {{ formatMLPercentage(mlPrediction.evidence.baselines?.training_mean_return?.mae) }}.
          </p>
          <p>
            Latest stored price: {{ formatMLDate(mlPrediction.evidence.latest_price_date) }}
            ({{ mlPrediction.evidence.price_age_days }} calendar days old).
            Approximate non-overlapping holdout windows:
            {{ mlPrediction.evidence.approx_non_overlapping_holdout_windows }}.
          </p>
          <ul v-if="mlPrediction.evidence.warnings?.length">
            <li v-for="warning in mlPrediction.evidence.warnings" :key="warning">{{ warning }}</li>
          </ul>
          <p>
            Predictions are experimental estimates, not probabilities of profit.
            Passing this diagnostic is not proof of a profitable investment strategy.
          </p>
        </div>

        <div class="ml-prediction-main-grid">
          <div class="ml-prediction-primary-card">
            <span class="ml-card-label">Experimental Future Return Estimate</span>
            <strong
              class="ml-primary-value"
              :class="returnValueClass(mlPredictionReturnPercentage)"
            >
              {{ formatMLPercentage(mlPrediction.prediction?.return) }}
            </strong>
            <span class="ml-card-help">
              Model estimate for the selected future-return horizon.
            </span>
          </div>

          <div class="ml-prediction-primary-card">
            <span class="ml-card-label">Prediction Range</span>
            <strong class="ml-range-value">
              {{ formatMLPercentage(mlPrediction.prediction?.lower_return) }}
              →
              {{ formatMLPercentage(mlPrediction.prediction?.upper_return) }}
            </strong>
            <span class="ml-card-help">
              Empirical {{ formatMLConfidence(mlPrediction.confidence) }} prediction interval calibrated from unseen historical data.
            </span>
          </div>

          <div class="ml-prediction-primary-card">
            <span class="ml-card-label">Current Price</span>
            <strong>
              {{ formatMLPrice(mlPrediction.prediction?.current_price) }}
            </strong>
            <span class="ml-card-help">
              Latest stored closing price, shown for context. The forecast assumes execution at the next session close, whose price is not yet known.
            </span>
          </div>
        </div>

        <div class="ml-prediction-grid">
          <div class="ml-prediction-item">
            <span>Future Price Estimate (not supported)</span>
            <strong>{{ formatMLPrice(mlPrediction.prediction?.estimated_price) }}</strong>
          </div>

          <div class="ml-prediction-item">
            <span>Lower Price Estimate</span>
            <strong>{{ formatMLPrice(mlPrediction.prediction?.lower_price) }}</strong>
          </div>

          <div class="ml-prediction-item">
            <span>Upper Price Estimate</span>
            <strong>{{ formatMLPrice(mlPrediction.prediction?.upper_price) }}</strong>
          </div>

          <div class="ml-prediction-item">
            <span>Validation MAE</span>
            <strong>{{ formatMLPercentage(mlPrediction.validation?.mae) }}</strong>
          </div>

          <div class="ml-prediction-item">
            <span>Validation RMSE</span>
            <strong>{{ formatMLPercentage(mlPrediction.validation?.rmse) }}</strong>
          </div>

          <div class="ml-prediction-item">
            <span>Directional Accuracy</span>
            <strong>{{ formatMLPercentage(mlPrediction.validation?.directional_accuracy) }}</strong>
          </div>

          <div class="ml-prediction-item">
            <span>Calibration Error Margin</span>
            <strong>{{ formatMLPercentage(mlPrediction.validation?.calibration_error_margin) }}</strong>
          </div>

          <div class="ml-prediction-item">
            <span>Training Observations</span>
            <strong>{{ formatMLObservations(mlPrediction.dataset?.training_observations) }}</strong>
          </div>

          <div class="ml-prediction-item">
            <span>Calibration Observations</span>
            <strong>{{ formatMLObservations(mlPrediction.dataset?.calibration_observations) }}</strong>
          </div>

          <div class="ml-prediction-item">
            <span>Test Observations</span>
            <strong>{{ formatMLObservations(mlPrediction.dataset?.testing_observations) }}</strong>
          </div>
        </div>

        <div class="ml-prediction-note">
          <strong>Important:</strong> The model predicts a future return, not a guaranteed future price.
          Price estimates shown above are mathematical conversions of the predicted return and its range.
          Validation metrics come from a chronological historical holdout, and final model selection will be
          tested further using walk-forward backtesting in Step 19.
        </div>
      </template>
    </div>

    <!-- =====================================================
         STEP 19.3 - BACKTEST VISUALISATION
    ====================================================== -->

    <div class="backtest-panel">
      <div class="backtest-header">
        <div>
          <span class="backtest-title">
            Strategy Backtest
          </span>

          <span class="backtest-subtitle">
            Walk-forward historical simulation using the current ML model and horizon
          </span>
        </div>

        <button
          type="button"
          class="backtest-run-button"
          :disabled="backtestLoading"
          @click="loadBacktest"
        >
          {{ backtestLoading ? "Running Backtest..." : "Run Backtest" }}
        </button>
      </div>

      <div class="backtest-configuration">
        <span>Model: <strong>{{ mlModelLabel }}</strong></span>
        <span>Horizon: <strong>{{ mlHorizonLabel }}</strong></span>
        <span>Transaction Cost: <strong>5 bps</strong></span>
        <span>Slippage: <strong>5 bps</strong></span>
      </div>

      <div
        v-if="backtestLoading"
        class="backtest-loading"
      >
        Running walk-forward backtest and generating strategy equity curves...
      </div>

      <div
        v-else-if="backtestError"
        class="backtest-error"
      >
        {{ backtestError }}
      </div>

      <div
        v-else-if="!backtestResult"
        class="backtest-empty"
      >
        Run the backtest to compare the ML strategy with Buy &amp; Hold and SMA 200.
      </div>

      <template v-else>
        <div class="backtest-period">
          Historical simulation: 
          {{ formatBacktestDate(backtestResult.backtest_period?.start_date) }}
          →
          {{ formatBacktestDate(backtestResult.backtest_period?.end_date) }}
          ·
          {{ formatBacktestObservations(backtestResult.backtest_period?.observations) }}
          observations
        </div>

        <div class="backtest-table-wrapper">
          <table class="backtest-table">
            <thead>
              <tr>
                <th>Metric</th>
                <th>ML Strategy</th>
                <th>Buy &amp; Hold</th>
                <th>SMA 200</th>
              </tr>
            </thead>

            <tbody>
              <tr>
                <td>Cumulative Return</td>
                <td :class="backtestReturnClass(backtestResult.strategies?.ml?.metrics?.cumulative_return)">
                  {{ formatBacktestPercentage(backtestResult.strategies?.ml?.metrics?.cumulative_return) }}
                </td>
                <td :class="backtestReturnClass(backtestResult.strategies?.buy_and_hold?.metrics?.cumulative_return)">
                  {{ formatBacktestPercentage(backtestResult.strategies?.buy_and_hold?.metrics?.cumulative_return) }}
                </td>
                <td :class="backtestReturnClass(backtestResult.strategies?.sma?.metrics?.cumulative_return)">
                  {{ formatBacktestPercentage(backtestResult.strategies?.sma?.metrics?.cumulative_return) }}
                </td>
              </tr>

              <tr>
                <td>Annualised Return</td>
                <td :class="backtestReturnClass(backtestResult.strategies?.ml?.metrics?.annualised_return)">
                  {{ formatBacktestPercentage(backtestResult.strategies?.ml?.metrics?.annualised_return) }}
                </td>
                <td :class="backtestReturnClass(backtestResult.strategies?.buy_and_hold?.metrics?.annualised_return)">
                  {{ formatBacktestPercentage(backtestResult.strategies?.buy_and_hold?.metrics?.annualised_return) }}
                </td>
                <td :class="backtestReturnClass(backtestResult.strategies?.sma?.metrics?.annualised_return)">
                  {{ formatBacktestPercentage(backtestResult.strategies?.sma?.metrics?.annualised_return) }}
                </td>
              </tr>

              <tr>
                <td>Annualised Volatility</td>
                <td>{{ formatBacktestPercentage(backtestResult.strategies?.ml?.metrics?.annualised_volatility) }}</td>
                <td>{{ formatBacktestPercentage(backtestResult.strategies?.buy_and_hold?.metrics?.annualised_volatility) }}</td>
                <td>{{ formatBacktestPercentage(backtestResult.strategies?.sma?.metrics?.annualised_volatility) }}</td>
              </tr>

              <tr>
                <td>Maximum Drawdown</td>
                <td class="negative-value">{{ formatBacktestPercentage(backtestResult.strategies?.ml?.metrics?.maximum_drawdown) }}</td>
                <td class="negative-value">{{ formatBacktestPercentage(backtestResult.strategies?.buy_and_hold?.metrics?.maximum_drawdown) }}</td>
                <td class="negative-value">{{ formatBacktestPercentage(backtestResult.strategies?.sma?.metrics?.maximum_drawdown) }}</td>
              </tr>

              <tr>
                <td>Sharpe Ratio</td>
                <td>{{ formatBacktestNumber(backtestResult.strategies?.ml?.metrics?.sharpe_ratio) }}</td>
                <td>{{ formatBacktestNumber(backtestResult.strategies?.buy_and_hold?.metrics?.sharpe_ratio) }}</td>
                <td>{{ formatBacktestNumber(backtestResult.strategies?.sma?.metrics?.sharpe_ratio) }}</td>
              </tr>

              <tr>
                <td>Sortino Ratio</td>
                <td>{{ formatBacktestNumber(backtestResult.strategies?.ml?.metrics?.sortino_ratio) }}</td>
                <td>{{ formatBacktestNumber(backtestResult.strategies?.buy_and_hold?.metrics?.sortino_ratio) }}</td>
                <td>{{ formatBacktestNumber(backtestResult.strategies?.sma?.metrics?.sortino_ratio) }}</td>
              </tr>

              <tr>
                <td>Win Rate</td>
                <td>{{ formatBacktestPercentage(backtestResult.strategies?.ml?.metrics?.win_rate) }}</td>
                <td>{{ formatBacktestPercentage(backtestResult.strategies?.buy_and_hold?.metrics?.win_rate) }}</td>
                <td>{{ formatBacktestPercentage(backtestResult.strategies?.sma?.metrics?.win_rate) }}</td>
              </tr>

              <tr>
                <td>Profit Factor</td>
                <td>{{ formatBacktestNumber(backtestResult.strategies?.ml?.metrics?.profit_factor) }}</td>
                <td>{{ formatBacktestNumber(backtestResult.strategies?.buy_and_hold?.metrics?.profit_factor) }}</td>
                <td>{{ formatBacktestNumber(backtestResult.strategies?.sma?.metrics?.profit_factor) }}</td>
              </tr>

              <tr>
                <td>Trades</td>
                <td>{{ formatBacktestObservations(backtestResult.strategies?.ml?.metrics?.trades) }}</td>
                <td>{{ formatBacktestObservations(backtestResult.strategies?.buy_and_hold?.metrics?.trades) }}</td>
                <td>{{ formatBacktestObservations(backtestResult.strategies?.sma?.metrics?.trades) }}</td>
              </tr>

              <tr>
                <td>Trading Costs</td>
                <td>{{ formatBacktestPercentage(backtestResult.strategies?.ml?.metrics?.total_trading_cost) }}</td>
                <td>{{ formatBacktestPercentage(backtestResult.strategies?.buy_and_hold?.metrics?.total_trading_cost) }}</td>
                <td>{{ formatBacktestPercentage(backtestResult.strategies?.sma?.metrics?.total_trading_cost) }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div
          ref="backtestChartElement"
          class="backtest-chart"
        ></div>

        <div class="backtest-notes">
          <strong>Backtest assumptions:</strong> 5 bps transaction cost + 5 bps slippage per position change.
          The ML signal is generated using walk-forward training and executed one trading day later.
          The equity curves are historical simulations and are not forecasts or guarantees of future returns.
        </div>
      </template>
    </div>

    <!-- =====================================================
         LOADING / ERROR
    ====================================================== -->

    <div
      v-if="loading"
      class="chart-message"
    >
      Loading market data...
    </div>

    <div
      v-if="error"
      class="chart-message error"
    >
      {{ error }}
    </div>

    <div
      v-if="
        !loading &&
        !error &&
        prices.length === 0
      "
      class="chart-message"
    >
      No historical market data available.
    </div>

    <!-- =====================================================
         CHARTS
    ====================================================== -->

    <div class="chart-container">
      <div
        ref="priceChartElement"
        class="price-chart"
      ></div>

      <div
        ref="volumeChartElement"
        class="volume-chart"
      ></div>

      <div
        ref="rsiChartElement"
        class="rsi-chart"
      ></div>

      <div
        ref="macdChartElement"
        class="macd-chart"
      ></div>

      <div
        ref="stochasticChartElement"
        class="stochastic-chart"
      ></div>

      <div
        ref="atrChartElement"
        class="atr-chart"
      ></div>

      <div
        ref="rocChartElement"
        class="roc-chart"
      ></div>

      <div
        ref="obvChartElement"
        class="obv-chart"
      ></div>

      <div
        ref="adxChartElement"
        class="adx-chart"
      ></div>
    </div>
  </section>
</template>

<script setup>
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
} from "vue";

import Plotly from "plotly.js-finance-dist-min";

import {
  getHistoricalPrices,
  getBenchmarkComparison,
  getFundamentals,
  getRiskMetrics,
  getMLReturnPrediction,
  getBacktestResults,
} from "../../services/api";

/* =========================================================
   PROPS
========================================================= */

const props = defineProps({
  stockId: {
    type: Number,
    required: true,
  },

  symbol: {
    type: String,
    required: true,
  },
});

/* =========================================================
   CHART REFERENCES
========================================================= */

const priceChartElement = ref(null);
const volumeChartElement = ref(null);
const rsiChartElement = ref(null);
const macdChartElement = ref(null);
const stochasticChartElement = ref(null);
const atrChartElement = ref(null);
const rocChartElement = ref(null);
const obvChartElement = ref(null);
const adxChartElement = ref(null);

const benchmarkChartElement = ref(null);
const backtestChartElement = ref(null);

/* =========================================================
   STEP 17.3 - RISK VISUALISATION REFERENCES
========================================================= */

const riskReturnChartElement = ref(null);
const riskDrawdownChartElement = ref(null);
const riskDistributionChartElement = ref(null);

/* =========================================================
   STATE
========================================================= */

const prices = ref([]);
const loading = ref(false);
const error = ref("");

const selectedPeriod = ref("1y");

const marketRegime = ref(null);
const regimeClass = ref("");

const performanceMetrics = ref(null);

const benchmarkMetrics = ref(null);
const benchmarkLoading = ref(false);
const benchmarkError = ref("");

// Render the historical comparison chart only when at least one usable series exists.
const benchmarkChartRenderError = ref("");

const hasUsableBenchmarkSeries = (series) => {
  if (
    !Array.isArray(series?.dates) ||
    !Array.isArray(series?.values) ||
    series.dates.length < 2 ||
    series.dates.length !== series.values.length
  ) {
    return false;
  }

  return series.values.some((value) => Number.isFinite(Number(value)));
};

const benchmarkChartHasData = computed(() => {
  const metrics = benchmarkMetrics.value;
  if (!metrics) return false;

  return [
    metrics.stockNormalized,
    metrics.sp500?.normalized,
    metrics.nasdaq100?.normalized,
    metrics.sector?.normalized,
  ].some(hasUsableBenchmarkSeries);
});

/* =========================================================
   STEP 16 - FUNDAMENTALS
========================================================= */

const fundamentals = ref([]);
const fundamentalsLoading = ref(false);
const fundamentalsError = ref("");
const fundamentalsPeriod = ref("annual");
const latestFundamental = ref(null);

/* =========================================================
   STEP 17.2 - RISK ANALYSIS
========================================================= */

const riskMetrics = ref(null);
const riskLoading = ref(false);
const riskError = ref("");
const riskPeriod = ref({
  startDate: "",
  endDate: "",
});

/* =========================================================
   STEP 17.3 - RISK INTERPRETATION STATE
========================================================= */

const riskInterpretation = ref({
  returnVolatility: "Risk-return information will appear when the historical metrics are available.",
  drawdown: "Historical drawdown information will appear when the selected price history is available.",
  tailRisk: "Historical tail-loss information will appear when VaR and Expected Shortfall are available.",
  benchmark: "Benchmark relationship information will appear when beta and correlation are available.",
});

/* =========================================================
   STEP 18.7 - ML RETURN PREDICTION
========================================================= */

const mlPrediction = ref(null);
const mlLoading = ref(false);
const mlError = ref("");
const mlModel = ref("random_forest");
const mlHorizon = ref(5);
const mlConfidence = ref(0.90);

/* =========================================================
   STEP 19.3 - BACKTEST VISUALISATION
========================================================= */

const backtestResult = ref(null);
const backtestLoading = ref(false);
const backtestError = ref("");

const mlModels = [
  {
    label: "Linear Regression",
    value: "linear_regression",
  },
  {
    label: "Random Forest",
    value: "random_forest",
  },
  {
    label: "XGBoost",
    value: "xgboost",
  },
];

const mlHorizons = [
  { label: "1D", value: 1 },
  { label: "5D", value: 5 },
  { label: "1M", value: 20 },
  { label: "3M", value: 60 },
  { label: "6M", value: 126 },
  { label: "1Y", value: 252 },
];


const periods = [
  {
    label: "1M",
    value: "1m",
  },
  {
    label: "2M",
    value: "2m",
  },
  {
    label: "3M",
    value: "3m",
  },
  {
    label: "6M",
    value: "6m",
  },
  {
    label: "1Y",
    value: "1y",
  },
  {
    label: "3Y",
    value: "3y",
  },
  {
    label: "5Y",
    value: "5y",
  },
  {
    label: "10Y",
    value: "10y",
  },
];

/* =========================================================
   SELECTED PERIOD LABEL
========================================================= */

const selectedPeriodLabel = ref("1Y");

const updateSelectedPeriodLabel = () => {
  const selected =
    periods.find(
      (period) =>
        period.value ===
        selectedPeriod.value
    );

  selectedPeriodLabel.value =
    selected?.label ||
    selectedPeriod.value;
};

/* =========================================================
   DATE HELPERS
========================================================= */

const getEndDate = () => {
  const date = new Date();

  return date
    .toISOString()
    .split("T")[0];
};

const getStartDate = (
  period
) => {
  const date = new Date();

  switch (period) {
    case "1m":
      date.setMonth(
        date.getMonth() - 1
      );
      break;

    case "2m":
      date.setMonth(
        date.getMonth() - 2
      );
      break;

    case "3m":
      date.setMonth(
        date.getMonth() - 3
      );
      break;

    case "6m":
      date.setMonth(
        date.getMonth() - 6
      );
      break;

    case "1y":
      date.setFullYear(
        date.getFullYear() - 1
      );
      break;

    case "3y":
      date.setFullYear(
        date.getFullYear() - 3
      );
      break;

    case "5y":
      date.setFullYear(
        date.getFullYear() - 5
      );
      break;

    case "10y":
      date.setFullYear(
        date.getFullYear() - 10
      );
      break;

    default:
      date.setFullYear(
        date.getFullYear() - 1
      );
  }

  return date
    .toISOString()
    .split("T")[0];
};

/* =========================================================
   MOVING AVERAGES
========================================================= */

const calculateSMA = (
  values,
  period
) => {
  const result =
    new Array(
      values.length
    ).fill(null);

  if (
    values.length <
    period
  ) {
    return result;
  }

  let sum = 0;

  for (
    let i = 0;
    i < values.length;
    i++
  ) {
    sum += values[i];

    if (i >= period) {
      sum -=
        values[
          i - period
        ];
    }

    if (
      i >=
      period - 1
    ) {
      result[i] =
        sum / period;
    }
  }

  return result;
};

const calculateEMA = (
  values,
  period
) => {
  const result =
    new Array(
      values.length
    ).fill(null);

  if (
    values.length <
    period
  ) {
    return result;
  }

  const multiplier =
    2 / (period + 1);

  let sum = 0;

  for (
    let i = 0;
    i < period;
    i++
  ) {
    sum += values[i];
  }

  result[
    period - 1
  ] =
    sum / period;

  for (
    let i = period;
    i < values.length;
    i++
  ) {
    result[i] =
      (values[i] -
        result[i - 1]) *
        multiplier +
      result[i - 1];
  }

  return result;
};

/* =========================================================
   RSI
========================================================= */

const calculateRSI = (
  values,
  period = 14
) => {
  const result =
    new Array(
      values.length
    ).fill(null);

  if (
    values.length <=
    period
  ) {
    return result;
  }

  let gains = 0;
  let losses = 0;

  for (
    let i = 1;
    i <= period;
    i++
  ) {
    const change =
      values[i] -
      values[i - 1];

    if (change > 0) {
      gains += change;
    } else {
      losses +=
        Math.abs(
          change
        );
    }
  }

  let averageGain =
    gains / period;

  let averageLoss =
    losses / period;

  if (
    averageLoss === 0
  ) {
    result[period] = 100;
  } else {
    const rs =
      averageGain /
      averageLoss;

    result[period] =
      100 -
      100 / (1 + rs);
  }

  for (
    let i = period + 1;
    i < values.length;
    i++
  ) {
    const change =
      values[i] -
      values[i - 1];

    const gain =
      Math.max(
        change,
        0
      );

    const loss =
      Math.max(
        -change,
        0
      );

    averageGain =
      ((averageGain *
        (period - 1)) +
        gain) /
      period;

    averageLoss =
      ((averageLoss *
        (period - 1)) +
        loss) /
      period;

    if (
      averageLoss === 0
    ) {
      result[i] = 100;
    } else {
      const rs =
        averageGain /
        averageLoss;

      result[i] =
        100 -
        100 / (1 + rs);
    }
  }

  return result;
};

/* =========================================================
   BOLLINGER BANDS
========================================================= */

const calculateBollingerBands = (
  values,
  period = 20,
  multiplier = 2
) => {
  const middle =
    new Array(
      values.length
    ).fill(null);

  const upper =
    new Array(
      values.length
    ).fill(null);

  const lower =
    new Array(
      values.length
    ).fill(null);

  for (
    let i = period - 1;
    i < values.length;
    i++
  ) {
    const window =
      values.slice(
        i - period + 1,
        i + 1
      );

    const mean =
      window.reduce(
        (
          sum,
          value
        ) =>
          sum + value,
        0
      ) / period;

    const variance =
      window.reduce(
        (
          sum,
          value
        ) =>
          sum +
          Math.pow(
            value - mean,
            2
          ),
        0
      ) / period;

    const standardDeviation =
      Math.sqrt(
        variance
      );

    middle[i] =
      mean;

    upper[i] =
      mean +
      multiplier *
        standardDeviation;

    lower[i] =
      mean -
      multiplier *
        standardDeviation;
  }

  return {
    middle,
    upper,
    lower,
  };
};

/* =========================================================
   STOCHASTIC
========================================================= */

const calculateStochastic = (
  highs,
  lows,
  closes,
  period = 14,
  smoothK = 3,
  smoothD = 3
) => {
  const rawK =
    new Array(
      closes.length
    ).fill(null);

  const k =
    new Array(
      closes.length
    ).fill(null);

  const d =
    new Array(
      closes.length
    ).fill(null);

  for (
    let i = period - 1;
    i < closes.length;
    i++
  ) {
    const periodHighs =
      highs.slice(
        i - period + 1,
        i + 1
      );

    const periodLows =
      lows.slice(
        i - period + 1,
        i + 1
      );

    const highestHigh =
      Math.max(
        ...periodHighs
      );

    const lowestLow =
      Math.min(
        ...periodLows
      );

    if (
      highestHigh ===
      lowestLow
    ) {
      rawK[i] = 0;
    } else {
      rawK[i] =
        ((closes[i] -
          lowestLow) /
          (highestHigh -
            lowestLow)) *
        100;
    }
  }

  for (
    let i = 0;
    i < closes.length;
    i++
  ) {
    if (
      i >=
      period -
        1 +
        smoothK -
        1
    ) {
      const values =
        rawK.slice(
          i - smoothK + 1,
          i + 1
        );

      const validValues =
        values.filter(
          (value) =>
            value !== null
        );

      if (
        validValues.length ===
        smoothK
      ) {
        k[i] =
          validValues.reduce(
            (
              sum,
              value
            ) =>
              sum + value,
            0
          ) / smoothK;
      }
    }
  }

  for (
    let i = 0;
    i < closes.length;
    i++
  ) {
    if (
      i >=
      period -
        1 +
        smoothK -
        1 +
        smoothD -
        1
    ) {
      const values =
        k.slice(
          i - smoothD + 1,
          i + 1
        );

      const validValues =
        values.filter(
          (value) =>
            value !== null
        );

      if (
        validValues.length ===
        smoothD
      ) {
        d[i] =
          validValues.reduce(
            (
              sum,
              value
            ) =>
              sum + value,
            0
          ) / smoothD;
      }
    }
  }

  return {
    k,
    d,
  };
};

/* =========================================================
   ATR
========================================================= */

const calculateATR = (
  highs,
  lows,
  closes,
  period = 14
) => {
  const trueRanges =
    new Array(
      closes.length
    ).fill(null);

  const atr =
    new Array(
      closes.length
    ).fill(null);

  for (
    let i = 0;
    i < closes.length;
    i++
  ) {
    if (i === 0) {
      trueRanges[i] =
        highs[i] -
        lows[i];
    } else {
      const highLow =
        highs[i] -
        lows[i];

      const highPreviousClose =
        Math.abs(
          highs[i] -
            closes[i - 1]
        );

      const lowPreviousClose =
        Math.abs(
          lows[i] -
            closes[i - 1]
        );

      trueRanges[i] =
        Math.max(
          highLow,
          highPreviousClose,
          lowPreviousClose
        );
    }
  }

  if (
    closes.length <
    period
  ) {
    return atr;
  }

  let initialATR = 0;

  for (
    let i = 0;
    i < period;
    i++
  ) {
    initialATR +=
      trueRanges[i];
  }

  atr[period - 1] =
    initialATR / period;

  for (
    let i = period;
    i < closes.length;
    i++
  ) {
    atr[i] =
      ((atr[i - 1] *
        (period - 1)) +
        trueRanges[i]) /
      period;
  }

  return atr;
};

/* =========================================================
   ROC
========================================================= */

const calculateROC = (
  values,
  period = 12
) => {
  const result =
    new Array(
      values.length
    ).fill(null);

  for (
    let i = period;
    i < values.length;
    i++
  ) {
    if (
      values[i - period] ===
      0
    ) {
      continue;
    }

    result[i] =
      ((values[i] -
        values[
          i - period
        ]) /
        values[
          i - period
        ]) *
      100;
  }

  return result;
};

/* =========================================================
   OBV
========================================================= */

const calculateOBV = (
  closes,
  volumes
) => {
  const result =
    new Array(
      closes.length
    ).fill(0);

  if (
    closes.length ===
    0
  ) {
    return result;
  }

  result[0] =
    volumes[0];

  for (
    let i = 1;
    i < closes.length;
    i++
  ) {
    if (
      closes[i] >
      closes[i - 1]
    ) {
      result[i] =
        result[i - 1] +
        volumes[i];
    } else if (
      closes[i] <
      closes[i - 1]
    ) {
      result[i] =
        result[i - 1] -
        volumes[i];
    } else {
      result[i] =
        result[i - 1];
    }
  }

  return result;
};

/* =========================================================
   MACD
========================================================= */

const calculateMACD = (
  values,
  fastPeriod = 12,
  slowPeriod = 26,
  signalPeriod = 9
) => {
  const fastEMA =
    calculateEMA(
      values,
      fastPeriod
    );

  const slowEMA =
    calculateEMA(
      values,
      slowPeriod
    );

  const macd =
    new Array(
      values.length
    ).fill(null);

  for (
    let i = 0;
    i < values.length;
    i++
  ) {
    if (
      fastEMA[i] !==
        null &&
      slowEMA[i] !==
        null
    ) {
      macd[i] =
        fastEMA[i] -
        slowEMA[i];
    }
  }

  const validMACD =
    macd.filter(
      (value) =>
        value !== null
    );

  const signalValid =
    calculateEMA(
      validMACD,
      signalPeriod
    );

  const signal =
    new Array(
      values.length
    ).fill(null);

  let validIndex = 0;

  for (
    let i = 0;
    i < values.length;
    i++
  ) {
    if (
      macd[i] !== null
    ) {
      signal[i] =
        signalValid[
          validIndex
        ];

      validIndex++;
    }
  }

  const histogram =
    new Array(
      values.length
    ).fill(null);

  for (
    let i = 0;
    i < values.length;
    i++
  ) {
    if (
      macd[i] !== null &&
      signal[i] !== null
    ) {
      histogram[i] =
        macd[i] -
        signal[i];
    }
  }

  return {
    macd,
    signal,
    histogram,
  };
};

/* =========================================================
   SUPPORT & RESISTANCE
========================================================= */

const calculateSupportResistance = (
  highs,
  lows,
  closes,
  lookback = 20
) => {
  const support = [];
  const resistance = [];

  if (
    closes.length <
    lookback
  ) {
    return {
      support,
      resistance,
    };
  }

  for (
    let i = lookback;
    i <
      closes.length -
        lookback;
    i++
  ) {
    const previousLows =
      lows.slice(
        i - lookback,
        i
      );

    const nextLows =
      lows.slice(
        i + 1,
        i +
          lookback +
          1
      );

    const previousHighs =
      highs.slice(
        i - lookback,
        i
      );

    const nextHighs =
      highs.slice(
        i + 1,
        i +
          lookback +
          1
      );

    const isSupport =
      lows[i] <=
        Math.min(
          ...previousLows
        ) &&
      lows[i] <=
        Math.min(
          ...nextLows
        );

    const isResistance =
      highs[i] >=
        Math.max(
          ...previousHighs
        ) &&
      highs[i] >=
        Math.max(
          ...nextHighs
        );

    if (isSupport) {
      support.push({
        index: i,
        price: lows[i],
      });
    }

    if (
      isResistance
    ) {
      resistance.push({
        index: i,
        price: highs[i],
      });
    }
  }

  return {
    support,
    resistance,
  };
};

/* =========================================================
   ADX + DI
========================================================= */

const calculateADX = (
  highs,
  lows,
  closes,
  period = 14
) => {
  const length =
    closes.length;

  const plusDM =
    new Array(length).fill(0);

  const minusDM =
    new Array(length).fill(0);

  const trueRange =
    new Array(length).fill(0);

  const plusDI =
    new Array(length).fill(null);

  const minusDI =
    new Array(length).fill(null);

  const adx =
    new Array(length).fill(null);

  for (
    let i = 1;
    i < length;
    i++
  ) {
    const upMove =
      highs[i] -
      highs[i - 1];

    const downMove =
      lows[i - 1] -
      lows[i];

    plusDM[i] =
      upMove >
        downMove &&
      upMove > 0
        ? upMove
        : 0;

    minusDM[i] =
      downMove >
        upMove &&
      downMove > 0
        ? downMove
        : 0;

    const highLow =
      highs[i] -
      lows[i];

    const highPreviousClose =
      Math.abs(
        highs[i] -
          closes[i - 1]
      );

    const lowPreviousClose =
      Math.abs(
        lows[i] -
          closes[i - 1]
      );

    trueRange[i] =
      Math.max(
        highLow,
        highPreviousClose,
        lowPreviousClose
      );
  }

  if (
    length <= period
  ) {
    return {
      adx,
      plusDI,
      minusDI,
    };
  }

  let smoothedTR = 0;
  let smoothedPlusDM = 0;
  let smoothedMinusDM = 0;

  for (
    let i = 1;
    i <= period;
    i++
  ) {
    smoothedTR +=
      trueRange[i];

    smoothedPlusDM +=
      plusDM[i];

    smoothedMinusDM +=
      minusDM[i];
  }

  for (
    let i = period;
    i < length;
    i++
  ) {
    if (i > period) {
      smoothedTR =
        smoothedTR -
        smoothedTR /
          period +
        trueRange[i];

      smoothedPlusDM =
        smoothedPlusDM -
        smoothedPlusDM /
          period +
        plusDM[i];

      smoothedMinusDM =
        smoothedMinusDM -
        smoothedMinusDM /
          period +
        minusDM[i];
    }

    if (
      smoothedTR !== 0
    ) {
      plusDI[i] =
        (100 *
          smoothedPlusDM) /
        smoothedTR;

      minusDI[i] =
        (100 *
          smoothedMinusDM) /
        smoothedTR;
    }
  }

  const dx =
    new Array(
      length
    ).fill(null);

  for (
    let i = period;
    i < length;
    i++
  ) {
    if (
      plusDI[i] !==
        null &&
      minusDI[i] !==
        null &&
      plusDI[i] +
        minusDI[i] !==
        0
    ) {
      dx[i] =
        (100 *
          Math.abs(
            plusDI[i] -
              minusDI[i]
          )) /
        (plusDI[i] +
          minusDI[i]);
    }
  }

  const firstADXValues = [];

  for (
    let i = period;
    i < length &&
    firstADXValues.length <
      period;
    i++
  ) {
    if (
      dx[i] !== null
    ) {
      firstADXValues.push(
        dx[i]
      );
    }
  }

  if (
    firstADXValues.length ===
    period
  ) {
    const firstADX =
      firstADXValues.reduce(
        (
          sum,
          value
        ) =>
          sum + value,
        0
      ) / period;

    const firstADXIndex =
      period +
      period -
      1;

    adx[firstADXIndex] =
      firstADX;

    for (
      let i =
        firstADXIndex + 1;
      i < length;
      i++
    ) {
      if (
        dx[i] !== null
      ) {
        adx[i] =
          ((adx[i - 1] *
            (period - 1)) +
            dx[i]) /
          period;
      }
    }
  }

  return {
    adx,
    plusDI,
    minusDI,
  };
};

/* =========================================================
   STEP 12
   GOLDEN CROSS / DEATH CROSS
========================================================= */

const calculateCrossovers = (
  sma50,
  sma200
) => {
  const goldenCross = [];
  const deathCross = [];

  for (
    let i = 1;
    i < sma50.length;
    i++
  ) {
    if (
      sma50[i - 1] ===
        null ||
      sma200[i - 1] ===
        null ||
      sma50[i] ===
        null ||
      sma200[i] ===
        null
    ) {
      continue;
    }

    const previousDifference =
      sma50[i - 1] -
      sma200[i - 1];

    const currentDifference =
      sma50[i] -
      sma200[i];

    if (
      previousDifference <=
        0 &&
      currentDifference >
        0
    ) {
      goldenCross.push(i);
    }

    if (
      previousDifference >=
        0 &&
      currentDifference <
        0
    ) {
      deathCross.push(i);
    }
  }

  return {
    goldenCross,
    deathCross,
  };
};

/* =========================================================
   STEP 13
   MARKET REGIME DETECTION
========================================================= */

const calculateMarketRegime = ({
  close,
  sma20,
  sma50,
  sma200,
  adx,
  plusDI,
  minusDI,
}) => {
  const latestIndex =
    close.length - 1;

  if (
    latestIndex < 0
  ) {
    return null;
  }

  const latestClose =
    close[latestIndex];

  const latestSMA20 =
    sma20[latestIndex];

  const latestSMA50 =
    sma50[latestIndex];

  const latestSMA200 =
    sma200[latestIndex];

  const latestADX =
    adx[latestIndex];

  const latestPlusDI =
    plusDI[latestIndex];

  const latestMinusDI =
    minusDI[latestIndex];

  if (
    latestSMA20 ===
      null ||
    latestSMA50 ===
      null ||
    latestSMA200 ===
      null
  ) {
    return {
      trend:
        "Insufficient Data",

      strength:
        "Insufficient Data",

      adx: latestADX,
      plusDI:
        latestPlusDI,
      minusDI:
        latestMinusDI,

      smaAlignment:
        "Insufficient Data",

      priceVsSMA200:
        "Insufficient Data",

      dataPoints:
        close.length,

      description:
        "This timeframe does not contain enough historical data to calculate the full 20/50/200-day trend structure.",
    };
  }

  let smaAlignment =
    "Mixed";

  if (
    latestSMA20 >
      latestSMA50 &&
    latestSMA50 >
      latestSMA200
  ) {
    smaAlignment =
      "Bullish: 20 > 50 > 200";
  } else if (
    latestSMA20 <
      latestSMA50 &&
    latestSMA50 <
      latestSMA200
  ) {
    smaAlignment =
      "Bearish: 20 < 50 < 200";
  }

  let priceVsSMA200 =
    "Near SMA 200";

  if (
    latestClose >
    latestSMA200
  ) {
    priceVsSMA200 =
      "Above SMA 200";
  } else if (
    latestClose <
    latestSMA200
  ) {
    priceVsSMA200 =
      "Below SMA 200";
  }

  let strength =
    "Insufficient Data";

  if (
    latestADX !== null
  ) {
    if (
      latestADX >= 25
    ) {
      strength =
        "Strong";
    } else if (
      latestADX >= 20
    ) {
      strength =
        "Moderate";
    } else {
      strength =
        "Weak / Ranging";
    }
  }

  let trend =
    "Neutral";

  const bullishSMA =
    latestSMA20 >
      latestSMA50 &&
    latestSMA50 >
      latestSMA200;

  const bearishSMA =
    latestSMA20 <
      latestSMA50 &&
    latestSMA50 <
      latestSMA200;

  const bullishDI =
    latestPlusDI !==
      null &&
    latestMinusDI !==
      null &&
    latestPlusDI >
      latestMinusDI;

  const bearishDI =
    latestPlusDI !==
      null &&
    latestMinusDI !==
      null &&
    latestMinusDI >
      latestPlusDI;

  const priceBullish =
    latestClose >
    latestSMA200;

  const priceBearish =
    latestClose <
    latestSMA200;

  if (
    bullishSMA &&
    priceBullish &&
    bullishDI
  ) {
    trend =
      "Bullish";
  } else if (
    bearishSMA &&
    priceBearish &&
    bearishDI
  ) {
    trend =
      "Bearish";
  } else {
    trend =
      "Neutral / Mixed";
  }

  let description =
    "The current indicators do not show a strongly aligned trend.";

  if (
    trend ===
    "Bullish"
  ) {
    description =
      "Price is above the 200-day SMA, the short- and medium-term moving averages are aligned above the long-term average, and +DI is above -DI.";
  } else if (
    trend ===
    "Bearish"
  ) {
    description =
      "Price is below the 200-day SMA, the short- and medium-term moving averages are aligned below the long-term average, and -DI is above +DI.";
  }

  if (
    strength ===
    "Weak / Ranging"
  ) {
    description +=
      " ADX is below 20, indicating relatively weak directional trend strength.";
  } else if (
    strength ===
    "Moderate"
  ) {
    description +=
      " ADX indicates a developing or moderate directional trend.";
  } else if (
    strength ===
    "Strong"
  ) {
    description +=
      " ADX indicates a relatively strong directional trend.";
  }

  return {
    trend,
    strength,
    adx: latestADX,
    plusDI:
      latestPlusDI,
    minusDI:
      latestMinusDI,
    smaAlignment,
    priceVsSMA200,
    dataPoints:
      close.length,
    description,
  };
};

/* =========================================================
   STEP 14
   PERFORMANCE ANALYSIS
========================================================= */

const calculatePerformanceMetrics = (
  dates,
  close
) => {
  if (
    !close.length ||
    close.length < 2
  ) {
    return null;
  }

  const startPrice =
    close[0];

  const endPrice =
    close[
      close.length - 1
    ];

  if (
    startPrice <= 0 ||
    endPrice <= 0
  ) {
    return null;
  }

  const priceChange =
    endPrice -
    startPrice;

  const totalReturn =
    ((endPrice -
      startPrice) /
      startPrice) *
    100;

  const dailyReturns = [];

  for (
    let i = 1;
    i < close.length;
    i++
  ) {
    if (
      close[i - 1] >
        0 &&
      close[i] > 0
    ) {
      dailyReturns.push(
        (close[i] -
          close[i - 1]) /
          close[i - 1]
      );
    }
  }

  let annualizedReturn =
    totalReturn;

  let annualizedVolatility =
    null;

  let bestDay = null;
  let worstDay = null;

  let positiveCount = 0;
  let negativeCount = 0;

  if (
    dailyReturns.length >
    0
  ) {
    bestDay =
      Math.max(
        ...dailyReturns
      ) * 100;

    worstDay =
      Math.min(
        ...dailyReturns
      ) * 100;

    positiveCount =
      dailyReturns.filter(
        (value) =>
          value > 0
      ).length;

    negativeCount =
      dailyReturns.filter(
        (value) =>
          value < 0
      ).length;

    const mean =
      dailyReturns.reduce(
        (
          sum,
          value
        ) =>
          sum + value,
        0
      ) /
      dailyReturns.length;

    const variance =
      dailyReturns.reduce(
        (
          sum,
          value
        ) =>
          sum +
          Math.pow(
            value - mean,
            2
          ),
        0
      ) /
      dailyReturns.length;

    const standardDeviation =
      Math.sqrt(
        variance
      );

    annualizedVolatility =
      standardDeviation *
      Math.sqrt(252) *
      100;
  }

  const startDate =
    new Date(
      dates[0]
    );

  const endDate =
    new Date(
      dates[
        dates.length - 1
      ]
    );

  const daysElapsed =
    Math.max(
      1,
      (endDate -
        startDate) /
        (1000 *
          60 *
          60 *
          24)
    );

  const yearsElapsed =
    daysElapsed /
    365.25;

  if (
    yearsElapsed > 0
  ) {
    annualizedReturn =
      (Math.pow(
        endPrice /
          startPrice,
        1 /
          yearsElapsed
      ) -
        1) *
      100;
  }

  let peak =
    close[0];

  let maxDrawdown = 0;

  for (
    let i = 0;
    i < close.length;
    i++
  ) {
    if (
      close[i] >
      peak
    ) {
      peak =
        close[i];
    }

    if (
      peak > 0
    ) {
      const drawdown =
        ((close[i] -
          peak) /
          peak) *
        100;

      if (
        drawdown <
        maxDrawdown
      ) {
        maxDrawdown =
          drawdown;
      }
    }
  }

  const totalDays =
    dailyReturns.length;

  const positiveDays =
    totalDays > 0
      ? (positiveCount /
          totalDays) *
        100
      : null;

  const negativeDays =
    totalDays > 0
      ? (negativeCount /
          totalDays) *
        100
      : null;

  let description =
    `Over the selected ${selectedPeriodLabel.value} period, ${props.symbol} moved from ${formatPrice(startPrice)} to ${formatPrice(endPrice)}.`;

  if (
    totalReturn > 0
  ) {
    description +=
      ` The stock generated a positive historical return of ${formatSignedPercentage(totalReturn)}.`;
  } else if (
    totalReturn < 0
  ) {
    description +=
      ` The stock generated a negative historical return of ${formatSignedPercentage(totalReturn)}.`;
  } else {
    description +=
      " The stock finished approximately unchanged from the starting price.";
  }

  if (
    maxDrawdown !==
    null
  ) {
    description +=
      ` The largest peak-to-trough decline during this period was ${formatSignedPercentage(maxDrawdown)}.`;
  }

  return {
    totalReturn,
    annualizedReturn,
    annualizedVolatility,
    maxDrawdown,
    bestDay,
    worstDay,
    positiveDays,
    negativeDays,
    startPrice,
    endPrice,
    priceChange,
    tradingDays:
      close.length,
    description,
  };
};

/* =========================================================
   STEP 15
   BENCHMARK CALCULATIONS
========================================================= */

const calculateReturns = (
  values
) => {
  if (
    !values ||
    values.length < 2
  ) {
    return [];
  }

  const returns = [];

  for (
    let i = 1;
    i < values.length;
    i++
  ) {
    if (
      values[i - 1] > 0 &&
      values[i] > 0
    ) {
      returns.push(
        (values[i] -
          values[i - 1]) /
          values[i - 1]
      );
    }
  }

  return returns;
};

const calculateAnnualizedReturn = (
  dates,
  values
) => {
  if (
    !dates ||
    !values ||
    values.length < 2
  ) {
    return null;
  }

  const start =
    Number(values[0]);

  const end =
    Number(
      values[
        values.length - 1
      ]
    );

  if (
    start <= 0 ||
    end <= 0
  ) {
    return null;
  }

  const startDate =
    new Date(dates[0]);

  const endDate =
    new Date(
      dates[
        dates.length - 1
      ]
    );

  const days =
    Math.max(
      1,
      (endDate -
        startDate) /
        (1000 *
          60 *
          60 *
          24)
    );

  const years =
    days / 365.25;

  return (
    Math.pow(
      end / start,
      1 / years
    ) -
    1
  ) * 100;
};

const calculateAnnualizedVolatility = (
  values
) => {
  const returns =
    calculateReturns(
      values
    );

  if (
    returns.length === 0
  ) {
    return null;
  }

  const mean =
    returns.reduce(
      (
        sum,
        value
      ) =>
        sum + value,
      0
    ) /
    returns.length;

  const variance =
    returns.reduce(
      (
        sum,
        value
      ) =>
        sum +
        Math.pow(
          value - mean,
          2
        ),
      0
    ) /
    returns.length;

  return (
    Math.sqrt(
      variance
    ) *
    Math.sqrt(252) *
    100
  );
};

const calculateCorrelation = (
  stockValues,
  benchmarkValues
) => {
  const stockMap =
    new Map();

  stockValues.forEach(
    (item) => {
      stockMap.set(
        item.date,
        Number(
          item.close
        )
      );
    }
  );

  const benchmarkMap =
    new Map();

  benchmarkValues.forEach(
    (item) => {
      benchmarkMap.set(
        item.date,
        Number(
          item.close
        )
      );
    }
  );

  const commonDates =
    [...stockMap.keys()]
      .filter(
        (date) =>
          benchmarkMap.has(
            date
          )
      )
      .sort();

  if (
    commonDates.length <
    3
  ) {
    return null;
  }

  const stockReturns = [];
  const benchmarkReturns = [];

  for (
    let i = 1;
    i <
      commonDates.length;
    i++
  ) {
    const previousDate =
      commonDates[
        i - 1
      ];

    const currentDate =
      commonDates[i];

    const stockPrevious =
      stockMap.get(
        previousDate
      );

    const stockCurrent =
      stockMap.get(
        currentDate
      );

    const benchmarkPrevious =
      benchmarkMap.get(
        previousDate
      );

    const benchmarkCurrent =
      benchmarkMap.get(
        currentDate
      );

    if (
      stockPrevious > 0 &&
      stockCurrent > 0 &&
      benchmarkPrevious > 0 &&
      benchmarkCurrent > 0
    ) {
      stockReturns.push(
        (stockCurrent -
          stockPrevious) /
          stockPrevious
      );

      benchmarkReturns.push(
        (benchmarkCurrent -
          benchmarkPrevious) /
          benchmarkPrevious
      );
    }
  }

  if (
    stockReturns.length <
    2
  ) {
    return null;
  }

  const stockMean =
    stockReturns.reduce(
      (
        sum,
        value
      ) =>
        sum + value,
      0
    ) /
    stockReturns.length;

  const benchmarkMean =
    benchmarkReturns.reduce(
      (
        sum,
        value
      ) =>
        sum + value,
      0
    ) /
    benchmarkReturns.length;

  let numerator = 0;
  let stockVariance = 0;
  let benchmarkVariance = 0;

  for (
    let i = 0;
    i <
      stockReturns.length;
    i++
  ) {
    const stockDifference =
      stockReturns[i] -
      stockMean;

    const benchmarkDifference =
      benchmarkReturns[i] -
      benchmarkMean;

    numerator +=
      stockDifference *
      benchmarkDifference;

    stockVariance +=
      Math.pow(
        stockDifference,
        2
      );

    benchmarkVariance +=
      Math.pow(
        benchmarkDifference,
        2
      );
  }

  if (
    stockVariance === 0 ||
    benchmarkVariance === 0
  ) {
    return null;
  }

  return (
    numerator /
    Math.sqrt(
      stockVariance *
        benchmarkVariance
    )
  );
};

const createBenchmarkSeries = (
  dates,
  close
) => {
  if (
    !dates ||
    !close ||
    dates.length !==
      close.length
  ) {
    return [];
  }

  return dates.map(
    (date, index) => ({
      date,
      close:
        Number(
          close[index]
        ),
    })
  );
};

const normalizeSeries = (
  dates,
  close
) => {
  if (
    !dates ||
    !close ||
    close.length ===
      0
  ) {
    return {
      dates: [],
      values: [],
    };
  }

  const first =
    Number(close[0]);

  if (
    !first ||
    first <= 0
  ) {
    return {
      dates: [],
      values: [],
    };
  }

  return {
    dates,
    values: close.map(
      (value) =>
        (Number(value) /
          first) *
        10000
    ),
  };
};

const buildBenchmarkMetric = (
  dates,
  close,
  stockSeries
) => {
  if (
    !dates ||
    !close ||
    close.length < 2
  ) {
    return {
      totalReturn: null,
      annualizedReturn: null,
      annualizedVolatility:
        null,
      correlation: null,
      normalized:
        {
          dates: [],
          values: [],
        },
    };
  }

  const totalReturn =
    ((Number(
      close[
        close.length - 1
      ]
    ) -
      Number(close[0])) /
      Number(close[0])) *
    100;

  const annualizedReturn =
    calculateAnnualizedReturn(
      dates,
      close
    );

  const annualizedVolatility =
    calculateAnnualizedVolatility(
      close
    );

  const benchmarkSeries =
    createBenchmarkSeries(
      dates,
      close
    );

  const correlation =
    calculateCorrelation(
      stockSeries,
      benchmarkSeries
    );

  return {
    totalReturn,
    annualizedReturn,
    annualizedVolatility,
    correlation,
    normalized:
      normalizeSeries(
        dates,
        close
      ),
  };
};

/* =========================================================
   STEP 15
   LOAD BENCHMARK DATA
========================================================= */

const loadBenchmarkData = async (
  startDate,
  endDate,
  stockDates,
  stockClose
) => {
  try {
    benchmarkLoading.value =
      true;

    benchmarkError.value =
      "";

    benchmarkChartRenderError.value = "";
    benchmarkMetrics.value =
      null;

    const response =
      await getBenchmarkComparison(
        startDate,
        endDate,
        "",
        props.symbol.endsWith(".L") ? "LSE" : "NASDAQ"
      );

    if (
      !response ||
      !response.benchmarks
    ) {
      throw new Error(
        "Invalid benchmark response."
      );
    }

    const stockSeries =
      createBenchmarkSeries(
        stockDates,
        stockClose
      );

    const sp500 =
      response.benchmarks
        .sp500;

    const nasdaq100 =
      response.benchmarks
        .nasdaq100;

    const sector =
      response.benchmarks
        .sector;

    const stockTotalReturn =
      stockClose.length >= 2
        ? ((stockClose[
            stockClose.length - 1
          ] -
            stockClose[0]) /
            stockClose[0]) *
          100
        : null;

    const stockAnnualizedReturn =
      calculateAnnualizedReturn(
        stockDates,
        stockClose
      );

    const stockAnnualizedVolatility =
      calculateAnnualizedVolatility(
        stockClose
      );

    const sp500Metrics =
      buildBenchmarkMetric(
        sp500.dates,
        sp500.close,
        stockSeries
      );

    const nasdaqMetrics =
      buildBenchmarkMetric(
        nasdaq100.dates,
        nasdaq100.close,
        stockSeries
      );

    const sectorMetrics =
      buildBenchmarkMetric(
        sector.dates,
        sector.close,
        stockSeries
      );

    benchmarkMetrics.value = {
      stock: {
        totalReturn:
          stockTotalReturn,

        annualizedReturn:
          stockAnnualizedReturn,

        annualizedVolatility:
          stockAnnualizedVolatility,
      },

      sp500:
        sp500Metrics,
      primaryName: sp500.name || "Primary benchmark",

      nasdaq100:
        nasdaqMetrics,
      secondaryName: nasdaq100.name || "Secondary benchmark",

      sector:
        sectorMetrics,

      sectorName:
        sector.name ||
        "Sector ETF",

      relative: {
        sp500:
          stockTotalReturn !==
            null &&
          sp500Metrics.totalReturn !==
            null
            ? stockTotalReturn -
              sp500Metrics.totalReturn
            : null,

        nasdaq100:
          stockTotalReturn !==
            null &&
          nasdaqMetrics.totalReturn !==
            null
            ? stockTotalReturn -
              nasdaqMetrics.totalReturn
            : null,

        sector:
          stockTotalReturn !==
            null &&
          sectorMetrics.totalReturn !==
            null
            ? stockTotalReturn -
              sectorMetrics.totalReturn
            : null,
      },

      stockNormalized:
        normalizeSeries(
          stockDates,
          stockClose
        ),
    };

    await nextTick();

    if (benchmarkChartHasData.value) {
      await renderBenchmarkChart();
    }

    console.log(
      "Benchmark Metrics:",
      benchmarkMetrics.value
    );
  } catch (err) {
    console.error(
      "Benchmark loading failed:",
      err
    );

    benchmarkError.value =
      "Unable to load benchmark market data.";

    benchmarkMetrics.value =
      null;

    fundamentals.value = [];
    latestFundamental.value = null;
  } finally {
    benchmarkLoading.value =
      false;
  }
};

/* =========================================================
   STEP 15
   BENCHMARK CHART
========================================================= */

const renderBenchmarkChart = async () => {
  if (
    !benchmarkChartElement.value ||
    !benchmarkMetrics.value ||
    !benchmarkChartHasData.value
  ) {
    return;
  }

  benchmarkChartRenderError.value = "";

  const stock =
    benchmarkMetrics.value
      .stockNormalized;

  const sp500 =
    benchmarkMetrics.value
      .sp500.normalized;

  const nasdaq100 =
    benchmarkMetrics.value
      .nasdaq100.normalized;

  const sector =
    benchmarkMetrics.value
      .sector.normalized;

  const traces = [];

  if (
    stock.dates.length > 0
  ) {
    traces.push({
      x: stock.dates,
      y: stock.values,
      type: "scatter",
      mode: "lines",
      name: props.symbol,

      line: {
        width: 3,
        color: "#111827",
      },

      hovertemplate:
        `<b>${props.symbol}</b><br>` +
        "$10,000 Growth: $%{y:,.2f}" +
        "<extra></extra>",
    });
  }

  if (
    sp500.dates.length > 0
  ) {
    traces.push({
      x: sp500.dates,
      y: sp500.values,
      type: "scatter",
      mode: "lines",
      name: benchmarkMetrics.value.primaryName,

      line: {
        width: 2,
        color: "#2563eb",
      },

      hovertemplate:
        `<b>${benchmarkMetrics.value.primaryName}</b><br>` +
        "$10,000 Growth: $%{y:,.2f}" +
        "<extra></extra>",
    });
  }

  if (
    nasdaq100.dates.length > 0
  ) {
    traces.push({
      x: nasdaq100.dates,
      y: nasdaq100.values,
      type: "scatter",
      mode: "lines",
      name: benchmarkMetrics.value.secondaryName,

      line: {
        width: 2,
        color: "#f59e0b",
      },

      hovertemplate:
        `<b>${benchmarkMetrics.value.secondaryName}</b><br>` +
        "$10,000 Growth: $%{y:,.2f}" +
        "<extra></extra>",
    });
  }

  if (
    sector.dates.length > 0
  ) {
    traces.push({
      x: sector.dates,
      y: sector.values,
      type: "scatter",
      mode: "lines",
      name:
        benchmarkMetrics.value
          .sectorName,

      line: {
        width: 2,
        color: "#7c3aed",
      },

      hovertemplate:
        "<b>%{fullData.name}</b><br>" +
        "$10,000 Growth: $%{y:,.2f}" +
        "<extra></extra>",
    });
  }

  const layout = {
    title: {
      text:
        "$10,000 Historical Growth Comparison",
      x: 0.02,
      xanchor: "left",
    },

    height: 250,

    margin: {
      l: 62,
      r: 20,
      t: 48,
      b: 42,
    },

    paper_bgcolor:
      "white",

    plot_bgcolor:
      "white",

    hovermode:
      "x unified",

    xaxis: {
      type: "date",

      showgrid: true,

      gridcolor:
        "#f3f4f6",
    },

    yaxis: {
      title:
        "Portfolio Value ($)",

      showgrid: true,

      gridcolor:
        "#f3f4f6",

      tickprefix: "$",

      separatethousands:
        true,
    },

    legend: {
      orientation: "h",

      y: 1.08,

      x: 0,
    },
  };

  const chartConfig = {
    responsive: true,

    displaylogo: false,

    scrollZoom: true,

    modeBarButtonsToRemove: [
      "lasso2d",
      "select2d",
    ],
  };

  if (traces.length === 0) {
    benchmarkChartRenderError.value =
      "Historical chart data is unavailable for this period. The comparison table remains available.";
    return;
  }

  try {
    await Plotly.react(
      benchmarkChartElement.value,
      traces,
      layout,
      chartConfig
    );

    if (benchmarkChartElement.value) {
      Plotly.Plots.resize(benchmarkChartElement.value);
    }
  } catch (error) {
    console.error("Benchmark chart rendering failed:", error);
    benchmarkChartRenderError.value =
      "The historical comparison chart could not be rendered. The comparison table remains available.";
  }
};

/* =========================================================
   REGIME CSS CLASS
========================================================= */

const updateRegimeClass = () => {
  if (
    !marketRegime.value
  ) {
    regimeClass.value =
      "";

    return;
  }

  if (
    marketRegime.value.trend ===
    "Bullish"
  ) {
    regimeClass.value =
      "regime-bullish";
  } else if (
    marketRegime.value.trend ===
    "Bearish"
  ) {
    regimeClass.value =
      "regime-bearish";
  } else {
    regimeClass.value =
      "regime-neutral";
  }
};

/* =========================================================
   PERFORMANCE CSS CLASS
========================================================= */

const performanceReturnClass =
  ref("");

const updatePerformanceReturnClass =
  () => {
    if (
      !performanceMetrics.value
    ) {
      performanceReturnClass.value =
        "";

      return;
    }

    if (
      performanceMetrics.value
        .totalReturn > 0
    ) {
      performanceReturnClass.value =
        "performance-positive";
    } else if (
      performanceMetrics.value
        .totalReturn < 0
    ) {
      performanceReturnClass.value =
        "performance-negative";
    } else {
      performanceReturnClass.value =
        "performance-neutral";
    }
  };

/* =========================================================
   FORMATTING
========================================================= */

const formatIndicator = (
  value
) => {
  if (
    value === null ||
    value === undefined ||
    Number.isNaN(value)
  ) {
    return "N/A";
  }

  return Number(
    value
  ).toFixed(2);
};

const formatPrice = (
  value
) => {
  if (
    value === null ||
    value === undefined ||
    Number.isNaN(value)
  ) {
    return "N/A";
  }

  return `$${Number(
    value
  ).toFixed(2)}`;
};

const formatPercentage = (
  value
) => {
  if (
    value === null ||
    value === undefined ||
    Number.isNaN(value)
  ) {
    return "N/A";
  }

  return `${Number(
    value
  ).toFixed(2)}%`;
};

const formatSignedPercentage = (
  value
) => {
  if (
    value === null ||
    value === undefined ||
    Number.isNaN(value)
  ) {
    return "N/A";
  }

  const number =
    Number(value);

  const sign =
    number > 0
      ? "+"
      : "";

  return `${sign}${number.toFixed(
    2
  )}%`;
};

const formatSignedPrice = (
  value
) => {
  if (
    value === null ||
    value === undefined ||
    Number.isNaN(value)
  ) {
    return "N/A";
  }

  const number =
    Number(value);

  const sign =
    number > 0
      ? "+"
      : "";

  return `${sign}$${number.toFixed(
    2
  )}`;
};

const formatCorrelation = (
  value
) => {
  if (
    value === null ||
    value === undefined ||
    Number.isNaN(value)
  ) {
    return "N/A";
  }

  return Number(
    value
  ).toFixed(2);
};

const returnValueClass = (
  value
) => {
  if (
    value === null ||
    value === undefined ||
    Number.isNaN(value)
  ) {
    return "";
  }

  if (value > 0) {
    return "positive-value";
  }

  if (value < 0) {
    return "negative-value";
  }

  return "neutral-value";
};

/* =========================================================
   LOAD DATA
========================================================= */

/* =========================================================
   STEP 16
   FUNDAMENTALS
========================================================= */

const loadFundamentals = async () => {
  try {
    fundamentalsLoading.value = true;
    fundamentalsError.value = "";
    latestFundamental.value = null;

    const response = await getFundamentals(
      props.symbol,
      fundamentalsPeriod.value
    );

    const data = Array.isArray(response)
      ? response
      : Array.isArray(response?.results)
        ? response.results
        : [];

    fundamentals.value = data;
    latestFundamental.value = data.length > 0 ? data[0] : null;
  } catch (err) {
    console.error("Fundamentals loading failed:", err);
    fundamentals.value = [];
    latestFundamental.value = null;
    fundamentalsError.value = "Unable to load fundamental data.";
  } finally {
    fundamentalsLoading.value = false;
  }
};

const changeFundamentalsPeriod = async (period) => {
  if (fundamentalsPeriod.value === period) return;
  fundamentalsPeriod.value = period;
  await loadFundamentals();
};

const formatFundamentalNumber = (value, decimals = 2) => {
  if (value === null || value === undefined || value === "") return "—";
  const number = Number(value);
  if (!Number.isFinite(number)) return "—";
  return number.toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
};

const formatFundamentalPercentage = (value) => {
  if (value === null || value === undefined || value === "") return "—";
  const number = Number(value);
  if (!Number.isFinite(number)) return "—";
  return `${(number * 100).toFixed(2)}%`;
};

const formatFundamentalCurrency = (value) => {
  if (value === null || value === undefined || value === "") return "—";
  const number = Number(value);
  if (!Number.isFinite(number)) return "—";
  return `$${number.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
};

const formatFundamentalDate = (value) => {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
};

/* =========================================================
   STEP 17.2
   RISK ANALYSIS
========================================================= */

const loadRiskMetrics = async (
  startDate,
  endDate
) => {
  try {
    riskLoading.value = true;
    riskError.value = "";
    riskMetrics.value = null;

    const response = await getRiskMetrics(
      props.symbol,
      startDate,
      endDate
    );

    if (
      !response ||
      !response.risk_metrics
    ) {
      throw new Error(
        "Invalid risk metrics response."
      );
    }

    riskMetrics.value =
      response.risk_metrics;

    riskPeriod.value = {
      startDate:
        response.start_date ||
        startDate,
      endDate:
        response.end_date ||
        endDate,
    };

    console.log(
      "Risk Metrics:",
      riskMetrics.value
    );
  } catch (err) {
    console.error(
      "Risk metrics loading failed:",
      err
    );

    riskMetrics.value = null;
    riskPeriod.value = {
      startDate: "",
      endDate: "",
    };

    riskError.value =
      "Unable to load risk metrics.";
  } finally {
    riskLoading.value = false;

    if (riskMetrics.value) {
      await nextTick();
      renderRiskVisualizations();
    }
  }
};

const toPercentageValue = (value) => {
  if (
    value === null ||
    value === undefined ||
    Number.isNaN(Number(value))
  ) {
    return null;
  }

  return Number(value) * 100;
};

const formatRiskPercentage = (value) => {
  if (
    value === null ||
    value === undefined ||
    value === "" ||
    Number.isNaN(Number(value))
  ) {
    return "N/A";
  }

  return `${(Number(value) * 100).toFixed(2)}%`;
};

const formatRiskRatio = (value) => {
  if (
    value === null ||
    value === undefined ||
    value === "" ||
    Number.isNaN(Number(value))
  ) {
    return "N/A";
  }

  return Number(value).toFixed(2);
};

const formatRiskCorrelation = (value) => {
  if (
    value === null ||
    value === undefined ||
    value === "" ||
    Number.isNaN(Number(value))
  ) {
    return "N/A";
  }

  return Number(value).toFixed(3);
};

const formatRiskObservations = (value) => {
  if (
    value === null ||
    value === undefined ||
    value === "" ||
    Number.isNaN(Number(value))
  ) {
    return "N/A";
  }

  return Number(value).toLocaleString("en-US");
};

const formatRiskDate = (value) => {
  if (!value) return "N/A";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
};

/* =========================================================
   STEP 17.3
   RISK VISUALISATION & INTERPRETATION
========================================================= */

const getRiskDailyReturns = () => {
  const result = [];

  for (let i = 1; i < prices.value.length; i++) {
    const previousClose = Number(
      prices.value[i - 1].close_price
    );

    const currentClose = Number(
      prices.value[i].close_price
    );

    if (
      Number.isFinite(previousClose) &&
      Number.isFinite(currentClose) &&
      previousClose > 0 &&
      currentClose > 0
    ) {
      result.push({
        date: prices.value[i].date,
        value: ((currentClose - previousClose) / previousClose) * 100,
      });
    }
  }

  return result;
};

const calculateDrawdownSeries = () => {
  let runningPeak = null;

  return prices.value
    .map((item) => ({
      date: item.date,
      close: Number(item.close_price),
    }))
    .filter(
      (item) =>
        Number.isFinite(item.close) &&
        item.close > 0
    )
    .map((item) => {
      if (runningPeak === null || item.close > runningPeak) {
        runningPeak = item.close;
      }

      return {
        date: item.date,
        drawdown: ((item.close - runningPeak) / runningPeak) * 100,
      };
    });
};

const updateRiskInterpretation = () => {
  if (!riskMetrics.value) {
    return;
  }

  const metrics = riskMetrics.value;
  const annualReturn = Number(metrics.annualised_return);
  const volatility = Number(metrics.annualised_volatility);
  const drawdown = Number(metrics.maximum_drawdown);
  const var95 = Number(metrics.var_95);
  const es95 = Number(metrics.expected_shortfall_95);
  const beta = Number(metrics.beta);
  const correlation = Number(metrics.benchmark_correlation);

  riskInterpretation.value = {
    returnVolatility:
      Number.isFinite(annualReturn) && Number.isFinite(volatility)
        ? `${props.symbol} recorded an annualised historical return of ${formatRiskPercentage(annualReturn)} alongside annualised volatility of ${formatRiskPercentage(volatility)} over the selected period.`
        : "Annualised return and volatility could not both be calculated for this period.",

    drawdown:
      Number.isFinite(drawdown)
        ? `The largest observed peak-to-trough decline was ${formatRiskPercentage(drawdown)}. The drawdown chart shows when the stock was below its previous running peak.`
        : "Maximum drawdown could not be calculated for this period.",

    tailRisk:
      Number.isFinite(var95) && Number.isFinite(es95)
        ? `The historical 95% VaR is ${formatRiskPercentage(var95)}, while Expected Shortfall is ${formatRiskPercentage(es95)}. Expected Shortfall describes the average return among observations at or below the VaR threshold.`
        : "Historical tail-loss measures are not available for this period.",

    benchmark:
      Number.isFinite(beta) && Number.isFinite(correlation)
        ? `Against the S&P 500, the measured beta is ${beta.toFixed(2)} and the daily-return correlation is ${correlation.toFixed(3)}.`
        : "Benchmark beta and correlation are not available for this period.",
  };
};

const renderRiskReturnChart = () => {
  if (!riskReturnChartElement.value || !riskMetrics.value) {
    return;
  }

  const points = [];

  const addPoint = (name, annualizedReturn, annualizedVolatility) => {
    const x = Number(annualizedVolatility);
    const y = Number(annualizedReturn);

    if (Number.isFinite(x) && Number.isFinite(y)) {
      points.push({
        name,
        x,
        y,
      });
    }
  };

  addPoint(
    props.symbol,
    Number(riskMetrics.value.annualised_return) * 100,
    Number(riskMetrics.value.annualised_volatility) * 100
  );

  if (benchmarkMetrics.value) {
    addPoint(
      benchmarkMetrics.value.primaryName || "Market benchmark",
      benchmarkMetrics.value.sp500?.annualizedReturn,
      benchmarkMetrics.value.sp500?.annualizedVolatility
    );

    addPoint(
      benchmarkMetrics.value.secondaryName || "Secondary benchmark",
      benchmarkMetrics.value.nasdaq100?.annualizedReturn,
      benchmarkMetrics.value.nasdaq100?.annualizedVolatility
    );

    addPoint(
      benchmarkMetrics.value.sectorName || "Sector ETF",
      benchmarkMetrics.value.sector?.annualizedReturn,
      benchmarkMetrics.value.sector?.annualizedVolatility
    );
  }

  const trace = {
    x: points.map((point) => point.x),
    y: points.map((point) => point.y),
    text: points.map((point) => point.name),
    type: "scatter",
    mode: "markers+text",
    textposition: "top center",
    hovertemplate:
      "%{text}<br>Volatility: %{x:.2f}%<br>Return: %{y:.2f}%<extra></extra>",
    marker: {
      size: 11,
      color: "#2563eb",
    },
    name: "Assets",
  };

  const layout = {
    height: 330,
    margin: {
      l: 60,
      r: 25,
      t: 20,
      b: 55,
    },
    paper_bgcolor: "white",
    plot_bgcolor: "white",
    showlegend: false,
    xaxis: {
      title: "Annualised Volatility (%)",
      showgrid: true,
      gridcolor: "#f3f4f6",
      zeroline: false,
    },
    yaxis: {
      title: "Annualised Return (%)",
      showgrid: true,
      gridcolor: "#f3f4f6",
      zeroline: true,
      zerolinecolor: "#d1d5db",
    },
  };

  const config = {
    responsive: true,
    displaylogo: false,
    modeBarButtonsToRemove: [
      "lasso2d",
      "select2d",
    ],
  };

  Plotly.react(
    riskReturnChartElement.value,
    [trace],
    layout,
    config
  );
};

const renderRiskDrawdownChart = () => {
  if (!riskDrawdownChartElement.value) {
    return;
  }

  const series = calculateDrawdownSeries();

  if (!series.length) {
    return;
  }

  const trace = {
    x: series.map((item) => item.date),
    y: series.map((item) => item.drawdown),
    type: "scatter",
    mode: "lines",
    name: "Drawdown",
    line: {
      width: 2,
      color: "#dc2626",
    },
    fill: "tozeroy",
    fillcolor: "rgba(220, 38, 38, 0.10)",
    hovertemplate:
      "%{x|%Y-%m-%d}<br>Drawdown: %{y:.2f}%<extra></extra>",
  };

  const maxDrawdown = Number(
    riskMetrics.value?.maximum_drawdown
  ) * 100;

  const shapes = [
    {
      type: "line",
      x0: series[0].date,
      x1: series[series.length - 1].date,
      y0: 0,
      y1: 0,
      line: {
        width: 1,
        color: "#9ca3af",
        dash: "dash",
      },
    },
  ];

  if (Number.isFinite(maxDrawdown)) {
    shapes.push({
      type: "line",
      x0: series[0].date,
      x1: series[series.length - 1].date,
      y0: maxDrawdown,
      y1: maxDrawdown,
      line: {
        width: 1,
        color: "#991b1b",
        dash: "dot",
      },
    });
  }

  const layout = {
    height: 330,
    margin: {
      l: 60,
      r: 25,
      t: 20,
      b: 55,
    },
    paper_bgcolor: "white",
    plot_bgcolor: "white",
    showlegend: false,
    shapes,
    xaxis: {
      type: "date",
      showgrid: true,
      gridcolor: "#f3f4f6",
    },
    yaxis: {
      title: "Drawdown (%)",
      showgrid: true,
      gridcolor: "#f3f4f6",
      ticksuffix: "%",
    },
  };

  const config = {
    responsive: true,
    displaylogo: false,
  };

  Plotly.react(
    riskDrawdownChartElement.value,
    [trace],
    layout,
    config
  );
};

const renderRiskDistributionChart = () => {
  if (!riskDistributionChartElement.value) {
    return;
  }

  const dailyReturns = getRiskDailyReturns();

  if (!dailyReturns.length) {
    return;
  }

  const values = dailyReturns.map((item) => item.value);
  const var95 = Number(riskMetrics.value?.var_95) * 100;
  const es95 = Number(riskMetrics.value?.expected_shortfall_95) * 100;

  const shapes = [
    {
      type: "line",
      x0: 0,
      x1: 0,
      y0: 0,
      y1: 1,
      yref: "paper",
      line: {
        color: "#6b7280",
        width: 1,
        dash: "dash",
      },
    },
  ];

  const annotations = [
    {
      x: 0,
      y: 1,
      yref: "paper",
      text: "0%",
      showarrow: false,
      yanchor: "bottom",
      font: { size: 10, color: "#6b7280" },
    },
  ];

  if (Number.isFinite(var95)) {
    shapes.push({
      type: "line",
      x0: var95,
      x1: var95,
      y0: 0,
      y1: 1,
      yref: "paper",
      line: {
        color: "#d97706",
        width: 2,
        dash: "dot",
      },
    });

    annotations.push({
      x: var95,
      y: 1,
      yref: "paper",
      text: `VaR 95% ${var95.toFixed(2)}%`,
      showarrow: false,
      yanchor: "bottom",
      font: { size: 10, color: "#92400e" },
    });
  }

  if (Number.isFinite(es95)) {
    shapes.push({
      type: "line",
      x0: es95,
      x1: es95,
      y0: 0,
      y1: 1,
      yref: "paper",
      line: {
        color: "#7f1d1d",
        width: 2,
        dash: "dashdot",
      },
    });

    annotations.push({
      x: es95,
      y: 0.88,
      yref: "paper",
      text: `ES 95% ${es95.toFixed(2)}%`,
      showarrow: false,
      yanchor: "bottom",
      font: { size: 10, color: "#7f1d1d" },
    });
  }

  const trace = {
    x: values,
    type: "histogram",
    nbinsx: Math.min(40, Math.max(12, Math.round(Math.sqrt(values.length)))),
    name: "Daily Returns",
    marker: {
      color: "#64748b",
      line: {
        color: "white",
        width: 0.5,
      },
    },
    hovertemplate:
      "Daily return: %{x:.2f}%<br>Days: %{y}<extra></extra>",
  };

  const layout = {
    height: 330,
    margin: {
      l: 60,
      r: 25,
      t: 20,
      b: 55,
    },
    paper_bgcolor: "white",
    plot_bgcolor: "white",
    showlegend: false,
    bargap: 0.04,
    shapes,
    annotations,
    xaxis: {
      title: "Daily Return (%)",
      showgrid: true,
      gridcolor: "#f3f4f6",
    },
    yaxis: {
      title: "Observations",
      showgrid: true,
      gridcolor: "#f3f4f6",
    },
  };

  const config = {
    responsive: true,
    displaylogo: false,
  };

  Plotly.react(
    riskDistributionChartElement.value,
    [trace],
    layout,
    config
  );
};

const renderRiskVisualizations = () => {
  if (!riskMetrics.value || !prices.value.length) {
    return;
  }

  updateRiskInterpretation();
  renderRiskReturnChart();
  renderRiskDrawdownChart();
  renderRiskDistributionChart();
};


const mlModelLabel = computed(() => {
  const selected = mlModels.find(
    (model) => model.value === mlModel.value
  );

  return selected?.label || mlModel.value;
});

const mlPredictionReturnPercentage = computed(() => {
  const value = Number(
    mlPrediction.value?.prediction?.return
  );

  return Number.isFinite(value)
    ? value * 100
    : null;
});

const formatMLPercentage = (value) => {
  if (
    value === null ||
    value === undefined ||
    value === "" ||
    Number.isNaN(Number(value))
  ) {
    return "N/A";
  }

  return `${(Number(value) * 100).toFixed(2)}%`;
};

const formatMLPrice = (value) => {
  if (
    value === null ||
    value === undefined ||
    value === "" ||
    Number.isNaN(Number(value))
  ) {
    return "N/A";
  }

  return `$${Number(value).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
};

const formatMLConfidence = (value) => {
  if (
    value === null ||
    value === undefined ||
    value === "" ||
    Number.isNaN(Number(value))
  ) {
    return "N/A";
  }

  return `${(Number(value) * 100).toFixed(0)}%`;
};

const formatMLObservations = (value) => {
  if (
    value === null ||
    value === undefined ||
    value === "" ||
    Number.isNaN(Number(value))
  ) {
    return "N/A";
  }

  return Number(value).toLocaleString("en-US");
};

const formatMLDate = (value) => {
  if (!value) {
    return "N/A";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
};

const mlHorizonLabel = computed(() => {
  const selected = mlHorizons.find(
    (horizon) => horizon.value === mlHorizon.value
  );

  return selected?.label || `${mlHorizon.value}D`;
});

const formatBacktestPercentage = (value) => {
  if (
    value === null ||
    value === undefined ||
    value === "" ||
    Number.isNaN(Number(value))
  ) {
    return "N/A";
  }

  return `${(Number(value) * 100).toFixed(2)}%`;
};

const formatBacktestNumber = (value) => {
  if (
    value === null ||
    value === undefined ||
    value === "" ||
    Number.isNaN(Number(value))
  ) {
    return "N/A";
  }

  if (!Number.isFinite(Number(value))) {
    return "N/A";
  }

  return Number(value).toFixed(2);
};

const formatBacktestObservations = (value) => {
  if (
    value === null ||
    value === undefined ||
    value === "" ||
    Number.isNaN(Number(value))
  ) {
    return "N/A";
  }

  return Number(value).toLocaleString("en-US");
};

const formatBacktestDate = (value) => {
  if (!value) {
    return "N/A";
  }

  const parsed = new Date(value);

  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return parsed.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
};

const backtestReturnClass = (value) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "";
  }

  return Number(value) >= 0
    ? "positive-value"
    : "negative-value";
};

const renderBacktestChart = (result) => {
  if (
    !backtestChartElement.value ||
    !result?.strategies
  ) {
    return;
  }

  const mlCurve = result.strategies.ml?.equity_curve;
  const buyHoldCurve = result.strategies.buy_and_hold?.equity_curve;
  const smaCurve = result.strategies.sma?.equity_curve;

  const traces = [];

  if (mlCurve?.dates?.length) {
    traces.push({
      x: mlCurve.dates,
      y: mlCurve.values,
      type: "scatter",
      mode: "lines",
      name: `ML Strategy - ${result.model_name}`,
      line: {
        width: 2.5,
        color: "#2563eb",
      },
    });
  }

  if (buyHoldCurve?.dates?.length) {
    traces.push({
      x: buyHoldCurve.dates,
      y: buyHoldCurve.values,
      type: "scatter",
      mode: "lines",
      name: "Buy & Hold",
      line: {
        width: 2,
        color: "#111827",
      },
    });
  }

  if (smaCurve?.dates?.length) {
    traces.push({
      x: smaCurve.dates,
      y: smaCurve.values,
      type: "scatter",
      mode: "lines",
      name: "SMA 200",
      line: {
        width: 2,
        color: "#f59e0b",
      },
    });
  }

  Plotly.react(
    backtestChartElement.value,
    traces,
    {
      title: {
        text: "Backtest Equity Curves",
        x: 0.02,
        xanchor: "left",
      },
      height: 420,
      margin: {
        l: 60,
        r: 30,
        t: 60,
        b: 50,
      },
      paper_bgcolor: "white",
      plot_bgcolor: "white",
      hovermode: "x unified",
      xaxis: {
        type: "date",
        showgrid: true,
        gridcolor: "#f3f4f6",
      },
      yaxis: {
        title: "Growth of 1.00",
        showgrid: true,
        gridcolor: "#f3f4f6",
      },
      legend: {
        orientation: "h",
        y: 1.08,
        x: 0,
      },
    },
    {
      responsive: true,
      displaylogo: false,
      modeBarButtonsToRemove: [
        "lasso2d",
        "select2d",
      ],
    }
  );
};

const formatResearchRequestError = (err, fallback, { minObservations = 0 } = {}) => {
  // DRF throttling and authentication often return "detail", not "error".
  const data = err?.response?.data || {};
  const status = err?.response?.status;
  const message = typeof data.error === "string" ? data.error
    : typeof data.detail === "string" ? data.detail
    : "";

  if (status === 429) {
    const wait = Number(data.wait);
    return Number.isFinite(wait) && wait > 0
      ? `Request limit reached. Retry after about ${Math.ceil(wait)} seconds. Forecasts are generated only when requested.`
      : "Request limit reached. Wait before retrying and avoid rapidly switching models.";
  }
  if (status === 401 || status === 403) {
    return "Your session is not authorized for this research request. Please sign in again.";
  }
  if (status === 400) {
    const count = Number(data.observations);
    const countText = Number.isFinite(count) && count >= 0 ? ` (${count} currently stored)` : "";
    if (minObservations && /historical observations/i.test(message)) {
      return `This stock needs at least ${minObservations} historical observations for this analysis${countText}. Try another stock or update its historical data in the restored test database.`;
    }
    return message || "The selected stock does not have enough usable data for this analysis.";
  }
  if (status === 404) {
    return message || "This stock was not found in the backend.";
  }
  if (status === 503) {
    return message || "The required market-data service is currently unavailable.";
  }
  if (status >= 500) {
    return `${fallback} The server returned an error. Check the Django terminal for diagnostic details.`;
  }
  if (!err?.response) {
    return "Unable to connect to the Django API. Confirm that the backend is running and try again.";
  }
  return message || (err?.message === "Invalid ML prediction response." ? err.message : fallback);
};

const loadBacktest = async () => {
  try {
    backtestLoading.value = true;
    backtestError.value = "";

    const response = await getBacktestResults(
      props.symbol,
      mlHorizon.value,
      mlModel.value,
      5,
      5,
      0
    );

    if (!response || !response.strategies) {
      throw new Error(
        "Invalid backtest response."
      );
    }

    backtestResult.value = response;

    await nextTick();
    renderBacktestChart(response);

    console.log(
      "Backtest Results:",
      response
    );
  } catch (err) {
    console.error(
      "Backtest loading failed:",
      err
    );

    backtestResult.value = null;
    backtestError.value = formatResearchRequestError(
      err,
      "Unable to run strategy backtest.",
      { minObservations: 1200 }
    );
  } finally {
    backtestLoading.value = false;
  }
};

const loadMLPrediction = async () => {
  try {
    mlLoading.value = true;
    mlError.value = "";

    const response = await getMLReturnPrediction(
      props.symbol,
      mlHorizon.value,
      mlModel.value,
      mlConfidence.value
    );

    if (!response || !response.prediction) {
      throw new Error(
        "Invalid ML prediction response."
      );
    }

    mlPrediction.value = response;

    console.log(
      "ML Prediction:",
      response
    );
  } catch (err) {
    console.error(
      "ML prediction loading failed:",
      err
    );

    mlPrediction.value = null;
    mlError.value = formatResearchRequestError(
      err,
      "Unable to generate ML return prediction.",
      { minObservations: 300 }
    );
  } finally {
    mlLoading.value = false;
  }
};

const changeMLModel = (model) => {
  if (mlModel.value === model) {
    return;
  }

  mlModel.value = model;
  backtestResult.value = null;
  backtestError.value = "";
  mlPrediction.value = null;
  mlError.value = "";
};

const changeMLHorizon = (horizon) => {
  if (mlHorizon.value === horizon) {
    return;
  }

  mlHorizon.value = horizon;
  backtestResult.value = null;
  backtestError.value = "";
  mlPrediction.value = null;
  mlError.value = "";
};

const loadPrices = async (includeML = false) => {
  try {
    loading.value =
      true;

    error.value = "";

    marketRegime.value =
      null;

    performanceMetrics.value =
      null;

    benchmarkMetrics.value =
      null;

    benchmarkError.value =
      "";

    fundamentals.value = [];
    latestFundamental.value = null;
    fundamentalsError.value = "";

    riskMetrics.value = null;
    riskError.value = "";
    riskPeriod.value = {
      startDate: "",
      endDate: "",
    };

    if (includeML) {
      mlPrediction.value = null;
      mlError.value = "";
      backtestResult.value = null;
      backtestError.value = "";
    }

    updateSelectedPeriodLabel();

    const startDate =
      getStartDate(
        selectedPeriod.value
      );

    const endDate =
      getEndDate();

    console.log(
      `Loading ${props.symbol} data:`,
      startDate,
      "to",
      endDate
    );

    const data =
      await getHistoricalPrices(
        props.stockId,
        startDate,
        endDate
      );

    console.log(
      "Historical API response:",
      data
    );

    console.log(
      "Number of records:",
      data.length
    );

    prices.value =
      Array.isArray(data)
        ? data
        : [];

    await nextTick();

    renderCharts();

    if (
      prices.value.length >
      1
    ) {
      const stockDates =
        prices.value.map(
          (item) =>
            item.date
        );

      const stockClose =
        prices.value.map(
          (item) =>
            Number(
              item.close_price
            )
        );

      await loadBenchmarkData(
        startDate,
        endDate,
        stockDates,
        stockClose
      );
    }

    await loadFundamentals();

    if (
      prices.value.length >
      1
    ) {
      await loadRiskMetrics(
        startDate,
        endDate
      );
    }

    // Don't automatically train ML models whenever a stock changes.
    // The user can explicitly generate a forecast from the ML panel.
  } catch (err) {
    console.error(
      "Failed to load historical prices:",
      err
    );

    error.value =
      "Unable to load historical market data.";

    marketRegime.value =
      null;

    performanceMetrics.value =
      null;

    benchmarkMetrics.value =
      null;

    riskMetrics.value = null;
    riskError.value =
      "Unable to load risk metrics.";
    riskPeriod.value = {
      startDate: "",
      endDate: "",
    };
  } finally {
    loading.value =
      false;
  }
};

/* =========================================================
   RENDER ALL CHARTS
========================================================= */

const renderCharts = () => {
  if (
    !prices.value.length
  ) {
    marketRegime.value =
      null;

    performanceMetrics.value =
      null;

    return;
  }

  if (
    !priceChartElement.value ||
    !volumeChartElement.value ||
    !rsiChartElement.value ||
    !macdChartElement.value ||
    !stochasticChartElement.value ||
    !atrChartElement.value ||
    !rocChartElement.value ||
    !obvChartElement.value ||
    !adxChartElement.value
  ) {
    return;
  }

  const dates =
    prices.value.map(
      (item) =>
        item.date
    );

  const open =
    prices.value.map(
      (item) =>
        Number(
          item.open_price
        )
    );

  const high =
    prices.value.map(
      (item) =>
        Number(
          item.high_price
        )
    );

  const low =
    prices.value.map(
      (item) =>
        Number(
          item.low_price
        )
    );

  const close =
    prices.value.map(
      (item) =>
        Number(
          item.close_price
        )
    );

  const volume =
    prices.value.map(
      (item) =>
        Number(
          item.volume
        )
    );

  /* =====================================================
     INDICATORS
  ====================================================== */

  const sma20 =
    calculateSMA(
      close,
      20
    );

  const sma50 =
    calculateSMA(
      close,
      50
    );

  const sma200 =
    calculateSMA(
      close,
      200
    );

  const bollinger =
    calculateBollingerBands(
      close,
      20,
      2
    );

  const rsi =
    calculateRSI(
      close,
      14
    );

  const macd =
    calculateMACD(
      close,
      12,
      26,
      9
    );

  const stochastic =
    calculateStochastic(
      high,
      low,
      close,
      14,
      3,
      3
    );

  const atr =
    calculateATR(
      high,
      low,
      close,
      14
    );

  const roc =
    calculateROC(
      close,
      12
    );

  const obv =
    calculateOBV(
      close,
      volume
    );

  const supportResistance =
    calculateSupportResistance(
      high,
      low,
      close,
      20
    );

  const adxData =
    calculateADX(
      high,
      low,
      close,
      14
    );

  const crossovers =
    calculateCrossovers(
      sma50,
      sma200
    );

  marketRegime.value =
    calculateMarketRegime({
      close,
      sma20,
      sma50,
      sma200,
      adx:
        adxData.adx,
      plusDI:
        adxData.plusDI,
      minusDI:
        adxData.minusDI,
    });

  updateRegimeClass();

  performanceMetrics.value =
    calculatePerformanceMetrics(
      dates,
      close
    );

  updatePerformanceReturnClass();

  const chartConfig = {
    responsive: true,
    displaylogo: false,
    scrollZoom: true,

    modeBarButtonsToRemove: [
      "lasso2d",
      "select2d",
    ],
  };

  /* =====================================================
     MAIN PRICE CHART
  ====================================================== */

  const priceTraces = [
    {
      x: dates,
      open,
      high,
      low,
      close,

      type: "candlestick",

      name:
        props.symbol,

      increasing: {
        line: {
          color:
            "#16a34a",
        },
      },

      decreasing: {
        line: {
          color:
            "#dc2626",
        },
      },
    },

    {
      x: dates,
      y: sma20,

      type: "scatter",

      mode: "lines",

      name:
        "SMA 20",

      line: {
        width: 1.5,
        color:
          "#2563eb",
      },

      connectgaps:
        false,
    },

    {
      x: dates,
      y: sma50,

      type: "scatter",

      mode: "lines",

      name:
        "SMA 50",

      line: {
        width: 1.7,
        color:
          "#f59e0b",
      },

      connectgaps:
        false,
    },

    {
      x: dates,
      y: sma200,

      type: "scatter",

      mode: "lines",

      name:
        "SMA 200",

      line: {
        width: 2,
        color:
          "#7c3aed",
      },

      connectgaps:
        false,
    },

    {
      x: dates,
      y:
        bollinger.upper,

      type: "scatter",

      mode: "lines",

      name:
        "Bollinger Upper",

      line: {
        width: 1,
        dash:
          "dot",
        color:
          "#6b7280",
      },

      connectgaps:
        false,
    },

    {
      x: dates,
      y:
        bollinger.middle,

      type: "scatter",

      mode: "lines",

      name:
        "Bollinger Middle",

      line: {
        width: 1,
        dash:
          "dash",
        color:
          "#9ca3af",
      },

      connectgaps:
        false,
    },

    {
      x: dates,
      y:
        bollinger.lower,

      type: "scatter",

      mode: "lines",

      name:
        "Bollinger Lower",

      line: {
        width: 1,
        dash:
          "dot",
        color:
          "#6b7280",
      },

      connectgaps:
        false,
    },
  ];

  /* =====================================================
     GOLDEN CROSS
  ====================================================== */

  if (
    crossovers.goldenCross
      .length > 0
  ) {
    priceTraces.push({
      x:
        crossovers.goldenCross.map(
          (index) =>
            dates[index]
        ),

      y:
        crossovers.goldenCross.map(
          (index) =>
            low[index]
        ),

      type: "scatter",

      mode: "markers",

      name:
        "Golden Cross",

      marker: {
        symbol:
          "triangle-up",

        size: 13,

        color:
          "#16a34a",

        line: {
          width: 1,
          color:
            "#ffffff",
        },
      },

      hovertemplate:
        "<b>Golden Cross</b><br>" +
        "Date: %{x}<br>" +
        "Price: %{y:.2f}" +
        "<extra></extra>",
    });
  }

  /* =====================================================
     DEATH CROSS
  ====================================================== */

  if (
    crossovers.deathCross
      .length > 0
  ) {
    priceTraces.push({
      x:
        crossovers.deathCross.map(
          (index) =>
            dates[index]
        ),

      y:
        crossovers.deathCross.map(
          (index) =>
            high[index]
        ),

      type: "scatter",

      mode: "markers",

      name:
        "Death Cross",

      marker: {
        symbol:
          "triangle-down",

        size: 13,

        color:
          "#dc2626",

        line: {
          width: 1,
          color:
            "#ffffff",
        },
      },

      hovertemplate:
        "<b>Death Cross</b><br>" +
        "Date: %{x}<br>" +
        "Price: %{y:.2f}" +
        "<extra></extra>",
    });
  }

  /* =====================================================
     SUPPORT
  ====================================================== */

  if (
    supportResistance
      .support.length > 0
  ) {
    priceTraces.push({
      x:
        supportResistance.support.map(
          (item) =>
            dates[
              item.index
            ]
        ),

      y:
        supportResistance.support.map(
          (item) =>
            item.price
        ),

      type: "scatter",

      mode: "markers",

      name:
        "Support",

      marker: {
        symbol:
          "triangle-up",

        size: 9,

        color:
          "#059669",
      },

      hovertemplate:
        "<b>Support</b><br>" +
        "Date: %{x}<br>" +
        "Price: %{y:.2f}" +
        "<extra></extra>",
    });
  }

  /* =====================================================
     RESISTANCE
  ====================================================== */

  if (
    supportResistance
      .resistance.length >
    0
  ) {
    priceTraces.push({
      x:
        supportResistance.resistance.map(
          (item) =>
            dates[
              item.index
            ]
        ),

      y:
        supportResistance.resistance.map(
          (item) =>
            item.price
        ),

      type: "scatter",

      mode: "markers",

      name:
        "Resistance",

      marker: {
        symbol:
          "triangle-down",

        size: 9,

        color:
          "#dc2626",
      },

      hovertemplate:
        "<b>Resistance</b><br>" +
        "Date: %{x}<br>" +
        "Price: %{y:.2f}" +
        "<extra></extra>",
    });
  }

  /* =====================================================
     PRICE LAYOUT
  ====================================================== */

  const priceLayout = {
    title: {
      text:
        `${props.symbol} Price`,

      x: 0.02,

      xanchor:
        "left",
    },

    height: 500,

    margin: {
      l: 60,
      r: 30,
      t: 60,
      b: 50,
    },

    paper_bgcolor:
      "white",

    plot_bgcolor:
      "white",

    hovermode:
      "x unified",

    xaxis: {
      rangeslider: {
        visible:
          false,
      },

      type:
        "date",

      showgrid:
        true,

      gridcolor:
        "#f3f4f6",
    },

    yaxis: {
      title:
        "Price",

      showgrid:
        true,

      gridcolor:
        "#f3f4f6",
    },

    legend: {
      orientation:
        "h",

      y: 1.08,

      x: 0,
    },
  };

  Plotly.react(
    priceChartElement.value,
    priceTraces,
    priceLayout,
    chartConfig
  );

  /* =====================================================
     VOLUME
  ====================================================== */

  const volumeTrace = {
    x: dates,
    y: volume,

    type: "bar",

    name:
      "Volume",

    marker: {
      color:
        "#64748b",
    },
  };

  const volumeLayout = {
    title: {
      text:
        "Volume",

      x: 0.02,

      xanchor:
        "left",
    },

    height: 220,

    margin: {
      l: 60,
      r: 30,
      t: 50,
      b: 50,
    },

    paper_bgcolor:
      "white",

    plot_bgcolor:
      "white",

    xaxis: {
      type:
        "date",

      showgrid:
        true,

      gridcolor:
        "#f3f4f6",
    },

    yaxis: {
      title:
        "Volume",

      showgrid:
        true,

      gridcolor:
        "#f3f4f6",
    },
  };

  Plotly.react(
    volumeChartElement.value,
    [volumeTrace],
    volumeLayout,
    chartConfig
  );

  /* =====================================================
     RSI
  ====================================================== */

  const rsiTrace = {
    x: dates,
    y: rsi,

    type: "scatter",

    mode: "lines",

    name:
      "RSI",

    line: {
      width: 2,
      color:
        "#2563eb",
    },

    connectgaps:
      false,
  };

  const rsiOverbought = {
    x: dates,

    y: dates.map(
      () => 70
    ),

    type: "scatter",

    mode: "lines",

    name:
      "Overbought 70",

    line: {
      dash:
        "dash",

      width: 1,

      color:
        "#dc2626",
    },
  };

  const rsiOversold = {
    x: dates,

    y: dates.map(
      () => 30
    ),

    type: "scatter",

    mode: "lines",

    name:
      "Oversold 30",

    line: {
      dash:
        "dash",

      width: 1,

      color:
        "#16a34a",
    },
  };

  const rsiLayout = {
    title: {
      text:
        "RSI (14)",

      x: 0.02,

      xanchor:
        "left",
    },

    height: 260,

    margin: {
      l: 60,
      r: 30,
      t: 50,
      b: 50,
    },

    paper_bgcolor:
      "white",

    plot_bgcolor:
      "white",

    xaxis: {
      type:
        "date",

      showgrid:
        true,

      gridcolor:
        "#f3f4f6",
    },

    yaxis: {
      title:
        "RSI",

      range:
        [0, 100],

      showgrid:
        true,

      gridcolor:
        "#f3f4f6",
    },
  };

  Plotly.react(
    rsiChartElement.value,
    [
      rsiTrace,
      rsiOverbought,
      rsiOversold,
    ],
    rsiLayout,
    chartConfig
  );

  /* =====================================================
     MACD
  ====================================================== */

  const macdTrace = {
    x: dates,
    y:
      macd.macd,

    type: "scatter",

    mode: "lines",

    name:
      "MACD",

    line: {
      width: 2,
      color:
        "#2563eb",
    },

    connectgaps:
      false,
  };

  const signalTrace = {
    x: dates,
    y:
      macd.signal,

    type: "scatter",

    mode: "lines",

    name:
      "Signal",

    line: {
      width: 2,
      color:
        "#f59e0b",
    },

    connectgaps:
      false,
  };

  const histogramTrace = {
    x: dates,
    y:
      macd.histogram,

    type: "bar",

    name:
      "Histogram",

    marker: {
      color:
        "#94a3b8",
    },
  };

  const macdLayout = {
    title: {
      text:
        "MACD (12, 26, 9)",

      x: 0.02,

      xanchor:
        "left",
    },

    height: 280,

    margin: {
      l: 60,
      r: 30,
      t: 50,
      b: 50,
    },

    paper_bgcolor:
      "white",

    plot_bgcolor:
      "white",

    xaxis: {
      type:
        "date",

      showgrid:
        true,

      gridcolor:
        "#f3f4f6",
    },

    yaxis: {
      title:
        "MACD",

      showgrid:
        true,

      gridcolor:
        "#f3f4f6",
    },

    legend: {
      orientation:
        "h",
    },
  };

  Plotly.react(
    macdChartElement.value,
    [
      histogramTrace,
      macdTrace,
      signalTrace,
    ],
    macdLayout,
    chartConfig
  );

  /* =====================================================
     STOCHASTIC
  ====================================================== */

  const stochasticKTrace = {
    x: dates,
    y:
      stochastic.k,

    type: "scatter",

    mode: "lines",

    name:
      "%K",

    line: {
      width: 2,
      color:
        "#2563eb",
    },

    connectgaps:
      false,
  };

  const stochasticDTrace = {
    x: dates,
    y:
      stochastic.d,

    type: "scatter",

    mode: "lines",

    name:
      "%D",

    line: {
      width: 2,
      color:
        "#f59e0b",
    },

    connectgaps:
      false,
  };

  const stochastic80 = {
    x: dates,

    y: dates.map(
      () => 80
    ),

    type: "scatter",

    mode: "lines",

    name:
      "Overbought 80",

    line: {
      dash:
        "dash",

      width: 1,

      color:
        "#dc2626",
    },
  };

  const stochastic20 = {
    x: dates,

    y: dates.map(
      () => 20
    ),

    type: "scatter",

    mode: "lines",

    name:
      "Oversold 20",

    line: {
      dash:
        "dash",

      width: 1,

      color:
        "#16a34a",
    },
  };

  const stochasticLayout = {
    title: {
      text:
        "Stochastic Oscillator (14, 3, 3)",

      x: 0.02,

      xanchor:
        "left",
    },

    height: 280,

    margin: {
      l: 60,
      r: 30,
      t: 50,
      b: 50,
    },

    paper_bgcolor:
      "white",

    plot_bgcolor:
      "white",

    xaxis: {
      type:
        "date",

      showgrid:
        true,

      gridcolor:
        "#f3f4f6",
    },

    yaxis: {
      title:
        "Stochastic",

      range:
        [0, 100],

      showgrid:
        true,

      gridcolor:
        "#f3f4f6",
    },

    legend: {
      orientation:
        "h",
    },
  };

  Plotly.react(
    stochasticChartElement.value,
    [
      stochasticKTrace,
      stochasticDTrace,
      stochastic80,
      stochastic20,
    ],
    stochasticLayout,
    chartConfig
  );

  /* =====================================================
     ATR
  ====================================================== */

  const atrTrace = {
    x: dates,
    y: atr,

    type: "scatter",

    mode: "lines",

    name:
      "ATR",

    line: {
      width: 2,
      color:
        "#7c3aed",
    },

    connectgaps:
      false,
  };

  const atrLayout = {
    title: {
      text:
        "Average True Range (14)",

      x: 0.02,

      xanchor:
        "left",
    },

    height: 280,

    margin: {
      l: 60,
      r: 30,
      t: 50,
      b: 50,
    },

    paper_bgcolor:
      "white",

    plot_bgcolor:
      "white",

    xaxis: {
      type:
        "date",

      showgrid:
        true,

      gridcolor:
        "#f3f4f6",
    },

    yaxis: {
      title:
        "ATR",

      showgrid:
        true,

      gridcolor:
        "#f3f4f6",
    },
  };

  Plotly.react(
    atrChartElement.value,
    [atrTrace],
    atrLayout,
    chartConfig
  );

  /* =====================================================
     ROC
  ====================================================== */

  const rocTrace = {
    x: dates,
    y: roc,

    type: "scatter",

    mode: "lines",

    name:
      "ROC",

    line: {
      width: 2,
      color:
        "#0891b2",
    },

    connectgaps:
      false,
  };

  const rocZero = {
    x: dates,

    y: dates.map(
      () => 0
    ),

    type: "scatter",

    mode: "lines",

    name:
      "Zero",

    line: {
      dash:
        "dash",

      width: 1,

      color:
        "#6b7280",
    },
  };

  const rocLayout = {
    title: {
      text:
        "Rate of Change (12)",

      x: 0.02,

      xanchor:
        "left",
    },

    height: 280,

    margin: {
      l: 60,
      r: 30,
      t: 50,
      b: 50,
    },

    paper_bgcolor:
      "white",

    plot_bgcolor:
      "white",

    xaxis: {
      type:
        "date",

      showgrid:
        true,

      gridcolor:
        "#f3f4f6",
    },

    yaxis: {
      title:
        "ROC %",

      showgrid:
        true,

      gridcolor:
        "#f3f4f6",
    },

    legend: {
      orientation:
        "h",
    },
  };

  Plotly.react(
    rocChartElement.value,
    [
      rocTrace,
      rocZero,
    ],
    rocLayout,
    chartConfig
  );

  /* =====================================================
     OBV
  ====================================================== */

  const obvTrace = {
    x: dates,
    y: obv,

    type: "scatter",

    mode: "lines",

    name:
      "OBV",

    line: {
      width: 2,
      color:
        "#059669",
    },
  };

  const obvLayout = {
    title: {
      text:
        "On-Balance Volume (OBV)",

      x: 0.02,

      xanchor:
        "left",
    },

    height: 280,

    margin: {
      l: 60,
      r: 30,
      t: 50,
      b: 50,
    },

    paper_bgcolor:
      "white",

    plot_bgcolor:
      "white",

    xaxis: {
      type:
        "date",

      showgrid:
        true,

      gridcolor:
        "#f3f4f6",
    },

    yaxis: {
      title:
        "OBV",

      showgrid:
        true,

      gridcolor:
        "#f3f4f6",
    },
  };

  Plotly.react(
    obvChartElement.value,
    [obvTrace],
    obvLayout,
    chartConfig
  );

  /* =====================================================
     ADX + DI
  ====================================================== */

  const adxTrace = {
    x: dates,
    y:
      adxData.adx,

    type: "scatter",

    mode: "lines",

    name:
      "ADX",

    line: {
      width: 2,
      color:
        "#7c3aed",
    },

    connectgaps:
      false,
  };

  const plusDITrace = {
    x: dates,
    y:
      adxData.plusDI,

    type: "scatter",

    mode: "lines",

    name:
      "+DI",

    line: {
      width: 2,
      color:
        "#16a34a",
    },

    connectgaps:
      false,
  };

  const minusDITrace = {
    x: dates,
    y:
      adxData.minusDI,

    type: "scatter",

    mode: "lines",

    name:
      "-DI",

    line: {
      width: 2,
      color:
        "#dc2626",
    },

    connectgaps:
      false,
  };

  const adx25 = {
    x: dates,

    y: dates.map(
      () => 25
    ),

    type: "scatter",

    mode: "lines",

    name:
      "ADX 25",

    line: {
      dash:
        "dash",

      width: 1,

      color:
        "#6b7280",
    },
  };

  const adxLayout = {
    title: {
      text:
        "ADX & Directional Indicators (14)",

      x: 0.02,

      xanchor:
        "left",
    },

    height: 300,

    margin: {
      l: 60,
      r: 30,
      t: 50,
      b: 50,
    },

    paper_bgcolor:
      "white",

    plot_bgcolor:
      "white",

    xaxis: {
      type:
        "date",

      showgrid:
        true,

      gridcolor:
        "#f3f4f6",
    },

    yaxis: {
      title:
        "ADX / DI",

      showgrid:
        true,

      gridcolor:
        "#f3f4f6",
    },

    legend: {
      orientation:
        "h",
    },
  };

  Plotly.react(
    adxChartElement.value,
    [
      adxTrace,
      plusDITrace,
      minusDITrace,
      adx25,
    ],
    adxLayout,
    chartConfig
  );
};

/* =========================================================
   PERIOD CHANGE
========================================================= */

const changePeriod = (
  period
) => {
  if (
    selectedPeriod.value ===
    period
  ) {
    return;
  }

  selectedPeriod.value =
    period;
};

/* =========================================================
   WATCHERS
========================================================= */

watch(
  selectedPeriod,
  () => {
    loadPrices(false);
  }
);

watch(
  () => props.stockId,
  () => {
    loadPrices(true);
  }
);

/* =========================================================
   MOUNT
========================================================= */

onMounted(() => {
  updateSelectedPeriodLabel();

  loadPrices(true);
});

/* =========================================================
   CLEANUP
========================================================= */

onBeforeUnmount(() => {
  const charts = [
    priceChartElement.value,
    volumeChartElement.value,
    rsiChartElement.value,
    macdChartElement.value,
    stochasticChartElement.value,
    atrChartElement.value,
    rocChartElement.value,
    obvChartElement.value,
    adxChartElement.value,
    benchmarkChartElement.value,
    backtestChartElement.value,
    riskReturnChartElement.value,
    riskDrawdownChartElement.value,
    riskDistributionChartElement.value,
  ];

  charts.forEach(
    (chart) => {
      if (chart) {
        try {
          Plotly.purge(
            chart
          );
        } catch (err) {
          console.warn(
            "Chart cleanup failed:",
            err
          );
        }
      }
    }
  );
});
</script>

<style scoped>
.ml-evidence-box {
  margin: 16px 0;
  padding: 14px 17px;
  border: 1px solid #b9c9ec;
  border-radius: 12px;
  background: #f7faff;
  color: #1e365a;
  font-size: 13px;
  line-height: 1.6;
}
.ml-evidence-warning { border-color: #f1c29b; background: #fff9f0; color: #734818; }
.ml-evidence-box p { margin: 8px 0 0; }
.ml-evidence-box ul { margin: 9px 0 0; padding-left: 20px; }

.chart-card {
  margin-top: 30px;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  overflow: hidden;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
  padding: 22px;
  border-bottom: 1px solid #e5e7eb;
}

.chart-header h2 {
  margin: 0;
  font-size: 20px;
}

.chart-header p {
  margin: 6px 0 0;
  color: #6b7280;
  font-size: 14px;
  line-height: 1.5;
}

.period-buttons {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.period-buttons button {
  border: 1px solid #d1d5db;
  background: white;
  color: #374151;
  padding: 7px 11px;
  border-radius: 7px;
  cursor: pointer;
  font-size: 13px;
}

.period-buttons button:hover {
  background: #f3f4f6;
}

.period-buttons button.active {
  background: #111827;
  color: white;
  border-color: #111827;
}

/* =========================================================
   STEP 13 - REGIME PANEL
========================================================= */

.regime-panel {
  margin: 18px 22px 0;
  padding: 18px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #f9fafb;
}

.regime-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 16px;
}

.regime-title {
  display: block;
  font-size: 16px;
  font-weight: 700;
  color: #111827;
}

.regime-subtitle {
  display: block;
  margin-top: 4px;
  color: #6b7280;
  font-size: 13px;
}

.regime-badge {
  padding: 7px 12px;
  border-radius: 7px;
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
}

.regime-bullish {
  background: #ecfdf5;
  color: #047857;
  border: 1px solid #a7f3d0;
}

.regime-bearish {
  background: #fef2f2;
  color: #b91c1c;
  border: 1px solid #fecaca;
}

.regime-neutral {
  background: #f3f4f6;
  color: #374151;
  border: 1px solid #d1d5db;
}

.regime-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.regime-item {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 12px;
}

.regime-label {
  display: block;
  color: #6b7280;
  font-size: 12px;
  margin-bottom: 5px;
}

.regime-item strong {
  display: block;
  color: #111827;
  font-size: 14px;
}

.regime-description {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid #e5e7eb;
  color: #4b5563;
  font-size: 13px;
  line-height: 1.5;
}

/* =========================================================
   STEP 14 - PERFORMANCE PANEL
========================================================= */

.performance-panel {
  margin: 18px 22px 0;
  padding: 18px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #f9fafb;
}

.performance-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 16px;
}

.performance-title {
  display: block;
  font-size: 16px;
  font-weight: 700;
  color: #111827;
}

.performance-subtitle {
  display: block;
  margin-top: 4px;
  color: #6b7280;
  font-size: 13px;
}

.performance-return {
  padding: 7px 12px;
  border-radius: 7px;
  font-size: 14px;
  font-weight: 700;
  white-space: nowrap;
}

.performance-positive {
  background: #ecfdf5;
  color: #047857;
  border: 1px solid #a7f3d0;
}

.performance-negative {
  background: #fef2f2;
  color: #b91c1c;
  border: 1px solid #fecaca;
}

.performance-neutral {
  background: #f3f4f6;
  color: #374151;
  border: 1px solid #d1d5db;
}

.performance-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.performance-item {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 12px;
}

.performance-label {
  display: block;
  color: #6b7280;
  font-size: 12px;
  margin-bottom: 5px;
}

.performance-item strong {
  display: block;
  color: #111827;
  font-size: 14px;
}

.positive-value {
  color: #047857 !important;
}

.negative-value {
  color: #b91c1c !important;
}

.neutral-value {
  color: #374151 !important;
}

.performance-description {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid #e5e7eb;
  color: #4b5563;
  font-size: 13px;
  line-height: 1.5;
}

/* =========================================================
   STEP 15 - BENCHMARK PANEL
========================================================= */

.benchmark-panel {
  margin: 18px 22px 0;
  padding: 16px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #f9fafb;
}

.benchmark-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 16px;
}

.benchmark-title {
  display: block;
  font-size: 16px;
  font-weight: 700;
  color: #111827;
}

.benchmark-subtitle {
  display: block;
  margin-top: 4px;
  color: #6b7280;
  font-size: 13px;
}

.benchmark-loading {
  padding: 20px;
  text-align: center;
  color: #6b7280;
}

.benchmark-error {
  padding: 14px;
  border-radius: 8px;
  background: #fef2f2;
  color: #b91c1c;
  border: 1px solid #fecaca;
}

.benchmark-table-wrapper {
  width: 100%;
  overflow-x: auto;
}

.benchmark-table {
  width: 100%;
  border-collapse: collapse;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
}

.benchmark-table th,
.benchmark-table td {
  padding: 12px 14px;
  border-bottom: 1px solid #e5e7eb;
  text-align: right;
  font-size: 13px;
  white-space: nowrap;
}

.benchmark-table th:first-child,
.benchmark-table td:first-child {
  text-align: left;
}

.benchmark-table th {
  background: #f3f4f6;
  color: #374151;
  font-weight: 700;
}

.benchmark-table td {
  color: #111827;
}

.benchmark-table tr:last-child td {
  border-bottom: none;
}

.benchmark-chart {
  display: block;
  width: 100%;
  min-width: 0;
  height: 250px;
  min-height: 220px;
  margin-top: 8px;
}

.benchmark-chart-empty {
  margin: 8px 0 0;
  padding: 12px 14px;
  border: 1px dashed #d1d5db;
  border-radius: 8px;
  background: #ffffff;
  color: #6b7280;
  font-size: 12px;
  line-height: 1.5;
}

.benchmark-description {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid #e5e7eb;
  color: #4b5563;
  font-size: 13px;
  line-height: 1.5;
}

/* =========================================================
   STEP 16 - FUNDAMENTALS PANEL
========================================================= */

.fundamentals-panel {
  margin: 18px 22px 0;
  padding: 18px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #f9fafb;
}

.fundamentals-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 16px;
}

.fundamentals-title { display: block; font-size: 16px; font-weight: 700; color: #111827; }
.fundamentals-subtitle { display: block; margin-top: 4px; color: #6b7280; font-size: 13px; }
.fundamentals-period-buttons { display: flex; gap: 6px; }
.fundamentals-period-buttons button { border: 1px solid #d1d5db; background: white; color: #374151; padding: 7px 12px; border-radius: 7px; cursor: pointer; font-size: 13px; }
.fundamentals-period-buttons button:hover { background: #f3f4f6; }
.fundamentals-period-buttons button.active { background: #111827; color: white; border-color: #111827; }
.fundamentals-period { margin-bottom: 14px; color: #6b7280; font-size: 13px; }
.fundamentals-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.fundamental-item { background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 14px; }
.fundamental-item span { display: block; color: #6b7280; font-size: 12px; margin-bottom: 6px; }
.fundamental-item strong { display: block; color: #111827; font-size: 15px; }
.fundamentals-loading { padding: 20px; text-align: center; color: #6b7280; }
.fundamentals-empty { padding: 20px; text-align: center; color: #6b7280; }
.fundamentals-error { padding: 14px; border-radius: 8px; background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; }

/* =========================================================
   STEP 17.2 - RISK ANALYSIS PANEL
========================================================= */

.risk-panel {
  margin: 18px 22px 0;
  padding: 18px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #f9fafb;
}

.risk-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 16px;
}

.risk-title {
  display: block;
  font-size: 16px;
  font-weight: 700;
  color: #111827;
}

.risk-subtitle {
  display: block;
  margin-top: 4px;
  color: #6b7280;
  font-size: 13px;
}

.risk-benchmark-badge {
  padding: 7px 11px;
  border-radius: 7px;
  border: 1px solid #dbeafe;
  background: #eff6ff;
  color: #1d4ed8;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
}

.risk-period {
  margin-bottom: 14px;
  color: #6b7280;
  font-size: 13px;
  line-height: 1.5;
}

.risk-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.risk-item {
  display: flex;
  min-height: 136px;
  flex-direction: column;
  justify-content: flex-start;
  gap: 0;
  padding: 14px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: white;
}

.risk-label {
  display: block;
  color: #6b7280;
  font-size: 12px;
  line-height: 1.35;
  margin-bottom: 7px;
}

.risk-item strong {
  display: block;
  color: #111827;
  font-size: 18px;
  line-height: 1.2;
}

.risk-help {
  display: block;
  margin-top: 9px;
  color: #6b7280;
  font-size: 11px;
  line-height: 1.45;
}

.risk-loading,
.risk-empty {
  padding: 20px;
  text-align: center;
  color: #6b7280;
}

.risk-error {
  padding: 14px;
  border-radius: 8px;
  background: #fef2f2;
  color: #b91c1c;
  border: 1px solid #fecaca;
}

.risk-note {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid #e5e7eb;
  color: #6b7280;
  font-size: 12px;
  line-height: 1.55;
}

/* =========================================================
   STEP 17.3 - RISK VISUALISATION & INTERPRETATION
========================================================= */

.risk-visual-section {
  margin-top: 18px;
  padding-top: 18px;
  border-top: 1px solid #e5e7eb;
}

.risk-section-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 14px;
}

.risk-section-title {
  display: block;
  color: #111827;
  font-size: 15px;
  font-weight: 700;
}

.risk-section-subtitle {
  display: block;
  margin-top: 4px;
  color: #6b7280;
  font-size: 12px;
  line-height: 1.45;
}

.risk-visual-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.risk-visual-card {
  min-width: 0;
  border: 1px solid #e5e7eb;
  border-radius: 9px;
  background: white;
  overflow: hidden;
}

.risk-distribution-card {
  grid-column: 1 / -1;
}

.risk-visual-card-header {
  padding: 14px 14px 0;
}

.risk-visual-card-title {
  display: block;
  color: #111827;
  font-size: 13px;
  font-weight: 700;
}

.risk-visual-card-subtitle {
  display: block;
  margin-top: 4px;
  color: #6b7280;
  font-size: 11px;
  line-height: 1.4;
}

.risk-return-chart,
.risk-drawdown-chart,
.risk-distribution-chart {
  width: 100%;
  height: 330px;
}

.risk-interpretation-panel {
  margin-top: 18px;
  padding-top: 18px;
  border-top: 1px solid #e5e7eb;
}

.risk-interpretation-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.risk-interpretation-item {
  padding: 14px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: white;
}

.risk-interpretation-label {
  display: block;
  margin-bottom: 7px;
  color: #374151;
  font-size: 12px;
  font-weight: 700;
}

.risk-interpretation-item p {
  margin: 0;
  color: #6b7280;
  font-size: 12px;
  line-height: 1.55;
}

.risk-interpretation-note {
  margin-top: 12px;
  padding: 12px 14px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #f9fafb;
  color: #6b7280;
  font-size: 11px;
  line-height: 1.55;
}

/* =========================================================
   CHARTS
========================================================= */

.chart-container {
  width: 100%;
  padding: 10px;
  background: white;
}

.price-chart {
  width: 100%;
  height: 500px;
}

.volume-chart {
  width: 100%;
  height: 220px;
}

.rsi-chart {
  width: 100%;
  height: 260px;
}

.macd-chart {
  width: 100%;
  height: 280px;
}

.stochastic-chart {
  width: 100%;
  height: 280px;
}

.atr-chart {
  width: 100%;
  height: 280px;
}

.roc-chart {
  width: 100%;
  height: 280px;
}

.obv-chart {
  width: 100%;
  height: 280px;
}

.adx-chart {
  width: 100%;
  height: 300px;
}

.chart-message {
  padding: 20px;
  text-align: center;
  color: #6b7280;
}

.chart-message.error {
  color: #b91c1c;
  background: #fef2f2;
}

/* =========================================================
   RESPONSIVE
========================================================= */

@media (max-width: 1100px) {
  .regime-grid,
  .performance-grid,
  .fundamentals-grid,
  .risk-grid {
    grid-template-columns: repeat(
      2,
      1fr
    );
  }
}

@media (max-width: 800px) {
  .chart-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .regime-header,
  .performance-header,
  .benchmark-header,
  .fundamentals-header,
  .risk-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .regime-grid,
  .performance-grid,
  .fundamentals-grid,
  .risk-grid {
    grid-template-columns: 1fr;
  }

  .fundamentals-period-buttons {
    width: 100%;
  }

  .fundamentals-period-buttons button {
    flex: 1;
  }

  .price-chart {
    height: 400px;
  }

  .volume-chart {
    height: 180px;
  }

  .rsi-chart {
    height: 220px;
  }

  .macd-chart {
    height: 240px;
  }

  .stochastic-chart {
    height: 240px;
  }

  .atr-chart {
    height: 240px;
  }

  .roc-chart {
    height: 240px;
  }

  .obv-chart {
    height: 240px;
  }

  .adx-chart {
    height: 260px;
  }

  .benchmark-chart {
    height: 240px;
    min-height: 220px;
  }

  .risk-visual-grid,
  .risk-interpretation-grid {
    grid-template-columns: 1fr;
  }

  .risk-distribution-card {
    grid-column: auto;
  }

  .risk-return-chart,
  .risk-drawdown-chart,
  .risk-distribution-chart {
    height: 300px;
  }

  .benchmark-table th,
  .benchmark-table td {
    padding: 9px 10px;
    font-size: 12px;
  }
}


/* =========================================================
   STEP 19.3 - BACKTEST VISUALISATION
========================================================= */

.backtest-panel {
  margin: 18px 22px 0;
  padding: 18px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #f9fafb;
}

.backtest-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 14px;
}

.backtest-title {
  display: block;
  font-size: 16px;
  font-weight: 700;
  color: #111827;
}

.backtest-subtitle {
  display: block;
  margin-top: 4px;
  color: #6b7280;
  font-size: 13px;
  line-height: 1.45;
}

.backtest-run-button {
  border: 1px solid #111827;
  background: #111827;
  color: white;
  padding: 8px 14px;
  border-radius: 7px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
}

.backtest-run-button:hover:not(:disabled) {
  background: #374151;
}

.backtest-run-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.backtest-configuration {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
  padding: 10px 12px;
  margin-bottom: 14px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: white;
  color: #6b7280;
  font-size: 11px;
}

.backtest-configuration strong {
  color: #111827;
}

.backtest-period {
  margin-bottom: 14px;
  color: #6b7280;
  font-size: 12px;
}

.backtest-table-wrapper {
  width: 100%;
  overflow-x: auto;
}

.backtest-table {
  width: 100%;
  min-width: 720px;
  border-collapse: collapse;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
}

.backtest-table th,
.backtest-table td {
  padding: 10px 12px;
  border-bottom: 1px solid #e5e7eb;
  text-align: right;
  font-size: 12px;
}

.backtest-table th:first-child,
.backtest-table td:first-child {
  text-align: left;
}

.backtest-table th {
  background: #f3f4f6;
  color: #374151;
  font-weight: 700;
}

.backtest-table td {
  color: #111827;
}

.backtest-table tbody tr:last-child td {
  border-bottom: none;
}

.backtest-chart {
  width: 100%;
  height: 420px;
  margin-top: 16px;
}

.backtest-notes {
  margin-top: 14px;
  padding: 12px 14px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: white;
  color: #6b7280;
  font-size: 11px;
  line-height: 1.6;
}

.backtest-loading,
.backtest-empty {
  padding: 20px;
  text-align: center;
  color: #6b7280;
}

.backtest-error {
  padding: 14px;
  border-radius: 8px;
  background: #fef2f2;
  color: #b91c1c;
  border: 1px solid #fecaca;
}

/* =========================================================
   STEP 18.7 - ML RETURN PREDICTION DASHBOARD
========================================================= */

.ml-prediction-panel {
  margin: 18px 22px 0;
  padding: 18px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #f9fafb;
}

.ml-prediction-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 16px;
}

.ml-prediction-title {
  display: block;
  font-size: 16px;
  font-weight: 700;
  color: #111827;
}

.ml-prediction-subtitle {
  display: block;
  margin-top: 4px;
  color: #6b7280;
  font-size: 13px;
  line-height: 1.45;
}

.ml-prediction-controls {
  display: flex;
  flex-direction: column;
  gap: 10px;
  align-items: flex-end;
}

.ml-control-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ml-control-label {
  color: #6b7280;
  font-size: 12px;
  font-weight: 600;
}

.ml-control-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.ml-control-buttons button {
  border: 1px solid #d1d5db;
  background: white;
  color: #374151;
  padding: 6px 9px;
  border-radius: 7px;
  cursor: pointer;
  font-size: 11px;
}

.ml-control-buttons button:hover {
  background: #f3f4f6;
}

.ml-control-buttons button.active {
  background: #111827;
  border-color: #111827;
  color: white;
}

.ml-prediction-period {
  margin-bottom: 14px;
  color: #6b7280;
  font-size: 12px;
  line-height: 1.5;
}

.ml-prediction-main-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.ml-prediction-primary-card {
  min-height: 128px;
  padding: 16px;
  border: 1px solid #e5e7eb;
  border-radius: 9px;
  background: white;
}

.ml-card-label {
  display: block;
  color: #6b7280;
  font-size: 12px;
  line-height: 1.35;
  margin-bottom: 8px;
}

.ml-prediction-primary-card strong {
  display: block;
  color: #111827;
  font-size: 24px;
  line-height: 1.2;
}

.ml-primary-value.positive-value {
  color: #15803d;
}

.ml-primary-value.negative-value {
  color: #b91c1c;
}

.ml-range-value {
  font-size: 20px !important;
}

.ml-card-help {
  display: block;
  margin-top: 10px;
  color: #6b7280;
  font-size: 11px;
  line-height: 1.45;
}

.ml-prediction-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 10px;
  margin-top: 12px;
}

.ml-prediction-item {
  padding: 13px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: white;
}

.ml-prediction-item span {
  display: block;
  margin-bottom: 6px;
  color: #6b7280;
  font-size: 11px;
  line-height: 1.4;
}

.ml-prediction-item strong {
  display: block;
  color: #111827;
  font-size: 14px;
}

.ml-prediction-note {
  margin-top: 14px;
  padding: 12px 14px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: white;
  color: #6b7280;
  font-size: 11px;
  line-height: 1.6;
}

.ml-prediction-loading,
.ml-prediction-empty {
  padding: 20px;
  text-align: center;
  color: #6b7280;
}

.ml-prediction-error {
  padding: 14px;
  border-radius: 8px;
  background: #fef2f2;
  color: #b91c1c;
  border: 1px solid #fecaca;
}

/* STEP 18.7 RESPONSIVE */
@media (max-width: 900px) {
  .backtest-header {
    flex-direction: column;
  }

  .backtest-run-button {
    width: 100%;
  }

  .backtest-chart {
    height: 340px;
  }

  .ml-prediction-header {
    flex-direction: column;
  }

  .ml-prediction-controls {
    width: 100%;
    align-items: flex-start;
  }

  .ml-prediction-main-grid {
    grid-template-columns: 1fr;
  }

  .ml-prediction-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .ml-control-group {
    align-items: flex-start;
    flex-direction: column;
  }
}

@media (max-width: 600px) {
  .ml-prediction-panel {
    margin-left: 12px;
    margin-right: 12px;
    padding: 14px;
  }

  .ml-prediction-grid {
    grid-template-columns: 1fr;
  }
}

.ml-generate-button {
  min-height: 40px;
  border-radius: 9px;
  border: 1px solid var(--accent, #2563eb);
  background: var(--accent, #2563eb);
  color: #fff;
  font-size: 13px;
  font-weight: 650;
  padding: 9px 15px;
  cursor: pointer;
}
.ml-generate-button:disabled {
  cursor: wait;
  opacity: .65;
}
.ml-generate-button:focus-visible {
  outline: 3px solid rgb(37 99 235 / 25%);
  outline-offset: 2px;
}
</style>