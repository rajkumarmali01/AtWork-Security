import streamlit as st
import pandas as pd

st.title("🏢 Atwork Employee Attendance Analyzer")

st.write("""
Upload your **Atwork Seating** and **Punch in/out** CSV files to generate:
- A summary of attendance for each seated employee
- A list of visitors without seat allotment
""")

seating_file = st.file_uploader("Upload Atwork Seating CSV", type="csv", key="seating")
punch_file = st.file_uploader("Upload Punch In/Out CSV", type="csv", key="punch")

def format_hours(td):
    if pd.isnull(td):
        return ""
    hours = int(td)
    minutes = int(round((td - hours) * 60))
    return f"{hours:02d}:{minutes:02d}"

def format_timedelta_to_hhmmss(td):
    if pd.isnull(td):
        return ""
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours}:{minutes:02d}:{seconds:02d}"

if seating_file and punch_file:
    try:
        # --- Step 1: Read files ---
        seating = pd.read_csv(seating_file, dtype=str)
        punch = pd.read_csv(punch_file, dtype=str)

        # --- Step 2: Clean and standardize column names ---
        seating.columns = [col.strip().upper() for col in seating.columns]
        punch.columns = [col.strip().upper() for col in punch.columns]

        # --- Step 3: Identify columns ---
        # Seating file columns
        seat_id_col = next((col for col in seating.columns if 'EMPLOYEE ID' in col and 'SECURITY' in col), None)
        seat_name_col = next((col for col in seating.columns if 'EMPLOYEE NAME' in col and 'SECURITY' in col), None)
        sr_no_col = next((col for col in seating.columns if 'SR' in col), None)

        # Punch file columns
        emp_id_col = next((col for col in punch.columns if col in ['EMPLOYEE ID', 'CARDHOLDER']), None)
        first_name_col = next((col for col in punch.columns if 'FIRST NAME' in col), None)
        last_name_col = next((col for col in punch.columns if 'LAST NAME' in col), None)
        event_col = next((col for col in punch.columns if 'EVENT' == col or 'EVENT' in col), None)
        timestamp_col = next((col for col in punch.columns if 'EVENT TIMESTAMP' in col), None)

        # --- Step 4: Clean Employee IDs for robust merging ---
        seating['EMPLOYEE_ID_CLEAN'] = seating[seat_id_col].astype(str).str.strip()
        punch['EMPLOYEE_ID_CLEAN'] = punch[emp_id_col].astype(str).str.strip()

        # --- Step 5: Create full name in punch file ---
        if first_name_col and last_name_col:
            punch['NAME'] = punch[first_name_col].astype(str).str.strip() + " " + punch[last_name_col].astype(str).str.strip()
        else:
            punch['NAME'] = punch['EMPLOYEE_ID_CLEAN']

        # --- Step 6: Parse timestamps and filter IN/OUT events ---
        punch[timestamp_col] = pd.to_datetime(punch[timestamp_col], errors='coerce')
        punch['DATE'] = punch[timestamp_col].dt.date
        punch = punch[punch[event_col].str.lower().isin(['in', 'out'])]

        # --- Step 7: Attendance calculation ---
        attendance = punch.groupby(['EMPLOYEE_ID_CLEAN', 'NAME', 'DATE']).agg(
            First_In=(timestamp_col, lambda x: x[punch.loc[x.index, event_col].str.lower() == 'in'].min()),
            Last_Out=(timestamp_col, lambda x: x[punch.loc[x.index, event_col].str.lower() == 'out'].max())
        ).reset_index()
        attendance['Total Time'] = attendance['Last_Out'] - attendance['First_In']

        # --- Step 8: Flag missing punches ---
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

       # --- Step 9: Days visited and total hours ---
# Calculate days visited and total hours from attendance
attendance['Total Time (hours)'] = attendance['Total Time'].dt.total_seconds() / 3600

summary = attendance.groupby('EMPLOYEE_ID_CLEAN').agg(
    Days_Visited=('DATE', 'nunique'),
    Total_Hours=('Total Time (hours)', 'sum')
).reset_index()

# Merge with seating to get names from seating sheet
final = pd.merge(
    seating,
    summary,
    left_on='EMPLOYEE_ID_CLEAN',
    right_on='EMPLOYEE_ID_CLEAN',
    how='left'
)

# Format for output
final['Total_Hours'] = final['Total_Hours'].apply(lambda x: format_hours(x) if pd.notnull(x) else "")
final['Days_Visited'] = final['Days_Visited'].fillna(0).astype(int)

# Use name from seating sheet
output_cols = [col for col in [sr_no_col, seat_id_col, seat_name_col, 'Days_Visited', 'Total_Hours'] if col in final.columns]
final_output = final[output_cols]

st.subheader("📝 Seated Employee Attendance Summary")
st.dataframe(final_output)

csv1 = final_output.to_csv(index=False).encode('utf-8')
st.download_button(
    label="Download Seated Employee Summary CSV",
    data=csv1,
    file_name="employee_attendance_summary.csv",
    mime="text/csv"
)
        
     # --- Step 10: Merge with seating data ---
        final = pd.merge(
            seating,
            summary,
            left_on='EMPLOYEE_ID_CLEAN',
            right_on='EMPLOYEE_ID_CLEAN',
            how='left'
        )

        # --- Step 11: Prepare outputs ---
        final_output = final[[col for col in [sr_no_col, seat_id_col, seat_name_col, 'EMPLOYEE_ID_CLEAN', 'NAME', 'Days_Visited', 'Total_Hours'] if col in final.columns or col in ['EMPLOYEE_ID_CLEAN', 'NAME', 'Days_Visited', 'Total_Hours']]]

        st.subheader("📝 Seated Employee Attendance Summary")
        st.dataframe(final_output)

        csv1 = final_output.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Seated Employee Summary CSV",
            data=csv1,
            file_name="employee_attendance_summary.csv",
            mime="text/csv"
        )

        # --- Step 12: Visitors without seat allotment ---
        no_seat = summary[~summary['EMPLOYEE_ID_CLEAN'].isin(seating['EMPLOYEE_ID_CLEAN'])]
        st.subheader("🚶‍♂️ Visitors Without Seat Allotment")
        st.dataframe(no_seat)

        csv2 = no_seat.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Visitors Without Seat CSV",
            data=csv2,
            file_name="visitors_without_seat.csv",
            mime="text/csv"
        )

        # --- Step 13: Detailed daily sheet (like your screenshot) ---
        attendance['First In'] = attendance['First_In'].dt.strftime("%I:%M:%S %p")
        attendance['Last Out'] = attendance['Last_Out'].dt.strftime("%I:%M:%S %p")
        attendance['Total Time'] = attendance['Total Time'].apply(format_timedelta_to_hhmmss)
        detail_output = attendance[['EMPLOYEE_ID_CLEAN', 'NAME', 'DATE', 'First In', 'Last Out', 'Total Time', 'Missing Punch']]
        st.subheader("📋 Detail Sheet (Per Employee Per Date)")
        st.dataframe(detail_output)
        csv3 = detail_output.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Detail Sheet as CSV",
            data=csv3,
            file_name="detail_sheet.csv",
            mime="text/csv"
        )

    except Exception as e:
        st.error(f"Error processing files: {e}")

else:
    st.info("Please upload both CSV files to proceed.")

st.markdown("---")
st.markdown("*Created by Rajkumar Mali Intern*")
