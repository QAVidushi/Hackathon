# Data Integrity Validator - Feature Documentation

## Table of Contents
1. [Overview](#overview)
2. [Data Upload & Processing](#data-upload--processing)
3. [Field Classification](#field-classification)
4. [Filter System](#filter-system)
5. [Overview Tab](#overview-tab)
6. [Drill Down Tab](#drill-down-tab)
7. [Trend Analysis Tab](#trend-analysis-tab)
8. [Advanced Check Tab](#advanced-check-tab)
9. [Calculation Formulas](#calculation-formulas)

---

## Overview

The Data Integrity Validator is a comprehensive data quality assessment tool that compares two datasets (NetSuite and Salesforce) to identify matches, mismatches, and quality issues.

---

## Data Upload & Processing

### Feature: File Upload
**Location:** Sidebar

**Description:**
- Accepts Excel files (.xlsx format) from NetSuite and Salesforce
- Automatically loads data into memory for processing
- Supports multiple sheets (uses first sheet by default)

**How It Works:**
1. User uploads two Excel files via file uploader
2. Files are read using `pandas.read_excel()` with openpyxl engine
3. Data is stored in DataFrames: `df_netsuite` and `df_salesforce`
4. Date columns are automatically detected and converted to datetime format

**Technical Details:**
```python
df_netsuite = pd.read_excel(netsuite_file, engine="openpyxl")
df_salesforce = pd.read_excel(salesforce_file, engine="openpyxl")

# Auto-detect and convert date columns
for col in df_netsuite.columns:
    if "date" in col.lower():
        df_netsuite[col] = pd.to_datetime(df_netsuite[col], errors="coerce")
```

---

## Field Classification

### Feature: Automatic Field Prioritization
**Location:** Automatically applied, visible in sidebar filters

**Description:**
Fields are automatically classified into three categories based on their uniqueness:
- **Primary Fields:** Top 3 most unique columns (highest uniqueness score)
- **Secondary Fields:** Next 5 most unique columns (medium uniqueness)
- **Tertiary Fields:** Remaining columns (lower uniqueness)

**Calculation:**
```
Uniqueness Score = Number of Unique Values / Total Number of Values
```

**Example:**
- Column with 100 unique values in 100 rows = Score of 1.0 (100%)
- Column with 10 unique values in 100 rows = Score of 0.1 (10%)

**Formula:**
```python
uniqueness_scores = {
    col: df[col].nunique(dropna=True) / len(df[col]) 
    for col in df.columns
}
```

**Why It Matters:**
- Primary fields (like ID, Email) are best for merging data
- Secondary fields provide additional context
- Tertiary fields often contain categorical data

---

## Filter System

### 1. Field Selection Filters
**Location:** Sidebar

**Description:**
Multi-select filters for choosing which fields to analyze.

**How It Works:**
- Users can select/deselect fields from each category
- Default: All fields are selected
- Selected fields are used throughout all tabs for analysis

### 2. Date Range Filter
**Location:** Sidebar

**Description:**
Filters data to a specific date range.

**How It Works:**
1. System auto-detects columns with "date" in the name
2. User selects which date column to use
3. User chooses start and end dates
4. Data is filtered: `start_date <= date <= end_date`

**Calculation:**
```python
filtered_ns = df_netsuite[
    (df_netsuite[date_col] >= start_date) & 
    (df_netsuite[date_col] <= end_date)
]
```

### 3. Account Filter
**Location:** Sidebar

**Description:**
Filters data to specific accounts.

**How It Works:**
1. System auto-detects columns with "account" in the name
2. User selects which account column to use
3. User chooses one or more accounts
4. Only records for selected accounts are shown

**Calculation:**
```python
filtered_ns = df_netsuite[
    df_netsuite[account_col].isin(account_filter)
]
```

---

## Overview Tab

### Feature 1: Overall Data Quality Distribution

**Description:**
Two visualizations showing the overall match vs mismatch status across all data.

**Visualizations:**
1. **Pie Chart:** Percentage breakdown of matches vs mismatches
2. **Bar Chart:** Visual comparison of match and mismatch rates

**Calculations:**

```
Total Match Count = Sum of all matching field values across both datasets
Total Mismatch Count = Sum of all mismatching field values

Match Percentage = (Total Match Count / Total Records) × 100
Mismatch Percentage = (Total Mismatch Count / Total Records) × 100
```

**Example:**
If analyzing 100 records across 5 fields:
- Total cells = 100 × 5 = 500
- Matching cells = 450
- Mismatching cells = 50
- Match Percentage = (450 / 500) × 100 = 90%
- Mismatch Percentage = (50 / 500) × 100 = 10%

### Feature 2: Global Match/Mismatch KPIs

**Description:**
Three key performance indicators showing overall data quality.

**KPI 1: Match Rate**
```
Match Rate = (Total Matches / Total Cells) × 100
```
- Higher is better (indicates data consistency)

**KPI 2: Mismatch Rate**
```
Mismatch Rate = (Total Mismatches / Total Cells) × 100
```
- Lower is better (indicates fewer discrepancies)
- Shown with record count delta

**KPI 3: Null Rate**
```
Null Rate = (Total Null Values / Total Cells) × 100
Total Cells = Number of Rows × Number of Columns
```
- Lower is better (indicates data completeness)
- Shown with null count delta

**Example Calculation:**
- Dataset: 100 rows, 10 columns
- Total Cells = 100 × 10 = 1,000
- Null Values = 50
- Null Rate = (50 / 1,000) × 100 = 5%

### Feature 3: Comprehensive Field-Level Analysis

**Description:**
Sunburst chart showing match vs mismatch breakdown for every field.

**How It Works:**
1. Inner ring: Match vs Mismatch categories
2. Outer ring: Individual fields
3. Size represents count of matches/mismatches
4. Click to zoom into specific categories

**Calculation for Each Field:**
```python
# For records present in both datasets
both_mask = merged_df["_merge"] == "both"
left_vals = merged_df.loc[both_mask, field_x]
right_vals = merged_df.loc[both_mask, field_y]

# Match if values are equal OR both are null
match_count = ((left_vals == right_vals) | 
               (left_vals.isna() & right_vals.isna())).sum()

# Mismatch = records not matching + orphan records
mismatch_count = total_records - match_count + 
                 left_only_count + right_only_count
```

---

## Drill Down Tab

### Feature 1: Match vs Mismatch Overview: All Fields

**Description:**
Comprehensive overview at the top showing all selected fields' match/mismatch status.

**Components:**
1. **Sunburst Chart:** Interactive visualization of all fields
2. **KPI Metrics:**
   - Total Fields: Count of fields being analyzed
   - Total Matches: Sum of matching values across all fields
   - Total Mismatches: Sum of mismatching values across all fields
   - Overall Match Rate: Percentage of matching values

**Calculations:**
```
For each field:
    Match Count = Number of matching values between datasets
    Mismatch Count = Total values - Match Count

Total Matches = Sum(Match Count for all fields)
Total Mismatches = Sum(Mismatch Count for all fields)
Overall Match Rate = (Total Matches / (Total Matches + Total Mismatches)) × 100
```

### Feature 2: Select Category (Primary/Secondary/Tertiary)

**Description:**
Radio button filter to view fields by category with donut charts.

**How It Works:**
1. User selects a category
2. System displays donut charts for all fields in that category
3. Charts are arranged in a 3-column grid
4. Each chart shows match vs mismatch for one field

**Per-Field Calculation:**
```python
# For field in selected category
if field in salesforce_columns:
    matches = (netsuite[field] == salesforce[field]).sum()
else:
    matches = 0

mismatches = total_records - matches
```

**Visual Layout:**
- 3 charts per row
- Field name displayed above each chart
- Color-coded: Green (Match), Orange (Mismatch)

### Feature 3: Drill Down Analysis - Field Details

**Description:**
Select an individual field for comprehensive analysis.

**Metrics Displayed:**

**1. Match Rate**
```
Match Rate = (Match Count / Total Records) × 100
```
- Shows percentage of matching values
- Displays count of matching records

**2. Mismatch Rate**
```
Mismatch Rate = (Mismatch Count / Total Records) × 100
```
- Shows percentage of mismatching values
- Displays count of mismatching records
- Delta shown in inverse color (red = bad)

**3. Null Rate**
```
Null Count = Number of null/NA values in field
Null Rate = (Null Count / Total Records) × 100
```
- Shows percentage of missing values
- Displays count of nulls

**4. Duplicate Rate**
```
Duplicate Count = Number of duplicate values
Duplicate Rate = (Duplicate Count / Total Records) × 100
```
- Shows percentage of repeated values
- Displays count of duplicates

**Visualizations:**
1. **Donut Chart:** Match vs Mismatch breakdown
2. **Bar Chart:** All four quality metrics compared

### Feature 4: All Fields Summary Table

**Description:**
Table showing match/mismatch statistics for all available fields.

**Columns:**
- Field Name
- Matches: Count of matching values
- Mismatches: Count of mismatching values
- Match %: Percentage of matches
- Mismatch %: Percentage of mismatches

**Calculation:**
```python
for field in all_fields:
    total = len(netsuite[field])
    matches = (netsuite[field] == salesforce[field]).sum()
    mismatches = total - matches
    match_pct = (matches / total) × 100
    mismatch_pct = (mismatches / total) × 100
```

---

## Trend Analysis Tab

### Feature 1: Match vs Mismatch Over Time

**Description:**
Line chart showing how match/mismatch rates change over time.

**Requirements:**
- Date column must be selected in sidebar
- Date range filter applied

**Calculation:**
```python
# Group data by date
for each_date in date_range:
    records_on_date = filter_by_date(date)
    
    # For each field, check matches
    for field in selected_fields:
        matches = (netsuite[field] == salesforce[field]).sum()
        mismatches = total - matches
    
    daily_match_rate = (total_matches / total_values) × 100
    daily_mismatch_rate = (total_mismatches / total_values) × 100
```

**X-axis:** Date
**Y-axis:** Percentage (0-100%)
**Lines:**
- Green: Match Rate trend
- Red: Mismatch Rate trend

**Use Case:**
- Identify when data quality improved or degraded
- Spot patterns (e.g., quality drops at month-end)
- Track improvement after data fixes

### Feature 2: Top 10 Mismatched Fields

**Description:**
Bar chart showing fields with the most mismatches.

**Calculation:**
```python
for field in all_fields:
    mismatch_count = (netsuite[field] != salesforce[field]).sum()

# Sort by mismatch count descending
top_10 = sorted_fields[:10]
```

**Visual:**
- Horizontal bar chart
- Color gradient: More mismatches = Darker red
- Fields sorted by mismatch count (highest first)

**Use Case:**
- Prioritize which fields need attention
- Focus data cleansing efforts
- Identify problematic data sources

### Feature 3: Top 10 Accounts with Most Mismatches

**Description:**
Bar chart showing accounts with the most data quality issues.

**Requirements:**
- Account column must be selected in sidebar

**Calculation:**
```python
# Identify mismatched records
mismatch_mask = (merged_df["_merge"] == "left_only") | 
                (merged_df["_merge"] == "right_only")

# Count mismatches per account
for account in unique_accounts:
    mismatch_count = mismatch_mask[
        merged_df[account_col] == account
    ].sum()

# Get top 10
top_10_accounts = sorted_by_mismatch[:10]
```

**Visual:**
- Vertical bar chart
- Color gradient: More mismatches = Darker red
- Accounts sorted by mismatch count

**Use Case:**
- Identify high-risk accounts
- Target specific customers for data verification
- Analyze if certain account types have more issues

---

## Advanced Check Tab

### Feature 1: Data Quality Issues Summary

**Description:**
Donut chart and KPIs showing overall data quality issues.

**Issue Types Tracked:**
1. **Clean Data:** Cells with no issues
2. **Nulls:** Missing values
3. **Duplicates:** Repeated values within a column
4. **Negatives:** Negative numbers (for numeric fields)
5. **Empty Strings:** Text fields with empty values ("")

**Calculations:**

```python
# For each field
nulls = field.isnull().sum()
duplicates = field.duplicated().sum()
negatives = (field < 0).sum() if numeric else 0
empties = (field == "").sum()

# Totals across all fields
total_nulls = sum(nulls for all fields)
total_duplicates = sum(duplicates for all fields)
total_negatives = sum(negatives for all fields)
total_empties = sum(empties for all fields)
total_issues = total_nulls + total_duplicates + total_negatives + total_empties

# Clean data
total_cells = number_of_rows × number_of_columns
clean_data = total_cells - total_issues
```

**KPIs Displayed:**

1. **Total Issues**
```
Total Issues = Nulls + Duplicates + Negatives + Empty Strings
```

2. **Clean Data %**
```
Clean Data % = (Clean Data / Total Cells) × 100
```

3. **Individual Issue Counts**
- Nulls: Count of null values
- Duplicates: Count of duplicate values
- Negatives: Count of negative numbers
- Empty Strings: Count of empty text values

**Example:**
- Dataset: 100 rows × 10 columns = 1,000 cells
- Nulls: 20
- Duplicates: 15
- Negatives: 5
- Empties: 10
- Total Issues: 50
- Clean Data: 1,000 - 50 = 950
- Clean Data %: (950 / 1,000) × 100 = 95%

### Feature 2: Field-Level Quality Checks Table

**Description:**
Detailed table showing quality issues for each field.

**Columns:**
- **Field:** Column name
- **Nulls:** Count of null/missing values
- **Duplicates:** Count of duplicate entries
- **Negatives:** Count of negative numbers (numeric fields only)
- **Empty Strings:** Count of empty text values

**Highlighting:**
- Cells with values > 0 are highlighted in red
- Makes it easy to spot problematic fields

**Calculation per Field:**
```python
nulls = df[field].isnull().sum()
duplicates = df[field].duplicated().sum()

if pd.api.types.is_numeric_dtype(df[field]):
    negatives = (df[field] < 0).sum()
else:
    negatives = 0

empties = (df[field] == "").sum()
```

**Use Case:**
- Identify which fields need data cleansing
- Prioritize data quality improvements
- Track data quality metrics over time

### Feature 3: Orphan Records Analysis

**Description:**
Identifies and displays records that exist in one dataset but not the other.

**Two Types of Orphans:**

**1. NetSuite Orphans**
- Records in NetSuite but missing in Salesforce
- Indicates data not synced to Salesforce

**Calculation:**
```python
merge_key = primary_field  # Usually ID or unique identifier
merged_df = pd.merge(
    netsuite, 
    salesforce, 
    on=merge_key, 
    how="outer", 
    indicator=True
)

netsuite_orphans = merged_df[merged_df["_merge"] == "left_only"]
orphan_count = len(netsuite_orphans)
```

**2. Salesforce Orphans**
- Records in Salesforce but missing in NetSuite
- Indicates data not synced to NetSuite

**Calculation:**
```python
salesforce_orphans = merged_df[merged_df["_merge"] == "right_only"]
orphan_count = len(salesforce_orphans)
```

**Features:**
- Expandable sections showing orphan counts
- Full data table of orphan records
- Download button to export orphan records as CSV
- Color-coded status indicators

**Use Case:**
- Identify sync failures between systems
- Find records that need manual reconciliation
- Audit data migration completeness

---

## Calculation Formulas

### Merging Logic

**How Datasets are Merged:**
```python
# Merge on primary key (usually most unique field)
merged_df = pd.merge(
    df_netsuite,
    df_salesforce,
    left_on=merge_key,
    right_on=merge_key,
    how="outer",  # Keep all records from both sides
    indicator=True  # Add _merge column showing source
)

# _merge values:
# "both" = Record exists in both datasets
# "left_only" = Record only in NetSuite
# "right_only" = Record only in Salesforce
```

### Match Detection

**How System Determines Matches:**
```python
# For each field
match = (value_netsuite == value_salesforce)

# Special cases:
# 1. Both null = considered a match
if pd.isna(value_netsuite) and pd.isna(value_salesforce):
    match = True

# 2. One null, one not = mismatch
if pd.isna(value_netsuite) != pd.isna(value_salesforce):
    match = False

# 3. Different values = mismatch
if value_netsuite != value_salesforce:
    match = False
```

### Percentage Calculations

**Standard Formula:**
```
Percentage = (Part / Whole) × 100
```

**Examples:**

1. **Match Rate:**
```
Match Rate = (Match Count / Total Records) × 100
```

2. **Quality Rate:**
```
Quality Rate = (Clean Data / Total Cells) × 100
```

3. **Issue Rate:**
```
Issue Rate = (Issue Count / Total Values) × 100
```

### Statistical Calculations

**Duplicate Detection:**
```python
# Marks all duplicates after the first occurrence
duplicates = df[field].duplicated()
duplicate_count = duplicates.sum()
```

**Null Detection:**
```python
# Counts all null, NA, NaN, None values
null_count = df[field].isnull().sum()
```

**Uniqueness Score:**
```python
# Ratio of unique values to total values
unique_values = df[field].nunique(dropna=True)
total_values = len(df[field])
uniqueness = unique_values / total_values
```

---

## Color Coding System

### Match Status Colors
- **Green (#4CAF50):** Match - Good data quality
- **Orange/Red (#FF7043):** Mismatch - Needs attention

### Quality Issue Colors
- **Green (#4CAF50):** Clean Data
- **Orange (#FF7043):** Nulls
- **Yellow (#FFC107):** Duplicates
- **Purple (#9C27B0):** Negatives
- **Red (#F44336):** Empty Strings

### Theme Support
- **Light Theme:** Brighter colors for better visibility
- **Dark Theme:** Muted colors to reduce eye strain

---

## Performance Considerations

### Memory Usage
```
Memory Required ≈ (File Size × 3)
- Original data
- Merged data
- Filtered views
```

### Processing Time
- Small files (<1MB): Instant
- Medium files (1-10MB): 1-5 seconds
- Large files (10-50MB): 5-30 seconds
- Very large files (>50MB): May require optimization

### Optimization Tips
1. Use date filters to reduce data volume
2. Select fewer fields for faster processing
3. Filter to specific accounts if possible
4. Close other applications to free memory

---

## Data Privacy & Security

### Data Handling
- All data processed in-memory only
- No data stored on disk
- No data sent to external servers
- Data cleared when browser session ends

### File Requirements
- Must be Excel format (.xlsx)
- Maximum recommended size: 50MB
- Should contain structured data with column headers

---

## Glossary

**Match:** Values in the same field are identical in both datasets
**Mismatch:** Values in the same field differ between datasets
**Orphan:** Record exists in one dataset but not the other
**Null:** Missing or undefined value
**Duplicate:** Value that appears more than once in a column
**Merge Key:** Primary field used to match records between datasets
**Uniqueness Score:** Ratio of unique values to total values (0-1)
**KPI:** Key Performance Indicator - important metric
**Field:** Column in the dataset
**Record:** Row in the dataset

---

**Document Version:** 1.0  
**Last Updated:** December 2025  
**Maintained By:** Vidushi Dubey
