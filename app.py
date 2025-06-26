import streamlit as st
import pandas as pd
from datetime import timedelta

st.set_page_config(page_title="XYZ Attendance Analyzer", layout="wide")

st.title("🏢 XYZ Building – Employee Attendance Analyzer")

st.write("""
Upload **Seating CSV** and **Punch In/Out CSV** from Security System.
This tool will:
- Match employees by full name
- Find daily first IN and last OUT
- Calculate total visit days
- Calculate total time spent inside the building
""")

# Uploads
seating_file = st.file_uploader("Upload Seating File", type="csv", key="seating")
punch_file = st.file_uploader("Upload Security Punch File", type="csv", key="punch")

def format_duration(td):
    if pd.isnull(td):
        return "00:00"
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    return f"{hours:02d}:{minutes:02d}"

def process_data(seating_df, punch_df):
    # Step 1: Prepare names
    punch_df['Full Name'] = (punch_df['First name'].fillna('') + ' ' + punch_df['Last name'].fillna('')).str.strip().str.upper()
    seating_df['EMPLOYEE NAME(Security)'] = seating_df['EMPLOYEE NAME(Security)'].str.strip().str.upper()

    # Step 2: Convert timestamps
    punch_df['Event timestamp'] = pd.to_datetime(punch_df['Event timestamp'], errors='coerce')
    punch_df = punch_df.dropna(subset=['Event timestamp'])

    # Step 3: Filter events
    valid_events = ['Access Granted', 'Door Forced Open', 'Access Denied']
    punch_df = punch_df[punch_df['Event'].isin(valid_events)]
    punch_df['Date'] = punch_df['Event timestamp'].dt.date

    # Step 4: Get daily IN and OUT
    attendance_summary = []
    for (name, date), group in punch_df.groupby(['Full Name', 'Date']):
        times = group['Event timestamp'].sort_values()
        duration = times.iloc[-1] - times.iloc[0] if len(times) > 1 else timedelta()
        attendance_summary.append({
            'EMPLOYEE NAME(Security)': name,
            'Date': date,
            'First In': times.iloc[0],
            'Last Out': times.iloc[-1],
            'Duration': duration
        })
    att_df = pd.DataFrame(attendance_summary)

    # Step 5: Group by person
    visit_counts = att_df.groupby('EMPLOYEE NAME(Security)').size().reset_index(name="Day^Visited")
    total_time = att_df.groupby('EMPLOYEE NAME(Security)')['Duration'].sum().reset_index()
    total_time['Total_Hours'] = total_time['Duration'].apply(format_duration)
    total_time.drop(columns='Duration', inplace=True)

    # Step 6: Merge with seating
    final_df = pd.merge(seating_df, visit_counts, on="EMPLOYEE NAME(Security)", how='left')
    final_df = pd.merge(final_df, total_time, on="EMPLOYEE NAME(Security)", how='left')
    final_df['Day^Visited'] = final_df['Day^Visited'].fillna(0).astype(int)
    final_df['Total_Hours'] = final_df['Total_Hours'].fillna("00:00")

    return final_df

# Run Analysis
if seating_file and punch_file:
    try:
        seating_df = pd.read_csv(seating_file)
        punch_df = pd.read_csv(punch_file)
        final_output = process_data(seating_df, punch_df)

        st.success("✅ Attendance Analyzed Successfully")
        st.dataframe(final_output)

        # Download
        csv_data = final_output.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Result CSV", csv_data, "XYZ_Attendance_Analysis.csv", "text/csv")

    except Exception as e:
        st.error(f"❌ Error: {e}")