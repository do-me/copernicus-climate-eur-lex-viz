# /// script
# dependencies =[
#   "duckdb",
#   "pandas",
#   "plotly",
#   "openpyxl", "kaleido", "pyarrow"
# ]
# ///

# this script filters for anything policy- and Copernicus-related for climate

import os
import re
import duckdb
import plotly.express as px
import pandas as pd
import plotly.graph_objects as go

# Ensure data directory exists
os.makedirs("data", exist_ok=True)

con = duckdb.connect()

# Extract category, context, and counts entirely in DuckDB for speed
df = con.execute(f"""
SELECT 
    * EXCLUDE text,
    
    -- Count of 'copernicus' occurrences
    length(regexp_extract_all(text, '(?i)copernicus')) AS count_copernicus,
    
    -- Count of climate/carbon/ghg/emissions occurrences
    length(regexp_extract_all(text, '(?i)climate|carbon|ghg|emissions')) AS count_climate_terms,
    
    -- Extracts the specific match from the title as a new column
    lower(regexp_extract(title, '(?i)^(decision|regulation|directive|communication|joint communication|commission delegated regulation|commission implementing regulation)', 1)) AS category,
    
    -- Extracts up to 250 characters before and after every match of 'copernicus' (case-insensitive + multiline)
    -- Concatenates the array into a string using '  |  ' as the delimiter, and replaces newlines with spaces
    replace(
        array_to_string(
            regexp_extract_all(text, '(?is).{{0,250}}copernicus.{{0,250}}'), 
            '  |  '
        ), 
        '\n', ' '
    ) AS copernicus_context

FROM 'EUR-LEX/files/*/*.parquet' 
            
WHERE 
    CAST(date AS DATE) >= '2014-01-01'
    --AND CAST(date AS DATE) <= '2024-12-31'
    
    -- 1. Must contain Copernicus
    AND regexp_matches(text, '(?i)copernicus')
    
    -- 2. AND must contain ANY of these words
    AND regexp_matches(text, '(?i)climate|carbon|ghg|emissions')
            
    -- 3. AND title must start with ANY of these words
    AND regexp_matches(title, '^(?i)(decision|regulation|directive|communication)')
    
    -- 4. AND exclude specific institution from the array
    AND NOT list_contains(institutions, 'Directorate-General for Budget')
    
    -- 5. AND exclude specific documents by title
    AND NOT regexp_matches(title, '(?i)(annual accounts|general report on the activities of the european union|multiannual financial framework)')
            
ORDER BY date DESC
""").df()

con.close()

# ==========================================
# Clean up illegal characters for Excel export
# ==========================================
# Excel does not allow certain control characters. This strips them out of any string column.
ILLEGAL_CHARACTERS_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]')
for col in df.select_dtypes(include=['object', 'string']).columns:
    df[col] = df[col].apply(lambda x: ILLEGAL_CHARACTERS_RE.sub("", x) if isinstance(x, str) else x)

# Write data exports to data/ directory (includes all amendments)
df.to_excel("data/query_results.xlsx", index=False)
df.to_parquet("data/query_results.parquet", index=False)


# ==========================================
# Data Deduplication for Plots
# ==========================================
# Create a base_celex by removing amendment suffixes like R(01), R(02) at the end of the string
df['base_celex'] = df['celex'].str.replace(r'R\(\d+\)$', '', regex=True)

# Deduplicate based on base_celex for the plots (keeps the first occurrence, which is the newest due to ORDER BY date DESC)
df_plot = df.drop_duplicates(subset=['base_celex']).copy()

# ==========================================
# 1. Data Preparation (Yearly)
# ==========================================
df_plot['year'] = pd.to_datetime(df_plot['date']).dt.year
plot_df = df_plot.groupby(['year', 'category']).size().reset_index(name='count')

# Calculate yearly totals for the labels on top
totals_df = plot_df.groupby('year')['count'].sum().reset_index(name='total')

# Calculate percentages for the tooltips
yearly_totals = plot_df.groupby('year')['count'].transform('sum')
plot_df['percentage'] = (plot_df['count'] / yearly_totals * 100).round(1)

# Ensure consistent colors and sorting order across both plots
all_categories = sorted([c for c in df_plot['category'].unique() if pd.notna(c)])
sci_palette =['#E64B35', '#4DBBD5', '#00A087', '#3C5488', '#F39B7F', '#8491B0', '#91D1C2']

# Map each sorted category to a specific color
category_colors = {cat: sci_palette[i % len(sci_palette)] for i, cat in enumerate(all_categories)}

# ==========================================
# 2. Original Stacked Bar Plot (Yearly)
# ==========================================
fig = px.bar(
    plot_df, 
    x='year', 
    y='count', 
    color='category',
    text_auto=True, 
    color_discrete_map=category_colors,
    template='plotly_white',
    barmode='stack',
    category_orders={"year": sorted(plot_df['year'].unique()), "category": all_categories}
)

fig.add_trace(go.Scatter(
    x=totals_df['year'],
    y=totals_df['total'],
    mode='text',
    text=totals_df['total'],
    textposition='top center',
    textfont=dict(family="Arial", size=22, color="black"),
    showlegend=False,
    hoverinfo='skip'
))

