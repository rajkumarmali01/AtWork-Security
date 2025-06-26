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

        seating.columns = [col.strip().upper() for col in seating.columns]
        punch.columns = [col.strip().upper() for col in punch.columns]

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

        if first_name_col and last_name_col:
            punch['NAME'] = punch[first_name_col].astype(str).str.strip() + " " + punch[last_name_col].astype(str).str.strip()
        else:
            punch['NAME'] = punch['EMPLOYEE_ID_CLEAN']

        punch[timestamp_col] = pd.to_datetime(punch[timestamp_col], errors='coerce')

        # ✅ Use a unique safe column name: INOUT_DATE_TEMP
        if 'INOUT_DATE_TEMP' in punch.columns:
            del punch['INOUT_DATE_TEMP']

        punch['INOUT_DATE_TEMP'] = punch[timestamp_col].dt.date

        punch = punch[punch[event_col].str.lower().isin(['in', 'out'])]

        def get_first_in(x):
            ins = x.loc[x[event_col].str.lower() == 'in', timestamp_col]
            return ins.min() if not ins.empty else pd.NaT

        def get_last_out(x):
            outs = x.loc[x[event_col].str.lower() == 'out', timestamp_col]
            return outs.max() if not outs.empty else pd.NaT

        attendance = (
            punch.groupby(['EMPLOYEE_ID_CLEAN', 'INOUT_DATE_TEMP'])
            .apply(lambda x: pd.Series({
                'First_In': get_first_in(x),
                'Last_Out': get_last_out(x)
            }))
            .reset_index()
        )

        attendance['Total Time'] = attendance['Last_Out'] - attendance['First_In']

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

        attendance['Total Time (hours)'] = attendance['Total Time'].dt.total_seconds() / 3600

        summary = attendance.groupby('EMPLOYEE_ID_CLEAN').agg(
            Days_Visited=('INOUT_DATE_TEMP', 'nunique'),
            Total_Hours=('Total Time (hours)', 'sum')
        ).reset_index()

        final = pd.merge(
            seating,
            summary,
            on='EMPLOYEE_ID_CLEAN',
            how='left'
        )

        final['Total_Hours'] = final['Total_Hours'].apply(lambda x: format_hours(x) if pd.notnull(x) else "")
        final['Days_Visited'] = final['Days_Visited'].fillna(0).astype(int)

        output_cols = [col for col in [sr_no_col, seat_id_col, seat_name_col, 'Days_Visited', 'Total_Hours'] if col in final.columns]
        final_output = final[output_cols]

        st.subheader("📝 Seated Employee Attendance Summary")
        st.dataframe(final_output)

        st.download_button(
            label="Download Seated Employee Summary CSV",
            data=final_output.to_csv(index=False).encode('utf-8'),
            file_name="employee_attendance_summary.csv",
            mime="text/csv"
        )

        no_seat = summary[~summary['EMPLOYEE_ID_CLEAN'].isin(seating['EMPLOYEE_ID_CLEAN'])]
        st.subheader("🚶‍♂️ Visitors / Employee Without Seat Allotment")
        st.dataframe(no_seat)

        st.download_button(
            label="Download Visitors Without Seat CSV",
            data=no_seat.to_csv(index=False).encode('utf-8'),
            file_name="visitors_without_seat.csv",
            mime="text/csv"
        )

        attendance['First In'] = attendance['First_In'].dt.strftime("%I:%M:%S %p")
        attendance['Last Out'] = attendance['Last_Out'].dt.strftime("%I:%M:%S %p")
        attendance['Total Time'] = attendance['Total Time'].apply(format_timedelta_to_hhmmss)
        detail_output = attendance[['EMPLOYEE_ID_CLEAN', 'INOUT_DATE_TEMP', 'First In', 'Last Out', 'Total Time', 'Missing Punch']]

        st.subheader("📋 Detail Sheet (Per Employee Per Date)")
        st.dataframe(detail_output)

        st.download_button(
            label="Download Detail Sheet as CSV",
            data=detail_output.to_csv(index=False).encode('utf-8'),
            file_name="detail_sheet.csv",
            mime="text/csv"
        )

    except Exception as e:
        st.error(f"Error processing files: {e}")

else:
    st.info("Please upload both CSV files to proceed.")

st.markdown("---")
st.markdown("*Created by Rajkumar Mali Intern*")