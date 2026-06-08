from pathlib import Path
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / 'data' / 'processed'
OUT = ROOT / 'reports' / 'dashboard_pages'
OUT.mkdir(parents=True, exist_ok=True)


def load_all():
    files = {
        'fund_master': '01_fund_master_processed.csv',
        'nav': '02_nav_history_processed.csv',
        'aum_by_house': '03_aum_by_fund_house_processed.csv',
        'monthly_sip': '04_monthly_sip_inflows_processed.csv',
        'category_inflows': '05_category_inflows_processed.csv',
        'folio': '06_industry_folio_count_processed.csv',
        'perf': '07_scheme_performance_processed.csv',
        'transactions': '08_investor_transactions_processed.csv',
        'holdings': '09_portfolio_holdings_processed.csv',
        'bench': '10_benchmark_indices_processed.csv',
    }
    data = {}
    for k, v in files.items():
        p = PROC / v
        if p.exists():
            if 'date' in pd.read_csv(p, nrows=1).columns:
                data[k] = pd.read_csv(p, parse_dates=['date'])
            else:
                data[k] = pd.read_csv(p)
        else:
            data[k] = pd.DataFrame()
    # normalize common column names for downstream plotting
    # monthly_sip: month -> date, sip_inflow_crore -> inflow_amount
    if 'monthly_sip' in data and not data['monthly_sip'].empty:
        ms = data['monthly_sip']
        if 'month' in ms.columns:
            ms = ms.rename(columns={'month': 'date'})
            ms['date'] = pd.to_datetime(ms['date'])
        if 'sip_inflow_crore' in ms.columns:
            ms = ms.rename(columns={'sip_inflow_crore': 'inflow_amount'})
        data['monthly_sip'] = ms
    # transactions: transaction_date -> date, amount_inr -> amount
    if 'transactions' in data and not data['transactions'].empty:
        tx = data['transactions']
        if 'transaction_date' in tx.columns:
            tx = tx.rename(columns={'transaction_date': 'date'})
            tx['date'] = pd.to_datetime(tx['date'])
        if 'amount_inr' in tx.columns:
            tx = tx.rename(columns={'amount_inr': 'amount'})
        data['transactions'] = tx
    # perf: normalize return and risk column names
    if 'perf' in data and not data['perf'].empty:
        p = data['perf']
        # prefer 3yr return where available
        if 'return_3yr_pct' in p.columns:
            p = p.rename(columns={'return_3yr_pct': 'return_pct'})
        elif 'return_1yr_pct' in p.columns:
            p = p.rename(columns={'return_1yr_pct': 'return_pct'})
        if 'std_dev_ann_pct' in p.columns:
            p = p.rename(columns={'std_dev_ann_pct': 'std_dev_pct'})
        data['perf'] = p
    return data


def page1(data):
    # KPIs
    fm = data['fund_master']
    folio = data['folio']
    aum_house = data['aum_by_house']
    monthly_sip = data['monthly_sip']
    # totals (fallbacks if missing)
    total_aum = None
    if not aum_house.empty:
        # prefer 'aum_crore' if present, otherwise try other fields
        if 'aum_crore' in aum_house.columns:
            total_aum = aum_house['aum_crore'].sum()
        elif 'aum' in aum_house.columns:
            total_aum = aum_house['aum'].sum()
        elif 'aum_lakh_crore' in aum_house.columns:
            # convert lakh crore to crore approximation
            total_aum = (aum_house['aum_lakh_crore'] * 100000).sum()
    if total_aum is None:
        total_aum = 0
    sip_total = 0
    if not monthly_sip.empty and 'inflow_amount' in monthly_sip.columns:
        sip_total = monthly_sip['inflow_amount'].sum()
    folios = folio['folio_count'].iloc[-1] if (not folio.empty and 'folio_count' in folio.columns) else np.nan
    schemes = fm['amfi_code'].nunique() if not fm.empty else 0

    # AUM trend line (aggregate by month)
    aum_trend = None
    if not aum_house.empty and 'date' in aum_house.columns:
        df = aum_house.copy()
        if 'aum' in df.columns:
            dfm = df.groupby(pd.Grouper(key='date', freq='ME'))['aum'].sum().reset_index()
            aum_trend = dfm

    # build figure
    fig = make_page_figure()
    # KPIs as annotations
    fig.add_annotation(text=f"Total AUM: ₹{total_aum:,.0f}", x=0.02, y=0.95, showarrow=False, font=dict(size=14))
    fig.add_annotation(text=f"SIP Inflows: ₹{sip_total:,.0f}", x=0.34, y=0.95, showarrow=False, font=dict(size=14))
    fig.add_annotation(text=f"Folios: {folios}", x=0.66, y=0.95, showarrow=False, font=dict(size=14))
    fig.add_annotation(text=f"Schemes: {schemes}", x=0.88, y=0.95, showarrow=False, font=dict(size=14))

    # add AUM trend subplot
    if aum_trend is not None:
        fig.add_trace(go.Scatter(x=aum_trend['date'], y=aum_trend['aum'], mode='lines', name='Industry AUM'), row=2, col=1)

    # AUM by AMC bar
    if not aum_house.empty and 'fund_house' in aum_house.columns:
        aum_col = 'aum_crore' if 'aum_crore' in aum_house.columns else ('aum' if 'aum' in aum_house.columns else None)
        if aum_col is None and 'aum_lakh_crore' in aum_house.columns:
            aum_house = aum_house.copy()
            aum_house['aum_crore_est'] = aum_house['aum_lakh_crore'] * 100000
            aum_col = 'aum_crore_est'
        if aum_col is not None:
            top = aum_house.groupby('fund_house')[aum_col].sum().nlargest(10).reset_index()
            y_vals = top[aum_col]
        else:
            top = aum_house.groupby('fund_house').size().nlargest(10).reset_index(name='count')
            y_vals = top['count']
        fig.add_trace(go.Bar(x=top['fund_house'], y=y_vals, name='AUM by AMC'), row=2, col=2)

    fig.update_layout(title_text='Industry Overview')
    fig.write_image(str(OUT / 'page1_industry_overview.png'))


