from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
OUT = ROOT / "reports" / "performance"
OUT.mkdir(parents=True, exist_ok=True)


def load_data():
    nav = pd.read_csv(PROC / "02_nav_history_processed.csv", parse_dates=["date"])
    perf = pd.read_csv(PROC / "07_scheme_performance_processed.csv")
    tx = pd.read_csv(PROC / "08_investor_transactions_processed.csv", parse_dates=["transaction_date"])
    holdings = pd.read_csv(PROC / "09_portfolio_holdings_processed.csv")
    return nav, perf, tx, holdings


def compute_daily_returns(nav):
    nav = nav.sort_values(["amfi_code", "date"]).copy()
    nav["daily_return"] = nav.groupby("amfi_code")["nav"].pct_change()
    return nav


def build_var_cvar(nav, perf):
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
    holdings = holdings.copy()
    holdings["weight_share"] = holdings["weight_pct"] / 100.0
    hhi = holdings.groupby("amfi_code")["weight_share"].apply(lambda w: np.sum(np.square(w))).reset_index(name="hhi")
    hhi = hhi.merge(perf[["amfi_code", "scheme_name", "fund_house", "category", "risk_grade"]], on="amfi_code", how="left")
    hhi = hhi.sort_values("hhi", ascending=False)
    return hhi


def main():
    nav, perf, tx, holdings = load_data()
    nav = compute_daily_returns(nav)
    var_cvar = build_var_cvar(nav, perf)
    rolling_chart = build_rolling_sharpe_chart(nav, perf)
    cohort_summary = build_investor_cohort_analysis(tx, perf)
    continuity, continuity_summary = build_sip_continuity(tx)
    hhi = compute_hhi(holdings, perf)

    print("Saved:")
    print(" - var_cvar_report.csv")
    print(f" - {rolling_chart}")
    print("Investor cohort rows:", len(cohort_summary))
    print("SIP continuity eligible investors:", continuity_summary["eligible_investors"])
    print("Top HHI funds:")
    print(hhi.head(5).to_string(index=False))

    hhi.to_csv(OUT / "sector_hhi_concentration.csv", index=False)
    cohort_summary.to_csv(OUT / "investor_cohort_summary.csv", index=False)
    continuity.to_csv(OUT / "sip_continuity_summary.csv", index=False)


if __name__ == "__main__":
    main()
