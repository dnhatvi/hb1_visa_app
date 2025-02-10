import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Page configuration
st.set_page_config(page_title="H-1B Visa Dashboard", layout="wide")

# Custom CSS for better styling
st.markdown("""
    <style>
    .metric-container {
        font-size: 18px !important;
        padding: 0.5rem !important;
        margin-bottom: 0.5rem !important;
    }
    .metric-container p {
        font-size: 18px !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    .small-header {
        font-size: 22px !important;
        margin-bottom: 0.5rem !important;
    }
    </style>
""", unsafe_allow_html=True)

# Load Data
@st.cache_data
def load_data():
    df = pd.read_parquet('employer_info.parquet')
    df.columns = df.columns.str.strip()
    # Data Preprocessing
    df = df.rename(columns={
        "Fiscal Year": "Year",
        "Employer (Petitioner) Name": "Employer Name",
        "Petitioner City": "City",
        "Petitioner State": "State",
        "Industry (NAICS) Code": "Industry", 
        "Initial Approval": "Initial_Approval", 
        "Initial Denial": "Initial_Denial", 
        "Continuing Approval": "Continuing_Approval", 
        "Continuing Denial": "Continuing_Denial"
    })
    
    df["Total_Approvals"] = df["Initial_Approval"] + df["Continuing_Approval"]
    df["Total_Denials"] = df["Initial_Denial"] + df["Continuing_Denial"]
    return df

df = load_data()

# Calculate YoY changes
def calculate_yoy_change(current_year, previous_year):
    if previous_year == 0:
        return 0
    return ((current_year - previous_year) / previous_year) * 100

# Main title
st.title("🎯 H-1B Visa Analytics Dashboard")

# Define target industries
target_industries = [
    "54 - Professional, Scientific, and Technical Services",
    "31-33 - Manufacturing",
    "44-45 - Retail Trade",
    "48-49 - Transportation and Warehousing",
    "21 - Mining, Quarrying, and Oil and Gas Extraction"
]

# Sidebar for year selection only
with st.sidebar:
    st.header("Filters")
    years = sorted(df["Year"].unique())
    selected_years = st.multiselect("Select Years", years, default=years)

# Filter data by years
year_filtered_df = df[df["Year"].isin(selected_years)]

# KPI Metrics Section - Overall Totals
st.header("📊 Key Metrics")
col1, col2 = st.columns(2)

# Calculate total approvals and YoY changes for all industries
yearly_approvals = year_filtered_df.groupby("Year")["Total_Approvals"].sum()
yearly_denials = year_filtered_df.groupby("Year")["Total_Denials"].sum()

with col1:
    st.markdown('<p class="small-header">Total Approvals by Year (with YoY changes)</p>', unsafe_allow_html=True)
    for year in selected_years:
        current_approvals = yearly_approvals.get(year, 0)
        previous_approvals = yearly_approvals.get(year-1, 0) if year-1 in yearly_approvals.index else 0
        yoy_change = calculate_yoy_change(current_approvals, previous_approvals)
        
        metric_text = f"{year}: {current_approvals:,.0f}"
        if yoy_change != 0:
            metric_text += f" ({yoy_change:+.1f}% YoY)"
        st.markdown(f'<div class="metric-container"><p>{metric_text}</p></div>', unsafe_allow_html=True)

with col2:
    st.markdown('<p class="small-header">Total Denials by Year (with YoY changes)</p>', unsafe_allow_html=True)
    for year in selected_years:
        current_denials = yearly_denials.get(year, 0)
        previous_denials = yearly_denials.get(year-1, 0) if year-1 in yearly_denials.index else 0
        yoy_change = calculate_yoy_change(current_denials, previous_denials)
        
        metric_text = f"{year}: {current_denials:,.0f}"
        if yoy_change != 0:
            metric_text += f" ({yoy_change:+.1f}% YoY)"
        st.markdown(f'<div class="metric-container"><p>{metric_text}</p></div>', unsafe_allow_html=True)

# Overall Trend Chart
fig_trend = go.Figure()
fig_trend.add_trace(go.Bar(
    x=yearly_approvals.index,
    y=yearly_approvals.values,
    name="Approvals",
    marker_color='rgb(26, 118, 255)'
))
fig_trend.add_trace(go.Bar(
    x=yearly_denials.index,
    y=yearly_denials.values,
    name="Denials",
    marker_color='rgb(255, 79, 79)'
))
fig_trend.update_layout(
    title="Overall Approvals and Denials Trend",
    barmode='group',
    xaxis_title="Year",
    yaxis_title="Number of Cases",
    height=500
)
st.plotly_chart(fig_trend, use_container_width=True)

# Get top 10 industries by total approvals
top_10_industries = year_filtered_df.groupby('Industry')['Total_Approvals'].sum().nlargest(10).index

# Create a copy of the dataframe and modify industry column for non-top-10
df_for_trend = year_filtered_df.copy()
df_for_trend['Industry_Category'] = df_for_trend['Industry'].apply(
    lambda x: x if x in top_10_industries else 'Others'
)

# Create pivot table with top 10 industries and Others
industry_yearly = df_for_trend.pivot_table(
    values="Total_Approvals",
    index="Year",
    columns="Industry_Category",
    aggfunc="sum"
).fillna(0)