def build_page1(data):
    # Composite Page 1: KPIs, AUM trend, AUM by AMC
    from plotly.subplots import make_subplots
    fig = make_subplots(rows=2, cols=2, specs=[[{"type":"indicator","colspan":2}, None],[{"type":"xy"}, {"type":"bar"}]], subplot_titles=("KPIs", "", "AUM Trend", "AUM by AMC"))
    # KPIs as indicators
    aum = data['aum_by_house']
    ms = data['monthly_sip']
    fol = data['folio']
    fm = data['fund_master']
    total_aum = aum['aum_crore'].sum() if (not aum.empty and 'aum_crore' in aum.columns) else (aum['aum'].sum() if (not aum.empty and 'aum' in aum.columns) else 0)
    sip_total = ms['inflow_amount'].sum() if (not ms.empty and 'inflow_amount' in ms.columns) else 0
    folios = fol['folio_count'].iloc[-1] if (not fol.empty and 'folio_count' in fol.columns) else np.nan
    schemes = fm['amfi_code'].nunique() if not fm.empty else 0
    fig.add_trace(go.Indicator(mode='number', value=total_aum, title={'text':'Total AUM (crore)'}), row=1, col=1)
    fig.add_trace(go.Indicator(mode='number', value=sip_total, title={'text':'SIP Inflows (crore)'}), row=1, col=1)
    # AUM trend
    if not aum.empty and 'date' in aum.columns:
        dfm = aum.groupby(pd.Grouper(key='date', freq='ME'))['aum_crore' if 'aum_crore' in aum.columns else 'aum'].sum().reset_index()
        fig.add_trace(go.Scatter(x=dfm['date'], y=dfm[dfm.columns[1]], name='AUM'), row=2, col=1)
    # AUM by AMC
    if not aum.empty and 'fund_house' in aum.columns:
        col = 'aum_crore' if 'aum_crore' in aum.columns else ('aum' if 'aum' in aum.columns else aum.columns[1])
        top = aum.groupby('fund_house')[col].sum().nlargest(10).reset_index()
        fig.add_trace(go.Bar(x=top['fund_house'], y=top[col], name='AUM by AMC'), row=2, col=2)
    fig.update_layout(height=800, title_text='Industry Overview')
    fig.write_image(str(OUT / 'page1.png'), scale=2)


