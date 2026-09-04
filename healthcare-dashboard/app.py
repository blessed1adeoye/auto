# healthcare-dashboard/app.py

# app.py - Complete Dashboard for New PythonAnywhere Account
import dash
from dash import Dash, dcc, html, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os
import sqlite3
import sys

# ============================================
# LOAD DATA FROM DJANGO DATABASE
# ============================================
def load_data_from_django():
    """
    Load data directly from the Django SQLite database on the original account.
    Path: /home/himuch/clinic_form/db.sqlite3
    """
    db_path = '/home/himuch/clinic_form/db.sqlite3'
    
    # Try alternate paths if the main one doesn't work
    alternate_paths = [
        '/home/himuch/clinic_form/db.sqlite3',
        '/home/himuch/db.sqlite3',
        'db.sqlite3'
    ]
    
    for path in alternate_paths:
        if os.path.exists(path):
            db_path = path
            print(f"✅ Found database at: {db_path}")
            break
    
    if not os.path.exists(db_path):
        print(f"⚠️ Database not found at any path. Using sample data.")
        return create_sample_data()
    
    try:
        # Connect to SQLite database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"📊 Found tables: {tables}")
        
        # Find the clinic/patient table
        possible_tables = ['clinic_form_patient', 'attendance_patient', 'patients', 'clinic']
        table_name = None
        
        for table in possible_tables:
            if table in tables:
                table_name = table
                break
        
        # If no matching table found, use the first table
        if not table_name and tables:
            table_name = tables[0]
            print(f"ℹ️ Using first available table: {table_name}")
        
        if not table_name:
            print("❌ No tables found in database")
            conn.close()
            return create_sample_data()
        
        print(f"📊 Reading from table: {table_name}")
        
        # Read the entire table
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
        conn.close()
        
        if df.empty:
            print("ℹ️ Table is empty. Using sample data.")
            return create_sample_data()
        
        print(f"✅ Loaded {len(df)} records from {table_name}")
        
        # Try to identify columns
        print(f"📋 Columns: {df.columns.tolist()}")
        
        # Transform data (add derived columns)
        df = transform_data(df)
        
        return df
        
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        import traceback
        traceback.print_exc()
        return create_sample_data()

