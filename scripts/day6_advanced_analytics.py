"""Day 6 advanced analytics helpers.

Provides functions to compute VaR/CVaR, rolling Sharpe charts, cohort
analysis, SIP continuity checks and HHI concentration metrics. Designed
to be imported and run from a master runner script.
"""

from __future__ import annotations

from pathlib import Path
import logging
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
OUT = ROOT / "reports" / "performance"
OUT.mkdir(parents=True, exist_ok=True)


def load_data():
    """Load processed datasets needed for advanced analytics."""
    nav = pd.read_csv(PROC / "02_nav_history_processed.csv", parse_dates=["date"])
    perf = pd.read_csv(PROC / "07_scheme_performance_processed.csv")
    tx = pd.read_csv(PROC / "08_investor_transactions_processed.csv", parse_dates=["transaction_date"])
    holdings = pd.read_csv(PROC / "09_portfolio_holdings_processed.csv")
    return nav, perf, tx, holdings


def compute_daily_returns(nav):
    """Add daily returns to cleaned NAV history by scheme."""
    nav = nav.sort_values(["amfi_code", "date"]).copy()
    nav["daily_return"] = nav.groupby("amfi_code")["nav"].pct_change()
    return nav


def build_var_cvar(nav, perf):
    """Compute historical 95 percent VaR and CVaR for each scheme."""
    rows = []
    for code, group in nav.groupby("amfi_code"):
        returns = group["daily_return"].dropna()
        if returns.empty:
            continue
        var_95 = returns.quantile(0.05)
        cvar_95 = returns[returns <= var_95].mean() if not returns[returns <= var_95].empty else var_95
        rows.append({
            "amfi_code": code,
            "var_95": var_95,
            "cvar_95": cvar_95,
            "observations": int(len(returns)),
        })
    df = pd.DataFrame(rows)
    df = df.merge(
        perf[["amfi_code", "scheme_name", "fund_house", "category", "plan", "risk_grade"]],
        on="amfi_code",
        how="left",
    )
    df = df.sort_values(["var_95", "amfi_code"])
    df.to_csv(OUT / "var_cvar_report.csv", index=False)
    return df


def build_rolling_sharpe_chart(nav, perf, top_n=5):
    """Create a rolling 90-day Sharpe chart for the largest AUM schemes."""
    top_funds = perf.sort_values("aum_crore", ascending=False).head(top_n)
    selected = nav[nav["amfi_code"].isin(top_funds["amfi_code"])].copy()
    selected = selected.sort_values(["amfi_code", "date"]).reset_index(drop=True)
    selected["daily_return"] = selected.groupby("amfi_code")["nav"].pct_change()

    def rolling_sharpe(series):
        roll_mean = series.rolling(90, min_periods=60).mean()
        roll_std = series.rolling(90, min_periods=60).std()
        return roll_mean.div(roll_std).mul(np.sqrt(252))

    selected["rolling_sharpe"] = selected.groupby("amfi_code")["daily_return"].transform(rolling_sharpe)
    pivot = selected.pivot(index="date", columns="amfi_code", values="rolling_sharpe")
    plt.figure(figsize=(12, 6))
    for code in pivot.columns:
        scheme_name = top_funds.loc[top_funds["amfi_code"] == code, "scheme_name"].iloc[0]
        plt.plot(pivot.index, pivot[code], label=f"{scheme_name} ({code})")
    plt.title("Rolling 90-day Sharpe Ratio for Top 5 AUM Funds")
    plt.ylabel("Rolling Sharpe")
    plt.xlabel("Date")
    plt.legend(loc="best", fontsize=8)
    plt.grid(alpha=0.2)
    plt.tight_layout()
    output_path = OUT / "rolling_sharpe_chart.png"
    plt.savefig(output_path, dpi=200)
    plt.close()
    return output_path