def page2(data):
    perf = data['perf']
    nav = data['nav']
    aum_house = data['aum_by_house']
    # prepare scatter: return vs std dev from perf
    if not perf.empty and {'amfi_code', 'return_pct', 'std_dev_pct'}.issubset(perf.columns):
        df = perf.copy()
        df['return'] = df['return_pct']
        df['risk'] = df['std_dev_pct']
        # bubble size from aum_by_house by scheme? fallback
        size = None
        # prefer aum from perf if present
        if 'aum_crore' in df.columns:
            size_col = 'aum_crore'
        else:
            size_col = None
            if not aum_house.empty and 'amfi_code' in aum_house.columns:
                # try to aggregate aum by scheme
                possible = None
                if 'aum_crore' in aum_house.columns:
                    possible = aum_house.groupby('amfi_code')['aum_crore'].sum()
                elif 'aum' in aum_house.columns:
                    possible = aum_house.groupby('amfi_code')['aum'].sum()
                if possible is not None:
                    df = df.merge(possible.rename('aum'), on='amfi_code', how='left')
                    size_col = 'aum'
        fig = px.scatter(df, x='return', y='risk', size=size_col, hover_data=['amfi_code'], title='Fund Return vs Risk')
        fig.write_image(str(OUT / 'page2_return_vs_risk.png'))

    # NAV vs benchmark for top fund
    if not nav.empty and not data['bench'].empty:
        top_code = perf.sort_values('annualized_return_pct', ascending=False)['amfi_code'].iloc[0] if ('annualized_return_pct' in perf.columns and not perf.empty) else nav['amfi_code'].unique()[0]
        s = nav[nav['amfi_code'] == top_code].sort_values('date')
        bench = data['bench']
        bench_pivot = bench.pivot(index='date', columns='index_name', values='close_value') if not bench.empty else None
        fig2 = go.Figure()
        fig2.add_trace(go.Line(x=s['date'], y=s['nav'] / s['nav'].iloc[0], name=str(top_code)))
        if bench_pivot is not None and 'NIFTY50' in bench_pivot.columns:
            b = bench_pivot['NIFTY50'].loc[bench_pivot.index.isin(s['date'])]
            if not b.empty:
                fig2.add_trace(go.Line(x=b.index, y=b.values / b.values[0], name='NIFTY50'))
        fig2.update_layout(title='NAV (normalized) vs Benchmark')
        fig2.write_image(str(OUT / 'page2_nav_vs_bench.png'))


def build_page2(data):
    # Composite Page 2: Scatter + Scorecard table + NAV vs Benchmark
    from plotly.subplots import make_subplots
    perf = data['perf']
    nav = data['nav']
    bench = data['bench']
    score = None
    try:
        score = pd.read_csv(Path('reports') / 'performance' / 'fund_scorecard.csv')
    except Exception:
        score = data['perf'].head(10)
    fig = make_subplots(rows=2, cols=2, specs=[[{"type":"xy"},{"type":"table"}],[{"colspan":2, "type":"xy"}, None]], subplot_titles=("Return vs Risk","Scorecard","NAV vs Benchmark",""))
    # Scatter
    if not perf.empty and {'return_pct','std_dev_pct','amfi_code'}.issubset(perf.columns):
        df = perf.copy()
        size_col = 'aum_crore' if 'aum_crore' in perf.columns else None
        fig.add_trace(go.Scatter(x=df['return_pct'], y=df['std_dev_pct'], mode='markers', marker=dict(size=(df[size_col].fillna(0)/1000) if size_col else 8), text=df['amfi_code']), row=1, col=1)
    # Scorecard table (top 10 by score)
    if score is not None:
        s = score.sort_values('score', ascending=False).head(10)
        fig.add_trace(go.Table(header=dict(values=list(s.columns)), cells=dict(values=[s[c].tolist() for c in s.columns])), row=1, col=2)
    # NAV vs benchmark
    if not nav.empty:
        top_code = perf.sort_values('return_pct', ascending=False)['amfi_code'].iloc[0] if ('return_pct' in perf.columns and not perf.empty) else nav['amfi_code'].unique()[0]
        s = nav[nav['amfi_code']==top_code].sort_values('date')
        fig.add_trace(go.Scatter(x=s['date'], y=s['nav']/s['nav'].iloc[0], name=str(top_code)), row=2, col=1)
        if not bench.empty:
            pivot = bench.pivot(index='date', columns='index_name', values='close_value')
            if 'NIFTY50' in pivot.columns:
                b = pivot['NIFTY50'].resample('ME').last()
                fig.add_trace(go.Scatter(x=b.index, y=b.values/b.values[0], name='NIFTY50'), row=2, col=1)
    fig.update_layout(height=900, title_text='Fund Performance')
    fig.write_image(str(OUT / 'page2.png'), scale=2)


