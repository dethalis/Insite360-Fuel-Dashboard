import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Insite360 Fuel Dashboard", layout="wide", initial_sidebar_state="expanded")
st.title("🚀 Insite360 Gilbarco Fuel Flow Dashboard")
st.markdown("**Professional Flow Rate Analytics** — Stations & Grades")

# File uploader
uploaded_file = st.file_uploader("Upload Insite360 Fuel Report CSV", type=["csv"])

if uploaded_file is None:
    st.info("👆 Upload your latest export from https://insite360.gilbarco.com/")
    st.stop()

@st.cache_data
def load_and_parse_data(uploaded_file):
    df_raw = pd.read_csv(uploaded_file)
    stations_data = []
    current_station = None
    grades = None

    for _, row in df_raw.iterrows():
        if row['Record Type'] == 'S':
            current_station = f"Station {row['Store/Fuel Position']}"
            grades = []
            for col in df_raw.columns[2:]:
                grade = str(row[col]).strip()
                if grade and grade not in [' ', 'Unknown', 'N/A', '']:
                    grades.append(grade)
            continue

        if row['Record Type'] == 'F' and current_station:
            position = row['Store/Fuel Position']
            for i, grade in enumerate(grades):
                col_name = f"Grade {i+1}"
                if col_name in row and pd.notna(row[col_name]):
                    flow = str(row[col_name]).strip()
                    if flow not in ['N/A', ' ', '']:
                        try:
                            flow_rate = float(flow)
                            stations_data.append({
                                'Station': current_station,
                                'Position': f"Pos {position}",
                                'Grade': grade,
                                'Flow_Rate': flow_rate
                            })
                        except:
                            pass
    return pd.DataFrame(stations_data)

data = load_and_parse_data(uploaded_file)

if data.empty:
    st.error("Failed to parse data. Try a fresh export.")
    st.stop()

# Custom Grade Order
GRADE_ORDER = ["Regular", "REGULAR", "Plus", "PLUS", "Premium", "PREMIUM", 
               "Supreme", "SUPREME", "Diesel", "DIESEL", "Recreational", 
               "Rec 90", "REC", "R90"]

def custom_grade_sort(grade):
    grade_upper = str(grade).upper().strip()
    for i, pattern in enumerate([g.upper() for g in GRADE_ORDER]):
        if pattern in grade_upper or grade_upper in pattern:
            return i
    return 999

# Apply sorting
data['Grade_Sort'] = data['Grade'].apply(custom_grade_sort)
data = data.sort_values(by=['Station', 'Grade_Sort']).reset_index(drop=True)

# Sidebar Filters
st.sidebar.header("🔍 Filters")

selected_station = st.sidebar.selectbox("Select Station", 
                                      options=sorted(data['Station'].unique()), 
                                      index=0)

station_grades = data[data['Station'] == selected_station]['Grade'].unique()
station_grades = sorted(station_grades, key=custom_grade_sort)

selected_grades = st.sidebar.multiselect("Select Grades", 
                                       options=station_grades, 
                                       default=station_grades)

filtered_data = data[(data['Station'] == selected_station) & 
                     (data['Grade'].isin(selected_grades))]

# KPI Cards
LOW_FLOW_THRESHOLD = 6.0

col1, col2, col3, col4 = st.columns(4)
col1.metric("**Station**", selected_station)
col2.metric("**Avg Flow Rate**", f"{filtered_data['Flow_Rate'].mean():.2f} gpm")
col3.metric("**Highest Flow**", f"{filtered_data['Flow_Rate'].max():.2f} gpm")
col4.metric(f"**Low Flow** (<{LOW_FLOW_THRESHOLD} gpm)", 
            len(filtered_data[filtered_data['Flow_Rate'] < LOW_FLOW_THRESHOLD]))

# Tabs - Now only 2 tabs
tab1, tab2 = st.tabs(["📊 Overview", "🔧 Fuel Position Details"])

with tab1:
    st.subheader("Average Flow Rate by Grade")
    avg_grade = filtered_data.groupby('Grade')['Flow_Rate'].mean().reset_index()
    avg_grade['Grade_Sort'] = avg_grade['Grade'].apply(custom_grade_sort)
    avg_grade = avg_grade.sort_values('Grade_Sort')
    
    fig1 = px.bar(avg_grade, x='Grade', y='Flow_Rate', color='Flow_Rate',
                 color_continuous_scale='Viridis', title=f"Performance at {selected_station}")
    st.plotly_chart(fig1, use_container_width=True)

    st.subheader("Flow Rate Distribution")
    fig2 = px.box(filtered_data, x='Grade', y='Flow_Rate', color='Grade',
                 category_orders={"Grade": station_grades},
                 title="Distribution by Grade")
    st.plotly_chart(fig2, use_container_width=True)

with tab2:
    st.subheader(f"Fuel Position Details - {selected_station}")
    
    for grade in station_grades:
        if grade in selected_grades:
            grade_data = filtered_data[filtered_data['Grade'] == grade]
            avg = grade_data['Flow_Rate'].mean()
            
            st.markdown(f"### {grade}")
            subcol1, subcol2 = st.columns([3,1])
            with subcol1:
                fig = px.bar(grade_data, x='Position', y='Flow_Rate', 
                            title=f"{grade} - Flow by Position",
                            color='Flow_Rate', color_continuous_scale='Blues')
                st.plotly_chart(fig, use_container_width=True)
            with subcol2:
                st.metric("Average", f"{avg:.2f} gpm")
                st.metric("Positions", len(grade_data))
                st.metric("Min / Max", f"{grade_data['Flow_Rate'].min():.1f} / {grade_data['Flow_Rate'].max():.1f}")
                low_count = len(grade_data[grade_data['Flow_Rate'] < LOW_FLOW_THRESHOLD])
                if low_count > 0:
                    st.warning(f"⚠️ {low_count} low flow position(s)")
            
            st.divider()