# Sort the columns based on the first year's values (highest to lowest)
first_year = industry_yearly.index[0]
sorted_columns = industry_yearly.loc[first_year].sort_values(ascending=False).index
industry_yearly = industry_yearly[sorted_columns]

# Display the sorted data table first
st.subheader("Industry Approval Numbers by Year")
st.dataframe(
    industry_yearly.round(0).astype(int).style.format(thousands=","),
    use_container_width=True
)

# Create line chart with sorted industries
fig_industry_trend = px.line(
    industry_yearly,
    title="Industry Trends Over Time (Top 10 Industries)",
    labels={"value": "Total Approvals", "Industry_Category": "Industry"},
    width=1200
)

# Update layout for better readability
fig_industry_trend.update_layout(
    height=600,
    xaxis=dict(
        tickmode='array',
        ticktext=[str(int(year)) for year in industry_yearly.index],
        tickvals=industry_yearly.index,
        dtick=1,
        tickformat="d"
    ),
    legend=dict(
        orientation="v",
        yanchor="top",
        y=1,
        xanchor="left",
        x=1.02
    ),
    showlegend=True,
    margin=dict(r=200)  # Add right margin for legend
)

# Update line styles - make "Others" dashed and grey
for trace in fig_industry_trend.data:
    if trace.name == "Others":
        trace.line.dash = 'dash'
        trace.line.color = 'grey'

st.plotly_chart(fig_industry_trend, use_container_width=True)

# Supply Chain Industry Analysis
st.header("🏢 Supply Chain Industry Analysis")

# Filter for target industries
supply_chain_df = year_filtered_df[year_filtered_df["Industry"].isin(target_industries)]

# Total approvals by supply chain industry
industry_approvals = supply_chain_df.groupby("Industry")["Total_Approvals"].sum().sort_values(ascending=True)
fig_industry = px.bar(
    industry_approvals,
    orientation='h',
    title="Total Approvals by Supply Chain Industry",
    labels={"value": "Total Approvals", "Industry": "Industry"}
)
fig_industry.update_layout(height=400)
st.plotly_chart(fig_industry, use_container_width=True)

# Industry trends over time
# Industry trends over time
industry_yearly = supply_chain_df.pivot_table(
    values="Total_Approvals",
    index="Year",
    columns="Industry",
    aggfunc="sum"
).fillna(0)

fig_industry_trend = px.line(
    industry_yearly,
    title="Supply Chain Industry Trends Over Time",
    labels={"value": "Total Approvals", "variable": "Industry"}
)

# Update x-axis settings to show only whole years
fig_industry_trend.update_layout(
    height=500,
    xaxis=dict(
        tickmode='array',
        ticktext=[str(int(year)) for year in industry_yearly.index],
        tickvals=industry_yearly.index,
        dtick=1,  # Force 1-year intervals
        tickformat="d"  # Display as integers
    )
)

st.plotly_chart(fig_industry_trend, use_container_width=True)

# Top Companies Section
st.header("🏆 Top Companies by Supply Chain Industry")

# Create tabs for each target industry
tabs = st.tabs(target_industries)

for tab, industry in zip(tabs, target_industries):
    with tab:
        industry_companies = supply_chain_df[supply_chain_df["Industry"] == industry]
        top_companies = industry_companies.groupby("Employer Name")["Total_Approvals"].sum().nlargest(30)
        
        fig_companies = px.bar(
            top_companies,
            title=f"Top 30 Companies in {industry}",
            labels={"value": "Total Approvals", "Employer Name": "Company"}
        )
        fig_companies.update_layout(height=500)
        st.plotly_chart(fig_companies, use_container_width=True)

# Optional: Raw Data Section with expander
# Initialize session state for reset
# Convert NaN (None) to an empty string for State & City to avoid sorting issues
supply_chain_df["State"] = supply_chain_df["State"].fillna("").astype(str)
supply_chain_df["City"] = supply_chain_df["City"].fillna("").astype(str)

# Initialize session state for reset
if "reset" not in st.session_state:
    st.session_state.reset = False

with st.expander("Show Raw Data"):
    # Reset button
    if st.button("Reset Filters"):
        st.session_state.reset = True
    else:
        st.session_state.reset = False

    # Default selections
    default_state = "All"
    default_city = "All"
    default_industry = supply_chain_df["Industry"].unique().tolist()  # Ensure it's always populated
    default_search = ""

    # Filters (Ensure sorting works correctly)
    selected_state = st.selectbox("Filter by State:", ["All"] + sorted(supply_chain_df["State"].unique(), key=str))
    selected_city = st.selectbox("Filter by City:", ["All"] + sorted(supply_chain_df["City"].unique(), key=str))
    selected_industry = st.multiselect("Select Industry:", supply_chain_df["Industry"].unique(), default=default_industry)
    search_company = st.text_input("Search Employer Name:", value=default_search)

    # Apply filters
    filtered_df = supply_chain_df.copy()

    if selected_state != "All":
        filtered_df = filtered_df[filtered_df["State"] == selected_state]

    if selected_city != "All":
        filtered_df = filtered_df[filtered_df["City"] == selected_city]

    if selected_industry:
        filtered_df = filtered_df[filtered_df["Industry"].isin(selected_industry)]

    if search_company:
        filtered_df = filtered_df[filtered_df["Employer Name"].str.contains(search_company, case=False, na=False)]

    # Display filtered data
    st.dataframe(filtered_df)