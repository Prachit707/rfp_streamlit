import streamlit as st
import pandas as pd

st.title("MERX Health IT Opportunities")

try:
    df = pd.read_csv("output.csv")
    st.success(f"Total Opportunities: {len(df)}")
    st.dataframe(df, use_container_width=True)

    st.download_button(
        label="Download CSV",
        data=df.to_csv(index=False),
        file_name="MERX_Output.csv",
        mime="text/csv"
    )

except:
    st.error("No data available yet. Run GitHub Action first.")
