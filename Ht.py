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
import requests
import json
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import webbrowser
import urllib.parse
import tempfile
import subprocess
import platform
import base64
import numpy as np
from collections import Counter
import time
import pickle
from pathlib import Path

# -------------------------
# Comparison History Management
# -------------------------
def save_comparison_history(comparison_data):
    """Save comparison results to history file."""
    history_file = Path("comparison_history.pkl")
    
    if history_file.exists():
        with open(history_file, 'rb') as f:
            history = pickle.load(f)
    else:
        history = []
    
    history.append(comparison_data)
    
    # Keep only last 10 comparisons
    if len(history) > 10:
        history = history[-10:]
    
    with open(history_file, 'wb') as f:
        pickle.dump(history, f)

def load_comparison_history():
    """Load comparison history from file."""
    history_file = Path("comparison_history.pkl")
    
    if history_file.exists():
        with open(history_file, 'rb') as f:
            return pickle.load(f)
    return []

# -------------------------
# Quick Fix Generator Functions
# -------------------------
def generate_sql_fixes(mismatches_df, field_name, source='netsuite', target='salesforce'):
    """Generate SQL UPDATE statements to fix mismatches."""
    sql_statements = []
    
    for idx, row in mismatches_df.head(10).iterrows():  # Show first 10
        if source == 'netsuite':
            old_value = row.get('NetSuite', '')
            new_value = row.get('Salesforce', '')
        else:
            old_value = row.get('Salesforce', '')
            new_value = row.get('NetSuite', '')
        
        # Escape single quotes in SQL
        new_value_escaped = str(new_value).replace("'", "''")
        old_value_escaped = str(old_value).replace("'", "''")
        
        sql = f"UPDATE records SET {field_name} = '{new_value_escaped}' WHERE {field_name} = '{old_value_escaped}';"
        sql_statements.append(sql)
    
    return '\n'.join(sql_statements)

def generate_api_fixes(mismatches_df, field_name):
    """Generate API call templates for bulk updates."""
    api_template = {
        "endpoint": "/api/v1/records/bulk-update",
        "method": "POST",
        "payload": []
    }
    
    for idx, row in mismatches_df.head(10).iterrows():
        record_update = {
            "record_id": row.get('Record #', idx),
            "field": field_name,
            "old_value": str(row.get('NetSuite', '')),
            "new_value": str(row.get('Salesforce', ''))
        }
        api_template["payload"].append(record_update)
    
    return json.dumps(api_template, indent=2)

