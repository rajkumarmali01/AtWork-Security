import streamlit as st
import pandas as pd
from datetime import datetime

def format_timedelta_to_hhmm(t):
    if pd.isnull(t):
        return ""
    total_minutes = int(t.total_seconds() // 60)
    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{hours:02d}:{minutes:02d}"

def process_data(df):
    # Combine date and time into a single datetime column
    df['datetime'] = pd.to_datetime(df['date'].astype(str) + ' ' + df['time'].astype(str), errors='coerce')
    # Clean up 'reader in and out' column robustly
    df['reader in and out'] = df['reader in and out'].apply(
        lambda x: str(x).strip().lower() if pd.notnull(x) else ""
    )
    # Mark entries as 'in' or 'out'
    def get_entry_type(x):
        if isinstance(x, str):
            if 'in' in x:
                return 'in'
            elif 'out' in x:
                return 'out'
        return None
    df['entry_type'] = df['reader in and out'].apply(get_entry_type)
    # Only keep rows with 'in' or 'out'
    df = df[df['entry_type'].isin(['in', 'out'])]

    # Group by employee id, name, date
    grouped = df.groupby(['employee id', 'employee name', 'date'])

    # Get earliest IN and latest OUT for each group
    first_in = grouped.apply(lambda x: x[x['entry_type'] == 'in']['datetime'].min()).reset_index(name='First In')
    last_out = grouped.apply(lambda x: x[x['entry_type'] == 'out']['datetime'].max()).reset_index(name='Last Out')

    # Merge first_in and last_out on employee id, name, date
    result = pd.merge(first_in, last_out, on=['employee id', 'employee name', 'date'], how='outer')

    # Calculate total time
    result['Total Time'] = result['Last Out'] - result['First In']

    # Flag missing punches
    def missing_punch(row):
        if pd.isnull(row['First In']) and pd.isnull(row['Last Out']):
            return "Both Missing"
        elif pd.isnull(row['First In']):
            return "Punch In Missing"
        elif pd.isnull(row['Last Out']):
            return "Punch Out Missing"
        else:
            return ""
    result['Missing Punch'] = result.apply(missing_punch, axis=1)

    # Reorder columns for clarity
    result = result[['employee id', 'employee name', 'date', 'First In', 'Last Out', 'Total Time', 'Missing Punch']]
    return result

st.title("🏢 Atwork Employee Daily Time Analysis")

uploaded_file = st.file_uploader("Choose a CSV file (punch data)", type="csv")

if uploaded_file:
    try:
        raw_df = pd.read_csv(uploaded_file)
        required_cols = {'employee id', 'employee name', 'date', 'time', 'reader in and out'}
        if not required_cols.issubset(set(raw_df.columns)):
            st.error(f"CSV must contain columns: {', '.join(required_cols)}")
        else:
            result_df = process_data(raw_df)

            # Show table with formatted times
            st.subheader("Daily Time Analysis (First In, Last Out, Total Time)")
            st.dataframe(result_df.style.format({
                'First In': lambda t: t.strftime("%I:%M:%S %p") if pd.notnull(t) else "",
                'Last Out': lambda t: t.strftime("%I:%M:%S %p") if pd.notnull(t) else "",
                'Total Time': format_timedelta_to_hhmm,
                'Missing Punch': lambda x: x if x else ""
            }))

            # Prepare for download
            result_df_export = result_df.copy()
            result_df_export['First In'] = result_df_export['First In'].dt.strftime("%I:%M:%S %p")
            result_df_export['Last Out'] = result_df_export['Last Out'].dt.strftime("%I:%M:%S %p")
            result_df_export['Total Time'] = result_df_export['Total Time'].apply(format_timedelta_to_hhmm)
            csv = result_df_export.to_csv(index=False)
            st.download_button(
                label="📥 Download Detail Sheet as CSV",
                data=csv,
                file_name=f"detail_sheet_{datetime.now().date()}.csv"
            )

    except Exception as e:
        st.error(f"Error processing file: {e}")
else:
    st.info("Awaiting CSV file upload.")

st.markdown("---")
st.markdown("*Sample CSV columns:* employee id, employee name, date, time, reader in and out")
