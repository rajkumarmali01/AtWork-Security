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

if seating_file and punch_file:
    try:
        # --- Step 1: Read files ---
        seating = pd.read_csv(seating_file)
        punch = pd.read_csv(punch_file)

        # --- Step 1.5: Print columns for debugging ---
        st.write("Seating file columns:", list(seating.columns))
        st.write("Punch file columns:", list(punch.columns))

        # --- Step 2: Prepare Punch Data ---
        # Try to use the correct column names regardless of spaces/case
        punch.columns = [col.strip().upper() for col in punch.columns]
        seating.columns = [col.strip().upper() for col in seating.columns]

        # Find correct columns for IDs and names
        # For punch data
        emp_id_col = None
        for col in ['EMPLOYEE ID', 'CARDHOLDER']:
            if col in punch.columns:
                emp_id_col = col
                break
        if not emp_id_col:
            st.error("Could not find Employee ID column in punch file!")
            st.stop()
        first_name_col = next((col for col in punch.columns if 'FIRST NAME' in col), None)
        last_name_col = next((col for col in punch.columns if 'LAST NAME' in col), None)
        name_col = next((col for col in punch.columns if 'NAME' in col and 'FIRST' not in col and 'LAST' not in col), None)

        if not name_col and first_name_col and last_name_col:
            punch['NAME'] = punch[first_name_col].astype(str).str.strip() + " " + punch[last_name_col].astype(str).str.strip()
        elif name_col:
            punch['NAME'] = punch[name_col].astype(str).str.strip()
        else:
            st.error("Could not find employee name columns in punch file!")
            st.stop()

        # Parse timestamps
        timestamp_col = next((col for col in punch.columns if 'EVENT TIMESTAMP' in col), None)
        if not timestamp_col:
            st.error("Could not find 'Event timestamp' column in punch file!")
            st.stop()
        punch[timestamp_col] = pd.to_datetime(punch[timestamp_col], errors='coerce')
        punch['DATE'] = punch[timestamp_col].dt.date

        # Only IN/OUT events
        event_col = next((col for col in punch.columns if 'EVENT' == col or 'EVENT' in col), None)
        punch = punch[punch[event_col].str.lower().isin(['in', 'out'])]

        # --- Step 3: Calculate First In, Last Out, Days Visited, Total Hours ---
        attendance = punch.groupby([emp_id_col, 'NAME', 'DATE']).agg(
            First_In=(timestamp_col, lambda x: x[punch.loc[x.index, event_col].str.lower() == 'in'].min()),
            Last_Out=(timestamp_col, lambda x: x[punch.loc[x.index, event_col].str.lower() == 'out'].max())
        ).reset_index()
        attendance['Total Time'] = attendance['Last_Out'] - attendance['First_In']

        # Days visited and total hours
        summary = attendance.groupby([emp_id_col, 'NAME']).agg(
            Days_Visited=('DATE', 'nunique'),
            Total_Hours=('Total Time', lambda x: x.sum().total_seconds() / 3600 if pd.notnull(x).any() else 0)
        ).reset_index()
        summary['Total_Hours'] = summary['Total_Hours'].apply(lambda x: format_hours(x))

        # --- Step 4: Merge with Seating Data ---
        # Try to find the correct column in seating for merge
        seat_id_col = next((col for col in seating.columns if 'EMPLOYEE ID' in col), None)
        seat_name_col = next((col for col in seating.columns if 'EMPLOYEE NAME' in col), None)
        sec_id_col = next((col for col in seating.columns if 'SECURITY' in col and 'ID' in col), None)
        sec_name_col = next((col for col in seating.columns if 'SECURITY' in col and 'NAME' in col), None)
        sr_no_col = next((col for col in seating.columns if 'SR.NO' in col or 'SR NO' in col or 'SR' in col), None)

        final = pd.merge(
            seating,
            summary,
            left_on=sec_id_col if sec_id_col else seat_id_col,
            right_on=emp_id_col,
            how='left'
        )

        # Select columns for output
        final_output = final[[col for col in [sr_no_col, seat_id_col, seat_name_col, sec_id_col, sec_name_col, 'Days_Visited', 'Total_Hours'] if col in final.columns]]

        st.subheader("📝 Seated Employee Attendance Summary")
        st.dataframe(final_output)

        csv1 = final_output.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Seated Employee Summary CSV",
            data=csv1,
            file_name="employee_attendance_summary.csv",
            mime="text/csv"
        )

        # --- Step 5: Employees Visiting Without Seat Allotment ---
        no_seat = summary[~summary[emp_id_col].isin(seating[sec_id_col if sec_id_col else seat_id_col])]
        st.subheader("🚶‍♂️ Visitors Without Seat Allotment")
        st.dataframe(no_seat)

        csv2 = no_seat.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Visitors Without Seat CSV",
            data=csv2,
            file_name="visitors_without_seat.csv",
            mime="text/csv"
        )

    except Exception as e:
        st.error(f"Error processing files: {e}")

else:
    st.info("Please upload both CSV files to proceed.")

st.markdown("---")
st.markdown("*Created by Rajkumar Mali Intern*")