def build_investor_cohort_analysis(tx, perf):
    """Summarize SIP behavior and top fund preference by investor cohort year."""
    tx = tx.copy()
    tx["cohort_year"] = tx.groupby("investor_id")["transaction_date"].transform("min").dt.year
    invested = tx[tx["transaction_type"].isin(["SIP", "Lumpsum"])].copy()
    sip = tx[tx["transaction_type"] == "SIP"].copy()

    cohort_summary = (
        sip.groupby("cohort_year")["amount_inr"].mean().rename("avg_sip_amount").to_frame()
        .join(invested.groupby("cohort_year")["amount_inr"].sum().rename("total_invested"))
        .reset_index()
    )

    fund_pref = (
        invested.groupby(["cohort_year", "amfi_code"])["amount_inr"].sum().reset_index()
        .sort_values(["cohort_year", "amount_inr"], ascending=[True, False])
        .groupby("cohort_year")
        .first()
        .reset_index()
    )
    fund_pref = fund_pref.merge(perf[["amfi_code", "scheme_name"]], on="amfi_code", how="left")
    fund_pref = fund_pref.rename(columns={"scheme_name": "top_fund_preference", "amount_inr": "top_fund_amount"})
    cohort_summary = cohort_summary.merge(fund_pref[["cohort_year", "top_fund_preference"]], on="cohort_year", how="left")
    cohort_summary = cohort_summary.sort_values("cohort_year")
    return cohort_summary


def build_sip_continuity(tx):
    """Identify investors with long average gaps between SIP installments."""
    sip = tx[tx["transaction_type"] == "SIP"].copy()
    sip = sip.sort_values(["investor_id", "transaction_date"]).reset_index(drop=True)
    counts = sip.groupby("investor_id").size()
    eligible_ids = counts[counts >= 6].index
    sip = sip[sip["investor_id"].isin(eligible_ids)].copy()
    sip["gap_days"] = sip.groupby("investor_id")["transaction_date"].diff().dt.days
    continuity = (
        sip.groupby("investor_id")["gap_days"].mean().reset_index(name="avg_gap_days")
    )
    continuity["at_risk"] = continuity["avg_gap_days"] > 35
    continuity_summary = {
        "eligible_investors": int(len(continuity)),
        "average_gap_days": float(continuity["avg_gap_days"].mean()) if not continuity.empty else np.nan,
        "at_risk_count": int(continuity["at_risk"].sum()),
        "at_risk_rate": float(continuity["at_risk"].mean()) if not continuity.empty else np.nan,
    }
    return continuity, continuity_summary


def compute_hhi(holdings, perf):
    """Calculate portfolio holding concentration with the Herfindahl index."""
    holdings = holdings.copy()
    holdings["weight_share"] = holdings["weight_pct"] / 100.0
    hhi = holdings.groupby("amfi_code")["weight_share"].apply(lambda w: np.sum(np.square(w))).reset_index(name="hhi")
    hhi = hhi.merge(perf[["amfi_code", "scheme_name", "fund_house", "category", "risk_grade"]], on="amfi_code", how="left")
    hhi = hhi.sort_values("hhi", ascending=False)
    return hhi


def build_monte_carlo_projection(nav: pd.DataFrame, perf: pd.DataFrame, years: int = 5, simulations: int = 1000) -> Path:
    """Project five-year NAV paths for top funds with uncertainty bands."""
    rng = np.random.default_rng(42)
    horizon_days = 252 * years
    selected_codes = perf.sort_values("aum_crore", ascending=False).head(5)["amfi_code"].tolist()
    rows: list[dict[str, float | int]] = []

    plt.figure(figsize=(12, 7))
    for code in selected_codes:
        fund_nav = nav[nav["amfi_code"] == code].sort_values("date")
        returns = fund_nav["daily_return"].dropna()
        if returns.empty:
            continue
        latest_nav = float(fund_nav["nav"].iloc[-1])
        mu = float(returns.mean())
        sigma = float(returns.std(ddof=0))
        shocks = rng.normal(mu, sigma, size=(horizon_days, simulations))
        paths = latest_nav * np.cumprod(1 + shocks, axis=0)
        p05, p50, p95 = np.percentile(paths, [5, 50, 95], axis=1)
        scheme = perf.loc[perf["amfi_code"] == code, "scheme_name"].iloc[0]
        x = np.arange(1, horizon_days + 1)
        plt.plot(x, p50, label=f"{scheme} median")
        plt.fill_between(x, p05, p95, alpha=0.12)
        rows.append({
            "amfi_code": int(code),
            "scheme_name": scheme,
            "latest_nav": latest_nav,
            "projected_nav_p05_5yr": float(p05[-1]),
            "projected_nav_p50_5yr": float(p50[-1]),
            "projected_nav_p95_5yr": float(p95[-1]),
            "simulations": simulations,
            "horizon_trading_days": horizon_days,
        })

    out_csv = OUT / "monte_carlo_nav_projection.csv"
    pd.DataFrame(rows).to_csv(out_csv, index=False)
    plt.title("5-Year Monte Carlo NAV Projection With 5%-95% Bands")
    plt.xlabel("Trading Days")
    plt.ylabel("Projected NAV")
    plt.legend(fontsize=8)
    plt.grid(alpha=0.2)
    plt.tight_layout()
    out_png = OUT / "monte_carlo_nav_projection.png"
    plt.savefig(out_png, dpi=200)
    plt.close()
    return out_png


