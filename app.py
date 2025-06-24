import streamlit as st
import pandas as pd
from datetime import datetime

st.title("🏢 Atwork Employee Daily Time Analysis (Two File Upload)")

st.write("""
Upload your **Atwork Seating** and **Punch In/Out** CSV files.
- The app will match employees by ID, calculate first in/last out per day, and show total time.
- Download the result as CSV for Excel.
""")

seating_file = st.file_uploader("Upload Atwork Seating CSV", type="csv")
punch_file = st.file_uploader("Upload Punch In/Out CSV", type="csv")

def format_timedelta_to_hhmm(t):
    if pd.isnull(t):
        return ""
    total_minutes = int(t.total_seconds() // 60)
    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{hours:02d}:{minutes:02d}"

def process_punch_data(punch):
    # Create EMPLOYEE ID and NAME columns if not present
    if 'EMPLOYEE ID' not in punch.columns:
        punch['EMPLOYEE ID'] = punch['Cardholder']
    if 'NAME' not in punch.columns:
        punch['NAME'] = punch['First name'].astype(str).str.strip() + " " + punch['Last name'].astype(str).str.strip()
    # Parse timestamps
    punch['Event timestamp'] = pd.to_datetime(punch['Event timestamp'], errors='coerce')
    punch['DATE'] = punch['Event timestamp'].dt.date
    punch['TIME'] = punch['Event timestamp'].dt.time
    # Only IN/OUT events
    punch = punch[punch['Event'].str.lower().isin(['in', 'out'])]
    # Group and get first in/last out
    attendance = punch.groupby(['EMPLOYEE ID', 'NAME', 'DATE']).agg(
        First_In=('Event timestamp', lambda x: x[punch.loc[x.index, 'Event'].str.lower() == 'in'].min()),
        Last_Out=('Event timestamp', lambda x: x[punch.loc[x.index, 'Event'].str.lower() == 'out'].max())
    ).reset_index()
    attendance['Total Time'] = attendance['Last_Out'] - attendance['First_In']
    # Flag missing punches
    def missing_punch(row):
        if pd.isnull(row['First_In']) and pd.isnull(row['Last_Out']):
            return "Both Missing"
        elif pd.isnull(row['First_In']):
            return "Punch In Missing"
        elif pd.isnull(row['Last_Out']):
            return "Punch Out Missing"
        else:
            return ""
    attendance['Missing Punch'] = attendance.apply(missing_punch, axis=1)
    return attendance

if seating_file and punch_file:
    try:
        # Read files
        seating = pd.read_csv(seating_file)
        punch = pd.read_csv(punch_file)

        # Process punch data
        attendance = process_punch_data(punch)

        # Merge seating info (optional: you can display only punch data if you want)
        merged = pd.merge(
            attendance,
            seating,
            left_on='EMPLOYEE ID',
            right_on='EMPLOYEE ID (Security)',  # Adjust if needed
            how='left'
        )

        # Select columns for output (edit as needed)
        output = merged[['EMPLOYEE ID', 'NAME', 'DATE', 'First_In', 'Last_Out', 'Total Time', 'Missing Punch']]
        # Format time columns for Excel
        output['First_In'] = output['First_In'].dt.strftime("%I:%M:%S %p")
        output['Last_Out'] = output['Last_Out'].dt.strftime("%I:%M:%S %p")
        output['Total Time'] = output['Total Time'].apply(format_timedelta_to_hhmm)

        st.subheader("📝 Daily Attendance Detail")
        st.dataframe(output)

        csv = output.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Detail Sheet as CSV",
            data=csv,
            file_name=f"detail_sheet_{datetime.now().date()}.csv",
            mime="text/csv"
        )

    except Exception as e:
        st.error(f"Error processing files: {e}")

else:
    st.info("Please upload both CSV files to proceed.")

st.markdown("---")
st.markdown("*Created by Rajkumar Mali Intern*")
