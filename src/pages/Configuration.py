import pandas as pd
import streamlit as st
from transform import load_data

antennas_dict, antennas_url = load_data("antennas")
pathloss_antennas, pathloss_url = load_data("pathloss_antennas")
enacom_cols, enacom_url = load_data("enacom_cols")


col1, col2 = st.columns(2)

with col1:
    st.write(f"## [Pathloss Antennas]({pathloss_url})")
    st.dataframe(pathloss_antennas)

with col2:
    st.write(f"## [MZ Antennas]({antennas_url})")
    st.dataframe(antennas_dict)

st.write(f"# [Columns Mapping and Order]({enacom_url})")
st.dataframe(enacom_cols)
