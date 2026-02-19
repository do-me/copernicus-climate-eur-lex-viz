# /// script
# dependencies = [
#   "duckdb",
#   "pandas",
#   "plotly"
# ]
# ///

# install uv, then

import duckdb
import plotly.express as px
import pandas as pd
import plotly.graph_objects as go

con = duckdb.connect()
df = con.execute(f"""
SELECT 
    * EXCLUDE text,
    -- Extracts the specific match from the title as a new column
    lower(regexp_extract(title, '(?i)^(decision|regulation|directive|communication|joint communication|commission delegated regulation|commission implementing regulation)', 1)) AS category
FROM 'EUR-LEX/files/*/*.parquet' 
            
WHERE 
    CAST(date AS DATE) >= '2014-01-01'
    --AND CAST(date AS DATE) <= '2024-12-31'
    
    -- 1. Must contain Copernicus
    AND regexp_matches(text, '(?i)copernicus')
    
    -- 2. AND must contain ANY of these words
    AND regexp_matches(text, '(?i)climate|carbon|ghg|emissions')
            
    -- 3. AND title must start with ANY of these words
    AND regexp_matches(title, '^(?i)(decision|regulation|directive|communication|joint communication|commission delegated regulation|commission implementing regulation)')
            
ORDER BY date DESC
""").df()

con.close()

# 1. Data Preparation
df['year'] = pd.to_datetime(df['date']).dt.year
plot_df = df.groupby(['year', 'category']).size().reset_index(name='count')

# Calculate yearly totals for the labels on top
totals_df = plot_df.groupby('year')['count'].sum().reset_index(name='total')

# Calculate percentages for the tooltips
yearly_totals = plot_df.groupby('year')['count'].transform('sum')
plot_df['percentage'] = (plot_df['count'] / yearly_totals * 100).round(1)

# 2. Scientific Palette
sci_palette = ['#E64B35', '#4DBBD5', '#00A087', '#3C5488', '#F39B7F', '#8491B0', '#91D1C2']

# 3. Create the Base Plot
fig = px.bar(
    plot_df, 
    x='year', 
    y='count', 
    color='category',
    text_auto=True, 
    color_discrete_sequence=sci_palette,
    template='plotly_white',
    barmode='stack',
    category_orders={"year": sorted(plot_df['year'].unique())}
)

# 4. Add the Cumulative Totals on top (Scatter trace)
fig.add_trace(go.Scatter(
    x=totals_df['year'],
    y=totals_df['total'],
    mode='text',
    text=totals_df['total'],
    textposition='top center',
    textfont=dict(family="Arial", size=22, color="black"), # Large bold total
    showlegend=False,
    hoverinfo='skip'
))

# 5. FIX: Apply Bar-specific styling ONLY to Bar traces
fig.update_traces(
    selector=dict(type='bar'), # <--- This prevents the Scatter trace error
    hovertemplate="<b>%{fullData.name}</b><br>Count: %{y}<br>Share: %{customdata[0]}%<extra></extra>",
    customdata=plot_df[['percentage']].values,
    marker_line_width=0,
    textfont=dict(size=16, color="white"), 
    textposition='inside',
    insidetextanchor='middle'
)

# 6. Global Layout Scaling
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
        tickfont=dict(size=20, color='#333'),
        showgrid=False
    ),
    yaxis=dict(
        title="Number of Documents", title_font=dict(size=22),
        showgrid=True, gridcolor='#EEEEEE', tickfont=dict(size=20, color='#333'),
        zeroline=False, dtick=5,
        range=[0, totals_df['total'].max() + 4] # Extra headroom for total labels
    ),
    margin=dict(t=160, l=100, r=40, b=80),
    bargap=0.35,
    height=1200
)

# Show and Save
fig.show()
fig.write_html("index.html", include_plotlyjs='cdn')
