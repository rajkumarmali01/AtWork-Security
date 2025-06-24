import streamlit as st
import pandas as pd
from datetime import datetime

st.title("🏢 Atwork Employee Daily Time Detail Sheet")

st.write("""
Upload your **Punch In/Out CSV** file.
- The app will calculate first in/last out per employee per date, total time, and missing punches.
- Download the result as CSV for Excel.
""")

uploaded_file = st.file_uploader("Upload Punch In/Out CSV", type="csv")

def format_timedelta_to_hhmmss(td):
    if pd.isnull(td):
        return ""
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours}:{minutes:02d}:{seconds:02d}"

def process_punch_data(punch):
    # Ensure proper column names
    punch.columns = [col.strip() for col in punch.columns]
    # Create EMPLOYEE ID and Name columns if not present
    if 'Employee ID' not in punch.columns:
        punch['Employee ID'] = punch['Cardholder']
    if 'Name' not in punch.columns:
        punch['Name'] = punch['First name'].astype(str).str.strip() + " " + punch['Last name'].astype(str).str.strip()
    # Parse timestamps
    punch['Event timestamp'] = pd.to_datetime(punch['Event timestamp'], errors='coerce')
    punch['Date'] = punch['Event timestamp'].dt.date
    punch['Time'] = punch['Event timestamp'].dt.time
    # Only IN/OUT events
    punch = punch[punch['Event'].str.lower().isin(['in', 'out'])]
    # Group and get first in/last out
    attendance = punch.groupby(['Employee ID', 'Name', 'Date']).agg(
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

if uploaded_file:
    try:
        punch = pd.read_csv(uploaded_file)
        attendance = process_punch_data(punch)
        # Format for Excel output
        attendance['First In'] = attendance['First_In'].dt.strftime("%I:%M:%S %p")
        attendance['Last Out'] = attendance['Last_Out'].dt.strftime("%I:%M:%S %p")
        attendance['Total Time'] = attendance['Total Time'].apply(format_timedelta_to_hhmmss)
        output = attendance[['Employee ID', 'Name', 'Date', 'First In', 'Last Out', 'Total Time', 'Missing Punch']]
        st.subheader("📝 Detail Sheet")
        st.dataframe(output)
        csv = output.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Detail Sheet as CSV",
            data=csv,
            file_name=f"detail_sheet_{datetime.now().date()}.csv",
            mime="text/csv"
        )
    except Exception as e:
        st.error(f"Error processing file: {e}")
else:
    st.info("Please upload your Punch In/Out CSV file to proceed.")

st.markdown("---")
st.markdown("*Created by Rajkumar Mali Intern*")
