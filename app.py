import streamlit as st
from ot_tracker import track_ot

st.title("OT Timesheet Tracker")

uploaded = st.file_uploader("Upload CSV")

if uploaded:
    df = track_ot(uploaded)

    st.write("Preview:")
    st.dataframe(df)

    st.download_button("Download CSV", df.to_csv(index=False), "output.csv")