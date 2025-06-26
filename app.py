import streamlit as st
import pandas as pd

st.title("🏢 Atwork Employee Attendance Analyzer")

st.write("""
Upload your **Atwork Seating** and **Punch in/out** CSV files to generate:
- A summary of attendance for each seated employee
- A list of visitors without seat allotment
- A daily detail sheet
""")

seating_file = st.file_uploader("Upload Atwork Seating CSV", type="csv", key="seating")
punch_file = st.file_uploader("Upload Punch In/Out CSV", type="csv", key="punch")

def format_hours(hours):
    if pd.isnull(hours) or hours == 0:
        return "00:00"
    h = int(hours)
    m = int(round((hours - h) * 60))
    return f"{h:02d}:{m:02d}"

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
        seating = pd.read_csv(seating_file, dtype=str)
        punch = pd.read_csv(punch_file, dtype=str)

        # Normalize column names
        seating.columns = [col.strip().upper() for col in seating.columns]
        punch.columns = [col.strip().upper() for col in punch.columns]

        # 🔍 Auto-detect columns
        seat_id_col = next((col for col in seating.columns if 'EMPLOYEE ID' in col and 'SECURITY' in col), None)
        seat_name_col = next((col for col in seating.columns if 'EMPLOYEE NAME' in col and 'SECURITY' in col), None)
        sr_no_col = next((col for col in seating.columns if 'SR' in col), None)

        emp_id_col = next((col for col in punch.columns if col in ['EMPLOYEE ID', 'CARDHOLDER']), None)
        first_name_col = next((col for col in punch.columns if 'FIRST NAME' in col), None)
        last_name_col = next((col for col in punch.columns if 'LAST NAME' in col), None)
        event_col = next((col for col in punch.columns if 'EVENT' == col or 'EVENT' in col), None)
        timestamp_col = next((col for col in punch.columns if 'EVENT TIMESTAMP' in col), None)

        seating['EMPLOYEE_ID_CLEAN'] = seating[seat_id_col].astype(str).str.strip()
        punch['EMPLOYEE_ID_CLEAN'] = punch[emp_id_col].astype(str).str.strip()

        # Combine names
        punch['NAME'] = punch[first_name_col].astype(str).str.strip() + " " + punch[last_name_col].astype(str).str.strip()

        punch[timestamp_col] = pd.to_datetime(punch[timestamp_col], errors='coerce')

        # ✅ Safe unique column name for date
        temp_date_col = 'INOUT_TEMP_DATE_V1_FINAL'
        if temp_date_col in punch.columns:
            punch.drop(columns=[temp_date_col], inplace=True)
        punch[temp_date_col] = punch[timestamp_col].dt.date

        punch = punch[punch[event_col].str.lower().isin(['in', 'out'])]

        def get_first_in(x):
            return x.loc[x[event_col].str.lower() == 'in', timestamp_col].min()

        def get_last_out(x):
            return x.loc[x[event_col].str.lower() == 'out', timestamp_col].max()

        attendance = punch.groupby(['EMPLOYEE_ID_CLEAN', temp_date_col]).apply(
            lambda x: pd.Series({
                'First_In': get_first_in(x),
                'Last_Out': get_last_out(x)
            })
        ).reset_index()

        attendance['Total Time'] = attendance['Last_Out'] - attendance['First_In']
        attendance['Missing Punch'] = attendance.apply(
            lambda row: "Both Missing" if pd.isnull(row['First_In']) and pd.isnull(row['Last_Out'])
            else "Punch In Missing" if pd.isnull(row['First_In'])
            else "Punch Out Missing" if pd.isnull(row['Last_Out'])
            else "", axis=1
        )

        attendance['Total Time (hours)'] = attendance['Total Time'].dt.total_seconds() / 3600

        summary = attendance.groupby('EMPLOYEE_ID_CLEAN').agg(
            Days_Visited=(temp_date_col, 'nunique'),
            Total_Hours=('Total Time (hours)', 'sum')
        ).reset_index()

        final = pd.merge(seating, summary, on='EMPLOYEE_ID_CLEAN', how='left')
        final['Total_Hours'] = final['Total_Hours'].apply(lambda x: format_hours(x) if pd.notnull(x) else "")
        final['Days_Visited'] = final['Days_Visited'].fillna(0).astype(int)

        output_cols = [col for col in [sr_no_col, seat_id_col, seat_name_col, 'Days_Visited', 'Total_Hours'] if col in final.columns]
        final_output = final[output_cols]

        st.subheader("📝 Seated Employee Attendance Summary")
        st.dataframe(final_output)
        st.download_button("Download Summary CSV", final_output.to_csv(index=False).encode(), "employee_summary.csv", "text/csv")

        no_seat = summary[~summary['EMPLOYEE_ID_CLEAN'].isin(seating['EMPLOYEE_ID_CLEAN'])]
        st.subheader("🚶‍♂️ Visitors Without Seat")
        st.dataframe(no_seat)
        st.download_button("Download Visitors CSV", no_seat.to_csv(index=False).encode(), "visitors.csv", "text/csv")

        attendance['First In'] = attendance['First_In'].dt.strftime("%I:%M:%S %p")
        attendance['Last Out'] = attendance['Last_Out'].dt.strftime("%I:%M:%S %p")
        attendance['Total Time'] = attendance['Total Time'].apply(format_timedelta_to_hhmmss)
        detail_output = attendance[['EMPLOYEE_ID_CLEAN', temp_date_col, 'First In', 'Last Out', 'Total Time', 'Missing Punch']]

        st.subheader("📋 Detail Sheet")
        st.dataframe(detail_output)
        st.download_button("Download Detail CSV", detail_output.to_csv(index=False).encode(), "detail_sheet.csv", "text/csv")

    except Exception as e:
        st.error(f"❌ Error processing files: {e}")

else:
    st.info("Please upload both CSV files to proceed.")

st.markdown("---")
st.markdown("*Created by Rajkumar Mali Intern*")