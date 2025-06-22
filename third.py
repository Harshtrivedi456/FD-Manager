import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import io

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



# Load FD data
@st.cache_data

def load_data():
uploaded_file = st.file_uploader("📁 Upload FD Excel File", type=["xlsx"])

if uploaded_file is not None:
    df = pd.read_excel(uploaded_file, sheet_name=0)
else:
    st.warning("Please upload the FD Excel file to proceed.")
    st.stop()
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

# Save Data

def save_data(df):
    df.to_excel("fdr.xlsx", index=False)

# Load current FD data
df = load_data()

# Filter by Customer Name or "ALL"
name_input = st.text_input("Enter Customer Name or Initial (e.g., V or Vishalbhai or ALL):").strip().upper()

if name_input:
    if name_input == "ALL":
        grouped = df.groupby("Bank")
        for bank, group in grouped:
            st.subheader(f"Bank: {bank}")
            group['Maturity Status'] = group['MA_Date'].apply(
                lambda x: '⚠️ Maturing Soon' if x - pd.Timestamp(datetime.now()) < timedelta(days=30) else '')
            st.dataframe(group)
            st.write("**Total for", bank, ":**")
            st.write(group[['DA', 'MA', 'Interest']].sum())
    else:
        filtered_df = df[(df['Initial'] == name_input) | (df['Customer'].str.upper().str.contains(name_input))]
        if not filtered_df.empty:
            filtered_df['Maturity Status'] = filtered_df['MA_Date'].apply(
                lambda x: '⚠️ Maturing Soon' if x - pd.Timestamp(datetime.now()) < timedelta(days=30) else '')
            st.subheader(f"FD Records for: {name_input}")
            st.dataframe(filtered_df)
        else:
            st.warning("No records found for that name or initial.")

st.markdown("---")
st.header("Add or Renew FD Entry")
entry_type = st.radio("Select Entry Type", ["New FD", "Renew Existing FD"])

if entry_type == "New FD":
    with st.form("new_fd_form"):
        cust_name = st.text_input("Customer Name")
        initial = st.text_input("Initial (First Letter)")
        bank = st.text_input("Bank Name")
        da = st.number_input("Deposit Amount (DA)", min_value=0.0)
        ma = st.number_input("Maturity Amount (MA)", min_value=0.0)
        da_date = st.date_input("Deposit Date")
        ma_date = st.date_input("Maturity Date")
        interest = st.number_input("Interest Amount", min_value=0.0)
        fdr_no = st.text_input("FDR Number")
        submit = st.form_submit_button("Add FD")
        if submit:
            new_entry = pd.DataFrame([{
                'Customer': cust_name,
                'Initial': initial.upper(),
                'Bank': bank,
                'DA': da,
                'MA': ma,
                'DA_Date': pd.to_datetime(da_date),
                'Interest': interest,
                'FDR_NO': fdr_no,
                'MA_Date': pd.to_datetime(ma_date)
            }])
            df = pd.concat([df, new_entry], ignore_index=True)
            save_data(df)
            st.success("New FD added successfully!")

elif entry_type == "Renew Existing FD":
    with st.form("renew_fd_search_form"):
        old_fdr = st.text_input("Enter Existing FDR Number to Renew")
        submit_search = st.form_submit_button("Search FD")

    if submit_search:
        renewal_found = df[df['FDR_NO'].astype(str).str.strip().str.upper() == str(old_fdr).strip().upper()]
        if not renewal_found.empty:
            st.subheader("Old FD Record")
            st.dataframe(renewal_found)
            st.info("Old FD found. Please enter new details to renew.")
            with st.form("renew_details_form"):
                new_fdr = st.text_input("New FDR Number")
                da = st.number_input("New Deposit Amount (DA)", min_value=0.0)
                ma = st.number_input("New Maturity Amount (MA)", min_value=0.0)
                da_date = st.date_input("New Deposit Date")
                ma_date = st.date_input("New Maturity Date")
                interest = st.number_input("New Interest Amount", min_value=0.0)
                submit_renew = st.form_submit_button("Renew FD")
                if submit_renew:
                    idx = renewal_found.index[0]
                    df.loc[idx, 'DA'] = da
                    df.loc[idx, 'MA'] = ma
                    df.loc[idx, 'DA_Date'] = pd.to_datetime(da_date)
                    df.loc[idx, 'Interest'] = interest
                    df.loc[idx, 'MA_Date'] = pd.to_datetime(ma_date)
                    df.loc[idx, 'FDR_NO'] = new_fdr
                    save_data(df)
                    st.success("FD renewed and updated successfully!")
        else:
            st.warning("FDR Number not found. Please check and try again.")

# Download updated file
st.markdown("---")
st.subheader("Download Updated FD Database")

output = io.BytesIO()
with pd.ExcelWriter(output, engine='openpyxl') as writer:
    df.to_excel(writer, index=False)
output.seek(0)

st.download_button(
    label="📥 Download FD Data as Excel",
    data=output,
    file_name="updated_fdr.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
