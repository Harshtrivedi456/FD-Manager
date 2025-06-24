import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import io
import plotly.express as px

# 🔐 Password Protection
st.title("FD Manager")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.attempted = False

if not st.session_state.authenticated:
    with st.form("auth_form"):
        password = st.text_input("Enter Password to Access App", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            st.session_state.attempted = True
            if password == "mysecurepass":
                st.session_state.authenticated = True

    if st.session_state.attempted and not st.session_state.authenticated:
        st.warning("Incorrect password. Please try again.")

    st.stop()

# ⬇️ Upload file at the top level
uploaded_file = st.file_uploader("📁 Upload FD Excel File", type=["xlsx"])

# ⬇️ Only proceed if file is uploaded
if uploaded_file is not None:
    def load_data(file):
        df = pd.read_excel(file, sheet_name=0)
        df = df.rename(columns={
            'Bank Name': 'Bank',
            'fisrt Name': 'Initial',
            'Deposit Amt': 'DA',
            'Maturity Amt': 'MA',
            'Deposit Date': 'DA_Date',
            'Interest': 'Interest',
            'Customer Name': 'Customer',
            'FDR NO': 'FDR_NO'
        })
        df = df[['Customer', 'Initial', 'Bank', 'DA', 'MA', 'DA_Date', 'Interest', 'FDR_NO']]
        df['DA'] = pd.to_numeric(df['DA'], errors='coerce')
        df['MA'] = pd.to_numeric(df['MA'], errors='coerce')
        df['Interest'] = pd.to_numeric(df['Interest'], errors='coerce')
        df['DA_Date'] = pd.to_datetime(df['DA_Date'], errors='coerce')
        df = df.dropna(subset=['Customer', 'Initial', 'Bank', 'DA', 'MA', 'DA_Date', 'Interest'])
        if 'MA_Date' not in df.columns:
            df['MA_Date'] = df['DA_Date'] + pd.DateOffset(months=60)
        return df

    df = load_data(uploaded_file)
else:
    st.warning("Please upload the FD Excel file to proceed.")
    st.stop()

# Save Data
def save_data(df):
    df.to_excel("fdr.xlsx", index=False)

# Filter by Customer Name or "ALL"
name_input = st.text_input("Enter Customer Name or Initial (e.g., V or Vishalbhai or ALL):").strip().upper()

if name_input:
    if name_input == "ALL":
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

        final_df = pd.concat(combined, ignore_index=True)
        st.dataframe(final_df)

        grand_total = final_df[['DA', 'MA', 'Interest']].sum(numeric_only=True)
        st.subheader("Grand Total")
        st.write(grand_total)
    else:
        filtered_df = df[df['Initial'].str.upper() == name_input]
        if not filtered_df.empty:
            filtered_df['Maturity Status'] = filtered_df['MA_Date'].apply(
                lambda x: '⚠️ Maturing Soon' if x - pd.Timestamp(datetime.now()) < timedelta(days=30) else '')
            st.subheader(f"FD Records for: {name_input}")
            st.dataframe(filtered_df)
        else:
            st.warning("No records found for that name or initial.")

# 📊 Optional Comparative Analysis
st.markdown("---")
if st.checkbox("📈 Show Comparative Analysis"):
    st.subheader("Comparative Analysis")

    st.markdown("**1. Total Interest Earned by Each Customer**")
    pie1 = px.pie(df, names='Customer', values='Interest', title='Interest by Customer')
    st.plotly_chart(pie1)

    st.markdown("**2. Total Deposit Amount (DA) by Bank**")
    pie2 = px.pie(df, names='Bank', values='DA', title='Deposit Amount by Bank')
    st.plotly_chart(pie2)

    st.markdown("**3. Total Maturity Amount (MA) by Customer**")
    pie3 = px.pie(df, names='Customer', values='MA', title='Maturity Amount by Customer')
    st.plotly_chart(pie3)

# 🔄 Pivot Table Section
st.markdown("---")
if st.checkbox("🕲 Show Pivot Table Analysis"):
    st.subheader("Interactive Pivot Table")
    available_cols = df.columns.tolist()

    rows = st.multiselect("Select Row Groups", available_cols, default=['Bank', 'Customer'])
    cols = st.multiselect("Select Column Groups", available_cols)
    values = st.multiselect("Select Values", ['DA', 'MA', 'Interest'], default=['DA'])
    aggfunc = st.selectbox("Aggregation Function", ['sum', 'mean', 'count'])

    if rows and values:
        pivot = pd.pivot_table(
            df,
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

# Download updated file
st.markdown("---")
st.subheader("Download Updated FD Database")

output = io.BytesIO()
with pd.ExcelWriter(output, engine='openpyxl') as writer:
    df.to_excel(writer, index=False)
output.seek(0)

st.download_button(
    label="📅 Download FD Data as Excel",
    data=output,
    file_name="updated_fdr.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
