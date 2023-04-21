import logging
import re
import pandas as pd
import streamlit as st

SHORT_DIAMETER_PATTERN = r"P \d[.,]?[\d+]?M"
LONG_DIAMETER_PATTERN = r"\d[,.]?\d? metros"
ANDREW = "ANDREW CORPORATION"

SITE_NAME = "SITE_NAME"
CALL_SIGN = "CALL_SIGN"
STATION_CODE = "STATION_CODE"
OWNER_CODE = "OWNER_CODE"
OPERATOR_CODE = "OPERATOR_CODE"
LATITUDE = "LATITUDE"
LONGITUDE = "LONGITUDE"
ANTENNA_MODEL = "ANTENNA_MODEL"
ANTENNA_CODE = "ANTENNA_CODE"
ANTENNA_DIAMETER = "ANTENNA_DIAMETER"
ANTENNA_HEIGHT = "ANTENNA_HEIGHT"
ANTENNA_GAIN = "ANTENNA_GAIN"
TX_FREQ = "TX_FREQ"
POL = "POL"
RADIO_CODE = "RADIO_CODE"
RADIO_MODEL = "RADIO_MODEL"
EM_DESIG = "EM_DESIG"
TX_POWER = "TX_POWER"
EMISSION_CODE = "EMISSION_CODE"
LINK_CODE = "LINK_CODE"

new_antennas = False
new_diameters = False

# Loggers
transaction_id = None
logger = logging.getLogger()
transform_logger = logging.getLogger("transformLogger")
generic_search_logger = logging.getLogger("genericSearchLogger")




@st.cache_data(ttl=120)
def load_data(name, add_hyphen=False):
    url = st.secrets[name]
    csv_url = url.replace("/edit#gid=", "/export?format=csv&gid=")
    df = pd.read_csv(csv_url)
    if add_hyphen:
        df.Cb = "-" + df.Cb
    return df, url


@st.cache_data
def convert_df(df):
    return df.to_csv(index=False, header=False).encode("utf-8")


def get_logging_message(message):
    return "[{}]:{}".format(transaction_id, message)


def get_pathloss_antenna(cb, diameter):
    pathloss_antennas, _ = load_data("pathloss_antennas", add_hyphen=True)

    transform_logger.info(
        get_logging_message(
            "start get_pathloss_antenna cb=[{}], diameter=[{}]".format(cb, diameter)
        )
    )
    antennas = pathloss_antennas.loc[
        pathloss_antennas.Cb.str.contains("-{}".format(cb))
        & (pathloss_antennas.Diameter <= diameter + 0.04)
        & (pathloss_antennas.Diameter >= diameter - 0.04),
        ["Diameter", "Gain", "Model", "Code"],
    ].values
    transform_logger.info(
        get_logging_message("end get_pathloss_antenna antennas=[{}]".format(antennas))
    )
    return antennas


def get_generic_antenna(cb, mma, diameter):
    pathloss_antennas, _ = load_data("pathloss_antennas", add_hyphen=True)

    generic_search_logger.info(
        get_logging_message(
            "start get_generic_antenna cb=[{}], mma=[{}], diameter=[{}]".format(
                cb, mma, diameter
            )
        )
    )

    generic_search = (cb, mma, diameter)

    generic_antennas = pathloss_antennas.loc[
        ~pathloss_antennas.Generic.isna()
        & pathloss_antennas.Cb.str.contains("-{}".format(cb)),
        ["Diameter", "Gain", "Model", "Code"],
    ].values[0]

    generic_search_logger.info(
        get_logging_message(
            "end get_generic_antenna generic_antennas=[{}]".format(generic_antennas)
        )
    )

    return generic_antennas, generic_search