# -------------------------
# PDF Export Function
# -------------------------
def generate_executive_pdf(quality_score, grade, match_percentage, total_matches, total_mismatches, 
                          total_records, num_fields, mismatch_counts, insights):
    """Generate executive summary PDF report."""
    from io import BytesIO
    
    # Create HTML content for PDF
    html_content = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            h1 {{ color: #1976D2; border-bottom: 3px solid #1976D2; padding-bottom: 10px; }}
            h2 {{ color: #424242; margin-top: 30px; }}
            .metric {{ background: #f5f5f5; padding: 15px; margin: 10px 0; border-radius: 5px; }}
            .metric-label {{ font-weight: bold; color: #666; }}
            .metric-value {{ font-size: 24px; color: #1976D2; }}
            .grade {{ font-size: 48px; font-weight: bold; text-align: center; padding: 20px; 
                     background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                     color: white; border-radius: 10px; }}
            .insight {{ padding: 15px; margin: 10px 0; border-left: 4px solid #FF9800; 
                       background: #FFF3E0; }}
            .critical {{ border-left-color: #F44336; background: #FFEBEE; }}
            .warning {{ border-left-color: #FF9800; background: #FFF3E0; }}
            .success {{ border-left-color: #4CAF50; background: #E8F5E9; }}
            table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
            th {{ background: #1976D2; color: white; padding: 12px; text-align: left; }}
            td {{ padding: 10px; border-bottom: 1px solid #ddd; }}
            tr:hover {{ background: #f5f5f5; }}
            .footer {{ margin-top: 50px; padding-top: 20px; border-top: 2px solid #ddd; 
                      text-align: center; color: #666; }}
        </style>
    </head>
    <body>
        <h1>📊 Data Integrity Executive Summary</h1>
        <p><strong>Generated:</strong> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
        
        <div class="grade">
            <div>Overall Grade: {grade}</div>
            <div style="font-size: 20px; margin-top: 10px;">Quality Score: {quality_score:.1f}/100</div>
        </div>
        
        <h2>📈 Key Metrics</h2>
        <div class="metric">
            <div class="metric-label">Match Percentage</div>
            <div class="metric-value">{match_percentage:.2f}%</div>
        </div>
        <div class="metric">
            <div class="metric-label">Total Records Compared</div>
            <div class="metric-value">{total_records:,}</div>
        </div>
        <div class="metric">
            <div class="metric-label">Fields Analyzed</div>
            <div class="metric-value">{num_fields}</div>
        </div>
        <div class="metric">
            <div class="metric-label">Total Matches</div>
            <div class="metric-value" style="color: #4CAF50;">{total_matches:,}</div>
        </div>
        <div class="metric">
            <div class="metric-label">Total Mismatches</div>
            <div class="metric-value" style="color: #F44336;">{total_mismatches:,}</div>
        </div>
        
        <h2>🎯 Top Issues Requiring Attention</h2>
        <table>
            <tr>
                <th>Field Name</th>
                <th>Mismatches</th>
                <th>Priority</th>
            </tr>
    """
    
    # Add top 10 mismatch fields
    for field, count in mismatch_counts[:10]:
        priority = "🔴 High" if count > total_records * 0.1 else ("🟡 Medium" if count > total_records * 0.05 else "🟢 Low")
        html_content += f"""
            <tr>
                <td>{field}</td>
                <td>{count:,}</td>
                <td>{priority}</td>
            </tr>
        """
    
    html_content += """
        </table>
        
        <h2>💡 AI-Powered Recommendations</h2>
    """
    
    # Add insights
    for insight in insights[:5]:
        insight_class = insight.get('type', 'info')
        html_content += f"""
        <div class="insight {insight_class}">
            <h3>{insight['icon']} {insight['title']}</h3>
            <p>{insight['description']}</p>
            <p><strong>Recommended Action:</strong> {insight['action']}</p>
        </div>
        """
    
    html_content += f"""
        <div class="footer">
            <p>Generated by Data Integrity Validator Dashboard</p>
            <p>Powered by AI-driven insights and real-time analysis</p>
            <p style="font-size: 12px; color: #999;">This report provides executive-level summary. 
            For detailed record-level analysis, please refer to the interactive dashboard.</p>
        </div>
    </body>
    </html>
    """
    
    return html_content

# -------------------------
# AI-Powered Insights Functions
# -------------------------
def generate_ai_insights(mismatch_counts, total_records, match_percentage):
    """Generate intelligent insights about data quality issues."""
    insights = []
    
    # Critical issues
    if match_percentage < 50:
        insights.append({
            'type': 'critical',
            'icon': '🚨',
            'title': 'Critical Data Quality Issue',
            'description': f'Only {match_percentage:.1f}% of records match. This requires immediate attention.',
            'action': 'Review data integration processes and field mappings.'
        })
    elif match_percentage < 75:
        insights.append({
            'type': 'warning',
            'icon': '⚠️',
            'title': 'Moderate Data Quality Issues',
            'description': f'{match_percentage:.1f}% match rate indicates room for improvement.',
            'action': 'Focus on top mismatched fields for quick wins.'
        })
    else:
        insights.append({
            'type': 'success',
            'icon': '✅',
            'title': 'Good Data Quality',
            'description': f'{match_percentage:.1f}% match rate shows strong data integrity.',
            'action': 'Continue monitoring and address remaining mismatches.'
        })
    
    # Top problem areas
    if mismatch_counts:
        top_problem = mismatch_counts[0]
        problem_pct = (top_problem[1] / total_records * 100) if total_records > 0 else 0
        insights.append({
            'type': 'info',
            'icon': '🎯',
            'title': f'Biggest Problem: {top_problem[0]}',
            'description': f'{top_problem[1]:,} mismatches ({problem_pct:.1f}% of records)',
            'action': f'Prioritize fixing "{top_problem[0]}" field - highest impact potential.'
        })
    
    # Pattern detection
    if len(mismatch_counts) >= 3:
        top_3_mismatches = sum([m[1] for m in mismatch_counts[:3]])
        top_3_pct = (top_3_mismatches / sum([m[1] for m in mismatch_counts]) * 100) if sum([m[1] for m in mismatch_counts]) > 0 else 0
        if top_3_pct > 60:
            insights.append({
                'type': 'insight',
                'icon': '💡',
                'title': 'Concentrated Issues Detected',
                'description': f'Top 3 fields account for {top_3_pct:.0f}% of all mismatches',
                'action': 'Focus on these specific fields for maximum efficiency.'
            })
    
    return insights

def calculate_data_quality_score(match_percentage, total_records, num_fields):
    """Calculate overall data quality score (0-100)."""
    # Base score from match percentage
    base_score = match_percentage
    
    # Penalty for low record count (less reliable)
    if total_records < 100:
        base_score *= 0.9
    
    # Bonus for comprehensive field coverage
    if num_fields >= 10:
        base_score = min(100, base_score * 1.05)
    
    return round(base_score, 1)

def get_score_color(score):
    """Return color based on score."""
    if score >= 90:
        return "#00C853"  # Green
    elif score >= 75:
        return "#FFB300"  # Amber
    elif score >= 50:
        return "#FF6F00"  # Orange
    else:
        return "#D50000"  # Red

def get_score_grade(score):
    """Return letter grade based on score."""
    if score >= 95:
        return "A+"
    elif score >= 90:
        return "A"
    elif score >= 85:
        return "A-"
    elif score >= 80:
        return "B+"
    elif score >= 75:
        return "B"
    elif score >= 70:
        return "B-"
    elif score >= 65:
        return "C+"
    elif score >= 60:
        return "C"
    elif score >= 50:
        return "D"
    else:
        return "F"

# -------------------------
# Email Functions
# -------------------------
def open_outlook_with_email(summary_stats, top_mismatches, recipient="bizappsqaautomation@chargepoint.com"):
    """Open Outlook desktop app with pre-filled email on macOS."""
    try:
        html_content = generate_email_report(summary_stats, top_mismatches)
        
        # Save HTML to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
            f.write(html_content)
            temp_file = f.name
        
        subject = f"Data Integrity Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # Create AppleScript to open Outlook with email
        applescript = f'''
        tell application "Microsoft Outlook"
            activate
            set newMessage to make new outgoing message with properties {{subject:"{subject}", content:""}}
            tell newMessage
                make new recipient at newMessage with properties {{email address:{{address:"{recipient}"}}}}
            end tell
            open newMessage
        end tell
        '''
        
        # Execute AppleScript
        subprocess.run(['osascript', '-e', applescript], check=True)
        
        return True, f"Outlook opened! Please attach the report from: {temp_file}"
    except Exception as e:
        return False, f"Could not open Outlook: {str(e)}"

def send_email_direct(summary_stats, top_mismatches, sender_email, sender_password, recipient="bizappsqaautomation@chargepoint.com"):
    """Send email report directly via SMTP."""
    
    # Validate inputs
    if not sender_email or not sender_password or not recipient:
        return False, "Missing email credentials. Please fill in all email fields."
    
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"Data Integrity Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} [ID: {datetime.now().strftime('%f')}]"
    msg['From'] = sender_email
    msg['To'] = recipient
    msg['Reply-To'] = sender_email
    msg['X-Priority'] = '3'
    msg['X-Mailer'] = 'Python SMTP'
    msg['Importance'] = 'Normal'
    
    html = generate_email_report(summary_stats, top_mismatches)
    msg.attach(MIMEText(html, 'html'))
    
    # Determine SMTP server based on sender email
    if 'gmail.com' in sender_email.lower():
        smtp_servers = [
            ('smtp.gmail.com', 587),
            ('smtp.gmail.com', 465)  # SSL port as fallback
        ]
    else:
        # Outlook/Office365
        smtp_servers = [
            ('smtp.office365.com', 587),
            ('smtp-mail.outlook.com', 587),
            ('outlook.office365.com', 587)
        ]
    
    last_error = None
    for smtp_host, smtp_port in smtp_servers:
        try:
            print(f"Attempting to connect to {smtp_host}:{smtp_port}...")
            
            if smtp_port == 465:
                # Use SMTP_SSL for port 465
                import ssl
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context, timeout=10) as server:
                    server.set_debuglevel(1)
                    print(f"Attempting login with {sender_email}...")
                    server.login(sender_email, sender_password)
                    print(f"Sending email to {recipient}...")
                    server.send_message(msg)
                    print("Email sent successfully!")
                    return True, f"Email sent successfully via {smtp_host}!"
            else:
                # Use SMTP with STARTTLS for port 587
                with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
                    server.set_debuglevel(1)
                    server.starttls()
                    print(f"Attempting login with {sender_email}...")
                    server.login(sender_email, sender_password)
                    print(f"Sending email to {recipient}...")
                    server.send_message(msg)
                    print("Email sent successfully!")
                    return True, f"Email sent successfully via {smtp_host}!"
        except smtplib.SMTPAuthenticationError as e:
            if 'gmail.com' in smtp_host:
                last_error = f"Gmail authentication failed. Please use an App Password (not your regular password). Error: {str(e)}"
            else:
                last_error = f"Authentication failed on {smtp_host}. Basic auth is likely disabled. Error: {str(e)}"
            print(last_error)
            continue
        except smtplib.SMTPException as e:
            last_error = f"SMTP error on {smtp_host}: {str(e)}"
            print(last_error)
            continue
        except Exception as e:
            last_error = f"Error on {smtp_host}: {str(e)}"
            print(last_error)
            continue
    
    # Provide helpful error message
    if 'gmail.com' in sender_email.lower():
        return False, "Gmail authentication failed. Please create an App Password at myaccount.google.com/apppasswords and use it instead of your regular password."
    else:
        return False, "SMTP authentication is disabled by your IT department. Please use Gmail with an App Password, or use the '📧 Outlook' button to open your email client."

def generate_email_report(summary_stats, top_mismatches):
    """Generate HTML email report as downloadable file."""
    html = f"""
    <!DOCTYPE html>
    <html>
      <head>
        <style>
          body {{ font-family: Arial, sans-serif; margin: 20px; }}
          h2 {{ color: #333; }}
          table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
          th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
          th {{ background-color: #4CAF50; color: white; }}
          ul {{ list-style-type: none; padding: 0; }}
          li {{ padding: 8px; margin: 5px 0; background-color: #f9f9f9; border-left: 4px solid #FF7043; }}
        </style>
      </head>
      <body>
        <h2>Data Integrity Validation Report</h2>
        <p><strong>Timestamp:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>From:</strong> vidushi.dubey@chargepoint.com</p>
        <p><strong>To:</strong> bizappsqaautomation@chargepoint.com</p>
        <hr>
        
        <h3>Summary Statistics</h3>
        <table>
          <tr><th>Metric</th><th>Value</th></tr>
          <tr><td>Total Records</td><td>{summary_stats.get('total_records', 0):,}</td></tr>
          <tr><td>Total Matches</td><td>{summary_stats.get('total_matches', 0):,}</td></tr>
          <tr><td>Total Mismatches</td><td>{summary_stats.get('total_mismatches', 0):,}</td></tr>
          <tr><td>Match Percentage</td><td>{summary_stats.get('match_percentage', 0):.2f}%</td></tr>
        </table>
        
        <h3>Top Mismatched Fields</h3>
        <ul>
    """
    
    for field, count in top_mismatches[:5]:
        html += f"<li><strong>{field}:</strong> {count:,} mismatches</li>"
    
    html += """
        </ul>
        <hr>
        <p><em>This is an automated report from the Data Integrity Validator dashboard.</em></p>
        <p><em>Please forward this report to bizappsqaautomation@chargepoint.com</em></p>
      </body>
    </html>
    """
    
    return html

# -------------------------
# Password Protection
# -------------------------
def check_password():
    """Returns `True` if the user had the correct password."""
    
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == "hackathon2025":  # Change this password
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password
        st.text_input(
            "🔐 Enter Password to Access Dashboard", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        st.info("Please enter the password to access the Data Integrity Validator.")
        return False
    elif not st.session_state["password_correct"]:
        # Password incorrect, show input + error
        st.text_input(
            "🔐 Enter Password to Access Dashboard", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        st.error("😕 Password incorrect. Please try again.")
        return False
    else:
        # Password correct
        return True

if not check_password():
    st.stop()  # Don't continue if password is incorrect

# -------------------------
# Page Config
# -------------------------
st.set_page_config(page_title="Advanced Data Integrity Dashboard", layout="wide")

# -------------------------
# View Mode Selection
# -------------------------
st.sidebar.title("🎯 View Mode")
view_mode = st.sidebar.radio(
    "Select your role:",
    ["👔 Business View", "🔧 Admin Mode"],
    help="Business View: Executive summary & key insights\nAdmin Mode: Full technical details & configurations"
)

is_admin_mode = (view_mode == "🔧 Admin Mode")

# -------------------------
# Sidebar: Upload Controls
# -------------------------
st.sidebar.title("Dashboard Controls")

# Force light theme for all visualizations
theme = "Light"

# Sidebar Upload
st.sidebar.subheader("Upload Files")
netsuite_file = st.sidebar.file_uploader("Upload NetSuite XLSX", type=["xlsx"])
salesforce_file = st.sidebar.file_uploader("Upload Salesforce XLSX", type=["xlsx"])

# Action Buttons
compare_button = st.sidebar.button("🔍 Compare Data", type="primary", use_container_width=True)
reset_button = st.sidebar.button("🔄 Reset", use_container_width=True)

# Handle reset
if reset_button:
    # Clear all session state keys
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.toast("🔄 Dashboard reset successfully!", icon="✨")
    st.rerun()

# Store comparison trigger in session state
if compare_button:
    if not netsuite_file or not salesforce_file:
        st.toast("⚠️ Please upload both files before comparing", icon="⚠️")
    else:
        st.session_state['comparison_triggered'] = True
        st.toast("🔍 Starting comparison...", icon="⏳")

st.sidebar.markdown("---")

# -------------------------
# Professional Header
# -------------------------
st.title("📊 Data Integrity Validator")
st.markdown("**Compare and validate data integrity between NetSuite and Salesforce**")
st.markdown("---")

# Sidebar Filters (only show when NetSuite file is uploaded)
if netsuite_file:
    st.sidebar.subheader("Filters")
    
primary_cols, secondary_cols, tertiary_cols = [], [], []
date_cols, account_cols = [], []
df_netsuite = None
all_cols = []
if netsuite_file:
    try:
        df_netsuite = pd.read_excel(netsuite_file, engine="openpyxl")
        uniqueness_scores = {col: df_netsuite[col].nunique(dropna=True)/len(df_netsuite[col]) if len(df_netsuite[col]) > 0 else 0 for col in df_netsuite.columns}
        sorted_cols = sorted(uniqueness_scores.items(), key=lambda x: x[1], reverse=True)
        sorted_column_names = [col for col, score in sorted_cols]
        all_cols = sorted_column_names
        primary_cols = sorted_column_names[:3]
        secondary_cols = sorted_column_names[3:8]
        tertiary_cols = sorted_column_names[8:]
        date_cols = [col for col in df_netsuite.columns if "date" in col.lower()]
        account_cols = [col for col in df_netsuite.columns if "account" in col.lower()]
    except Exception:
        pass

if netsuite_file:
    # Add Smart Match Key selector
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔑 Smart Match Key")
    st.sidebar.caption("Select the unique identifier to match records between systems")
    
    # Find potential match keys (Document Number, Order Number, ID fields)
    potential_keys = [col for col in all_cols if any(keyword in col.lower() for keyword in ['document', 'order', 'number', 'id', 'key'])]
    default_key = potential_keys[0] if potential_keys else (all_cols[0] if all_cols else None)
    
    match_key = st.sidebar.selectbox(
        "Match records by:",
        options=all_cols,
        index=all_cols.index(default_key) if default_key in all_cols else 0,
        help="Records with the same value in this field will be compared",
        key="match_key_selector"
    )
    
    st.sidebar.markdown("---")
    selected_primary = st.sidebar.multiselect("Primary Fields", all_cols, default=primary_cols, key="primary_multiselect")
    selected_secondary = st.sidebar.multiselect("Secondary Fields", all_cols, default=secondary_cols, key="secondary_multiselect")
    selected_tertiary = st.sidebar.multiselect("Tertiary Fields", all_cols, default=tertiary_cols, key="tertiary_multiselect")
else:
    match_key = None
    selected_primary = []
    selected_secondary = []
    selected_tertiary = []

date_range = None
date_col = None
if date_cols and netsuite_file:
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

# Email configuration (before comparison to prevent rerun issues)
if is_admin_mode:
    st.sidebar.markdown("---")
    st.sidebar.subheader("📧 Email Settings")

    # Encrypted credentials using base64
    encrypted_email = "dmlkdXNoaS5kdWJleTIxMDdAZ21haWwuY29t"  # vidushi.dubey2107@gmail.com
    encrypted_password = "bXFzdGllaW9hanZrZXFwZQ=="  # mqstieioajvkeqpe

    # Decode credentials
    default_gmail = base64.b64decode(encrypted_email).decode()
    default_password = base64.b64decode(encrypted_password).decode()

    sender_email = st.sidebar.text_input("Your Email", value=default_gmail, key="sender_email", placeholder="your.email@gmail.com", help="Use Gmail for best results")
    sender_password = st.sidebar.text_input("Email Password/App Password", type="password", value=default_password, key="sender_password", help="For Gmail: Use App Password")
    recipient_email = st.sidebar.text_input("Recipient Email", value="vidushi.dubey@chargepoint.com, bizappsqaautomation@chargepoint.com, vidushi.dubey2107@gmail.com", key="recipient_email", help="Comma-separated for multiple recipients")
    auto_send = st.sidebar.checkbox("🚀 Auto-send email after comparison", value=True, key="auto_send_checkbox", help="Automatically send email when comparison completes")
else:
    # Business View: Set defaults silently
    default_gmail = base64.b64decode("dmlkdXNoaS5kdWJleTIxMDdAZ21haWwuY29t").decode()
    default_password = base64.b64decode("bXFzdGllaW9hanZrZXFwZQ==").decode()
    st.session_state["sender_email"] = default_gmail
    st.session_state["sender_password"] = default_password
    st.session_state["recipient_email"] = "vidushi.dubey@chargepoint.com, bizappsqaautomation@chargepoint.com, vidushi.dubey2107@gmail.com"
    st.session_state["auto_send_checkbox"] = True

if netsuite_file and salesforce_file and (compare_button or st.session_state.get('comparison_triggered', False)):
    # Real-Time Progress Tracker
    if compare_button:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        status_text.text("⏳ Step 1/5: Loading NetSuite data...")
        progress_bar.progress(10)
        time.sleep(0.3)
    
    if df_netsuite is None:
        df_netsuite = pd.read_excel(netsuite_file, engine="openpyxl")
    
    if compare_button:
        status_text.text("⏳ Step 2/5: Loading Salesforce data...")
        progress_bar.progress(25)
        time.sleep(0.3)
    
    df_salesforce = pd.read_excel(salesforce_file, engine="openpyxl")
    
    if compare_button:
        status_text.text("⏳ Step 3/5: Mapping columns...")
        progress_bar.progress(45)
        time.sleep(0.3)

    # Column Mapping Feature
    st.sidebar.markdown("---")
    st.sidebar.subheader("Column Mapping")
    
    # Choose mapping method
    mapping_method = st.sidebar.radio(
        "Mapping Method",
        ["By Position (Sequential)", "By Name (Manual)"],
        index=0,  # Default to sequential
        help="Sequential: Columns compared in order (1→1, 2→2, etc.)"
    )
    
    ns_columns = list(df_netsuite.columns)
    sf_columns = list(df_salesforce.columns)
    
    if mapping_method == "By Position (Sequential)":
        # Automatically map columns by position
        min_cols = min(len(ns_columns), len(sf_columns))
        st.sidebar.success(f"✅ Sequential: {min_cols} columns mapped")
        st.sidebar.caption("NS Col 1 ↔ SF Col 1, Col 2 ↔ Col 2...")
        # Rename Salesforce columns to match NetSuite column names by position
        df_salesforce_renamed = df_salesforce.copy()
        rename_dict = {sf_columns[i]: ns_columns[i] for i in range(min_cols)}
        df_salesforce_renamed = df_salesforce_renamed.rename(columns=rename_dict)
        df_salesforce = df_salesforce_renamed
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

    if compare_button:
        status_text.text("⏳ Step 4/5: Analyzing data quality...")
        progress_bar.progress(65)
        time.sleep(0.3)

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
    # IMPORTANT: Don't filter - include ALL records from both sheets
    filtered_ns = df_netsuite.copy()
    filtered_sf = df_salesforce.copy()
    # Commenting out filters to ensure ALL records are included
    # if date_range and len(date_range) == 2 and date_col:
    #     start_date = pd.to_datetime(date_range[0]).tz_localize(None)
    #     end_date = pd.to_datetime(date_range[1]).tz_localize(None)
    #     filtered_ns = filtered_ns[(filtered_ns[date_col].dt.tz_localize(None) >= start_date) & (filtered_ns[date_col].dt.tz_localize(None) <= end_date)]
    #     if date_col in filtered_sf.columns:
    #         filtered_sf = filtered_sf[(filtered_sf[date_col].dt.tz_localize(None) >= start_date) & (filtered_sf[date_col].dt.tz_localize(None) <= end_date)]
    # if account_filter and account_col:
    #     filtered_ns = filtered_ns[filtered_ns[account_col].isin(account_filter)]
    #     if account_col in filtered_sf.columns:
    #         filtered_sf = filtered_sf[filtered_sf[account_col].isin(account_filter)]

    # Use the user-selected match key for merging
    merge_key = match_key if match_key else (primary_cols[0] if primary_cols else None)
    
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
    # Keep ALL columns from original data, don't filter to only selected fields
    # This ensures we don't lose records during merge
    # filtered_ns = filtered_ns.reindex(columns=all_fields, fill_value=pd.NA)
    # filtered_sf = filtered_sf.reindex(columns=all_fields, fill_value=pd.NA)
    if not merge_key or merge_key not in filtered_ns.columns or merge_key not in filtered_sf.columns:
        st.warning(f"⚠️ Cannot calculate KPIs: Match key '{merge_key}' is missing. Please select a valid match key in the sidebar.")
    else:
        st.info(f"🔑 Matching records by: **{merge_key}** | Records are compared when this field matches between NetSuite and Salesforce")
        
        # Show sample of what's being matched
        with st.expander("🔍 Preview: How records are matched", expanded=False):
            st.caption(f"Records with the same **{merge_key}** value are compared, regardless of row position")
            sample_ns = filtered_ns[[merge_key]].head(3).reset_index(drop=True)
            sample_sf = filtered_sf[[merge_key]].head(3).reset_index(drop=True)
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**NetSuite (any rows)**")
                st.dataframe(sample_ns, use_container_width=True)
            with col2:
                st.markdown("**Salesforce (any rows)**")
                st.dataframe(sample_sf, use_container_width=True)
            st.info(f"Example: If NS row 2 has {merge_key}='12345' and SF row 8 has {merge_key}='12345', they WILL be matched and compared ✅")
        
        try:
            # Merge on the match key to align records properly
            merged_df = pd.merge(filtered_ns, filtered_sf, left_on=merge_key, right_on=merge_key, how="outer", indicator=True, suffixes=('_NS', '_SF'))
            merged_df["_merge"] = merged_df["_merge"] if "_merge" in merged_df else "concat"
            
            # Show merge statistics
            match_records = (merged_df["_merge"] == "both").sum()
            ns_only = (merged_df["_merge"] == "left_only").sum()
            sf_only = (merged_df["_merge"] == "right_only").sum()
            
            merge_cols = st.columns(3)
            with merge_cols[0]:
                st.metric("✅ Matched Records", f"{match_records:,}", help="Records found in both systems")
            with merge_cols[1]:
                st.metric("🟦 NS Only", f"{ns_only:,}", delta_color="off", help="Records only in NetSuite")
            with merge_cols[2]:
                st.metric("🟧 SF Only", f"{sf_only:,}", delta_color="off", help="Records only in Salesforce")
            
            if ns_only > 0 or sf_only > 0:
                st.warning(f"⚠️ {ns_only + sf_only} records don't have a matching {merge_key} in the other system")
            
        except ValueError as e:
            st.error(f"❌ Merge error: {str(e)}")
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
        
        # Use ONLY the selected fields for comparison (not all Excel columns)
        # This respects the user's field selection
        selected_fields_for_comparison = selected_fields  # These are the filtered fields chosen by user
        
        sunburst_data = []
        per_field_stats = []  # For KPI cards
        
        for col in selected_fields_for_comparison:
            # After merge with suffixes=('_NS', '_SF'), columns become col_NS and col_SF
            col_ns = f"{col}_NS" if f"{col}_NS" in merged_df.columns else col
            col_sf = f"{col}_SF" if f"{col}_SF" in merged_df.columns else col
            
            if col_ns not in merged_df.columns or col_sf not in merged_df.columns:
                match_count = 0
                mismatch_count = 0
            else:
                # Only consider rows present in both (matched by key)
                both_mask = merged_df["_merge"] == "both"
                ns_vals = merged_df.loc[both_mask, col_ns]
                sf_vals = merged_df.loc[both_mask, col_sf]
                
                # Compare values for matched records
                match_mask = (ns_vals == sf_vals) | (ns_vals.isna() & sf_vals.isna())
                match_count = match_mask.sum()
                mismatch_count = (~match_mask).sum()
                
                # Only count records that matched by key but have different field values
                # Don't double-count left_only/right_only as these are different records entirely
            sunburst_data.append(["Match", col, match_count])
            sunburst_data.append(["Mismatch", col, mismatch_count])
            per_field_stats.append({"Field": col, "Match": match_count, "Mismatch": mismatch_count})
        
        if compare_button:
            status_text.text("⏳ Step 5/5: Generating insights...")
            progress_bar.progress(85)
            time.sleep(0.3)
        
        # Calculate totals for distribution chart
        total_match_sb = sum([row[2] for row in sunburst_data if row[0] == "Match"])
        total_mismatch_sb = sum([row[2] for row in sunburst_data if row[0] == "Mismatch"])
        total_records = total_match_sb + total_mismatch_sb
        match_percentage = (total_match_sb / total_records * 100) if total_records > 0 else 0
        mismatch_percentage = (total_mismatch_sb / total_records * 100) if total_records > 0 else 0
        
        # Save to comparison history
        if compare_button:
            comparison_data = {
                'timestamp': datetime.now(),
                'total_records': total_records,
                'match_percentage': match_percentage,
                'total_matches': total_match_sb,
                'total_mismatches': total_mismatch_sb,
                'num_fields': len(selected_fields)
            }
            save_comparison_history(comparison_data)
        
        # Complete progress
        if compare_button:
            progress_bar.progress(100)
            status_text.text("✅ Analysis complete!")
            time.sleep(0.5)
            status_text.empty()
            progress_bar.empty()
        
        # Show completion toast only on first comparison
        if compare_button:
            st.toast(f"✅ Comparison complete! {total_records:,} records analyzed", icon="🎉")
        
        # Smart Alerts & Thresholds
        if is_admin_mode:
            st.sidebar.markdown("---")
            st.sidebar.subheader("🔔 Smart Alerts")
            
            # Threshold setting
            threshold = st.sidebar.slider(
                "Alert Threshold (%)", 
                min_value=50, 
                max_value=100, 
                value=80,
                help="Alert if match rate falls below this percentage"
            )
        else:
            threshold = 80  # Default for Business View
        
        # Alert status (show for both modes but in different locations)
        if is_admin_mode:
            if match_percentage < threshold:
                st.sidebar.error(f"🚨 ALERT: Match rate ({match_percentage:.1f}%) is below threshold ({threshold}%)")
                if match_percentage < 50:
                    st.sidebar.error("⛔ CRITICAL: Immediate action required!")
            elif match_percentage < threshold + 10:
                st.sidebar.warning(f"⚠️ WARNING: Match rate ({match_percentage:.1f}%) is close to threshold")
            else:
                st.sidebar.success(f"✅ HEALTHY: Match rate ({match_percentage:.1f}%) exceeds threshold")
        
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
        
        # AI-Powered Data Quality Score - Better than Power BI!
        st.markdown("---")
        
        # Business View: Simplified Executive Dashboard
        if not is_admin_mode:
            st.subheader("📊 Executive Summary Dashboard")
            st.caption("High-level overview for business stakeholders")
            
            # Calculate quality score
            quality_score = calculate_data_quality_score(match_percentage, total_records, len(selected_fields))
            score_grade = get_score_grade(quality_score)
            
            # Big KPIs for executives
            exec_cols = st.columns(4)
            with exec_cols[0]:
                st.metric("Data Quality Grade", score_grade, help="Overall data quality assessment")
            with exec_cols[1]:
                st.metric("Quality Score", f"{quality_score:.0f}/100", help="AI-calculated quality score")
            with exec_cols[2]:
                status_icon = "✅" if match_percentage >= 80 else ("⚠️" if match_percentage >= 50 else "🚨")
                st.metric("Match Rate", f"{match_percentage:.1f}%", help="Percentage of matching records")
            with exec_cols[3]:
                st.metric("Records Analyzed", f"{total_records:,}", help="Total records in comparison")
            
            st.markdown("---")
            
        # Admin Mode: Full Technical Dashboard
        if is_admin_mode:
            st.subheader("🤖 AI-Powered Data Quality Intelligence")
        
        # Calculate quality score (if not already done in business view)
        if is_admin_mode:
            quality_score = calculate_data_quality_score(match_percentage, total_records, len(selected_fields))
            score_color = get_score_color(quality_score)
            score_grade = get_score_grade(quality_score)
        
        score_col1, score_col2, score_col3 = st.columns([2, 1, 1])
        
        # Show gauge chart only in Admin Mode
        if is_admin_mode:
            with score_col1:
                # Gauge chart for quality score
                fig_gauge = go.Figure(go.Indicator(
                    mode="gauge+number+delta",
                    value=quality_score,
                    domain={'x': [0, 1], 'y': [0, 1]},
                    title={'text': "Overall Data Quality Score", 'font': {'size': 20}},
                    delta={'reference': 90, 'increasing': {'color': "green"}},
                    gauge={
                        'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "darkgray"},
                        'bar': {'color': score_color},
                        'bgcolor': "white",
                        'borderwidth': 2,
                        'bordercolor': "gray",
                        'steps': [
                            {'range': [0, 50], 'color': '#FFCDD2'},
                            {'range': [50, 75], 'color': '#FFE082'},
                            {'range': [75, 90], 'color': '#C5E1A5'},
                            {'range': [90, 100], 'color': '#A5D6A7'}
                        ],
                        'threshold': {
                            'line': {'color': "red", 'width': 4},
                            'thickness': 0.75,
                            'value': 90
                        }
                    }
            ))
            fig_gauge.update_layout(
                height=250,
                margin=dict(l=20, r=20, t=50, b=20),
                paper_bgcolor='white',
                font={'size': 16}
            )
            st.plotly_chart(fig_gauge, use_container_width=True, key="quality_score_gauge")
        
            with score_col2:
                st.markdown(f"### Grade: **{score_grade}**")
                st.markdown(f"**Score:** {quality_score}/100")
                st.markdown(f"**Records:** {total_records:,}")
                st.markdown(f"**Fields:** {len(selected_fields)}")
            
            with score_col3:
                if quality_score >= 90:
                    st.success("🎉 Excellent!")
                elif quality_score >= 75:
                    st.info("👍 Good")
                elif quality_score >= 50:
                    st.warning("⚠️ Needs Work")
                else:
                    st.error("🚨 Critical")
                
                # Download score report
                score_report = f"Data Quality Report\n{'='*30}\nScore: {quality_score}/100\nGrade: {score_grade}\nMatch Rate: {match_percentage:.1f}%\nTotal Records: {total_records:,}\nTimestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                st.download_button(
                    "📄 Download Score",
                    score_report,
                    file_name=f"quality_score_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain",
                    use_container_width=True
                )
        
        # Calculate top mismatched fields for insights
        mismatch_counts = []
        for field in selected_fields:
            if field in filtered_ns.columns and field in filtered_sf.columns:
                ns_vals = filtered_ns[field].astype(str).reset_index(drop=True)
                sf_vals = filtered_sf[field].astype(str).reset_index(drop=True)
                min_len = min(len(ns_vals), len(sf_vals))
                mismatches = (ns_vals[:min_len] != sf_vals[:min_len]).sum()
                if mismatches > 0:
                    mismatch_counts.append((field, mismatches))
        
        mismatch_counts.sort(key=lambda x: x[1], reverse=True)
        
        # Calculate num_fields for PDF export
        num_fields = len(selected_fields)
        
        # AI Insights Section
        st.markdown("### 💡 Smart Insights & Recommendations")
        insights = generate_ai_insights(mismatch_counts, total_records, match_percentage)
        
        insight_cols = st.columns(len(insights) if len(insights) <= 3 else 3)
        for idx, insight in enumerate(insights[:3]):  # Show top 3 insights
            with insight_cols[idx]:
                if insight['type'] == 'critical':
                    st.error(f"**{insight['icon']} {insight['title']}**")
                elif insight['type'] == 'warning':
                    st.warning(f"**{insight['icon']} {insight['title']}**")
                elif insight['type'] == 'success':
                    st.success(f"**{insight['icon']} {insight['title']}**")
                else:
                    st.info(f"**{insight['icon']} {insight['title']}**")
                
                st.markdown(f"*{insight['description']}*")
                st.caption(f"💡 **Action:** {insight['action']}")
        
        # Executive Summary PDF Export (now that all variables are available)
        st.sidebar.markdown("---")
        st.sidebar.subheader("📄 Executive Summary")
        
        pdf_html = generate_executive_pdf(
            quality_score, score_grade, match_percentage, 
            total_match_sb, total_mismatch_sb, total_records, 
            num_fields, mismatch_counts, insights
        )
        
        st.sidebar.download_button(
            label="📑 Download PDF Summary",
            data=pdf_html,
            file_name=f"executive_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
            mime="text/html",
            help="Download executive summary for stakeholders (HTML format - print to PDF in browser)",
            use_container_width=True
        )
        st.sidebar.caption("💡 Tip: Open in browser and print to PDF for formal reports")
        
        # Generate email report option (Admin Mode only for manual controls)
        if is_admin_mode:
            st.sidebar.markdown("---")
            st.sidebar.subheader("📧 Email Report")
        
        summary_stats = {
            'total_records': total_records,
            'total_matches': total_match_sb,
            'total_mismatches': total_mismatch_sb,
            'match_percentage': match_percentage
        }
        
        # Generate HTML report
        email_html = generate_email_report(summary_stats, mismatch_counts)
        
        # Auto-send email if enabled (use values from sidebar inputs set before comparison)
        auto_send = st.session_state.get("auto_send_checkbox", False)
        sender_email_val = st.session_state.get("sender_email", "vidushi.dubey@chargepoint.com")
        sender_password_val = st.session_state.get("sender_password", "")
        recipient_email_val = st.session_state.get("recipient_email", "bizappsqaautomation@chargepoint.com")
        
        if auto_send and sender_password_val:
            # Create a unique key for this comparison to track if email was sent
            comparison_key = f"email_sent_{total_records}_{total_match_sb}_{total_mismatch_sb}"
            
            if comparison_key not in st.session_state:
                st.session_state[comparison_key] = False
            
            if not st.session_state[comparison_key]:
                with st.spinner("Automatically sending email..."):
                    success, message = send_email_direct(summary_stats, mismatch_counts, sender_email_val, sender_password_val, recipient_email_val)
                    if success:
                        st.sidebar.success(f"✅ {message}")
                        st.session_state[comparison_key] = True
                    else:
                        st.sidebar.error(f"❌ {message}")
            else:
                st.sidebar.info("✉️ Email already sent for this comparison")
        elif auto_send and not sender_password_val:
            if is_admin_mode:
                st.sidebar.warning("⚠️ Enter email password to enable auto-send")
        
        # Email control buttons (Admin Mode only)
        if is_admin_mode:
            col1, col2, col3 = st.sidebar.columns(3)
            
            # Open Outlook button (primary method)
            if col1.button("📧 Outlook", type="primary", use_container_width=True, help="Open Outlook with pre-filled email"):
                success, message = open_outlook_with_email(summary_stats, mismatch_counts, recipient_email_val)
                if success:
                    st.sidebar.success(f"✅ {message}")
                else:
                    st.sidebar.error(f"❌ {message}")
            
            # Send via SMTP button (alternative method)
            if col2.button("📤 SMTP", use_container_width=True, help="Send via SMTP manually"):
                if not sender_password_val:
                    st.sidebar.error("⚠️ Please enter your email password above")
                else:
                    with st.spinner("Sending email..."):
                        success, message = send_email_direct(summary_stats, mismatch_counts, sender_email_val, sender_password_val, recipient_email_val)
                        if success:
                            st.sidebar.success(f"✅ {message}")
                        else:
                            st.sidebar.error(f"❌ {message}")
            
            # Download button for email report
            col3.download_button(
                label="📥 Save",
                data=email_html,
                file_name=f"data_integrity_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
                mime="text/html",
                help="Download HTML report",
                use_container_width=True
            )
        
        # Comparison History & Trends
        st.sidebar.markdown("---")
        st.sidebar.subheader("💾 Comparison History")
        
        history = load_comparison_history()
        if history:
            st.sidebar.caption(f"📊 {len(history)} previous comparisons")
            
            # Show trend
            trend_data = pd.DataFrame(history)
            if len(trend_data) > 1:
                latest_score = trend_data.iloc[-1]['match_percentage']
                previous_score = trend_data.iloc[-2]['match_percentage']
                delta = latest_score - previous_score
                
                if delta > 0:
                    st.sidebar.success(f"📈 Quality improving: +{delta:.1f}%")
                elif delta < 0:
                    st.sidebar.error(f"📉 Quality declining: {delta:.1f}%")
                else:
                    st.sidebar.info("➡️ Quality stable")
            
            # Show mini trend chart
            with st.sidebar.expander("📈 View Trend Chart"):
                fig_trend = go.Figure()
                fig_trend.add_trace(go.Scatter(
                    x=[h['timestamp'].strftime('%m/%d %H:%M') for h in history],
                    y=[h['match_percentage'] for h in history],
                    mode='lines+markers',
                    line=dict(color='#4CAF50', width=2),
                    marker=dict(size=8)
                ))
                fig_trend.update_layout(
                    title="Match Rate Trend",
                    xaxis_title="Time",
                    yaxis_title="Match %",
                    height=200,
                    margin=dict(l=20, r=20, t=40, b=20)
                )
                st.plotly_chart(fig_trend, use_container_width=True, key="history_trend")
                
                # Show history table
                st.caption("Recent Comparisons:")
                for idx, h in enumerate(reversed(history[-5:])):
                    st.caption(f"{idx+1}. {h['timestamp'].strftime('%m/%d %H:%M')} - {h['match_percentage']:.1f}%")
        else:
            st.sidebar.info("No history yet. Run a comparison to start tracking trends!")
        
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
        # Interactive Record-Level Comparison - Better than Power BI!
        st.subheader("🔍 Interactive Record-Level Drill-Down")
        st.caption("Click-through analysis at individual record level - feature not available in standard Power BI!")
        
        # Field selector for drill-down
        all_available_fields = selected_primary + selected_secondary + selected_tertiary
        drill_field = st.selectbox(
            "Select field to analyze at record level:",
            all_available_fields,
            key="drill_down_field_selector"
        )
        
        if drill_field:
            # Use the MERGED data to compare records properly by match key
            # This ensures records are matched by key, not by row position
            
            drill_field_ns = f"{drill_field}_NS" if f"{drill_field}_NS" in merged_df.columns else drill_field
            drill_field_sf = f"{drill_field}_SF" if f"{drill_field}_SF" in merged_df.columns else drill_field
            
            # Get matched records (both)
            matched_records = merged_df[merged_df["_merge"] == "both"].copy()
            
            # Get unmatched records (NS only and SF only)
            ns_only_records = merged_df[merged_df["_merge"] == "left_only"].copy()
            sf_only_records = merged_df[merged_df["_merge"] == "right_only"].copy()
            
            # Show summary
            st.caption(f"📊 Found: {len(matched_records)} matched, {len(ns_only_records)} NS-only, {len(sf_only_records)} SF-only")
            
            comparison_rows = []
            
            # Add matched records
            for idx, row in matched_records.iterrows():
                ns_val = str(row[drill_field_ns]) if drill_field_ns in matched_records.columns else 'N/A'
                sf_val = str(row[drill_field_sf]) if drill_field_sf in matched_records.columns else 'N/A'
                comparison_rows.append({
                    'Match Key': str(row[match_key]),
                    'NetSuite': ns_val,
                    'Salesforce': sf_val,
                    'Status': '✅ Match' if ns_val == sf_val else '❌ Mismatch'
                })
            
            # Add NS-only records
            for idx, row in ns_only_records.iterrows():
                # Try to get the drill field value, but use match key if not available
                if drill_field_ns in ns_only_records.columns and pd.notna(row[drill_field_ns]):
                    ns_val = str(row[drill_field_ns])
                elif drill_field in ns_only_records.columns and pd.notna(row[drill_field]):
                    ns_val = str(row[drill_field])
                else:
                    # If drill field is empty, show match key value instead
                    ns_val = str(row[match_key]) if match_key in row.index else 'N/A'
                
                # Get match key value
                key_val = str(row[match_key]) if match_key in row.index else 'N/A'
                
                comparison_rows.append({
                    'Match Key': key_val,
                    'NetSuite': ns_val,
                    'Salesforce': '(Not in Salesforce)',
                    'Status': '🟦 NS Only'
                })
            
            # Add SF-only records
            for idx, row in sf_only_records.iterrows():
                # Try to get the drill field value, but use match key if not available
                if drill_field_sf in sf_only_records.columns and pd.notna(row[drill_field_sf]):
                    sf_val = str(row[drill_field_sf])
                elif drill_field in sf_only_records.columns and pd.notna(row[drill_field]):
                    sf_val = str(row[drill_field])
                else:
                    # If drill field is empty, show match key value instead
                    sf_val = str(row[match_key]) if match_key in row.index else 'N/A'
                
                comparison_rows.append({
                    'Match Key': str(row[match_key]) if match_key in row else 'N/A',
                    'NetSuite': '(Not in NetSuite)',
                    'Salesforce': sf_val,
                    'Status': '🟧 SF Only'
                })
            
            # Create comparison dataframe
            comparison_df = pd.DataFrame(comparison_rows)
            comparison_df.insert(0, 'Record #', range(1, len(comparison_df) + 1))
            
            # Statistics
            total_compared = len(comparison_df)
            matches = (comparison_df['Status'] == '✅ Match').sum()
            mismatches = (comparison_df['Status'] == '❌ Mismatch').sum()
            match_rate = (matches / total_compared * 100) if total_compared > 0 else 0
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Records", f"{total_compared:,}")
            with col2:
                st.metric("Matches", f"{matches:,}", delta=f"{match_rate:.1f}%")
            with col3:
                st.metric("Mismatches", f"{mismatches:,}", delta_color="inverse")
            with col4:
                if match_rate >= 90:
                    st.success("Excellent ✨")
                elif match_rate >= 75:
                    st.info("Good 👍")
                else:
                    st.warning("Review ⚠️")
            
            # Filter options
            st.markdown("---")
            filter_option = st.radio(
                "Show records:",
                ["All Records", "Mismatches Only", "Matches Only"],
                horizontal=True,
                key="drill_filter_option"
            )
            
            if filter_option == "Mismatches Only":
                comparison_df = comparison_df[comparison_df['Status'] == '❌ Mismatch']
            elif filter_option == "Matches Only":
                comparison_df = comparison_df[comparison_df['Status'] == '✅ Match']
            
            # Interactive table with highlighting
            st.markdown(f"### 📋 Record-Level Comparison: {drill_field}")
            st.caption(f"Showing {len(comparison_df)} records")
            
            # Color code the dataframe
            def highlight_mismatches(row):
                if row['Status'] == '❌ Mismatch':
                    return ['background-color: #FFEBEE'] * len(row)
                else:
                    return ['background-color: #E8F5E9'] * len(row)
            
            styled_df = comparison_df.style.apply(highlight_mismatches, axis=1)
            st.dataframe(styled_df, use_container_width=True, height=400)
            
            # Download comparison
            csv = comparison_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Download Detailed Comparison",
                csv,
                file_name=f"{drill_field}_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
            
            # Show sample mismatches for quick review
            if mismatches > 0:
                st.markdown("### 🔎 Sample Mismatch Examples")
                mismatched_samples = comparison_df[comparison_df['Status'] == '❌ Mismatch'].head(5)
                for idx, row in mismatched_samples.iterrows():
                    with st.expander(f"Record #{row['Record #']} - Mismatch Details"):
                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.markdown("**NetSuite Value:**")
                            st.code(row['NetSuite'], language=None)
                        with col_b:
                            st.markdown("**Salesforce Value:**")
                            st.code(row['Salesforce'], language=None)
                        
                        # Show difference
                        if str(row['NetSuite']).strip() == '':
                            st.warning("⚠️ NetSuite value is empty")
                        if str(row['Salesforce']).strip() == '':
                            st.warning("⚠️ Salesforce value is empty")
            
            # Quick Fixes Generator - Actionable Solutions!
            if mismatches > 0:
                st.markdown("---")
                st.markdown("### 🛠️ Quick Fix Generator")
                st.caption("Auto-generated code to resolve mismatches - copy and use directly!")
                
                fix_tab1, fix_tab2 = st.tabs(["📝 SQL Updates", "🔌 API Calls"])
                
                with fix_tab1:
                    sql_fixes = generate_sql_fixes(comparison_df[comparison_df['Status'] == '❌ Mismatch'], drill_field)
                    st.code(sql_fixes, language="sql")
                    st.download_button(
                        "📥 Download SQL Script",
                        sql_fixes,
                        file_name=f"fix_{drill_field}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql",
                        mime="text/plain",
                        use_container_width=True
                    )
                
                with fix_tab2:
                    api_fixes = generate_api_fixes(comparison_df[comparison_df['Status'] == '❌ Mismatch'], drill_field)
                    st.code(api_fixes, language="json")
                    st.download_button(
                        "📥 Download API Template",
                        api_fixes,
                        file_name=f"api_fix_{drill_field}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json",
                        use_container_width=True
                    )
        
        st.markdown("---")
        
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

elif netsuite_file and salesforce_file and not compare_button and not st.session_state.get('comparison_triggered', False):
    st.info("👈 Click the '🔍 Compare Data' button in the sidebar to start the analysis.")
elif not netsuite_file or not salesforce_file:
    # Don't show warning if files aren't uploaded - toast message handles it
    pass
