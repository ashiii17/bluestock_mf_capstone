from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

ROOT = Path(__file__).resolve().parents[1]
PROC_DIR = ROOT / 'data' / 'processed'
FIG_DIR = ROOT / 'reports' / 'eda_charts'
FIG_DIR.mkdir(parents=True, exist_ok=True)

nav = pd.read_csv(PROC_DIR / '02_nav_history_processed.csv', parse_dates=['date'])
aum = pd.read_csv(PROC_DIR / '03_aum_by_fund_house_processed.csv', parse_dates=['date'])
sip = pd.read_csv(PROC_DIR / '04_monthly_sip_inflows_processed.csv', parse_dates=['month'])
category = pd.read_csv(PROC_DIR / '05_category_inflows_processed.csv', parse_dates=['month'])
folio = pd.read_csv(PROC_DIR / '06_industry_folio_count_processed.csv', parse_dates=['month'])
perf = pd.read_csv(PROC_DIR / '07_scheme_performance_processed.csv')
trans = pd.read_csv(PROC_DIR / '08_investor_transactions_processed.csv', parse_dates=['transaction_date'])
holdings = pd.read_csv(PROC_DIR / '09_portfolio_holdings_processed.csv', parse_dates=['portfolio_date'])

nav = nav.merge(perf[['amfi_code', 'scheme_name']], on='amfi_code', how='left')
nav['date_str'] = nav['date'].dt.strftime('%Y-%m-%d')
sip['month_str'] = sip['month'].dt.strftime('%Y-%m')

# 1. NAV trend
fig_nav = px.line(
    nav,
    x='date_str',
    y='nav',
    color='scheme_name',
    title='Daily NAV Trend for All 40 Schemes (2022–2026)',
    labels={'nav': 'NAV', 'date_str': 'Date', 'scheme_name': 'Scheme'},
    width=1100,
    height=600,
)
fig_nav.update_layout(
    legend=dict(title='Scheme', orientation='h', yanchor='bottom', y=1.02, x=0, xanchor='left'),
    margin=dict(l=50, r=30, t=70, b=50),
)
fig_nav.add_vrect(x0='2023-01-01', x1='2023-12-31', fillcolor='green', opacity=0.1, layer='below', line_width=0)
fig_nav.add_vrect(x0='2024-01-01', x1='2024-12-31', fillcolor='red', opacity=0.08, layer='below', line_width=0)
fig_nav.add_annotation(x='2023-06-30', y=nav['nav'].max(), text='2023 bull run', showarrow=False, yshift=20)
fig_nav.add_annotation(x='2024-06-30', y=nav['nav'].max() * 0.85, text='2024 market corrections', showarrow=False, yshift=-20)
fig_nav.write_image(FIG_DIR / 'nav_trend_all_schemes.png')

# 2. AUM growth grouped bar chart

aum['year'] = aum['date'].dt.year
aum_bar = aum.groupby(['year', 'fund_house'], as_index=False)['aum_crore'].sum()
plt.figure(figsize=(14, 6))
palette = {name: ('#d62728' if name == 'SBI Mutual Fund' else '#7f7f7f') for name in aum_bar['fund_house'].unique()}
sns.barplot(data=aum_bar, x='year', y='aum_crore', hue='fund_house', palette=palette, dodge=True)
plt.title('AUM Growth by Fund House (2022–2025) — SBI highlighted for ₹12.5L Cr dominance')
plt.ylabel('AUM (₹ Crore)')
plt.xlabel('Year')
plt.xticks(rotation=0)
plt.legend(title='Fund House', bbox_to_anchor=(1.05, 1), loc='upper left')
sbi_peak = aum_bar[aum_bar['fund_house'] == 'SBI Mutual Fund'].sort_values('year').iloc[-1]
plt.annotate(
    f"SBI: ₹{sbi_peak['aum_crore']:,.0f} Cr",
    xy=(sbi_peak['year'], sbi_peak['aum_crore']),
    xytext=(sbi_peak['year'] + 0.2, sbi_peak['aum_crore'] * 0.95),
    arrowprops=dict(arrowstyle='->', color='#d62728'),
    color='#d62728',
)
plt.tight_layout()
plt.savefig(FIG_DIR / 'aum_growth_by_fund_house.png', dpi=200)
plt.close()

