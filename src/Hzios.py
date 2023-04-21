import uuid
import pandas as pd
import streamlit as st

from auth import auth
from transform import get_result_df, convert_df

st.set_page_config(layout="wide",
                   page_title="Hzios",
                   page_icon="statics/mz_logo.ico")

st.sidebar.image("statics/mz_logo.ico")
st.sidebar.title("Hzios")
st.sidebar.caption("Made by Santiago Maldonado.")

authenticator = auth()
if st.session_state["authentication_status"]:
    authenticator.logout('Logout', 'sidebar')

    st.write("# Hzios")
    st.write(f'Welcome *{st.session_state["name"]}*')

    col1, col2 = st.columns(2)
    with col1:
        st.write("## Enacom File")
        enacom_file = st.file_uploader("Enacom File")
        if enacom_file is not None:
            enacom_df = pd.read_excel(enacom_file)
            st.dataframe(enacom_df)

    with col2:
        st.write("## Pathloss File")
        sub_col1, sub_col2 = st.columns(2)
        with sub_col1:
            file_name = st.text_input("Result Filename", "result")

        if enacom_file:
            transaction_id = uuid.uuid4()
            messages = "Transaction ID: {}\n".format(transaction_id)
            (
                messages,
                result_df,
                new_antennas,
                generic_searches,
                new_diameters,
            ) = get_result_df(enacom_df, messages)
            st.text("")
            st.text("")
            st.text("")
            st.text("")
            st.text("")
            st.dataframe(result_df)
            csv = convert_df(result_df)
            with sub_col2:
                st.text("")
                st.text("")
                st.download_button(
                    label="Descargame todo wacho",
                    data=csv,
                    file_name=f"{file_name}.csv",
                    mime="text/csv",
                )

    if enacom_file:
        st.write(messages)

        col1, col2 = st.columns(2)
        with col1:
            st.write("### New Antennas")
            if new_antennas:
                st.write(
                    pd.DataFrame(
                        list(new_antennas),
                        columns=["Cb", "trademark", "model", "diameter", "gain"],
                    )
                )
            else:
                st.write("No new Antennas found")

        with col2:
            st.write("### Generic Searches")
            if generic_searches:
                st.write(
                    pd.DataFrame(
                        list(generic_searches), columns=["cb", "antena", "diameter"]
                    )
                )
            else:
                st.write("No generis searches made")

elif st.session_state["authentication_status"]:
    st.error('Username/password is incorrect')


