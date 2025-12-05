

# Ensure Streamlit always uses the light theme for this project
import os
config_dir = os.path.join(os.getcwd(), ".streamlit")
os.makedirs(config_dir, exist_ok=True)
with open(os.path.join(config_dir, "config.toml"), "w") as f:
    f.write('[theme]\nbase="light"\n')


# Ensure Streamlit always uses the light theme for this project
import os
config_dir = os.path.join(os.getcwd(), ".streamlit")
os.makedirs(config_dir, exist_ok=True)
with open(os.path.join(config_dir, "config.toml"), "w") as f:
    f.write('[theme]\nbase="light"\n')

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io

# -------------------------
# Page Config
# -------------------------
st.set_page_config(page_title="Advanced Data Integrity Dashboard", layout="wide")

# -------------------------
# Sidebar: Upload & Theme Toggle
# -------------------------
st.sidebar.title("Dashboard Controls")

theme = st.sidebar.radio("Select Theme", ["Light", "Dark"])
# The theme toggle below is for plot color logic only.
# Do not use any custom CSS for backgrounds or sidebar colors.
# To force the app to be light, set [theme]\nbase="light" in .streamlit/config.toml
# This ensures the sidebar and all widgets use the correct theme colors.

# Sidebar Upload
st.sidebar.subheader("Upload Files")
netsuite_file = st.sidebar.file_uploader("Upload NetSuite XLSX", type=["xlsx"])
salesforce_file = st.sidebar.file_uploader("Upload Salesforce XLSX", type=["xlsx"])

# -------------------------
# Professional Header
# -------------------------
st.title("📊 Data Integrity Validator")
st.markdown("**Compare and validate data integrity between NetSuite and Salesforce**")
st.markdown("---")

# Sidebar Filters (always visible)
st.sidebar.subheader("Filters")
primary_cols, secondary_cols, tertiary_cols = [], [], []
date_cols, account_cols = [], []
df_netsuite = None
if netsuite_file:
    try:
        df_netsuite = pd.read_excel(netsuite_file, engine="openpyxl")
        uniqueness_scores = {col: df_netsuite[col].nunique(dropna=True)/len(df_netsuite[col]) if len(df_netsuite[col]) > 0 else 0 for col in df_netsuite.columns}
        sorted_cols = sorted(uniqueness_scores.items(), key=lambda x: x[1], reverse=True)
        sorted_column_names = [col for col, score in sorted_cols]
        primary_cols = sorted_column_names[:3]
        secondary_cols = sorted_column_names[3:8]
        tertiary_cols = sorted_column_names[8:]
        date_cols = [col for col in df_netsuite.columns if "date" in col.lower()]
        account_cols = [col for col in df_netsuite.columns if "account" in col.lower()]
    except Exception:
        pass

selected_primary = st.sidebar.multiselect("Primary Fields", primary_cols, default=primary_cols)
selected_secondary = st.sidebar.multiselect("Secondary Fields", secondary_cols, default=secondary_cols)
selected_tertiary = st.sidebar.multiselect("Tertiary Fields", tertiary_cols, default=tertiary_cols)

date_range = None
date_col = None
if date_cols:
    date_col = st.sidebar.selectbox("Select Date Column", date_cols, key="sidebar_date_col")
    if df_netsuite is not None and date_col:
        # Convert to datetime and handle errors
        df_netsuite[date_col] = pd.to_datetime(df_netsuite[date_col], errors="coerce")
        # Remove any NaT values before finding min/max
        valid_dates = df_netsuite[date_col].dropna()
        if len(valid_dates) > 0:
            min_date, max_date = valid_dates.min(), valid_dates.max()
            date_range = st.sidebar.date_input("Date Range", [min_date, max_date], key="sidebar_date_range")
        else:
            st.sidebar.warning(f"No valid dates found in {date_col}")

account_filter = None
account_col = None
if account_cols:
    account_col = st.sidebar.selectbox("Select Account Column", account_cols, key="sidebar_account_col")
    if df_netsuite is not None and account_col:
        account_filter = st.sidebar.multiselect("Filter by Account", df_netsuite[account_col].dropna().unique(), key="sidebar_account_filter")

# Compare Button
st.sidebar.markdown("---")
compare_button = st.sidebar.button("🔍 Compare Data", type="primary", use_container_width=True)