def mma_transform(mma, mma2, cb, antennas_dict):
    transform_logger.info(
        get_logging_message(
            "start mma_transform mma=[{}], mma2=[{}], cb=[{}]".format(mma, mma2, cb)
        )
    )

    diameter = ""
    cb = int(cb)
    search_local = True
    new_antenna = None
    generic_search = None
    new_diameters = False

    if mma:
        if mma2 and re.search(
            SHORT_DIAMETER_PATTERN + "|" + LONG_DIAMETER_PATTERN, mma2
        ):
            mma = mma.replace("ANDREW", "").replace("CORPORATION -", "").strip()
            diameter = get_diameter(mma2)
            info = get_pathloss_antenna(cb, diameter)
            search_local = len(info) == 0
        elif mma2:
            mma = mma2.replace(" ", "")

        if search_local:
            transform_logger.info(
                get_logging_message("start local search mma=[{}]".format(mma))
            )
            local_info = antennas_dict.loc[
                antennas_dict.model.str.contains(mma), ["diameter", "gain", "model"]
            ].values

            if len(local_info) == 0:
                transform_logger.info(
                    get_logging_message(
                        "end local search - Antenna not found mma=[{}]".format(mma)
                    )
                )
                new_antenna = ("-{}".format(cb), "", mma, diameter, "")
                info = [(diameter, "", mma, "")]
            else:
                diameter = local_info[0][0]
                transform_logger.info(
                    get_logging_message(
                        "end local search antennas=[{}]".format(local_info)
                    )
                )
                info = []
                if diameter:
                    info = get_pathloss_antenna(cb, diameter)

                if len(info) == 0:
                    info = get_generic_antenna(cb, mma, diameter)

    elif mma2 and re.match(SHORT_DIAMETER_PATTERN + "|" + LONG_DIAMETER_PATTERN, mma2):
        info = get_pathloss_antenna(cb, get_diameter(mma2))

        if len(info) == 0:
            info, generic_search = get_generic_antenna(cb, mma2, get_diameter(mma2))
            new_diameters = True
    else:
        info, generic_search = get_generic_antenna(cb, "", "")

    return_tuple = tuple(info[0])
    transform_logger.info(
        get_logging_message(
            "end mma_transform diameter=[{}], gain=[{}], model=[{}], code=[{}]".format(
                *return_tuple
            )
        )
    )
    return return_tuple, new_antenna, generic_search, new_diameters


def lat_transformation(lat_lon, lat=True):
    lat_lon = lat_lon.replace("°", "")
    lat_lon = lat_lon.replace("'", "")
    lat_lon = lat_lon.replace('"', "")
    lat_lon = lat_lon + " S" if lat else lat_lon + " W"
    return lat_lon


def lon_transformation(lat_lon):
    return lat_transformation(lat_lon, False)


def get_diameter(antenna_desc):
    diameter = antenna_desc
    if re.search(SHORT_DIAMETER_PATTERN, antenna_desc):
        diameter = re.findall(SHORT_DIAMETER_PATTERN, antenna_desc)[0]
        diameter = diameter.replace("P ", "")
        diameter = diameter.replace("M", "")
        diameter = diameter.replace(",", ".")
        diameter = diameter.strip()
        diameter = float(diameter)
    elif re.search(LONG_DIAMETER_PATTERN, antenna_desc):
        diameter = re.findall(LONG_DIAMETER_PATTERN, antenna_desc)[0]
        diameter = diameter.replace(",", ".")
        diameter = diameter.replace("metros", "")
        diameter = diameter.strip()
        diameter = float(diameter)
    return diameter


