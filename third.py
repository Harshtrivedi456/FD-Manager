import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import io
import plotly.express as px

st.title("FD Manager")

# ⬇️ Upload file
uploaded_file = st.file_uploader("📁 Upload FD Excel File", type=["xlsx"])

def load_data(file):
    df = pd.read_excel(file, sheet_name=0)

    # Rename expected columns for consistency
    rename_map = {
        'Bank Name': 'Bank',
        'fisrt Name': 'Initial',
        'first Name': 'Initial',
        'Deposit Amt': 'DA',
        'Deposit Amount': 'DA',
        'Maturity Amt': 'MA',
        'Maturity Amount': 'MA',
        'Deposit Date': 'DA_Date',
        'Interest Rate': 'Interest',
        'Customer Name': 'Customer',
        'FDR NO': 'FDR_NO',
        'FDR Number': 'FDR_NO'
    }

    df.rename(columns={old: new for old, new in rename_map.items() if old in df.columns}, inplace=True)

    # Ensure all required columns exist
    required_cols = ['Customer', 'Initial', 'Bank', 'DA', 'MA', 'DA_Date', 'Interest', 'FDR_NO']
    for col in required_cols:
        if col not in df.columns:
            df[col] = None  # If missing, create with None

    # Convert only required columns
    df['DA'] = pd.to_numeric(df['DA'], errors='coerce')
    df['MA'] = pd.to_numeric(df['MA'], errors='coerce')
    df['Interest'] = pd.to_numeric(df['Interest'], errors='coerce')
    df['DA_Date'] = pd.to_datetime(df['DA_Date'], errors='coerce')

    # Drop only rows that are missing the essential columns (others retained)
    df = df.dropna(subset=['Customer', 'Initial', 'Bank', 'DA', 'MA', 'DA_Date', 'Interest'])

    # Add Maturity Date if not already there
    if 'MA_Date' not in df.columns:
        df['MA_Date'] = df['DA_Date'] + pd.DateOffset(months=60)

    return df

if uploaded_file is not None:
    df = load_data(uploaded_file)
else:
    st.warning("Please upload the FD Excel file to proceed.")
    st.stop()

# Filter input
name_input = st.text_input("Enter Customer Name or Initial (e.g., V or Vishalbhai or ALL):").strip().upper()

# ----------------------------
# 🔥 MAIN FILTER LOGIC
# ----------------------------
df_to_use = df  # default to whole data

if name_input:
    if name_input == "ALL":
        df_to_use = df
        df_sorted = df.sort_values(by=["Bank", "Customer"])
        combined = []
        for bank, group in df_sorted.groupby("Bank"):
            user_totals = group.groupby("Customer")[['DA', 'MA', 'Interest']].sum().reset_index()
            user_totals.insert(0, 'Bank', bank)
            combined.append(user_totals)
            bank_total = pd.DataFrame([{
                'Bank': bank,
                'Customer': f"{bank} Total",
                'DA': user_totals['DA'].sum(),
                'MA': user_totals['MA'].sum(),
                'Interest': user_totals['Interest'].sum()
            }])
            combined.append(bank_total)

        if combined:
            final_df = pd.concat(combined, ignore_index=True)
            st.dataframe(final_df)
            grand_total = final_df[['DA', 'MA', 'Interest']].sum(numeric_only=True)
            st.subheader("Grand Total")
            st.write(grand_total)
    else:
        df_filtered = df[df['Initial'].str.upper() == name_input]
        if not df_filtered.empty:
            df_filtered['Maturity Status'] = df_filtered['MA_Date'].apply(
                lambda x: '⚠️ Maturing Soon' if x - pd.Timestamp(datetime.now()) < timedelta(days=30) else ''
            )
            st.subheader(f"FD Records for: {name_input}")
            st.dataframe(df_filtered)
            df_to_use = df_filtered
        else:
            st.warning("No records found for that name or initial.")
            df_to_use = pd.DataFrame()  # empty to avoid pivot or charts breaking

# ----------------------------
# 📊 Comparative Analysis
# ----------------------------
st.markdown("---")
if st.checkbox("📈 Show Comparative Analysis"):
    if not df_to_use.empty:
        st.subheader("Comparative Analysis")

        st.markdown("**1. Total Interest Earned by Each Customer**")
        pie1 = px.pie(df_to_use, names='Customer', values='Interest', title='Interest by Customer')
        st.plotly_chart(pie1)

        st.markdown("**2. Total Deposit Amount (DA) by Bank**")
        pie2 = px.pie(df_to_use, names='Bank', values='DA', title='Deposit Amount by Bank')
        st.plotly_chart(pie2)

        st.markdown("**3. Total Maturity Amount (MA) by Customer**")
        pie3 = px.pie(df_to_use, names='Customer', values='MA', title='Maturity Amount by Customer')
        st.plotly_chart(pie3)
    else:
        st.warning("No data to display in comparative analysis for the selected filter.")

# ----------------------------
# 🔄 Pivot Table Section
# ----------------------------
st.markdown("---")
if st.checkbox("🕲 Show Pivot Table Analysis"):
    if not df_to_use.empty:
        st.subheader("Interactive Pivot Table")
        available_cols = df_to_use.columns.tolist()

        rows = st.multiselect("Select Row Groups", available_cols, default=['Bank', 'Customer'])
        cols = st.multiselect("Select Column Groups", available_cols)
        values = st.multiselect("Select Values", ['DA', 'MA', 'Interest'], default=['DA'])
        aggfunc = st.selectbox("Aggregation Function", ['sum', 'mean', 'count'])

        if rows and values:
            pivot = pd.pivot_table(
                df_to_use,
                index=rows,
                columns=cols if cols else None,
                values=values,
                aggfunc=aggfunc,
                fill_value=0,
                margins=True,
                margins_name="Grand Total"
            )

            if rows == ['Bank', 'Customer'] and aggfunc == 'sum':
                pivot = pivot.reset_index()
                subtotals = []
                for bank, group in pivot.groupby('Bank'):
                    subtotals.append(group)
                    subtotal_row = pd.DataFrame([{
                        'Bank': bank,
                        'Customer': f"{bank} Total",
                        **{col: group[col].sum() for col in group.columns if col not in ['Bank', 'Customer']}
                    }])
                    subtotals.append(subtotal_row)
                pivot = pd.concat(subtotals, ignore_index=True)

            st.dataframe(pivot)
    else:
        st.warning("No data to create pivot table for the selected filter.")

# ----------------------------
# ⬇️ Download Final Output
# ----------------------------
st.markdown("---")
st.subheader("📥 Download Updated FD Database")

output = io.BytesIO()
with pd.ExcelWriter(output, engine='openpyxl') as writer:
    df.to_excel(writer, index=False)  # Includes all columns
output.seek(0)

st.download_button(
    label="📅 Download FD Data as Excel",
    data=output,
    file_name="updated_fdr.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