# 3. SIP inflow time-series with annotation
sip = sip.sort_values('month')
fig_sip = px.line(
    sip,
    x='month_str',
    y='sip_inflow_crore',
    title='Monthly SIP Inflows Jan 2022 – Dec 2025',
    labels={'month_str': 'Month', 'sip_inflow_crore': 'SIP Inflow (₹ Crore)'},
    width=1000,
    height=540,
)
max_row = sip.loc[sip['sip_inflow_crore'].idxmax()]
fig_sip.add_trace(
    go.Scatter(
        x=[max_row['month_str']],
        y=[max_row['sip_inflow_crore']],
        mode='markers+text',
        text=['₹31,002 Cr peak'],
        textposition='top center',
        marker=dict(size=12, color='red'),
    )
)
fig_sip.write_image(FIG_DIR / 'sip_inflow_trend.png')

# 4. Category inflow heatmap
heat = category.pivot_table(index='category', columns='month', values='net_inflow_crore', aggfunc='sum')
heat = heat.sort_index()
plt.figure(figsize=(16, 6))
sns.heatmap(heat, annot=True, fmt='.0f', cmap='YlGnBu', cbar_kws={'label': 'Net inflow (₹ Crore)'})
plt.title('Category Inflow Heatmap by Month and Category')
plt.xlabel('Month')
plt.ylabel('Category')
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
plt.savefig(FIG_DIR / 'category_inflow_heatmap.png', dpi=200)
plt.close()

# 5. Investor demographics: age group distribution and gender split
age_counts = trans['age_group'].value_counts().sort_index()
fig_age = px.pie(values=age_counts.values, names=age_counts.index, title='Investor Age Group Distribution', hole=0.35)
fig_age.write_image(FIG_DIR / 'age_group_distribution.png')

sip_trans = trans[trans['transaction_type'] == 'SIP']
plt.figure(figsize=(12, 6))
sns.boxplot(data=sip_trans, x='age_group', y='amount_inr', order=sorted(sip_trans['age_group'].unique()))
plt.title('SIP Amount Distribution by Age Group')
plt.ylabel('SIP Amount (₹)')
plt.xlabel('Age Group')
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig(FIG_DIR / 'sip_amount_by_age_group.png', dpi=200)
plt.close()

gender_counts = trans['gender'].value_counts()
fig_gender = px.bar(x=gender_counts.index, y=gender_counts.values, title='Investor Gender Split', labels={'x': 'Gender', 'y': 'Count'}, text=gender_counts.values)
fig_gender.update_traces(marker_color=['#636EFA', '#EF553B', '#00CC96'])
fig_gender.write_image(FIG_DIR / 'gender_split.png')

# 6. Geographic distribution
state_sip = sip_trans.groupby('state')['amount_inr'].sum().sort_values(ascending=True).tail(20)
plt.figure(figsize=(10, 8))
state_sip.plot(kind='barh', color='#1f77b4')
plt.title('Top 20 States by SIP Amount')
plt.xlabel('Total SIP Amount (₹)')
plt.ylabel('State')
plt.tight_layout()
plt.savefig(FIG_DIR / 'top_states_sip_amount.png', dpi=200)
plt.close()

city_tier_counts = trans['city_tier'].value_counts()
fig_city = px.pie(values=city_tier_counts.values, names=city_tier_counts.index, title='T30 vs B30 City Tier Split', hole=0.4)
fig_city.write_image(FIG_DIR / 'city_tier_split.png')

# 7. Folio count growth line
plt.figure(figsize=(12, 6))
plt.plot(folio['month'], folio['total_folios_crore'], marker='o', color='#2ca02c')
plt.title('Folio Count Growth (Cr) 2022–2025')
plt.xlabel('Month')
plt.ylabel('Total Folios (Crore)')
plt.xticks(rotation=45)
for idx, row in folio.iterrows():
    if row['month'].month in [1, 7, 12] or row['total_folios_crore'] in [13.26, 26.12]:
        plt.annotate(f"{row['total_folios_crore']}", (row['month'], row['total_folios_crore']), textcoords='offset points', xytext=(0, 8), ha='center')