def build_markowitz_frontier(nav: pd.DataFrame, perf: pd.DataFrame, portfolios: int = 5000) -> Path:
    """Simulate a long-only Markowitz efficient frontier for five selected funds."""
    rng = np.random.default_rng(42)
    selected_codes = perf.sort_values("sharpe_ratio", ascending=False).head(5)["amfi_code"].tolist()
    returns = (
        nav[nav["amfi_code"].isin(selected_codes)]
        .pivot(index="date", columns="amfi_code", values="daily_return")
        .dropna()
    )
    mean_returns = returns.mean() * 252
    cov_matrix = returns.cov() * 252
    rows: list[dict[str, float]] = []

    for _ in range(portfolios):
        weights = rng.random(len(selected_codes))
        weights = weights / weights.sum()
        expected_return = float(np.dot(weights, mean_returns))
        volatility = float(np.sqrt(weights.T @ cov_matrix.values @ weights))
        sharpe = expected_return / volatility if volatility > 0 else np.nan
        row = {
            "expected_return": expected_return,
            "volatility": volatility,
            "sharpe_ratio": sharpe,
        }
        row.update({f"weight_{code}": float(weight) for code, weight in zip(selected_codes, weights)})
        rows.append(row)

    frontier = pd.DataFrame(rows)
    frontier.to_csv(OUT / "markowitz_efficient_frontier.csv", index=False)
    best = frontier.loc[frontier["sharpe_ratio"].idxmax()]

    plt.figure(figsize=(10, 7))
    scatter = plt.scatter(frontier["volatility"], frontier["expected_return"], c=frontier["sharpe_ratio"], cmap="viridis", s=12)
    plt.scatter(best["volatility"], best["expected_return"], color="red", marker="*", s=180, label="Max Sharpe")
    plt.colorbar(scatter, label="Sharpe Ratio")
    plt.xlabel("Annualized Volatility")
    plt.ylabel("Expected Annual Return")
    plt.title("Markowitz Efficient Frontier - 5 Selected Funds")
    plt.legend()
    plt.tight_layout()
    out_png = OUT / "markowitz_efficient_frontier.png"
    plt.savefig(out_png, dpi=200)
    plt.close()
    return out_png


def main() -> None:
    """Run all Day 6 analytics and write outputs to reports/performance."""
    logging.info("Running Day 6 advanced analytics")
    nav, perf, tx, holdings = load_data()
    nav = compute_daily_returns(nav)
    var_cvar = build_var_cvar(nav, perf)
    rolling_chart = build_rolling_sharpe_chart(nav, perf)
    cohort_summary = build_investor_cohort_analysis(tx, perf)
    continuity, continuity_summary = build_sip_continuity(tx)
    hhi = compute_hhi(holdings, perf)
    monte_carlo_chart = build_monte_carlo_projection(nav, perf)
    frontier_chart = build_markowitz_frontier(nav, perf)

    hhi.to_csv(OUT / "sector_hhi_concentration.csv", index=False)
    cohort_summary.to_csv(OUT / "investor_cohort_summary.csv", index=False)
    continuity.to_csv(OUT / "sip_continuity_summary.csv", index=False)
    var_cvar.to_csv(OUT / "var_cvar_report.csv", index=False)

    logging.info("Monte Carlo chart written to %s", monte_carlo_chart)
    logging.info("Markowitz frontier chart written to %s", frontier_chart)
    logging.info("Day 6 analytics complete. Outputs written to %s", OUT)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
