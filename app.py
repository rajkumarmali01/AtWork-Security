import streamlit as st
import pandas as pd

st.title("🏢 Atwork Employee Attendance Analyzer")

st.write("""
Upload your **Atwork Seating** and **Punch in/out** CSV files to generate:
- A summary of attendance for each seated employee
- A list of visitors without seat allotment
""")

seating_file = st.file_uploader("Upload Atwork Seating CSV", type="csv")
punch_file = st.file_uploader("Upload Punch In/Out CSV", type="csv")

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

        # --- Step 2: Prepare Punch Data ---
        punch['EMPLOYEE ID'] = punch['Cardholder']
        punch['NAME'] = punch['First name'].astype(str).str.strip() + " " + punch['Last name'].astype(str).str.strip()
        punch['Event timestamp'] = pd.to_datetime(punch['Event timestamp'], errors='coerce')
        punch['DATE'] = punch['Event timestamp'].dt.date
        punch['TIME'] = punch['Event timestamp'].dt.time

        # Only IN/OUT events
        punch = punch[punch['Event'].str.lower().isin(['in', 'out'])]

        # --- Step 3: Calculate First In, Last Out, Days Visited, Total Hours ---
        grouped = punch.groupby(['EMPLOYEE ID', 'NAME', 'DATE'])

        first_in = grouped.apply(lambda x: x[x['Event'].str.lower() == 'in']['Event timestamp'].min())
        last_out = grouped.apply(lambda x: x[x['Event'].str.lower() == 'out']['Event timestamp'].max())

        attendance = pd.DataFrame({
            'EMPLOYEE ID': first_in.index.get_level_values(0),
            'NAME': first_in.index.get_level_values(1),
            'DATE': first_in.index.get_level_values(2),
            'First In': first_in.values,
            'Last Out': last_out.values
        })

        attendance['First In'] = pd.to_datetime(attendance['First In'])
        attendance['Last Out'] = pd.to_datetime(attendance['Last Out'])
        attendance['Total Time'] = attendance['Last Out'] - attendance['First In']

        # Days visited and total hours
        summary = attendance.groupby(['EMPLOYEE ID', 'NAME']).agg(
            Days_Visited=('DATE', 'nunique'),
            Total_Hours=('Total Time', lambda x: x.sum().total_seconds() / 3600)
        ).reset_index()

        summary['Total_Hours'] = summary['Total_Hours'].apply(lambda x: format_hours(x))

        # --- Step 4: Merge with Seating Data ---
        final = pd.merge(
            seating,
            summary,
            left_on='EMPLOYEE ID (Security)',
            right_on='EMPLOYEE ID',
            how='left'
        )

        final_output = final[['SR.NO', 'EMPLOYEE ID', 'EMPLOYEE NAME', 'EMPLOYEE ID (Security)', 'EMPLOYEE NAME (Security)', 'Days_Visited', 'Total_Hours']]

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
        no_seat = summary[~summary['EMPLOYEE ID'].isin(seating['EMPLOYEE ID (Security)'])]
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