def transform_data(df):
    """
    Transform the data - add derived columns like Clinic Type, date components, etc.
    """
    if df is None or df.empty:
        return df
    
    df_transformed = df.copy()
    
    # Standardize column names (make them case-insensitive)
    column_map = {}
    for col in df_transformed.columns:
        col_lower = col.lower()
        if col_lower == 'date':
            column_map[col] = 'Date'
        elif col_lower in ['clinic', 'clinics']:
            column_map[col] = 'Clinic'
        elif col_lower in ['specialty', 'specialities']:
            column_map[col] = 'Specialty'
        elif 'grand' in col_lower and 'total' in col_lower:
            column_map[col] = 'Grand Total'
        elif 'new' in col_lower and 'male' in col_lower and 'children' in col_lower:
            column_map[col] = 'New Male Children'
        elif 'new' in col_lower and 'female' in col_lower and 'children' in col_lower:
            column_map[col] = 'New Female Children'
        elif 'new' in col_lower and 'male' in col_lower and 'adult' in col_lower:
            column_map[col] = 'New Male Adult'
        elif 'new' in col_lower and 'female' in col_lower and 'adult' in col_lower:
            column_map[col] = 'New Female Adult'
        elif 'follow' in col_lower and 'male' in col_lower and 'children' in col_lower:
            column_map[col] = 'Follow-up Male Children'
        elif 'follow' in col_lower and 'female' in col_lower and 'children' in col_lower:
            column_map[col] = 'Follow-up Female Children'
        elif 'follow' in col_lower and 'male' in col_lower and 'adult' in col_lower:
            column_map[col] = 'Follow-up Male Adult'
        elif 'follow' in col_lower and 'female' in col_lower and 'adult' in col_lower:
            column_map[col] = 'Follow-up Female Adult'
    
    if column_map:
        df_transformed = df_transformed.rename(columns=column_map)
        print(f"   Renamed columns: {list(column_map.values())}")
    
    # ============================================
    # 1. Add Clinic Type (Your exact logic)
    # ============================================
    def get_clinic_type(row):
        clinic = str(row.get('Clinic', '')).strip().upper()
        specialty = str(row.get('Specialty', '')).strip().upper()
        
        # Emergency Department rules
        if clinic == "EMERGENCY DEPARTMENT" and specialty == "Casualty Unit":
            return "Consultative"
        if clinic == "EMERGENCY DEPARTMENT" and specialty == "EMERGENCY Unit":
            return "Non-Consultative"
        
        # Consultative clinics list
        consultative_clinics = [
            "MOP", "HEMATOLOGY", "STC", "PSYCHIATRY", 
            "SOP", "EYE", "ENT", "DENTAL",
            "RADIATION ONCOLOGY", "OBS & GYN", "CHOP",
            "Dental Private"
        ]
        
        if clinic in consultative_clinics:
            return "Consultative"
        
        return "Non-Consultative"
    
    # Apply Clinic Type function
    df_transformed['Clinic Type'] = df_transformed.apply(get_clinic_type, axis=1)
    
    # ============================================
    # 2. Add Date components
    # ============================================
    date_col = 'Date' if 'Date' in df_transformed.columns else None
    if date_col:
        df_transformed['Date'] = pd.to_datetime(df_transformed['Date'])
        df_transformed['YEAR'] = df_transformed['Date'].dt.year
        df_transformed['MONTH'] = df_transformed['Date'].dt.month
        df_transformed['DAY'] = df_transformed['Date'].dt.day
        df_transformed['Month Name'] = df_transformed['Date'].dt.strftime('%B')
        df_transformed['DayOfWeek'] = df_transformed['Date'].dt.day_name()
        df_transformed['Week'] = df_transformed['Date'].dt.isocalendar().week
        df_transformed['Quarter'] = df_transformed['Date'].dt.quarter
    
    # ============================================
    # 3. Add derived patient counts
    # ============================================
    # Try to find or calculate required columns
    cols = df_transformed.columns.tolist()
    
    # Total New Male
    if 'Total New Male' not in cols:
        new_male_cols = [c for c in cols if 'new' in c.lower() and 'male' in c.lower()]
        if new_male_cols:
            df_transformed['Total New Male'] = df_transformed[new_male_cols[0]]
    
    # Total New Female
    if 'Total New Female' not in cols:
        new_female_cols = [c for c in cols if 'new' in c.lower() and 'female' in c.lower()]
        if new_female_cols:
            df_transformed['Total New Female'] = df_transformed[new_female_cols[0]]
    
    # Total Follow-up Male
    if 'Total Follow-up Male' not in cols:
        follow_male_cols = [c for c in cols if 'follow' in c.lower() and 'male' in c.lower()]
        if follow_male_cols:
            df_transformed['Total Follow-up Male'] = df_transformed[follow_male_cols[0]]
    
    # Total Follow-up Female
    if 'Total Follow-up Female' not in cols:
        follow_female_cols = [c for c in cols if 'follow' in c.lower() and 'female' in c.lower()]
        if follow_female_cols:
            df_transformed['Total Follow-up Female'] = df_transformed[follow_female_cols[0]]
    
    # Calculate derived metrics
    if 'Total New Male' in df_transformed.columns and 'Total New Female' in df_transformed.columns:
        df_transformed['New Patients'] = df_transformed['Total New Male'] + df_transformed['Total New Female']
    
    if 'Total Follow-up Male' in df_transformed.columns and 'Total Follow-up Female' in df_transformed.columns:
        df_transformed['Follow-up Patients'] = df_transformed['Total Follow-up Male'] + df_transformed['Total Follow-up Female']
    
    # Children calculation
    children_cols = ['New Male Children', 'New Female Children', 
                   'Follow-up Male Children', 'Follow-up Female Children']
    if all(col in df_transformed.columns for col in children_cols):
        df_transformed['Children'] = sum(df_transformed[col] for col in children_cols)
    
    # Adults calculation
    adult_cols = ['New Male Adult', 'New Female Adult', 
                 'Follow-up Male Adult', 'Follow-up Female Adult']
    if all(col in df_transformed.columns for col in adult_cols):
        df_transformed['Adults'] = sum(df_transformed[col] for col in adult_cols)
    
    # Male calculation
    male_cols = ['New Male Children', 'New Male Adult', 
                'Follow-up Male Children', 'Follow-up Male Adult']
    if all(col in df_transformed.columns for col in male_cols):
        df_transformed['Male'] = sum(df_transformed[col] for col in male_cols)
    
    # Female calculation
    female_cols = ['New Female Children', 'New Female Adult', 
                  'Follow-up Female Children', 'Follow-up Female Adult']
    if all(col in df_transformed.columns for col in female_cols):
        df_transformed['Female'] = sum(df_transformed[col] for col in female_cols)
    
    # Total Patients
    if 'Grand Total' in df_transformed.columns:
        df_transformed['Total Patients'] = df_transformed['Grand Total']
    elif 'New Patients' in df_transformed.columns and 'Follow-up Patients' in df_transformed.columns:
        df_transformed['Total Patients'] = df_transformed['New Patients'] + df_transformed['Follow-up Patients']
    
    print(f"✅ Transformed data with columns: {df_transformed.columns.tolist()}")
    
    return df_transformed

def create_sample_data():
    """Create sample data for demonstration when database is not available"""
    print("📊 Creating sample data for demonstration...")
    np.random.seed(42)
    dates = pd.date_range('2026-01-01', '2026-08-31', freq='D')
    clinics = ['Clinic A', 'Clinic B', 'Clinic C', 'Clinic D']
    specialties = ['Cardiology', 'Neurology', 'Orthopedics', 'Pediatrics', 'Dermatology']
    clinic_types = ['Consultative', 'Non-consultative']
    
    data = []
    for date in dates:
        for clinic in clinics:
            for specialty in specialties[:3]:
                data.append({
                    'Date': date,
                    'Clinic': clinic,
                    'Specialty': specialty,
                    'Clinic Type': np.random.choice(clinic_types),
                    'Grand Total': np.random.randint(5, 30),
                    'Total New Male': np.random.randint(1, 10),
                    'Total New Female': np.random.randint(1, 10),
                    'Total Follow-up Male': np.random.randint(1, 8),
                    'Total Follow-up Female': np.random.randint(1, 8),
                    'New Male Children': np.random.randint(0, 5),
                    'New Female Children': np.random.randint(0, 5),
                    'New Male Adult': np.random.randint(1, 8),
                    'New Female Adult': np.random.randint(1, 8),
                    'Follow-up Male Children': np.random.randint(0, 3),
                    'Follow-up Female Children': np.random.randint(0, 3),
                    'Follow-up Male Adult': np.random.randint(1, 6),
                    'Follow-up Female Adult': np.random.randint(1, 6),
                })
    
    df = pd.DataFrame(data)
    
    # Add derived columns
    df['New Patients'] = df['Total New Male'] + df['Total New Female']
    df['Follow-up Patients'] = df['Total Follow-up Male'] + df['Total Follow-up Female']
    df['Children'] = df['New Male Children'] + df['New Female Children'] + df['Follow-up Male Children'] + df['Follow-up Female Children']
    df['Adults'] = df['New Male Adult'] + df['New Female Adult'] + df['Follow-up Male Adult'] + df['Follow-up Male Adult']
    df['Male'] = df['New Male Children'] + df['New Male Adult'] + df['Follow-up Male Children'] + df['Follow-up Male Adult']
    df['Female'] = df['New Female Children'] + df['New Female Adult'] + df['Follow-up Female Children'] + df['Follow-up Female Adult']
    df['Total Patients'] = df['Grand Total']
    df['Month Name'] = df['Date'].dt.strftime('%B')
    df['YEAR'] = df['Date'].dt.year
    df['MONTH'] = df['Date'].dt.month
    df['DAY'] = df['Date'].dt.day
    
    return df