def page3(data):
    tx = data['transactions']
    if not tx.empty:
        # transactions by state
        if 'state' in tx.columns and 'amount' in tx.columns:
            st = tx.groupby('state')['amount'].sum().nlargest(20).reset_index()
            fig = px.bar(st, x='state', y='amount', title='Transaction Amount by State')
            fig.write_image(str(OUT / 'page3_tx_by_state.png'))
        # donut split by tx type
        if 'transaction_type' in tx.columns and 'amount' in tx.columns:
            d = tx.groupby('transaction_type')['amount'].sum().reset_index()
            fig2 = px.pie(d, names='transaction_type', values='amount', hole=0.5, title='Transaction Type Split')
            fig2.write_image(str(OUT / 'page3_tx_type_donut.png'))
        # age group vs avg SIP amount
        if 'age_group' in tx.columns and 'amount' in tx.columns and 'transaction_type' in tx.columns:
            sip = tx[tx['transaction_type'].str.upper() == 'SIP']
            if not sip.empty:
                ag = sip.groupby('age_group')['amount'].mean().reset_index().sort_values('amount', ascending=False)
                fig3 = px.bar(ag, x='age_group', y='amount', title='Avg SIP Amount by Age Group')
                fig3.write_image(str(OUT / 'page3_age_avg_sip.png'))
        # monthly transaction volume line (count)
        if 'date' in tx.columns:
            mv = tx.set_index('date').resample('ME').size().rename('tx_count').reset_index()
            fig4 = px.line(mv, x='date', y='tx_count', title='Monthly Transaction Volume')
            fig4.write_image(str(OUT / 'page3_monthly_tx_volume.png'))


def build_page3(data):
    # Composite Page 3: tx by state, donut, age-group avg SIP, monthly tx volume
    from plotly.subplots import make_subplots
    tx = data['transactions']
    fig = make_subplots(rows=2, cols=2, specs=[[{"type":"xy"},{"type":"domain"}], [{"type":"xy"},{"type":"xy"}]], subplot_titles=("Tx by State","Tx Type Split","Avg SIP by Age","Monthly Tx Volume"))
    if not tx.empty:
        if 'state' in tx.columns and 'amount' in tx.columns:
            st = tx.groupby('state')['amount'].sum().nlargest(20).reset_index()
            fig.add_trace(go.Bar(x=st['state'], y=st['amount']), row=1, col=1)
        if 'transaction_type' in tx.columns and 'amount' in tx.columns:
            d = tx.groupby('transaction_type')['amount'].sum().reset_index()
            fig.add_trace(go.Pie(labels=d['transaction_type'], values=d['amount'], hole=0.5), row=1, col=2)
        # avg SIP by age
        if 'transaction_type' in tx.columns and 'age_group' in tx.columns and 'amount' in tx.columns:
            sip = tx[tx['transaction_type']=='SIP']
            if not sip.empty:
                ag = sip.groupby('age_group')['amount'].mean().reset_index()
                fig.add_trace(go.Bar(x=ag['age_group'], y=ag['amount']), row=2, col=1)
        # monthly tx volume
        if 'date' in tx.columns:
            mv = tx.set_index('date').resample('ME').size().reset_index(name='tx_count')
            fig.add_trace(go.Scatter(x=mv['date'], y=mv['tx_count']), row=2, col=2)
    fig.update_layout(height=900, title_text='Investor Analytics')
    fig.write_image(str(OUT / 'page3.png'), scale=2)


def page4(data):
    monthly_sip = data['monthly_sip']
    bench = data['bench']
    if not monthly_sip.empty:
        # aggregate monthly SIP
        if 'date' in monthly_sip.columns and 'inflow_amount' in monthly_sip.columns:
            ms = monthly_sip.groupby(pd.Grouper(key='date', freq='ME'))['inflow_amount'].sum().reset_index()
            fig = make_dual_axis(ms, bench)
            fig.write_image(str(OUT / 'page4_sip_market_trends.png'))
    # category inflow heatmap and top5 categories FY25
    cat = data.get('category_inflows', pd.DataFrame())
    if not cat.empty and 'month' in cat.columns:
        c = cat.copy()
        if 'month' in c.columns:
            c = c.rename(columns={'month': 'date'})
            c['date'] = pd.to_datetime(c['date'])
        # heatmap pivot month x category
        pivot = c.pivot_table(index=pd.Grouper(key='date', freq='ME'), columns='category', values='net_inflow_crore', aggfunc='sum').fillna(0)
        # plot heatmap using plotly
        hm = go.Figure(data=go.Heatmap(z=pivot.T.values, x=pivot.index.astype(str), y=pivot.columns, colorscale='Viridis'))
        hm.update_layout(title='Category Inflow Heatmap')
        hm.write_image(str(OUT / 'page4_category_inflow_heatmap.png'))
        # top 5 categories by net inflow FY25 (filter year==2025)
        fy25 = c[c['date'].dt.year == 2025]
        if not fy25.empty:
            top5 = fy25.groupby('category')['net_inflow_crore'].sum().nlargest(5).reset_index()
            figtop = px.bar(top5, x='category', y='net_inflow_crore', title='Top 5 Categories by Net Inflow FY25')
            figtop.write_image(str(OUT / 'page4_top5_categories_fy25.png'))


