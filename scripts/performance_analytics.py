from pathlib import Path
import pandas as pd
import numpy as np
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from scipy.stats import linregress
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / 'data' / 'processed'
OUT = ROOT / 'reports' / 'performance'
OUT.mkdir(parents=True, exist_ok=True)


def load_data():
    nav = pd.read_csv(PROC / '02_nav_history_processed.csv', parse_dates=['date'])
    perf = pd.read_csv(PROC / '07_scheme_performance_processed.csv')
    bench = pd.read_csv(PROC / '10_benchmark_indices_processed.csv', parse_dates=['date'])
    return nav, perf, bench


def compute_daily_returns(nav):
    nav = nav.sort_values(['amfi_code', 'date']).copy()
    nav['daily_return'] = nav.groupby('amfi_code')['nav'].pct_change()
    nav.to_csv(OUT / 'daily_returns.csv', index=False)
    return nav


def calc_cagr(nav, years_list=(1, 3, 5)):
    last_date = nav['date'].max()
    results = []
    for code, g in nav.groupby('amfi_code'):
        s = g.set_index('date').sort_index()
        end_nav = s['nav'].iloc[-1]
        row = {'amfi_code': code}
        for y in years_list:
            start_date = last_date - relativedelta(years=y)
            # find nearest date on or before start_date
            s_before = s[s.index <= start_date]
            if len(s_before) == 0:
                row[f'cagr_{y}yr'] = np.nan
            else:
                start_nav = s_before['nav'].iloc[-1]
                row[f'cagr_{y}yr'] = (end_nav / start_nav) ** (1 / y) - 1
        results.append(row)
    df = pd.DataFrame(results)
    df.to_csv(OUT / 'cagr_table.csv', index=False)
    return df


def annualize(x):
    return x.mean() * 252, x.std(ddof=0) * np.sqrt(252)


def calc_sharpe_sortino(nav_returns, rf=0.065):
    rows = []
    for code, g in nav_returns.groupby('amfi_code'):
        r = g['daily_return'].dropna()
        if r.empty:
            rows.append({'amfi_code': code, 'sharpe': np.nan, 'sortino': np.nan})
            continue
        mean_ann, std_ann = annualize(r)
        sharpe = (mean_ann - rf) / (std_ann if std_ann > 0 else np.nan)
        # downside std
        neg = r[r < 0]
        if len(neg) > 0:
            dd = np.sqrt((neg ** 2).mean()) * np.sqrt(252)
        else:
            dd = 0.0
        sortino = (mean_ann - rf) / (dd if dd > 0 else np.nan)
        rows.append({'amfi_code': code, 'sharpe': sharpe, 'sortino': sortino})
    df = pd.DataFrame(rows)
    df.to_csv(OUT / 'sharpe_sortino.csv', index=False)
    return df


def calc_alpha_beta(nav_returns, bench_returns):
    # bench_returns: DataFrame with date and benchmark columns
    bench_returns = bench_returns.set_index('date').sort_index()
    bench_returns['bench_ret'] = bench_returns['close_value'].pct_change()
    bench_ret = bench_returns['bench_ret']
    rows = []
    for code, g in nav_returns.groupby('amfi_code'):
        df = g.set_index('date').join(bench_ret, how='inner')
        df = df.dropna(subset=['daily_return', 'bench_ret'])
        if len(df) < 10:
            rows.append({'amfi_code': code, 'alpha': np.nan, 'beta': np.nan, 'tracking_error': np.nan})
            continue
        slope, intercept, rvalue, pvalue, stderr = linregress(df['bench_ret'], df['daily_return'])
        alpha = intercept * 252
        beta = slope
        tracking_error = df['daily_return'].sub(df['bench_ret']).std(ddof=0) * np.sqrt(252)
        rows.append({'amfi_code': code, 'alpha': alpha, 'beta': beta, 'tracking_error': tracking_error})
    out = pd.DataFrame(rows)
    out.to_csv(OUT / 'alpha_beta.csv', index=False)
    return out