# ============================================
# LOAD THE DATA
# ============================================
print("="*60)
print("🚀 Starting Healthcare Dashboard")
print("="*60)

# Load data from Django database
df_clean = load_data_from_django()

if df_clean is None or df_clean.empty:
    print("⚠️ No data loaded, using sample data")
    df_clean = create_sample_data()

# Ensure Date column is datetime
if 'Date' in df_clean.columns:
    df_clean['Date'] = pd.to_datetime(df_clean['Date'])

print(f"📊 Final dataset: {len(df_clean)} records")
print(f"📋 Columns: {df_clean.columns.tolist()}")
print("="*60)

# ============================================
# GET UNIQUE VALUES FOR FILTERS
# ============================================
clinic_types = ['All'] + sorted(df_clean['Clinic Type'].dropna().unique().tolist()) if 'Clinic Type' in df_clean.columns else ['All']
all_clinics = ['All'] + sorted(df_clean['Clinic'].dropna().unique().tolist()) if 'Clinic' in df_clean.columns else ['All']
all_specialties = ['All'] + sorted(df_clean['Specialty'].dropna().unique().tolist()) if 'Specialty' in df_clean.columns else ['All']
month_order = ['January', 'February', 'March', 'April', 'May', 'June', 
               'July', 'August', 'September', 'October', 'November', 'December']

# Get date range
if not df_clean.empty and 'Date' in df_clean.columns:
    min_date = df_clean['Date'].min()
    max_date = df_clean['Date'].max()
else:
    min_date = datetime.now() - timedelta(days=30)
    max_date = datetime.now()

# Create mapping for cascading filters
clinic_type_clinic_map = {}
if 'Clinic Type' in df_clean.columns and 'Clinic' in df_clean.columns and not df_clean.empty:
    for clinic_type in df_clean['Clinic Type'].dropna().unique():
        clinics = df_clean[df_clean['Clinic Type'] == clinic_type]['Clinic'].dropna().unique().tolist()
        clinic_type_clinic_map[clinic_type] = ['All'] + sorted(clinics)

clinic_specialty_map = {}
if 'Clinic' in df_clean.columns and 'Specialty' in df_clean.columns and not df_clean.empty:
    for clinic in df_clean['Clinic'].dropna().unique():
        specialties = df_clean[df_clean['Clinic'] == clinic]['Specialty'].dropna().unique().tolist()
        clinic_specialty_map[clinic] = ['All'] + sorted(specialties)

# ============================================
# CREATE THE DASH APP WITH RESPONSIVE DESIGN
# ============================================
app = Dash(
    __name__, 
    external_stylesheets=[dbc.themes.DARKLY],
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
    title='Healthcare Dashboard'
)

# Server for gunicorn
server = app.server