def build_page4(data):
    # Composite Page 4: Dual-axis SIP + Nifty, category inflow heatmap, top5 categories FY25
    from plotly.subplots import make_subplots
    ms = data['monthly_sip']
    cat = data['category_inflows']
    bench = data['bench']
    fig = make_subplots(rows=2, cols=2, specs=[[{"colspan":2, "type":"xy"}, None],[{"type":"heatmap"}, {"type":"bar"}]], subplot_titles=("SIP Inflow vs Nifty50","", "Category Inflow Heatmap","Top 5 Categories FY25"))
    # SIP dual axis
    if not ms.empty:
        fig.add_trace(go.Bar(x=ms['date'], y=ms['inflow_amount'], name='SIP Inflow', marker_color='steelblue'), row=1, col=1)
    if not bench.empty:
        pivot = bench.pivot(index='date', columns='index_name', values='close_value')
        if 'NIFTY50' in pivot.columns:
            b = pivot['NIFTY50'].resample('ME').last()
            fig.add_trace(go.Scatter(x=b.index, y=b.values, name='NIFTY50', yaxis='y2', line=dict(color='orange')), row=1, col=1)
    # heatmap
    if not cat.empty:
        c = cat.copy()
        if 'month' in c.columns:
            c['date'] = pd.to_datetime(c['month'])
        pivot = c.pivot(index='category', columns='date', values='net_inflow_crore').fillna(0)
        fig.add_trace(go.Heatmap(z=pivot.values, x=[d.strftime('%Y-%m') for d in pivot.columns], y=pivot.index, colorscale='Viridis'), row=2, col=1)
        # top5 FY25 (assume FY25 = 2024-04-01 to 2025-03-31)
        fy25_start = pd.to_datetime('2024-04-01')
        fy25_end = pd.to_datetime('2025-03-31')
        mask = (c['date'] >= fy25_start) & (c['date'] <= fy25_end)
        top5 = c[mask].groupby('category')['net_inflow_crore'].sum().nlargest(5).reset_index()
        fig.add_trace(go.Bar(x=top5['category'], y=top5['net_inflow_crore'], marker_color='teal'), row=2, col=2)
    fig.update_layout(height=1000, title_text='SIP & Market Trends')
    fig.write_image(str(OUT / 'page4.png'), scale=2)


def make_dual_axis(ms, bench):
    fig = go.Figure()
    fig.add_trace(go.Bar(x=ms['date'], y=ms['inflow_amount'], name='SIP Inflow', yaxis='y'))
    if not bench.empty and 'index_name' in bench.columns:
        pivot = bench.pivot(index='date', columns='index_name', values='close_value')
        if 'NIFTY50' in pivot.columns:
            b = pivot['NIFTY50'].resample('ME').last()
            fig.add_trace(go.Line(x=b.index, y=b.values, name='NIFTY50', yaxis='y2'))
    fig.update_layout(yaxis=dict(title='SIP Inflow'), yaxis2=dict(title='NIFTY50', overlaying='y', side='right'))
    fig.update_layout(title='SIP Inflow vs Nifty50')
    return fig


def make_page_figure():
    from plotly.subplots import make_subplots
    fig = make_subplots(rows=2, cols=2, subplot_titles=("", "", "AUM Trend", "AUM by AMC"))
    return fig


def combine_pngs_to_pdf(png_paths, out_pdf):
    imgs = [Image.open(p).convert('RGB') for p in png_paths]
    if imgs:
        imgs[0].save(out_pdf, save_all=True, append_images=imgs[1:], quality=95)


def main():
    data = load_all()
    # build composite pages
    build_page1(data)
    build_page2(data)
    build_page3(data)
    build_page4(data)
    # also keep individual component images for reference
    page1(data)
    page2(data)
    page3(data)
    page4(data)
    # combine to pdf using final page1..page4
    pngs = [OUT / f'page{i}.png' for i in range(1,5) if (OUT / f'page{i}.png').exists()]
    combine_pngs_to_pdf(pngs, OUT / 'Dashboard.pdf')
    print('Dashboard pages written to', OUT)


if __name__ == '__main__':
    main()