def max_drawdown(nav):
    rows = []
    for code, g in nav.groupby('amfi_code'):
        s = g.sort_values('date').set_index('date')['nav']
        running_max = s.cummax()
        dd = s / running_max - 1
        mdd = dd.min()
        if pd.isna(mdd):
            rows.append({'amfi_code': code, 'max_drawdown': np.nan, 'mdd_date': pd.NaT})
            continue
        end_date = dd.idxmin()
        start_date = s[:end_date].idxmax()
        rows.append({'amfi_code': code, 'max_drawdown': mdd, 'mdd_start': start_date, 'mdd_end': end_date})
    out = pd.DataFrame(rows)
    out.to_csv(OUT / 'max_drawdown.csv', index=False)
    return out


def build_scorecard(cagr_df, sharpe_df, alpha_df, perf_df, mdd_df):
    # merge
    df = cagr_df.merge(sharpe_df, on='amfi_code', how='left')
    df = df.merge(alpha_df[['amfi_code', 'alpha', 'beta']], on='amfi_code', how='left')
    df = df.merge(perf_df[['amfi_code', 'expense_ratio_pct']], on='amfi_code', how='left')
    df = df.merge(mdd_df[['amfi_code', 'max_drawdown']], on='amfi_code', how='left')
    # ranks as percentiles (higher better)
    df['rank_3yr'] = df['cagr_3yr'].rank(pct=True, ascending=True)
    df['rank_sharpe'] = df['sharpe'].rank(pct=True, ascending=True)
    df['rank_alpha'] = df['alpha'].rank(pct=True, ascending=True)
    df['rank_expense_inv'] = (1 - df['expense_ratio_pct'].rank(pct=True, ascending=True))
    df['rank_mdd_inv'] = (1 - df['max_drawdown'].rank(pct=True, ascending=True))
    df['score'] = 100 * (0.30 * df['rank_3yr'] + 0.25 * df['rank_sharpe'] + 0.20 * df['rank_alpha'] + 0.15 * df['rank_expense_inv'] + 0.10 * df['rank_mdd_inv'])
    out = df[['amfi_code', 'cagr_1yr', 'cagr_3yr', 'cagr_5yr', 'sharpe', 'sortino', 'alpha', 'beta', 'max_drawdown', 'expense_ratio_pct', 'score']]
    out.to_csv(OUT / 'fund_scorecard.csv', index=False)
    return out


def benchmark_comparison(nav, scorecard, bench, years=3):
    last = nav['date'].max()
    start = last - relativedelta(years=years)
    top5 = scorecard.sort_values('score', ascending=False).head(5)['amfi_code'].tolist()
    plt.figure(figsize=(12, 6))
    for code in top5:
        s = nav[nav['amfi_code'] == code].set_index('date')['nav'].sort_index()
        s = s[s.index >= start]
        if s.empty: continue
        cum = s / s.iloc[0]
        plt.plot(cum.index, cum.values, label=f'{code}')
    # benchmarks: plot NIFTY50 and NIFTY100 if present
    bench_pivot = bench.pivot(index='date', columns='index_name', values='close_value')
    for name in ['NIFTY50', 'NIFTY100']:
        if name in bench_pivot.columns:
            b = bench_pivot[name].loc[bench_pivot.index >= start]
            b = b / b.iloc[0]
            plt.plot(b.index, b.values, label=name, linestyle='--')
    plt.legend()
    plt.title(f'Top 5 Funds vs Benchmarks ({years}y)')
    plt.tight_layout()
    plt.savefig(OUT / 'benchmark_comparison_top5.png', dpi=200)
    plt.close()


def main():
    nav, perf, bench = load_data()
    navr = compute_daily_returns(nav)
    cagr = calc_cagr(nav)
    shar = calc_sharpe_sortino(navr)
    # pick NIFTY100 if exists else NIFTY50
    bench_choice = bench[bench['index_name'] == 'NIFTY100'] if 'NIFTY100' in bench['index_name'].unique() else bench[bench['index_name'] == 'NIFTY50']
    alpha_beta = calc_alpha_beta(navr, bench_choice)
    mdd = max_drawdown(nav)
    score = build_scorecard(cagr, shar, alpha_beta, perf, mdd)
    benchmark_comparison(nav, score, bench)
    print('Performance analytics outputs written to', OUT)


if __name__ == '__main__':
    main()