# Custom CSS with responsive design
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            /* RED Color Scheme and Responsive Design */
            :root {
                --primary-red: #dc2626;
                --primary-red-dark: #b91c1c;
                --primary-red-light: #ef4444;
                --secondary-red: #f87171;
                --gold: #fbbf24;
                --gradient-red: linear-gradient(135deg, #dc2626 0%, #7f1d1d 100%);
                --gradient-red-light: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
                --gradient-gold: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
                --bg-dark: #0f0f1a;
                --bg-card: #1a1a2e;
                --bg-hover: #2d1b1b;
                --text-primary: #ffffff;
                --text-secondary: #e2e8f0;
                --border-color: #4a1a1a;
            }
            
            .dashboard-container {
                width: 100%;
                max-width: 100%;
                margin: 0 auto;
                padding: 0;
                background: var(--bg-dark);
                min-height: 100vh;
            }
            
            .sidebar-div {
                background: linear-gradient(180deg, #0f0f1a 0%, #1a0f0f 100%) !important;
                border-right: 2px solid #4a1a1a !important;
                height: 100vh;
                overflow-y: auto;
                position: sticky;
                top: 0;
            }
            
            @media (max-width: 768px) {
                .sidebar-div {
                    height: auto;
                    max-height: 50vh;
                    position: relative;
                    border-right: none !important;
                    border-bottom: 2px solid #4a1a1a !important;
                }
            }
            
            .content-div {
                background-color: #0f0f1a;
                min-height: 100vh;
                padding: 20px;
            }
            
            @media (max-width: 768px) {
                .content-div {
                    padding: 10px;
                }
            }
            
            .Select-control {
                background: var(--bg-card) !important;
                border: 2px solid #4a1a1a !important;
                border-radius: 8px !important;
                min-height: 42px !important;
                transition: all 0.3s ease !important;
            }
            .Select-control:hover {
                border-color: var(--primary-red) !important;
                box-shadow: 0 0 20px rgba(220, 38, 38, 0.3) !important;
            }
            .is-open .Select-control {
                border-color: var(--primary-red) !important;
                box-shadow: 0 0 30px rgba(220, 38, 38, 0.5) !important;
            }
            .Select-value-label {
                color: #fbbf24 !important;
                font-weight: 700 !important;
                font-size: 15px !important;
                text-shadow: 0 0 15px rgba(251, 191, 36, 0.3) !important;
            }
            .Select-menu-outer {
                background: var(--bg-card) !important;
                border: 2px solid #4a1a1a !important;
                border-radius: 8px !important;
                margin-top: 4px !important;
            }
            .Select-option {
                background: var(--bg-card) !important;
                color: var(--text-primary) !important;
                padding: 10px 15px !important;
                transition: all 0.2s ease !important;
            }
            .Select-option:hover {
                background: var(--gradient-red) !important;
                color: #ffffff !important;
            }
            .Select-option.is-selected {
                background: var(--gradient-red-light) !important;
                color: #ffffff !important;
                font-weight: 600 !important;
            }
            
            .filter-label {
                color: #fca5a5 !important;
                font-weight: 700 !important;
                font-size: 14px !important;
                margin-bottom: 8px !important;
                display: block !important;
                letter-spacing: 0.5px !important;
                text-shadow: 0 0 10px rgba(220, 38, 38, 0.3) !important;
            }
            
            .DateInput_input {
                background: var(--bg-card) !important;
                color: var(--text-primary) !important;
                border: 2px solid #4a1a1a !important;
                border-radius: 8px !important;
                padding: 8px 12px !important;
                transition: all 0.3s ease !important;
                font-size: 14px !important;
            }
            .DateInput_input:focus {
                border-color: var(--primary-red) !important;
                box-shadow: 0 0 20px rgba(220, 38, 38, 0.3) !important;
            }
            .DateRangePickerInput {
                background: var(--bg-card) !important;
                border-radius: 8px !important;
                width: 100% !important;
            }
            .DateRangePickerInput_arrow {
                color: #fca5a5 !important;
            }
            
            @media (max-width: 480px) {
                .DateRangePickerInput {
                    flex-direction: column !important;
                }
                .DateInput {
                    width: 100% !important;
                }
                .DateRangePickerInput_arrow {
                    transform: rotate(90deg);
                    margin: 5px 0 !important;
                }
            }
            
            .btn-primary {
                background: var(--gradient-red) !important;
                border: none !important;
                border-radius: 8px !important;
                font-weight: 600 !important;
                padding: 8px 16px !important;
                transition: all 0.3s ease !important;
                box-shadow: 0 4px 15px rgba(220, 38, 38, 0.4) !important;
            }
            .btn-primary:hover {
                transform: translateY(-2px) !important;
                box-shadow: 0 6px 25px rgba(220, 38, 38, 0.6) !important;
            }
            .btn-success {
                background: var(--gradient-gold) !important;
                border: none !important;
                border-radius: 8px !important;
                font-weight: 600 !important;
                padding: 8px 16px !important;
                transition: all 0.3s ease !important;
                box-shadow: 0 4px 15px rgba(251, 191, 36, 0.4) !important;
                color: #1a1a2e !important;
            }
            .btn-success:hover {
                transform: translateY(-2px) !important;
                box-shadow: 0 6px 25px rgba(251, 191, 36, 0.6) !important;
            }
            
            @media (max-width: 480px) {
                .btn {
                    font-size: 12px !important;
                    padding: 6px 12px !important;
                }
            }
            
            .stat-item {
                padding: 6px 0;
                color: #e2e8f0;
                font-size: 13px;
                font-weight: 500;
                border-bottom: 1px solid rgba(74, 26, 26, 0.3);
                display: block !important;
            }
            .stat-item:last-child {
                border-bottom: none;
            }
            .stat-value {
                color: #fca5a5 !important;
                font-weight: 700 !important;
                font-size: 14px !important;
                text-shadow: 0 0 10px rgba(220, 38, 38, 0.2) !important;
            }
            
            .sidebar-title {
                color: #fca5a5 !important;
                text-shadow: 0 0 20px rgba(220, 38, 38, 0.3) !important;
                font-weight: 800 !important;
            }
            .main-title {
                color: #fca5a5 !important;
                text-shadow: 0 0 30px rgba(220, 38, 38, 0.3) !important;
                font-weight: 800 !important;
            }
            
            ::-webkit-scrollbar {
                width: 8px;
            }
            ::-webkit-scrollbar-track {
                background: #1a1a2e;
            }
            ::-webkit-scrollbar-thumb {
                background: var(--gradient-red);
                border-radius: 4px;
            }
            ::-webkit-scrollbar-thumb:hover {
                background: var(--gradient-red-light);
            }
            
            .custom-hr {
                border: none;
                height: 2px;
                background: linear-gradient(90deg, #dc2626, #ef4444, #f87171, #dc2626);
                opacity: 0.6;
            }
            
            .graph-container {
                width: 100%;
                height: auto;
            }
            
            @media (max-width: 768px) {
                .graph-container {
                    height: 500px;
                }
            }
            
            @media (max-width: 480px) {
                .graph-container {
                    height: 400px;
                }
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# ============================================
# FUNCTION TO CREATE YOUR DASHBOARD FIGURE
# ============================================
def create_dashboard_figure(df, selected_clinic='All', selected_specialty='All', 
                            selected_clinic_type='All', start_date=None, end_date=None):
    """Create the advanced dashboard figure with filters applied"""
    
    # Filter data
    filtered_df = df.copy()
    
    if 'Clinic Type' in df.columns and selected_clinic_type != 'All':
        filtered_df = filtered_df[filtered_df['Clinic Type'] == selected_clinic_type]
    if 'Clinic' in df.columns and selected_clinic != 'All':
        filtered_df = filtered_df[filtered_df['Clinic'] == selected_clinic]
    if 'Specialty' in df.columns and selected_specialty != 'All':
        filtered_df = filtered_df[filtered_df['Specialty'] == selected_specialty]
    if 'Date' in df.columns:
        if start_date:
            filtered_df = filtered_df[filtered_df['Date'] >= start_date]
        if end_date:
            filtered_df = filtered_df[filtered_df['Date'] <= end_date]
    
    # Create subplots
    fig = make_subplots(
        rows=3, 
        cols=3,
        subplot_titles=(
            '📈 Patient Volume Trend', 
            '📊 Distribution',
            '🏥 Clinic Performance',
            '📅 Monthly Trends', 
            '👥 Age Distribution',
            '⚧️ Gender Distribution',
            '🔄 New vs Follow-up',
            '📊 Top Specialties',
            '📈 Cumulative Patients'
        ),
        specs=[
            [{"type": "xy"}, {"type": "xy"}, {"type": "xy"}],
            [{"type": "xy"}, {"type": "domain"}, {"type": "domain"}],
            [{"type": "xy"}, {"type": "xy"}, {"type": "xy"}]
        ],
        vertical_spacing=0.12, 
        horizontal_spacing=0.12
    )
    
    # Chart 1: Time Series
    if not filtered_df.empty and 'Date' in filtered_df.columns and 'Total Patients' in filtered_df.columns:
        daily_data = filtered_df.groupby('Date')['Total Patients'].sum().reset_index()
        rolling_avg = daily_data['Total Patients'].rolling(window=7).mean()
        
        fig.add_trace(
            go.Scatter(
                x=daily_data['Date'], 
                y=daily_data['Total Patients'],
                mode='lines',
                name='Daily',
                line=dict(color='#ef4444', width=3),
                fill='tozeroy',
                fillcolor='rgba(239, 68, 68, 0.2)',
                hovertemplate='Date: %{x}<br>Patients: %{y:,}<extra></extra>'
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=daily_data['Date'], 
                y=rolling_avg,
                mode='lines',
                name='7-Day Avg',
                line=dict(color='#fbbf24', width=4, dash='dash'),
                hovertemplate='Date: %{x}<br>7-Day Avg: %{y:.0f}<extra></extra>'
            ),
            row=1, col=1
        )
        
        # Chart 2: Distribution
        fig.add_trace(
            go.Histogram(
                x=filtered_df['Total Patients'],
                name='Distribution',
                nbinsx=25,
                marker=dict(
                    color=filtered_df['Total Patients'],
                    colorscale='Reds',
                    line=dict(color='white', width=1),
                    showscale=False
                ),
                hovertemplate='Patients: %{x}<br>Frequency: %{y}<extra></extra>'
            ),
            row=1, col=2
        )
        
        # Add mean and median lines
        mean_val = filtered_df['Total Patients'].mean()
        median_val = filtered_df['Total Patients'].median()
        
        fig.add_vline(
            x=mean_val, 
            line_dash="dash", 
            line_color="#ef4444", 
            annotation_text=f"Mean: {mean_val:.0f}", 
            annotation_position="top",
            row=1, col=2
        )
        fig.add_vline(
            x=median_val, 
            line_dash="dash", 
            line_color="#fbbf24",
            annotation_text=f"Median: {median_val:.0f}", 
            annotation_position="bottom",
            row=1, col=2
        )
        
        # Chart 3: Clinic Performance
        if 'Clinic' in filtered_df.columns:
            clinic_data = filtered_df.groupby('Clinic')['Total Patients'].sum().sort_values(ascending=False).reset_index()
            fig.add_trace(
                go.Bar(
                    x=clinic_data['Clinic'],
                    y=clinic_data['Total Patients'],
                    name='Clinic Volume',
                    marker=dict(
                        color=clinic_data['Total Patients'],
                        colorscale='Reds',
                        showscale=False,
                        line=dict(color='white', width=1)
                    ),
                    text=clinic_data['Total Patients'],
                    textposition='outside',
                    textfont=dict(size=10),
                    hovertemplate='Clinic: %{x}<br>Patients: %{y:,}<extra></extra>'
                ),
                row=1, col=3
            )
        
        # Chart 4: Monthly Trends
        if 'Month Name' in filtered_df.columns:
            month_data = filtered_df.groupby('Month Name')['Total Patients'].sum().reindex(month_order).reset_index()
            fig.add_trace(
                go.Scatter(
                    x=month_data['Month Name'],
                    y=month_data['Total Patients'],
                    mode='lines+markers',
                    name='Monthly',
                    line=dict(color='#f87171', width=3),
                    marker=dict(size=12, color='#f87171'),
                    fill='tozeroy',
                    fillcolor='rgba(248, 113, 113, 0.15)',
                    hovertemplate='Month: %{x}<br>Patients: %{y:,}<extra></extra>'
                ),
                row=2, col=1
            )
        
        # Chart 5: Age Distribution
        if 'Children' in filtered_df.columns and 'Adults' in filtered_df.columns:
            age_data = pd.DataFrame({
                'Category': ['Children', 'Adults'],
                'Count': [filtered_df['Children'].sum(), filtered_df['Adults'].sum()]
            })
            fig.add_trace(
                go.Pie(
                    labels=age_data['Category'],
                    values=age_data['Count'],
                    name='Age',
                    hole=0.45,
                    marker=dict(colors=['#ef4444', '#fca5a5']),
                    textinfo='label+percent',
                    textfont=dict(size=12, color='white'),
                    hoverinfo='label+value',
                    pull=[0.05, 0],
                    showlegend=False
                ),
                row=2, col=2
            )
        
        # Chart 6: Gender Distribution
        if 'Male' in filtered_df.columns and 'Female' in filtered_df.columns:
            gender_data = pd.DataFrame({
                'Category': ['Male', 'Female'],
                'Count': [filtered_df['Male'].sum(), filtered_df['Female'].sum()]
            })
            fig.add_trace(
                go.Pie(
                    labels=gender_data['Category'],
                    values=gender_data['Count'],
                    name='Gender',
                    hole=0.45,
                    marker=dict(colors=['#fbbf24', '#fca5a5']),
                    textinfo='label+percent',
                    textfont=dict(size=12, color='white'),
                    hoverinfo='label+value',
                    pull=[0.05, 0],
                    showlegend=False
                ),
                row=2, col=3
            )
        
        # Chart 7: New vs Follow-up
        if 'New Patients' in filtered_df.columns and 'Follow-up Patients' in filtered_df.columns:
            fig.add_trace(
                go.Scatter(
                    x=filtered_df['New Patients'],
                    y=filtered_df['Follow-up Patients'],
                    mode='markers',
                    name='Patient Mix',
                    marker=dict(
                        size=10,
                        color=filtered_df['Total Patients'],
                        colorscale='Reds',
                        showscale=False,
                        opacity=0.8,
                        line=dict(color='white', width=0.5)
                    ),
                    text=filtered_df['Clinic'] if 'Clinic' in filtered_df.columns else None,
                    hovertemplate='New: %{x:,}<br>Follow-up: %{y:,}<br>Total: %{marker.color:,}<extra></extra>'
                ),
                row=3, col=1
            )
            
            # Add diagonal reference line
            max_val = max(filtered_df['New Patients'].max(), filtered_df['Follow-up Patients'].max())
            fig.add_trace(
                go.Scatter(
                    x=[0, max_val],
                    y=[0, max_val],
                    mode='lines',
                    name='Reference',
                    line=dict(color='#94a3b8', dash='dot', width=2),
                    showlegend=False,
                    hoverinfo='skip'
                ),
                row=3, col=1
            )
        
        # Chart 8: Top Specialties
        if 'Specialty' in filtered_df.columns:
            top_spec = filtered_df.groupby('Specialty')['Total Patients'].sum().sort_values(ascending=False).head(8).reset_index()
            fig.add_trace(
                go.Bar(
                    x=top_spec['Total Patients'],
                    y=top_spec['Specialty'],
                    orientation='h',
                    name='Specialties',
                    marker=dict(
                        color=top_spec['Total Patients'],
                        colorscale='Reds',
                        showscale=False,
                        line=dict(color='white', width=0.5)
                    ),
                    text=top_spec['Total Patients'],
                    textposition='outside',
                    textfont=dict(size=10),
                    hovertemplate='Specialty: %{y}<br>Patients: %{x:,}<extra></extra>'
                ),
                row=3, col=2
            )
        
        # Chart 9: Cumulative Patients
        cumulative = filtered_df.groupby('Date')['Total Patients'].sum().cumsum().reset_index()
        fig.add_trace(
            go.Scatter(
                x=cumulative['Date'],
                y=cumulative['Total Patients'],
                mode='lines',
                name='Cumulative',
                line=dict(color='#fca5a5', width=3),
                fill='tozeroy',
                fillcolor='rgba(252, 165, 165, 0.15)',
                hovertemplate='Date: %{x}<br>Cumulative: %{y:,}<extra></extra>'
            ),
            row=3, col=3
        )
    
    # Update layout - Responsive
    fig.update_layout(
        title=dict(
            text=f'🏥 ADVANCED HEALTHCARE PATIENT ANALYTICS DASHBOARD',
            font=dict(size=24, color='#fca5a5', family='Arial Black'),
            x=0.5,
            y=0.98,
            xanchor='center',
            yanchor='top'
        ),
        height=900,
        template='plotly_dark',
        paper_bgcolor='#0f0f1a',
        plot_bgcolor='#1a1a2e',
        font=dict(color='#e2e8f0', size=11),
        margin=dict(t=80, b=50, l=30, r=30),
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='center',
            x=0.5,
            font=dict(size=10),
            bgcolor='rgba(26, 26, 46, 0.8)',
            bordercolor='#4a1a1a',
            borderwidth=1
        ),
        hovermode='x unified',
        autosize=True
    )
    
    # Update axes
    fig.update_xaxes(gridcolor='#2d1b1b', gridwidth=1)
    fig.update_yaxes(gridcolor='#2d1b1b', gridwidth=1)
    
    # Add rangeslider to first chart
    fig.update_xaxes(
        rangeslider=dict(
            visible=True,
            thickness=0.05,
            bgcolor='#1a1a2e',
            bordercolor='#4a1a1a'
        ),
        row=1, col=1
    )
    
    return fig

# ============================================
# CREATE SIDEBAR WITH FILTERS - RESPONSIVE
# ============================================
sidebar = html.Div(
    [
        html.H2("🏥 Filters", className="sidebar-title display-6 text-center mb-3"),
        html.Hr(className="custom-hr"),
        
        # Clinic Type filter
        html.Label("🏢 Clinic Type", className="filter-label"),
        dcc.Dropdown(
            id="clinic-type-dropdown",
            options=[{"label": ct, "value": ct} for ct in clinic_types],
            value="All",
            clearable=False,
            className="mb-3"
        ),
        
        # Clinic filter
        html.Label("🏥 Clinic", className="filter-label"),
        dcc.Dropdown(
            id="clinic-dropdown",
            options=[{"label": clinic, "value": clinic} for clinic in all_clinics],
            value="All",
            clearable=False,
            className="mb-3"
        ),
        
        # Specialty filter
        html.Label("🔬 Specialty", className="filter-label"),
        dcc.Dropdown(
            id="specialty-dropdown",
            options=[{"label": spec, "value": spec} for spec in all_specialties],
            value="All",
            clearable=False,
            className="mb-3"
        ),
        
        html.Hr(className="custom-hr"),
        
        # Date Range filter
        html.Label("📅 Date Range", className="filter-label"),
        dcc.DatePickerRange(
            id='date-range-picker',
            min_date_allowed=min_date,
            max_date_allowed=max_date,
            initial_visible_month=min_date,
            start_date=min_date,
            end_date=max_date,
            className="mb-2",
            style={'width': '100%'}
        ),
        
        html.Hr(className="custom-hr"),
        
        # Summary statistics
        html.H5("📊 Summary", className="text-center mb-2", style={'color': '#fca5a5'}),
        html.Div(id="summary-stats", children=[
            html.Div("🏥 Total Patients: 0", className="stat-item"),
            html.Div("📊 Avg Patients: 0", className="stat-item"),
            html.Div("🏥 Total Clinics: 0", className="stat-item"),
        ]),
        
        html.Hr(className="custom-hr"),
        
        # Action buttons - Responsive
        dbc.Row(
            [
                dbc.Col(
                    dbc.Button(
                        "🔄 Reset",
                        id="reset-button",
                        color="primary",
                        className="w-100",
                        size="sm"
                    ),
                    width=6
                ),
                dbc.Col(
                    dbc.Button(
                        "💾 Download HTML",
                        id="download-button",
                        color="success",
                        className="w-100",
                        size="sm"
                    ),
                    width=6
                ),
            ],
            className="mb-2"
        ),
        
        html.Div(id="download-status", className="text-success small text-center"),
        
        # Hidden download component
        dcc.Download(id="download-html"),
        
        html.Br(),
        
        # Info
        html.Div(
            f"📅 Data Range: {min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}",
            className="text-muted small text-center",
            style={'color': '#94a3b8'}
        ),
    ],
    className="sidebar-div",
)

# ============================================
# CREATE MAIN CONTENT AREA - RESPONSIVE
# ============================================
content = html.Div(
    [
        html.Div(
            [
                html.H1("Patient Analytics Dashboard", className="text-center mb-3 main-title"),
                html.P(
                    "Interactive healthcare analytics with advanced filter controls",
                    className="text-center text-muted"
                ),
            ],
            style={"padding": "20px 0"}
        ),
        html.Div(
            dcc.Graph(
                id="main-dashboard",
                figure=create_dashboard_figure(df_clean, 'All', 'All', 'All', min_date, max_date),
                config={'responsive': True, 'displayModeBar': True}
            ),
            className="graph-container"
        ),
        
        # Hidden divs for storing data
        dcc.Store(id='figure-data-store'),
        dcc.Store(id='filter-state-store'),
    ],
    className="content-div",
)

# ============================================
# APP LAYOUT - RESPONSIVE
# ============================================
app.layout = dbc.Container(
    [
        dbc.Row(
            [
                # Sidebar - responsive: full width on mobile, 3 cols on desktop
                dbc.Col(
                    sidebar,
                    width=12,
                    lg=3,
                    style={"padding": "0"}
                ),
                
                # Main content - responsive: full width on mobile, 9 cols on desktop
                dbc.Col(
                    content,
                    width=12,
                    lg=9,
                    style={"padding": "0"}
                ),
            ],
            className="g-0",
            style={"minHeight": "100vh"}
        ),
    ],
    fluid=True,
    className="dashboard-container"
)

# ============================================
# CALLBACKS FOR INTERACTIVITY
# ============================================

# Callback for cascading clinic dropdown based on clinic type
@app.callback(
    Output("clinic-dropdown", "options"),
    Output("clinic-dropdown", "value"),
    Input("clinic-type-dropdown", "value")
)
def update_clinic_options(selected_clinic_type):
    """Update clinic dropdown based on selected clinic type"""
    if selected_clinic_type != 'All' and selected_clinic_type in clinic_type_clinic_map:
        options = [{"label": clinic, "value": clinic} for clinic in clinic_type_clinic_map[selected_clinic_type]]
        return options, 'All'
    else:
        options = [{"label": clinic, "value": clinic} for clinic in all_clinics]
        return options, 'All'

# Callback for cascading specialty dropdown based on clinic
@app.callback(
    Output("specialty-dropdown", "options"),
    Output("specialty-dropdown", "value"),
    Input("clinic-dropdown", "value")
)
def update_specialty_options(selected_clinic):
    """Update specialty dropdown based on selected clinic"""
    if selected_clinic != 'All' and selected_clinic in clinic_specialty_map:
        options = [{"label": spec, "value": spec} for spec in clinic_specialty_map[selected_clinic]]
        return options, 'All'
    else:
        options = [{"label": spec, "value": spec} for spec in all_specialties]
        return options, 'All'

# Main callback for updating dashboard
@app.callback(
    Output("main-dashboard", "figure"),
    Output("summary-stats", "children"),
    Output("figure-data-store", "data"),
    Output("filter-state-store", "data"),
    Input("clinic-type-dropdown", "value"),
    Input("clinic-dropdown", "value"),
    Input("specialty-dropdown", "value"),
    Input("date-range-picker", "start_date"),
    Input("date-range-picker", "end_date"),
    Input("reset-button", "n_clicks"),
    prevent_initial_call=False
)
def update_dashboard(selected_clinic_type, selected_clinic, selected_specialty, 
                     start_date, end_date, reset_clicks):
    """Update dashboard based on filter selections"""
    
    # Check which input triggered the callback
    triggered_id = ctx.triggered_id if hasattr(ctx, 'triggered_id') else None
    
    # Reset filters if reset button clicked
    if triggered_id == 'reset-button':
        selected_clinic_type = 'All'
        selected_clinic = 'All'
        selected_specialty = 'All'
        start_date = min_date
        end_date = max_date
    
    # Convert dates if provided
    if start_date:
        start_date = pd.to_datetime(start_date)
    else:
        start_date = min_date
    
    if end_date:
        end_date = pd.to_datetime(end_date)
    else:
        end_date = max_date
    
    # Create figure
    fig = create_dashboard_figure(df_clean, selected_clinic, selected_specialty, 
                                   selected_clinic_type, start_date, end_date)
    
    # Update title with filters
    title = "🏥 ADVANCED HEALTHCARE PATIENT ANALYTICS DASHBOARD"
    filters_applied = []
    if selected_clinic_type != 'All':
        filters_applied.append(selected_clinic_type)
    if selected_clinic != 'All':
        filters_applied.append(selected_clinic)
    if selected_specialty != 'All':
        filters_applied.append(selected_specialty)
    
    if filters_applied:
        title += f" | {' | '.join(filters_applied)}"
    
    fig.update_layout(title_text=title)
    
    # Create summary statistics
    filtered_df = df_clean.copy()
    
    if 'Clinic Type' in filtered_df.columns and selected_clinic_type != 'All':
        filtered_df = filtered_df[filtered_df['Clinic Type'] == selected_clinic_type]
    if 'Clinic' in filtered_df.columns and selected_clinic != 'All':
        filtered_df = filtered_df[filtered_df['Clinic'] == selected_clinic]
    if 'Specialty' in filtered_df.columns and selected_specialty != 'All':
        filtered_df = filtered_df[filtered_df['Specialty'] == selected_specialty]
    if 'Date' in filtered_df.columns:
        filtered_df = filtered_df[(filtered_df['Date'] >= start_date) & (filtered_df['Date'] <= end_date)]
    
    total_patients = filtered_df['Total Patients'].sum() if 'Total Patients' in filtered_df.columns else 0
    avg_patients = filtered_df['Total Patients'].mean() if 'Total Patients' in filtered_df.columns else 0
    total_clinics = filtered_df['Clinic'].nunique() if 'Clinic' in filtered_df.columns else 0
    total_records = len(filtered_df)
    
    summary = [
        html.Div([
            html.Span("🏥 Total Patients: ", style={'color': '#e2e8f0'}),
            html.Span(f"{total_patients:,.0f}", className="stat-value")
        ], className="stat-item"),
        html.Div([
            html.Span("📊 Avg Patients: ", style={'color': '#e2e8f0'}),
            html.Span(f"{avg_patients:.0f}", className="stat-value")
        ], className="stat-item"),
        html.Div([
            html.Span("🏥 Total Clinics: ", style={'color': '#e2e8f0'}),
            html.Span(f"{total_clinics}", className="stat-value")
        ], className="stat-item"),
        html.Div([
            html.Span("📅 Records: ", style={'color': '#e2e8f0'}),
            html.Span(f"{total_records:,}", className="stat-value")
        ], className="stat-item"),
        html.Div([
            html.Span("📆 Period: ", style={'color': '#e2e8f0'}),
            html.Span(f"{start_date.strftime('%Y-%m-%d')}", className="stat-value"),
            html.Span(" to ", style={'color': '#e2e8f0'}),
            html.Span(f"{end_date.strftime('%Y-%m-%d')}", className="stat-value")
        ], className="stat-item"),
    ]
    
    # Store filter state for download
    filter_state = {
        'clinic_type': selected_clinic_type,
        'clinic': selected_clinic,
        'specialty': selected_specialty,
        'start_date': start_date.isoformat() if start_date else None,
        'end_date': end_date.isoformat() if end_date else None
    }
    
    # Store figure data for saving
    fig_json = fig.to_json()
    
    return fig, summary, fig_json, filter_state

# Callback for downloading HTML with filters included
@app.callback(
    Output("download-html", "data"),
    Output("download-status", "children"),
    Output("download-status", "style"),
    Input("download-button", "n_clicks"),
    State("filter-state-store", "data"),
    prevent_initial_call=True
)
def download_dashboard_html(n_clicks, filter_state):
    """Download the complete dashboard with filters as an HTML file"""
    if n_clicks and filter_state:
        try:
            # Extract filter values
            selected_clinic_type = filter_state.get('clinic_type', 'All')
            selected_clinic = filter_state.get('clinic', 'All')
            selected_specialty = filter_state.get('specialty', 'All')
            
            start_date = filter_state.get('start_date')
            end_date = filter_state.get('end_date')
            
            if start_date:
                start_date = pd.to_datetime(start_date)
            else:
                start_date = min_date
                
            if end_date:
                end_date = pd.to_datetime(end_date)
            else:
                end_date = max_date
            
            # Create figure
            fig = create_dashboard_figure(df_clean, selected_clinic, selected_specialty, 
                                         selected_clinic_type, start_date, end_date)
            
            # Update title with filters
            title = "🏥 ADVANCED HEALTHCARE PATIENT ANALYTICS DASHBOARD"
            filters_applied = []
            if selected_clinic_type != 'All':
                filters_applied.append(selected_clinic_type)
            if selected_clinic != 'All':
                filters_applied.append(selected_clinic)
            if selected_specialty != 'All':
                filters_applied.append(selected_specialty)
            
            if filters_applied:
                title += f" | {' | '.join(filters_applied)}"
            
            fig.update_layout(title_text=title)
            
            # Generate HTML
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"dashboard_filters_{timestamp}.html"
            
            # Return download data
            return (
                dict(content=fig.to_html(
                    include_plotlyjs='cdn',
                    full_html=True,
                    config={'responsive': True, 'displayModeBar': True}
                ), filename=filename),
                html.Div([
                    html.Span(f"✅ Download ready: {filename}", className="text-success"),
                    html.Br(),
                    html.Span("📁 Dashboard includes all filters", 
                             className="text-muted small")
                ]),
                {'color': '#fbbf24', 'margin-top': '5px', 'margin-bottom': '5px'}
            )
            
        except Exception as e:
            return (
                None,
                f"❌ Error: {str(e)}",
                {'color': '#ef4444', 'margin-top': '5px', 'margin-bottom': '5px'}
            )
    
    return None, "", {}

# ============================================
# RUN THE APP
# ============================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(
        debug=False,
        host='0.0.0.0',
        port=port
    )