fig.update_traces(
    selector=dict(type='bar'), 
    hovertemplate="<b>%{fullData.name}</b><br>Count: %{y}<br>Share: %{customdata[0]}%<extra></extra>",
    customdata=plot_df[['percentage']].values,
    marker_line_width=0,
    textfont=dict(size=16, color="white"), 
    textposition='inside',
    insidetextanchor='middle'
)

fig.update_layout(
    title={
        'text': "<b>EU Legislative Acts Referencing Copernicus and Climate</b><br><span style='font-size:22px; color:#666'>Document volume by category (2014–Present)</span>",
        'y': 0.94, 'x': 0.02, 'xanchor': 'left', 'yanchor': 'top',
        'font': dict(family="Arial", size=32, color='#2c3e50')
    },
    legend=dict(
        title=None, x=0.02, y=0.85, xanchor='left', yanchor='top',
        bgcolor='rgba(255, 255, 255, 0)',
        font=dict(size=20, color='#333')
    ),
    xaxis=dict(
        title="", type='category', showline=True, linecolor='#333', linewidth=2,
        tickfont=dict(size=20, color='#333'), showgrid=False
    ),
    yaxis=dict(
        title="Number of Documents", title_font=dict(size=22),
        showgrid=True, gridcolor='#EEEEEE', tickfont=dict(size=20, color='#333'),
        zeroline=False, dtick=5,
        range=[0, totals_df['total'].max() + 4] 
    ),
    margin=dict(t=160, l=100, r=40, b=80),
    bargap=0.35,
    height=1200
)

# Output charts to data/ directory
fig.write_image("data/query_results.png", width=1600, height=1200, scale=2)
fig.write_html("data/index.html", include_plotlyjs='cdn')


# ==========================================
# 3. Cumulative Data Preparation
# ==========================================
# To properly calculate cumulative sum in a stacked bar, pivot to fill missing category/year combinations with 0
pivot_df = plot_df.pivot(index='year', columns='category', values='count').fillna(0)
cum_pivot_df = pivot_df.cumsum()

# Melt back to long format for Plotly
cum_plot_df = cum_pivot_df.reset_index().melt(id_vars='year', value_name='cum_count')

# Calculate percentages for tooltips relative to the cumulative yearly total
cum_yearly_totals = cum_plot_df.groupby('year')['cum_count'].transform('sum')
cum_plot_df['cum_percentage'] = (cum_plot_df['cum_count'] / cum_yearly_totals * 100).round(1)

# Remove categories with 0 cumulative count for a cleaner chart
cum_plot_df = cum_plot_df[cum_plot_df['cum_count'] > 0]

# Calculate cumulative totals for the scatter text at the top
cum_totals_df = totals_df.copy()
cum_totals_df['cum_total'] = cum_totals_df['total'].cumsum()


# ==========================================
# 4. Cumulative Stacked Bar Plot
# ==========================================
fig_cum = px.bar(
    cum_plot_df, 
    x='year', 
    y='cum_count', 
    color='category',
    text_auto=True, 
    color_discrete_map=category_colors,
    template='plotly_white',
    barmode='stack',
    category_orders={"year": sorted(cum_plot_df['year'].unique()), "category": all_categories}
)

fig_cum.add_trace(go.Scatter(
    x=cum_totals_df['year'],
    y=cum_totals_df['cum_total'],
    mode='text',
    text=cum_totals_df['cum_total'],
    textposition='top center',
    textfont=dict(family="Arial", size=22, color="black"), 
    showlegend=False,
    hoverinfo='skip'
))

fig_cum.update_traces(
    selector=dict(type='bar'), 
    hovertemplate="<b>%{fullData.name}</b><br>Cumulative Count: %{y}<br>Share: %{customdata[0]}%<extra></extra>",
    customdata=cum_plot_df[['cum_percentage']].values,
    marker_line_width=0,
    textfont=dict(size=16, color="white"), 
    textposition='inside',
    insidetextanchor='middle'
)

fig_cum.update_layout(
    title={
        'text': "<b>EU Legislative Acts Referencing Copernicus and Climate</b><br><span style='font-size:22px; color:#666'>Cumulative document volume by category (2014–Present)</span>",
        'y': 0.94, 'x': 0.02, 'xanchor': 'left', 'yanchor': 'top',
        'font': dict(family="Arial", size=32, color='#2c3e50')
    },
    legend=dict(
        title=None, x=0.02, y=0.85, xanchor='left', yanchor='top',
        bgcolor='rgba(255, 255, 255, 0)',
        font=dict(size=20, color='#333')
    ),
    xaxis=dict(
        title="", type='category', showline=True, linecolor='#333', linewidth=2,
        tickfont=dict(size=20, color='#333'), showgrid=False
    ),
    yaxis=dict(
        title="Cumulative Documents", title_font=dict(size=22),
        showgrid=True, gridcolor='#EEEEEE', tickfont=dict(size=20, color='#333'),
        zeroline=False,
        range=[0, cum_totals_df['cum_total'].max() * 1.05] 
    ),
    margin=dict(t=160, l=100, r=40, b=80),
    bargap=0.35,
    height=1200
)

# Output charts to data/ directory
fig_cum.write_image("data/query_results_cumulative.png", width=1600, height=1200, scale=2)
fig_cum.write_html("data/cumulative.html", include_plotlyjs='cdn')

# To display both plots if running in Jupyter/Interactive mode
fig.show()
fig_cum.show()