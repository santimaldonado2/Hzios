import streamlit as st
from transform import load_data

if st.session_state["authentication_status"]:
    antennas_dict, antennas_url = load_data("antennas")
    pathloss_antennas, pathloss_url = load_data("pathloss_antennas")
    enacom_cols, enacom_url = load_data("enacom_cols")

    col1, col2 = st.columns(2)

    with col1:
        sub_col1, sub_col2 = st.columns([10, 2])
        with sub_col1:
            st.write(f"### Pathloss Antennas")
        with sub_col2:
            st.markdown(
                f"""<p><a href={pathloss_url} class="btn btn-outline-primary btn-lg btn-block" type="button" aria-pressed="true">View File</a></p>""",
                unsafe_allow_html=True,
            )
        st.dataframe(pathloss_antennas)

        sub_col1, sub_col2 = st.columns([10, 2])
        with sub_col1:
            st.write(f"### Columns Mapping and Order")
        with sub_col2:
            st.markdown(
                f"""<p><a href={enacom_url} class="btn btn-outline-primary btn-lg btn-block" type="button" aria-pressed="true">View File</a></p>""",
                unsafe_allow_html=True,
            )
        st.dataframe(enacom_cols)

    with col2:
        sub_col1, sub_col2 = st.columns([10, 2])
        with sub_col1:
            st.write(f"### MZ Antennas")
        with sub_col2:
            st.markdown(
                f"""<p><a href={antennas_url} class="btn btn-outline-primary btn-lg btn-block" type="button" aria-pressed="true">View File</a></p>""",
                unsafe_allow_html=True,
            )
        st.dataframe(antennas_dict)
else:
    st.info("Go back to main and log in!")