if netsuite_file and salesforce_file and compare_button:
    if df_netsuite is None:
        df_netsuite = pd.read_excel(netsuite_file, engine="openpyxl")
    df_salesforce = pd.read_excel(salesforce_file, engine="openpyxl")

    # Column Mapping Feature
    st.sidebar.markdown("---")
    st.sidebar.subheader("Column Mapping")
    
    # Choose mapping method
    mapping_method = st.sidebar.radio(
        "Mapping Method",
        ["By Position (Sequential)", "By Name (Manual)"],
        help="Choose how to map Salesforce columns to NetSuite columns"
    )
    
    ns_columns = list(df_netsuite.columns)
    sf_columns = list(df_salesforce.columns)
    
    if mapping_method == "By Position (Sequential)":
        # Automatically map columns by position
        st.sidebar.info("✓ Columns mapped by position (column 1 → column 1, etc.)")
        # Rename Salesforce columns to match NetSuite column names by position
        df_salesforce_renamed = df_salesforce.copy()
        min_cols = min(len(ns_columns), len(sf_columns))
        rename_dict = {sf_columns[i]: ns_columns[i] for i in range(min_cols)}
        df_salesforce_renamed = df_salesforce_renamed.rename(columns=rename_dict)
        df_salesforce = df_salesforce_renamed
        st.sidebar.success(f"✓ {min_cols} columns mapped by position")
    else:
        # Manual column mapping
        st.sidebar.info("Map Salesforce columns to NetSuite columns manually")
        column_mapping = {}
        
        with st.sidebar.expander("Configure Column Mappings", expanded=False):
            st.write("**Map Salesforce → NetSuite**")
            for sf_col in sf_columns:
                # Try to find a matching column name automatically
                default_match = sf_col if sf_col in ns_columns else (ns_columns[0] if ns_columns else None)
                mapped_col = st.selectbox(
                    f"SFDC: {sf_col}",
                    options=["(Skip)"] + ns_columns,
                    index=ns_columns.index(default_match) + 1 if default_match and default_match in ns_columns else 0,
                    key=f"map_{sf_col}"
                )
                if mapped_col != "(Skip)":
                    column_mapping[mapped_col] = sf_col
        
        # Rename Salesforce columns to match NetSuite columns based on mapping
        if column_mapping:
            df_salesforce_renamed = df_salesforce.copy()
            reverse_mapping = {v: k for k, v in column_mapping.items()}
            df_salesforce_renamed = df_salesforce_renamed.rename(columns=reverse_mapping)
            df_salesforce = df_salesforce_renamed
            st.sidebar.success(f"✓ {len(column_mapping)} columns mapped manually")

    # Define tabs after files are uploaded
    tab1, tab2, tab3, tab4 = st.tabs(["🌍 Overview", "🔍 Drill Down", "📈 Trend", "✅ Advanced Check"])

    # Convert date columns to datetime
    for col in df_netsuite.columns:
        if "date" in col.lower():
            df_netsuite[col] = pd.to_datetime(df_netsuite[col], errors="coerce")
    for col in df_salesforce.columns:
        if "date" in col.lower():
            df_salesforce[col] = pd.to_datetime(df_salesforce[col], errors="coerce")

    # Apply filters to both NetSuite and Salesforce
    filtered_ns = df_netsuite.copy()
    filtered_sf = df_salesforce.copy()
    if date_range and len(date_range) == 2 and date_col:
        start_date = pd.to_datetime(date_range[0]).tz_localize(None)
        end_date = pd.to_datetime(date_range[1]).tz_localize(None)
        filtered_ns = filtered_ns[(filtered_ns[date_col].dt.tz_localize(None) >= start_date) & (filtered_ns[date_col].dt.tz_localize(None) <= end_date)]
        if date_col in filtered_sf.columns:
            filtered_sf = filtered_sf[(filtered_sf[date_col].dt.tz_localize(None) >= start_date) & (filtered_sf[date_col].dt.tz_localize(None) <= end_date)]
    if account_filter and account_col:
        filtered_ns = filtered_ns[filtered_ns[account_col].isin(account_filter)]
        if account_col in filtered_sf.columns:
            filtered_sf = filtered_sf[filtered_sf[account_col].isin(account_filter)]

    # Always define merge_key before using it
    merge_key = primary_cols[0] if primary_cols else None
    # Always include merge key, date, and account columns in filtered data
    selected_fields = list(set(selected_primary + selected_secondary + selected_tertiary))
    extra_cols = []
    if merge_key and merge_key not in selected_fields:
        extra_cols.append(merge_key)
    if date_col and date_col not in selected_fields:
        extra_cols.append(date_col)
    if account_col and account_col not in selected_fields:
        extra_cols.append(account_col)
    all_fields = selected_fields + extra_cols
    all_fields = [col for col in all_fields if col]  # remove None
    # Ensure all selected fields are present in both filtered_ns and filtered_sf
    for col in all_fields:
        if col not in filtered_ns.columns:
            filtered_ns[col] = pd.NA
        if col not in filtered_sf.columns:
            filtered_sf[col] = pd.NA
    # Also ensure all_fields are present in both after merge (for sunburst/KPI)
    filtered_ns = filtered_ns.reindex(columns=all_fields, fill_value=pd.NA)
    filtered_sf = filtered_sf.reindex(columns=all_fields, fill_value=pd.NA)
    if not merge_key or merge_key not in filtered_ns.columns or merge_key not in filtered_sf.columns:
        st.warning("Cannot calculate KPIs: Merge key is missing from selected fields.")
    else:
        try:
            merged_df = pd.merge(filtered_ns, filtered_sf, left_on=merge_key, right_on=merge_key, how="outer", indicator=True)
            merged_df["_merge"] = merged_df["_merge"] if "_merge" in merged_df else "concat"
        except ValueError:
            merged_df = pd.concat([filtered_ns, filtered_sf], ignore_index=True)
            merged_df["_merge"] = "concat"

        # ------------------------- 
        # Global KPI Summary (use merged data)
        # -------------------------
        total_match = (merged_df["_merge"] == "both").sum()
        total_mismatch = ((merged_df["_merge"] == "left_only") | (merged_df["_merge"] == "right_only")).sum()
        total_nulls = merged_df.isnull().sum().sum()

        # ...existing code...

    # Global KPI values are now only shown in the Overview tab below the sunburst chart.

    # -------------------------
    # Tab 1: Overview (from merged_df)
    # -------------------------
    with tab1:
        st.header("Global Overview")
        
        # Calculate percentages first for overall distribution
        total_match_sb_temp = 0
        total_mismatch_sb_temp = 0
        
        # Show match vs mismatch for every field in the Excel sheet
        # Use all columns from both uploaded Excel sheets
        all_excel_fields = []
        if netsuite_file:
            all_excel_fields += list(pd.read_excel(netsuite_file, engine="openpyxl").columns)
        if salesforce_file:
            all_excel_fields += list(pd.read_excel(salesforce_file, engine="openpyxl").columns)
        all_excel_fields = list(dict.fromkeys(all_excel_fields))  # remove duplicates, preserve order
        sunburst_data = []
        per_field_stats = []  # For KPI cards
        for col in all_excel_fields:
            # Try to get the correct columns from merged_df (may be col, col_x, col_y)
            col_x = f"{col}_x" if f"{col}_x" in merged_df.columns else col
            col_y = f"{col}_y" if f"{col}_y" in merged_df.columns else col
            if col_x not in merged_df.columns or col_y not in merged_df.columns:
                match_count = 0
                mismatch_count = 0
            else:
                # Only consider rows present in both
                both_mask = merged_df["_merge"] == "both"
                left_vals = merged_df.loc[both_mask, col_x]
                right_vals = merged_df.loc[both_mask, col_y]
                match_mask = (left_vals == right_vals) | (left_vals.isna() & right_vals.isna())
                match_count = match_mask.sum()
                mismatch_count = (~match_mask).sum()
                # Add mismatches for left_only and right_only
                mismatch_count += (merged_df["_merge"] == "left_only").sum() + (merged_df["_merge"] == "right_only").sum()
            sunburst_data.append(["Match", col, match_count])
            sunburst_data.append(["Mismatch", col, mismatch_count])
            per_field_stats.append({"Field": col, "Match": match_count, "Mismatch": mismatch_count})
        
        # Calculate totals for distribution chart
        total_match_sb = sum([row[2] for row in sunburst_data if row[0] == "Match"])
        total_mismatch_sb = sum([row[2] for row in sunburst_data if row[0] == "Mismatch"])
        total_records = total_match_sb + total_mismatch_sb
        match_percentage = (total_match_sb / total_records * 100) if total_records > 0 else 0
        mismatch_percentage = (total_mismatch_sb / total_records * 100) if total_records > 0 else 0
        
        # Overall Data Quality Distribution at the top
        st.subheader("Overall Data Quality Distribution")
        quality_data = pd.DataFrame({
            "Status": ["Match", "Mismatch"],
            "Percentage": [match_percentage, mismatch_percentage],
            "Count": [total_match_sb, total_mismatch_sb]
        })
        
        col1, col2 = st.columns(2)
        with col1:
            fig_pie = px.pie(
                quality_data, 
                values="Percentage", 
                names="Status",
                title="Match vs Mismatch Distribution",
                color="Status",
                color_discrete_map={"Match": "#4CAF50" if theme == "Light" else "#81C784",
                                   "Mismatch": "#FF7043" if theme == "Light" else "#FF8A65"},
                hole=0.4
            )
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            fig_pie.update_layout(
                paper_bgcolor='white' if theme == 'Light' else '#121212',
                plot_bgcolor='white' if theme == 'Light' else '#121212',
                font_color='white' if theme == 'Dark' else 'black'
            )
            st.plotly_chart(fig_pie, use_container_width=True, key="plotly_chart_quality_pie_tab1")
        
        with col2:
            fig_bar = px.bar(
                quality_data,
                x="Status",
                y="Percentage",
                title="Match vs Mismatch Rate Comparison",
                color="Status",
                color_discrete_map={"Match": "#4CAF50" if theme == "Light" else "#81C784",
                                   "Mismatch": "#FF7043" if theme == "Light" else "#FF8A65"},
                text="Percentage"
            )
            fig_bar.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            fig_bar.update_layout(
                paper_bgcolor='white' if theme == 'Light' else '#121212',
                plot_bgcolor='white' if theme == 'Light' else '#121212',
                font_color='white' if theme == 'Dark' else 'black',
                showlegend=False,
                yaxis=dict(range=[0, max(quality_data["Percentage"]) * 1.15])  # Add 15% padding to prevent cutoff
            )
            st.plotly_chart(fig_bar, use_container_width=True, key="plotly_chart_quality_bar_tab1")
        
        # Display Global Match/Mismatch KPIs right after distribution charts
        st.subheader("Global Match/Mismatch KPIs")
        total_cells = merged_df.shape[0] * merged_df.shape[1]
        null_percentage = (total_nulls / total_cells * 100) if total_cells > 0 else 0
        
        kpi_cols = st.columns(3)
        with kpi_cols[0]:
            st.metric(
                label="Match Rate", 
                value=f"{match_percentage:.1f}%", 
                help="Percentage of all field-level matches across both files"
            )
        with kpi_cols[1]:
            st.metric(
                label="Mismatch Rate", 
                value=f"{mismatch_percentage:.1f}%", 
                delta=f"{total_mismatch_sb:,} records",
                delta_color="inverse",
                help="Percentage of all field-level mismatches across both files"
            )
        with kpi_cols[2]:
            st.metric(
                label="Null Rate", 
                value=f"{null_percentage:.1f}%", 
                delta=f"{total_nulls:,} nulls",
                delta_color="inverse",
                help="Percentage of null values across selected data"
            )
        
        # Sunburst chart
        sb_df = pd.DataFrame(sunburst_data, columns=["Status", "Field", "Count"])
        fig_sunburst = px.sunburst(sb_df, path=["Status", "Field"], values="Count", color="Status",
                                   color_discrete_map={"Match": "#4CAF50" if theme == "Light" else "#81C784",
                                                       "Mismatch": "#FF7043" if theme == "Light" else "#FF8A65"},
                                   title="Comprehensive Field-Level Data Integrity Analysis")
        st.plotly_chart(fig_sunburst, use_container_width=True, key="plotly_chart_sunburst_tab1_allfields")

    # -------------------------
    # Tab 2: Drill Down
    # -------------------------
    with tab2:
        # Match vs Mismatch Overview: All Fields - FIRST THING
        st.subheader("Match vs Mismatch Overview: All Fields")
        
        # Build sunburst data for drill down tab
        drill_sunburst_data = []
        total_matches_all = 0
        total_mismatches_all = 0
        
        all_available_fields = selected_primary + selected_secondary + selected_tertiary
        for field in all_available_fields:
            if field in filtered_ns.columns:
                total = len(filtered_ns[field])
                if field in filtered_sf.columns:
                    # Reset indices to ensure alignment for comparison
                    ns_vals = filtered_ns[field].reset_index(drop=True).astype(str)
                    sf_vals = filtered_sf[field].reset_index(drop=True).astype(str)
                    # Use the minimum length to avoid index mismatch
                    min_len = min(len(ns_vals), len(sf_vals))
                    if min_len > 0:
                        matches = (ns_vals[:min_len] == sf_vals[:min_len]).sum()
                    else:
                        matches = 0
                    mismatches = total - matches
                else:
                    matches = 0
                    mismatches = total
                
                drill_sunburst_data.append(["Match", field, matches])
                drill_sunburst_data.append(["Mismatch", field, mismatches])
                total_matches_all += matches
                total_mismatches_all += mismatches
        
        # Create sunburst chart
        drill_sb_df = pd.DataFrame(drill_sunburst_data, columns=["Status", "Field", "Count"])
        fig_drill_sunburst = px.sunburst(
            drill_sb_df, 
            path=["Status", "Field"], 
            values="Count", 
            color="Status",
            color_discrete_map={"Match": "#4CAF50" if theme == "Light" else "#81C784",
                               "Mismatch": "#FF7043" if theme == "Light" else "#FF8A65"},
            title="Field-Level Match vs Mismatch Distribution"
        )
        fig_drill_sunburst.update_layout(
            paper_bgcolor='white' if theme == 'Light' else '#121212',
            plot_bgcolor='white' if theme == 'Light' else '#121212',
            font_color='white' if theme == 'Dark' else 'black'
        )
        st.plotly_chart(fig_drill_sunburst, use_container_width=True, key="plotly_chart_sunburst_drilldown")
        
        # KPI metrics in numbers
        st.subheader("Overall Field Statistics")
        kpi_cols = st.columns(4)
        with kpi_cols[0]:
            st.metric("Total Fields", len(all_available_fields))
        with kpi_cols[1]:
            st.metric("Total Matches", f"{total_matches_all:,}")
        with kpi_cols[2]:
            st.metric("Total Mismatches", f"{total_mismatches_all:,}")
        with kpi_cols[3]:
            total_all = total_matches_all + total_mismatches_all
            match_rate_all = (total_matches_all / total_all * 100) if total_all > 0 else 0
            st.metric("Overall Match Rate", f"{match_rate_all:.1f}%")
        
        st.markdown("---")
        
        # Category selection for filtering fields
        st.subheader("Select Category")
        category_choice = st.radio("Select Category for Drill Down", ["Primary", "Secondary", "Tertiary"], key="drill_radio_tab2b_unique")
        drill_fields = selected_primary if category_choice == "Primary" else selected_secondary if category_choice == "Secondary" else selected_tertiary
        
        # Display donut charts for all fields in the selected category
        if drill_fields:
            st.markdown(f"### {category_choice} Fields - Match vs Mismatch")
            
            # Create a grid layout for donut charts - process all fields
            valid_fields = [col for col in drill_fields if col in filtered_ns.columns]
            
            # Display charts in rows of 3
            for i in range(0, len(valid_fields), 3):
                cols = st.columns(3)
                
                # Fill each of the 3 columns
                for j in range(3):
                    with cols[j]:
                        if i + j < len(valid_fields):
                            col = valid_fields[i + j]
                            st.markdown(f"**{col}**")
                            match_count = filtered_ns[col].isin(filtered_sf[col]).sum() if col in filtered_sf.columns else 0
                            mismatch_count = len(filtered_ns[col]) - match_count
                            
                            fig = go.Figure(data=[go.Pie(
                                labels=['Match', 'Mismatch'], 
                                values=[match_count, mismatch_count], 
                                hole=.4, 
                                textinfo='label+percent+value'
                            )])
                            fig.update_traces(
                                marker=dict(colors=['#4CAF50', '#FF7043'] if theme == 'Light' else ['#81C784', '#FF8A65']),
                                textfont_color='white' if theme == 'Dark' else 'black'
                            )
                            fig.update_layout(
                                paper_bgcolor='white' if theme == 'Light' else '#121212',
                                plot_bgcolor='white' if theme == 'Light' else '#121212',
                                font_color='white' if theme == 'Dark' else 'black',
                                showlegend=True,
                                height=300,
                                margin=dict(l=10, r=10, t=30, b=10)
                            )
                            st.plotly_chart(fig, use_container_width=True, key=f"drill_chart_{category_choice}_{i}_{j}")
                        else:
                            # Add empty space to maintain column structure
                            st.container()
        
        st.markdown("---")
        
        # Drill Down Analysis section
        st.header("Drill Down Analysis")
        
        # Per-field selection from the selected category
        st.subheader("Select Field for Detailed Analysis")
        selected_field = st.selectbox("Choose a field to analyze", drill_fields if drill_fields else all_available_fields, key="drill_field_selector")
        
        if selected_field and selected_field in filtered_ns.columns:
            # Calculate field-level metrics
            total_records = len(filtered_ns[selected_field])
            null_count = filtered_ns[selected_field].isnull().sum()
            duplicate_count = filtered_ns[selected_field].duplicated().sum()
            
            if selected_field in filtered_sf.columns:
                # Reset indices to ensure alignment for comparison
                ns_vals = filtered_ns[selected_field].reset_index(drop=True).astype(str)
                sf_vals = filtered_sf[selected_field].reset_index(drop=True).astype(str)
                min_len = min(len(ns_vals), len(sf_vals))
                if min_len > 0:
                    match_count = (ns_vals[:min_len] == sf_vals[:min_len]).sum()
                else:
                    match_count = 0
                mismatch_count = total_records - match_count
                match_rate = (match_count / total_records * 100) if total_records > 0 else 0
                mismatch_rate = (mismatch_count / total_records * 100) if total_records > 0 else 0
            else:
                match_count = 0
                mismatch_count = total_records
                match_rate = 0
                mismatch_rate = 100
            
            null_rate = (null_count / total_records * 100) if total_records > 0 else 0
            duplicate_rate = (duplicate_count / total_records * 100) if total_records > 0 else 0
            
            # Display field KPIs
            st.markdown(f"### 📊 Field Metrics: **{selected_field}**")
            kpi_cols = st.columns(4)
            with kpi_cols[0]:
                st.metric("Match Rate", f"{match_rate:.1f}%", help=f"{match_count:,} matching records")
            with kpi_cols[1]:
                st.metric("Mismatch Rate", f"{mismatch_rate:.1f}%", delta=f"{mismatch_count:,} records", delta_color="inverse")
            with kpi_cols[2]:
                st.metric("Null Rate", f"{null_rate:.1f}%", delta=f"{null_count:,} nulls", delta_color="inverse")
            with kpi_cols[3]:
                st.metric("Duplicate Rate", f"{duplicate_rate:.1f}%", delta=f"{duplicate_count:,} duplicates", delta_color="inverse")
            
            # Field visualizations
            col1, col2 = st.columns(2)
            
            with col1:
                # Pie chart for match/mismatch
                field_status_data = pd.DataFrame({
                    "Status": ["Match", "Mismatch"],
                    "Count": [match_count, mismatch_count]
                })
                fig_field_pie = px.pie(
                    field_status_data,
                    values="Count",
                    names="Status",
                    title=f"Match vs Mismatch: {selected_field}",
                    color="Status",
                    color_discrete_map={"Match": "#4CAF50" if theme == "Light" else "#81C784",
                                       "Mismatch": "#FF7043" if theme == "Light" else "#FF8A65"},
                    hole=0.4
                )
                fig_field_pie.update_traces(textposition='inside', textinfo='percent+label')
                fig_field_pie.update_layout(
                    paper_bgcolor='white' if theme == 'Light' else '#121212',
                    plot_bgcolor='white' if theme == 'Light' else '#121212',
                    font_color='white' if theme == 'Dark' else 'black'
                )
                st.plotly_chart(fig_field_pie, use_container_width=True, key=f"drill_pie_{selected_field}")
            
            with col2:
                # Bar chart for data quality metrics
                quality_metrics = pd.DataFrame({
                    "Metric": ["Match Rate", "Mismatch Rate", "Null Rate", "Duplicate Rate"],
                    "Percentage": [match_rate, mismatch_rate, null_rate, duplicate_rate],
                    "Color": ["#4CAF50", "#FF7043", "#FFC107", "#9C27B0"]
                })
                fig_field_bar = px.bar(
                    quality_metrics,
                    x="Metric",
                    y="Percentage",
                    title=f"Quality Metrics: {selected_field}",
                    color="Metric",
                    color_discrete_sequence=["#4CAF50", "#FF7043", "#FFC107", "#9C27B0"],
                    text="Percentage"
                )
                fig_field_bar.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                fig_field_bar.update_layout(
                    paper_bgcolor='white' if theme == 'Light' else '#121212',
                    plot_bgcolor='white' if theme == 'Light' else '#121212',
                    font_color='white' if theme == 'Dark' else 'black',
                    showlegend=False,
                    yaxis=dict(range=[0, max(quality_metrics["Percentage"]) * 1.15])  # Add 15% padding to prevent cutoff
                )
                st.plotly_chart(fig_field_bar, use_container_width=True, key=f"drill_bar_{selected_field}")
        else:
            st.info("Please select a field from the dropdown above to view detailed analysis.")
        
        # Per-field summary section
        st.markdown("---")
        st.subheader("All Fields Summary")
        st.write("Overview of match vs mismatch rates across all available fields")
        
        # Calculate metrics for all fields
        field_summary_data = []
        for field in all_available_fields:
            if field in filtered_ns.columns:
                total = len(filtered_ns[field])
                if field in filtered_sf.columns:
                    # Reset indices to ensure alignment for comparison
                    ns_vals = filtered_ns[field].reset_index(drop=True).astype(str)
                    sf_vals = filtered_sf[field].reset_index(drop=True).astype(str)
                    min_len = min(len(ns_vals), len(sf_vals))
                    if min_len > 0:
                        matches = (ns_vals[:min_len] == sf_vals[:min_len]).sum()
                    else:
                        matches = 0
                    mismatches = total - matches
                    match_pct = (matches / total * 100) if total > 0 else 0
                    mismatch_pct = (mismatches / total * 100) if total > 0 else 0
                else:
                    matches = 0
                    mismatches = total
                    match_pct = 0
                    mismatch_pct = 100
                
                field_summary_data.append({
                    "Field": field,
                    "Matches": matches,
                    "Mismatches": mismatches,
                    "Match %": match_pct,
                    "Mismatch %": mismatch_pct
                })
        
        if field_summary_data:
            summary_df = pd.DataFrame(field_summary_data)
            
            # Display summary table without styling (to avoid matplotlib dependency)
            st.dataframe(summary_df, use_container_width=True)

    # ------------------------- 
    # Tab 3: Trend
    # -------------------------
    with tab3:
        st.header("Trend Analysis")

        # 2. Field-level match rate comparison (bar chart) - moved outside date_cols check
        st.subheader("Field Match Rate Comparison")
        field_match_data = []
        for col in selected_primary + selected_secondary[:5]:  # Top fields
            if col in filtered_ns.columns and col in filtered_sf.columns:
                ns_vals = filtered_ns[col].reset_index(drop=True).astype(str)
                sf_vals = filtered_sf[col].reset_index(drop=True).astype(str)
                min_len = min(len(ns_vals), len(sf_vals))
                match_count = (ns_vals[:min_len] == sf_vals[:min_len]).sum() if min_len > 0 else 0
                total_count = len(filtered_ns[col])
                match_rate = (match_count / total_count * 100) if total_count > 0 else 0
                field_match_data.append({"Field": col, "Match Rate (%)": match_rate})
        
        if field_match_data:
            field_match_df = pd.DataFrame(field_match_data)
            fig_field_match = px.bar(field_match_df, x="Field", y="Match Rate (%)", 
                                    title="Match Rate by Field",
                                    color="Match Rate (%)",
                                    color_continuous_scale=["#FF7043", "#FFD54F", "#4CAF50"])
            fig_field_match.update_layout(paper_bgcolor='white' if theme == 'Light' else '#121212',
                                        plot_bgcolor='white' if theme == 'Light' else '#121212',
                                        font_color='white' if theme == 'Dark' else 'black')
            st.plotly_chart(fig_field_match, use_container_width=True, key="plotly_chart_field_match_tab3")
        else:
            st.info("No matching fields available for comparison.")

        # 3. Heatmap: Field correlation with match quality
        st.subheader("Data Quality Heatmap")
        heatmap_data = []
        for col in selected_primary + selected_secondary[:5]:
            if col in filtered_ns.columns:
                nulls = filtered_ns[col].isnull().sum()
                duplicates = filtered_ns[col].duplicated().sum()
                if col in filtered_sf.columns:
                    ns_vals = filtered_ns[col].reset_index(drop=True).astype(str)
                    sf_vals = filtered_sf[col].reset_index(drop=True).astype(str)
                    min_len = min(len(ns_vals), len(sf_vals))
                    matches = (ns_vals[:min_len] == sf_vals[:min_len]).sum() if min_len > 0 else 0
                else:
                    matches = 0
                total = len(filtered_ns[col])
                heatmap_data.append({
                    "Field": col,
                    "Null Rate (%)": (nulls / total * 100) if total > 0 else 0,
                    "Duplicate Rate (%)": (duplicates / total * 100) if total > 0 else 0,
                    "Match Rate (%)": (matches / total * 100) if total > 0 else 0
                })
        
        if heatmap_data:
            heatmap_df = pd.DataFrame(heatmap_data)
            heatmap_df = heatmap_df.set_index("Field")
            fig_heatmap = px.imshow(heatmap_df.T, 
                                   title="Data Quality Metrics Heatmap",
                                   labels=dict(x="Field", y="Metric", color="Percentage"),
                                   color_continuous_scale="RdYlGn_r",
                                   aspect="auto")
            fig_heatmap.update_layout(paper_bgcolor='white' if theme == 'Light' else '#121212',
                                     plot_bgcolor='white' if theme == 'Light' else '#121212',
                                     font_color='white' if theme == 'Dark' else 'black')
            st.plotly_chart(fig_heatmap, use_container_width=True, key="plotly_chart_heatmap_tab3")
        else:
            st.info("No field data available for heatmap.")
        
        # Show available date columns for debugging
        if not date_cols:
            with st.expander("ℹ️ Time-based charts info"):
                st.info("No date columns detected. Date columns must have 'date' in their name.")
                st.write("**Available columns:**", list(filtered_ns.columns))

        if date_cols and date_col:
            # 1. Monthly match vs mismatch (stacked bar)
            merged_month = merged_df.copy()
            if date_col in merged_month.columns:
                # Ensure date column is datetime type
                merged_month[date_col] = pd.to_datetime(merged_month[date_col], errors="coerce")
                # Remove rows with invalid dates
                merged_month = merged_month[merged_month[date_col].notna()]
                if len(merged_month) > 0:
                    merged_month["Month"] = merged_month[date_col].dt.to_period("M").astype(str)
                    match_mask = merged_month["_merge"] == "both"
                    mismatch_mask = (merged_month["_merge"] == "left_only") | (merged_month["_merge"] == "right_only")
                    match_month = merged_month[match_mask].groupby("Month").size().reset_index(name="Match")
                    mismatch_month = merged_month[mismatch_mask].groupby("Month").size().reset_index(name="Mismatch")
                    match_mismatch = pd.merge(match_month, mismatch_month, on="Month", how="outer").fillna(0)
                    match_mismatch = match_mismatch.sort_values("Month")
                    fig_mm = go.Figure()
                    fig_mm.add_trace(go.Bar(x=match_mismatch["Month"], y=match_mismatch["Match"], name="Match", marker_color="#4CAF50"))
                    fig_mm.add_trace(go.Bar(x=match_mismatch["Month"], y=match_mismatch["Mismatch"], name="Mismatch", marker_color="#FF7043"))
                    fig_mm.update_layout(barmode='stack', title="Monthly Match vs Mismatch Trend",
                                        paper_bgcolor='white' if theme == 'Light' else '#121212',
                                        plot_bgcolor='white' if theme == 'Light' else '#121212',
                                        font_color='white' if theme == 'Dark' else 'black')
                    st.plotly_chart(fig_mm, use_container_width=True, key="plotly_chart_trend_matchmismatch_tab3")

            # 4. Cumulative match rate trend
            if date_col in merged_df.columns:
                st.subheader("Cumulative Match Rate Over Time")
                merged_cumulative = merged_df.copy()
                # Ensure date column is datetime type
                merged_cumulative[date_col] = pd.to_datetime(merged_cumulative[date_col], errors="coerce")
                # Remove rows with invalid dates
                merged_cumulative = merged_cumulative[merged_cumulative[date_col].notna()]
                if len(merged_cumulative) > 0:
                    merged_cumulative = merged_cumulative.sort_values(date_col)
                    merged_cumulative["is_match"] = merged_cumulative["_merge"] == "both"
                    merged_cumulative["cum_match"] = merged_cumulative["is_match"].cumsum()
                    merged_cumulative["cum_total"] = range(1, len(merged_cumulative) + 1)
                    merged_cumulative["cum_rate"] = merged_cumulative["cum_match"] / merged_cumulative["cum_total"]
                    merged_cumulative["Month"] = merged_cumulative[date_col].dt.to_period("M").astype(str)
                    cum_month = merged_cumulative.groupby("Month").agg({"cum_rate": "max"}).reset_index()
                    fig_cum = px.line(cum_month, x="Month", y="cum_rate", 
                                     title="Cumulative Match Rate Trend",
                                     labels={"cum_rate": "Cumulative Match Rate"},
                                     markers=True)
                    fig_cum.update_layout(paper_bgcolor='white' if theme == 'Light' else '#121212',
                                         plot_bgcolor='white' if theme == 'Light' else '#121212',
                                         font_color='white' if theme == 'Dark' else 'black')
                    st.plotly_chart(fig_cum, use_container_width=True, key="plotly_chart_trend_cumrate_tab3")
        else:
            st.info("No date columns available for time-based trend analysis.")

        # 5. Top 10 accounts/entities with most mismatches
        if account_col and account_col in merged_df.columns:
            st.subheader("Top Accounts with Mismatches")
            mismatch_mask = (merged_df["_merge"] == "left_only") | (merged_df["_merge"] == "right_only")
            mismatch_accounts = merged_df[mismatch_mask][account_col].value_counts().nlargest(10).reset_index()
            mismatch_accounts.columns = [account_col, "Mismatch Count"]
            fig_acc = px.bar(mismatch_accounts, x=account_col, y="Mismatch Count", 
                            title="Top 10 Accounts with Most Mismatches",
                            color="Mismatch Count",
                            color_continuous_scale="Reds")
            fig_acc.update_layout(paper_bgcolor='white' if theme == 'Light' else '#121212',
                                 plot_bgcolor='white' if theme == 'Light' else '#121212',
                                 font_color='white' if theme == 'Dark' else 'black')
            st.plotly_chart(fig_acc, use_container_width=True, key="plotly_chart_trend_accounts_tab3")

    # -------------------------
    # Tab 4: Advanced Check
    # -------------------------
    with tab4:
        st.header("Advanced Data Quality Checks")
        
        # Calculate summary metrics for all checks
        checks = []
        total_nulls = 0
        total_duplicates = 0
        total_negatives = 0
        total_empties = 0
        
        for col in filtered_ns.columns:
            nulls = filtered_ns[col].isnull().sum()
            duplicates = filtered_ns[col].duplicated().sum()
            negatives = (filtered_ns[col] < 0).sum() if pd.api.types.is_numeric_dtype(filtered_ns[col]) else 0
            empties = (filtered_ns[col] == "").sum()
            checks.append([col, nulls, duplicates, negatives, empties])
            total_nulls += nulls
            total_duplicates += duplicates
            total_negatives += negatives
            total_empties += empties
        
        # Display summary donut chart at the top
        st.subheader("Data Quality Issues Summary")
        total_issues = total_nulls + total_duplicates + total_negatives + total_empties
        total_cells = filtered_ns.shape[0] * filtered_ns.shape[1]
        clean_records = total_cells - total_issues
        
        summary_data = pd.DataFrame({
            "Category": ["Clean Data", "Nulls", "Duplicates", "Negatives", "Empty Strings"],
            "Count": [clean_records, total_nulls, total_duplicates, total_negatives, total_empties]
        })
        
        # Donut chart
        fig_summary = px.pie(
            summary_data,
            values="Count",
            names="Category",
            title="Data Quality Overview",
            hole=0.4,
            color="Category",
            color_discrete_map={
                "Clean Data": "#4CAF50" if theme == "Light" else "#81C784",
                "Nulls": "#FF7043" if theme == "Light" else "#FF8A65",
                "Duplicates": "#FFC107" if theme == "Light" else "#FFD54F",
                "Negatives": "#9C27B0" if theme == "Light" else "#BA68C8",
                "Empty Strings": "#F44336" if theme == "Light" else "#EF5350"
            }
        )
        fig_summary.update_traces(textposition='inside', textinfo='percent+label')
        fig_summary.update_layout(
            paper_bgcolor='white' if theme == 'Light' else '#121212',
            plot_bgcolor='white' if theme == 'Light' else '#121212',
            font_color='white' if theme == 'Dark' else 'black'
        )
        st.plotly_chart(fig_summary, use_container_width=True, key="advanced_check_summary_donut")
        
        # KPI cards in horizontal layout
        kpi_cols = st.columns(6)
        with kpi_cols[0]:
            st.metric("Total Issues", f"{total_issues:,}")
        with kpi_cols[1]:
            st.metric("Clean Data %", f"{(clean_records/total_cells*100):.1f}%")
        with kpi_cols[2]:
            st.metric("Nulls", f"{total_nulls:,}")
        with kpi_cols[3]:
            st.metric("Duplicates", f"{total_duplicates:,}")
        with kpi_cols[4]:
            st.metric("Negatives", f"{total_negatives:,}")
        with kpi_cols[5]:
            st.metric("Empty Strings", f"{total_empties:,}")
        
        st.markdown("---")
        
        # Detailed checks table
        st.subheader("Field-Level Quality Checks")
        check_df = pd.DataFrame(checks, columns=["Field", "Nulls", "Duplicates", "Negatives", "Empty Strings"])
        
        # Highlight non-zero values
        def highlight_nonzero(val):
            if isinstance(val, (int, float)) and val > 0:
                return 'background-color: #FF7043; color: white'
            return ''
        
        styled_df = check_df.style.applymap(highlight_nonzero, subset=["Nulls", "Duplicates", "Negatives", "Empty Strings"])
        st.dataframe(styled_df, use_container_width=True)
        
        # Orphan Records Section
        st.subheader("Orphan Records Analysis")
        
        # NetSuite Orphans (records in NetSuite but not in Salesforce)
        netsuite_orphans = merged_df[merged_df["_merge"] == "left_only"]
        with st.expander(f"🔴 NetSuite Orphans ({len(netsuite_orphans)} records)"):
            if len(netsuite_orphans) > 0:
                st.info(f"Records present in NetSuite but missing in Salesforce: {len(netsuite_orphans)}")
                # Show only columns from the original NetSuite data (ending with _x)
                ns_cols = [col for col in netsuite_orphans.columns if col.endswith("_x") or col == merge_key]
                if ns_cols:
                    display_orphans_ns = netsuite_orphans[ns_cols].copy()
                    # Remove _x suffix for cleaner display
                    display_orphans_ns.columns = [col.replace("_x", "") for col in display_orphans_ns.columns]
                    st.dataframe(display_orphans_ns, use_container_width=True)
                else:
                    st.dataframe(netsuite_orphans.drop(columns=["_merge"], errors="ignore"), use_container_width=True)
                
                # Download button
                csv = display_orphans_ns.to_csv(index=False) if ns_cols else netsuite_orphans.to_csv(index=False)
                st.download_button(
                    label="📥 Download NetSuite Orphans",
                    data=csv,
                    file_name="netsuite_orphans.csv",
                    mime="text/csv",
                    key="download_ns_orphans"
                )
            else:
                st.success("No orphan records found in NetSuite!")
        
        # Salesforce Orphans (records in Salesforce but not in NetSuite)
        salesforce_orphans = merged_df[merged_df["_merge"] == "right_only"]
        with st.expander(f"🔵 Salesforce Orphans ({len(salesforce_orphans)} records)"):
            if len(salesforce_orphans) > 0:
                st.info(f"Records present in Salesforce but missing in NetSuite: {len(salesforce_orphans)}")
                # Show only columns from the original Salesforce data (ending with _y)
                sf_cols = [col for col in salesforce_orphans.columns if col.endswith("_y") or col == merge_key]
                if sf_cols:
                    display_orphans_sf = salesforce_orphans[sf_cols].copy()
                    # Remove _y suffix for cleaner display
                    display_orphans_sf.columns = [col.replace("_y", "") for col in display_orphans_sf.columns]
                    st.dataframe(display_orphans_sf, use_container_width=True)
                else:
                    st.dataframe(salesforce_orphans.drop(columns=["_merge"], errors="ignore"), use_container_width=True)
                
                # Download button
                csv = display_orphans_sf.to_csv(index=False) if sf_cols else salesforce_orphans.to_csv(index=False)
                st.download_button(
                    label="📥 Download Salesforce Orphans",
                    data=csv,
                    file_name="salesforce_orphans.csv",
                    mime="text/csv",
                    key="download_sf_orphans"
                )
            else:
                st.success("No orphan records found in Salesforce!")

elif netsuite_file and salesforce_file and not compare_button:
    st.info("👆 Click the '🔍 Compare Data' button in the sidebar to start the analysis.")
else:
    st.warning("📁 Please upload both NetSuite and Salesforce files from the sidebar to begin.")