def get_result_df(enacom_export, messages):
    columns_df, _ = load_data("enacom_cols")
    enacom_columns = pd.Series(
        columns_df["Enacom"].values, index=columns_df["Column"]
    ).to_dict()
    columns_order = columns_df["Column"]

    antennas_dict, _ = load_data("antennas", True)
    new_antennas = set()
    generic_searches = set()
    new_diameters = False

    not_linked_antennas = [
        uid
        for uid in enacom_export[enacom_columns[LINK_CODE]].unique()
        if uid not in enacom_export[enacom_columns[EMISSION_CODE]].unique()
    ]
    if len(not_linked_antennas) > 0:
        messages += (
            "WARNING: There are some un-linked antennas, the file may be corrupted\n"
        )
    enacom_antenas_info = enacom_export.loc[:, enacom_columns.values()]
    enacom_antenas_info.columns = columns_df["Column"]
    logger.info(get_logging_message("Start Column Transformation"))
    # Columns Transformation
    pathloss_df = enacom_antenas_info.copy()
    pathloss_df.loc[pathloss_df[SITE_NAME].isna(), SITE_NAME] = pathloss_df[
        SITE_NAME
    ].mode()[0]
    pathloss_df.loc[pathloss_df[CALL_SIGN].isna(), CALL_SIGN] = pathloss_df[
        CALL_SIGN
    ].mode()[0]
    pathloss_df[SITE_NAME] = pathloss_df[SITE_NAME].apply(
        lambda name: "{0:.0f}".format(name)
    )
    pathloss_df[CALL_SIGN] = pathloss_df[CALL_SIGN].apply(
        lambda name: "{0:.0f}".format(name)
    )
    pathloss_df[LATITUDE] = pathloss_df[LATITUDE].apply(lat_transformation)
    pathloss_df[LONGITUDE] = pathloss_df[LONGITUDE].apply(lon_transformation)
    pathloss_df[[ANTENNA_MODEL, ANTENNA_DIAMETER, CALL_SIGN]] = pathloss_df[
        [ANTENNA_MODEL, ANTENNA_DIAMETER, CALL_SIGN]
    ].fillna("")

    for i, row in pathloss_df[[ANTENNA_MODEL, ANTENNA_DIAMETER, CALL_SIGN]].iterrows():
        info, new_antenna, generic_search, new_diameter = mma_transform(
            mma=row[ANTENNA_MODEL],
            mma2=row[ANTENNA_DIAMETER],
            cb=row[CALL_SIGN],
            antennas_dict=antennas_dict,
        )
        (
            row[ANTENNA_DIAMETER],
            row[ANTENNA_GAIN],
            row[ANTENNA_MODEL],
            row[ANTENNA_CODE],
        ) = info
        if new_antenna:
            new_antennas.add(new_antenna)
        if generic_search:
            generic_searches.add(generic_search)

        new_diameters = new_diameters or new_diameter

    pathloss_df[TX_FREQ] = pathloss_df[TX_FREQ].apply(
        lambda freq: "{0:.4f}".format(freq)
    )
    pathloss_df[POL] = pathloss_df[POL].apply(lambda pol: pol[-2])
    logger.info(get_logging_message("End Column Transformation"))
    # Merging with itself
    pathloss_df_complete = pd.merge(
        pathloss_df,
        pathloss_df,
        left_on=LINK_CODE,
        right_on=EMISSION_CODE,
        suffixes=("_S1", "_S2"),
        how="inner",
    )
    # Remove Duplicated Links
    na_hertz = set()
    rows = []
    for index, row in pathloss_df_complete.iterrows():
        if row[f"{EMISSION_CODE}_S1"] not in na_hertz:
            rows.append(index)
        na_hertz.add(row[f"{EMISSION_CODE}_S1"])
        na_hertz.add(row[f"{LINK_CODE}_S1"])
    pathloss_df_complete = pathloss_df_complete.loc[rows, :]
    # Columns rearrangement
    pathloss_df_complete = pathloss_df_complete[
        [col + suffix for col in columns_order for suffix in ("_S1", "_S2")]
    ]
    pathloss_df_complete = pathloss_df_complete.drop(
        columns=[
            f"{LINK_CODE}_S1",
            f"{LINK_CODE}_S2",
            f"{EMISSION_CODE}_S1",
            f"{EMISSION_CODE}_S2",
        ]
    )
    # Adding number sequences
    col1 = [str(pos) for pos in range(10, 10 + len(pathloss_df_complete) * 2, 2)]
    col2 = [str(pos) for pos in range(11, 11 + len(pathloss_df_complete) * 2, 2)]
    for col, col_suffix in [(SITE_NAME, col1), (CALL_SIGN, col2)]:
        for suffix in ["S1", "S2"]:
            pathloss_df_complete[f"{col}_{suffix}"] = (
                pathloss_df_complete[f"{col}_{suffix}"].map(str) + "-" + col_suffix
            )
    return messages, pathloss_df_complete, new_antennas, generic_searches, new_diameters