plt.tight_layout()
plt.savefig(FIG_DIR / 'folio_count_growth.png', dpi=200)
plt.close()

# 8. NAV return correlation matrix for selected funds
selected_codes = perf.sort_values('aum_crore', ascending=False).head(10)['amfi_code'].tolist()
returns = nav[nav['amfi_code'].isin(selected_codes)].copy()
returns['daily_return'] = returns.groupby('amfi_code')['nav'].pct_change()
returns_pivot = returns.pivot(index='date', columns='amfi_code', values='daily_return').dropna()
corr = returns_pivot.corr()
plt.figure(figsize=(10, 8))
sns.heatmap(corr, annot=True, fmt='.2f', cmap='RdBu_r', vmin=-1, vmax=1, xticklabels=corr.columns, yticklabels=corr.columns)
plt.title('Correlation Matrix of Daily NAV Returns for Top 10 Schemes by AUM')
plt.tight_layout()
plt.savefig(FIG_DIR / 'nav_return_correlation_matrix.png', dpi=200)
plt.close()

# 9. Sector allocation donut
sector_weights = holdings.groupby('sector', as_index=False)['weight_pct'].sum().sort_values('weight_pct', ascending=False)
fig_sector = px.pie(sector_weights, values='weight_pct', names='sector', title='Sector Allocation by Aggregate Portfolio Weight', hole=0.4)
fig_sector.update_traces(textposition='inside', textinfo='percent+label')
fig_sector.write_image(FIG_DIR / 'sector_allocation_donut.png')

# 10. Additional charts: AUM share 2025, SIP YoY growth and 1-year return distribution
latest_aum = aum[aum['year'] == 2025].groupby('fund_house', as_index=False)['aum_crore'].sum().sort_values('aum_crore', ascending=False)
fig_aum_share = px.pie(latest_aum, values='aum_crore', names='fund_house', title='AUM Market Share by Fund House in 2025', hole=0.4)
fig_aum_share.write_image(FIG_DIR / 'aum_share_2025.png')

sip['year'] = sip['month'].dt.year
sip_growth = sip.groupby('year', as_index=False)['yoy_growth_pct'].mean()
fig_sip_growth = px.bar(sip_growth, x='year', y='yoy_growth_pct', title='Average SIP YoY Growth by Year', labels={'yoy_growth_pct': 'YoY Growth (%)'})
fig_sip_growth.write_image(FIG_DIR / 'sip_yoy_growth.png')

plt.figure(figsize=(12, 6))
sns.histplot(perf['return_1yr_pct'].dropna(), bins=12, kde=True, color='#636EFA')
plt.title('Distribution of 1-Year Scheme Returns')
plt.xlabel('1-Year Return (%)')
plt.ylabel('Number of Schemes')
plt.tight_layout()
plt.savefig(FIG_DIR / 'one_year_return_distribution.png', dpi=200)
plt.close()

# 11. Top 10 schemes by 1-year return
returns_top10 = perf[['scheme_name', 'return_1yr_pct']].dropna().sort_values('return_1yr_pct', ascending=False).head(10)
fig_top_returns = px.bar(
    returns_top10,
    x='scheme_name',
    y='return_1yr_pct',
    title='Top 10 Schemes by 1-Year Return',
    labels={'scheme_name': 'Scheme', 'return_1yr_pct': '1-Year Return (%)'},
    text='return_1yr_pct',
    width=1000,
    height=600,
)
fig_top_returns.update_traces(marker_color='#636EFA', texttemplate='%{text:.2f}%')
fig_top_returns.update_layout(xaxis_tickangle=-45, margin=dict(l=80, r=40, t=70, b=160))
fig_top_returns.write_image(FIG_DIR / 'top_10_schemes_1yr_return.png')

print('Saved charts to', FIG_DIR)
