import logging
import pickle
import re
import pandas as pd
import uuid

SHORT_DIAMETER_PATTERN = r'P \d[.,]?[\d+]?M'
LONG_DIAMETER_PATTERN = r'\d[,.]?\d? metros'
ANDREW = "ANDREW CORPORATION"

antennas_dict = pd.read_csv('config/antennas_dict.csv')
pathloss_antennas = pd.read_csv('config/pathloss_antennas.csv')
generic_searches = pd.read_csv('config/generic_searches.csv')

antennas_dict.cb = "-" + antennas_dict.cb
pathloss_antennas.Cb = "-" + pathloss_antennas.Cb

new_antennas = False
new_diameters = False

# Loggers
transaction_id = None
logger = logging.getLogger()
transform_logger = logging.getLogger('transformLogger')
generic_search_logger = logging.getLogger('genericSearchLogger')


def get_logging_message(message):
    return '[{}]:{}'.format(transaction_id, message)


def get_pathloss_antenna(cb, diameter):
    global pathloss_antennas
    transform_logger.info(get_logging_message('start get_pathloss_antenna cb=[{}], diameter=[{}]'.format(cb, diameter)))
    antennas = pathloss_antennas.loc[
        pathloss_antennas.Cb.str.contains('-{}'.format(cb)) &
        (pathloss_antennas.Diameter <= diameter + 0.04) &
        (pathloss_antennas.Diameter >= diameter - 0.04), ["Diameter", "Gain", "Model", "Code"]].values
    transform_logger.info(get_logging_message('end get_pathloss_antenna antennas=[{}]'.format(antennas)))
    return antennas


def get_generic_antenna(cb, mma, diameter):
    global pathloss_antennas, generic_searches, transaction_id
    generic_search_logger.info(
        get_logging_message('start get_generic_antenna cb=[{}], mma=[{}], diameter=[{}]'.format(cb, mma, diameter)))

    generic_searches = generic_searches.append(pd.DataFrame({
        "transaction_id": [transaction_id],
        "cb": [cb],
        "antenna": [mma],
        "diameter": [diameter]
    }), ignore_index=True, sort=False)

    generic_antennas = pathloss_antennas.loc[
        ~pathloss_antennas.Generic.isna() &
        pathloss_antennas.Cb.str.contains('-{}'.format(cb)), ["Diameter", "Gain", "Model", "Code"]].values

    generic_search_logger.info(
        get_logging_message('end get_generic_antenna generic_antennas=[{}]'.format(generic_antennas)))

    return generic_antennas


def mma_transform(mma, mma2, cb):
    transform_logger.info(get_logging_message('start mma_transform mma=[{}], mma2=[{}], cb=[{}]'.format(mma, mma2, cb)))

    global new_antennas, new_diameters, antennas_dict
    diameter = ""
    cb = int(cb)
    search_local = True

    if mma:
        if mma2 and re.search(SHORT_DIAMETER_PATTERN + '|' + LONG_DIAMETER_PATTERN, mma2):
            mma = mma.replace("ANDREW", "").replace("CORPORATION -", "").strip()
            diameter = get_diameter(mma2)
            info = get_pathloss_antenna(cb, diameter)
            search_local = len(info) == 0
        elif mma2:
            mma = mma2.replace(" ", "")

        if search_local:
            transform_logger.info(get_logging_message('start local search mma=[{}]'.format(mma)))
            local_info = antennas_dict.loc[
                antennas_dict.model.str.contains(mma), ["diameter", "gain", "model"]].values

            if len(local_info) == 0:
                transform_logger.info(get_logging_message('end local search - Antenna not found mma=[{}]'.format(mma)))
                antennas_dict = antennas_dict.append(pd.DataFrame({
                    "cb": ['-{}'.format(cb)],
                    "trademark": [""],
                    "model": [mma],
                    "diameter": [diameter],
                    "gain": [""]
                }), ignore_index=True)

                info = [(diameter, '', mma, '')]
                new_antennas = True
            else:
                diameter = local_info[0][0]
                transform_logger.info(get_logging_message('end local search antennas=[{}]'.format(local_info)))
                if diameter:
                    info = get_pathloss_antenna(cb, diameter)
                else:
                    info = get_generic_antenna(cb, mma, diameter)

                if len(info) == 0:
                    info = get_generic_antenna(cb, mma, diameter)

    elif mma2:
        if re.match(SHORT_DIAMETER_PATTERN + '|' + LONG_DIAMETER_PATTERN, mma2):
            info = get_pathloss_antenna(cb, get_diameter(mma2))

            if len(info) == 0:
                info = get_generic_antenna(cb, mma2, get_diameter(mma2))
                new_diameters = True

        else:
            info = get_generic_antenna(cb, "", "")
    else:
        info = get_generic_antenna(cb, "", "")

    return_tuple = tuple(info[0])
    transform_logger.info(
        get_logging_message('end mma_transform diameter=[{}], gain=[{}], model=[{}], code=[{}]'.format(*return_tuple)))
    return return_tuple


def lat_transformation(lat_lon, lat=True):
    lat_lon = lat_lon.replace('°', '')
    lat_lon = lat_lon.replace("'", '')
    lat_lon = lat_lon.replace('"', '')
    lat_lon = lat_lon + " S" if lat else lat_lon + " W"
    return lat_lon


def lon_transformation(lat_lon):
    return lat_transformation(lat_lon, False)


def get_diameter(antenna_desc):
    diameter = antenna_desc
    if re.search(SHORT_DIAMETER_PATTERN, antenna_desc):
        diameter = re.findall(SHORT_DIAMETER_PATTERN, antenna_desc)[0]
        diameter = diameter.replace('P ', '')
        diameter = diameter.replace('M', '')
        diameter = diameter.replace(',', '.')
        diameter = diameter.strip()
        diameter = float(diameter)
    elif re.search(LONG_DIAMETER_PATTERN, antenna_desc):
        diameter = re.findall(LONG_DIAMETER_PATTERN, antenna_desc)[0]
        diameter = diameter.replace(',', '.')
        diameter = diameter.replace('metros', '')
        diameter = diameter.strip()
        diameter = float(diameter)
    return diameter


def update_antennas_dict():
    global antennas_dict, generic_searches

    antennas_dict.cb = antennas_dict.cb.str.strip('-')
    antennas_dict.to_csv('config/antennas_dict.csv', index=False)
    generic_searches.to_csv('config/generic_searches.csv', index=False)


def transform(import_file, result_dir, result_filename):
    global transaction_id
    transaction_id = uuid.uuid4()
    try:
        logger.info(get_logging_message(
            "Starting Transform input_file=[{}], result_dir=[{}], result_filename=[{}]".format(import_file, result_dir,
                                                                                               result_filename)))

        with open('config/pathloss_columns.pkl', 'rb') as file:
            pathloss_columns = pickle.load(file)

        with open('config/enacom_selected_columns.pkl', 'rb') as file:
            enacom_selected_columns = pickle.load(file)

        messages = "Transaction ID: {}\n".format(transaction_id)
        global new_antennas, new_diameters
        new_antennas, new_diameters = False, False

        # File Import
        enacom_export = pd.read_excel(import_file)

        # Integrity Check
        not_linked_antennas = [uid for uid in enacom_export.NA_ENLAZADO.unique() if
                               uid not in enacom_export.NA_HERTZ.unique()]
        if len(not_linked_antennas) > 0:
            messages += "WARNING: There are some un-linked antennas, the file may be corrupted\n"

        # Enacom Columns processing
        enacom_selected_columns = enacom_selected_columns[::2]
        enacom_selected_columns.append("NA_HERTZ")
        enacom_selected_columns.append("NA_ENLAZADO")

        enacom_antenas_info = enacom_export.loc[:, enacom_selected_columns]

        # Pathloss Columns processing
        pathloss_columns = pathloss_columns[::2]
        pathloss_columns = [re.sub(r' .+', '', column)[3:] for column in pathloss_columns]
        pathloss_columns.append("NA_HERTZ")
        pathloss_columns.append("NA_ENLAZADO")

        enacom_antenas_info.columns = pathloss_columns

        logger.info(get_logging_message("Start Column Transformation"))
        # Columns Transformation
        pathloss_df = enacom_antenas_info.copy()
        pathloss_df.loc[pathloss_df.SiteName.isna(), 'SiteName'] = pathloss_df.SiteName.mode()[0]
        pathloss_df.loc[pathloss_df.CallSign.isna(), 'CallSign'] = pathloss_df.CallSign.mode()[0]
        pathloss_df.SiteName = pathloss_df.SiteName.apply(lambda name: '{0:.0f}'.format(name))
        pathloss_df.CallSign = pathloss_df.CallSign.apply(lambda name: '{0:.0f}'.format(name))
        pathloss_df.Latitude = pathloss_df.Latitude.apply(lat_transformation)
        pathloss_df.Longitude = pathloss_df.Longitude.apply(lon_transformation)
        pathloss_df.loc[:, ["AntennaModel", "AntennaDiameter", "CallSign"]] = pathloss_df.loc[:,
                                                                              ["AntennaModel", "AntennaDiameter",
                                                                               "CallSign"]].fillna("")
        tuple_list = [mma_transform(*tuple(row)) for row in
                      pathloss_df.loc[:, ["AntennaModel", "AntennaDiameter", "CallSign"]].values]

        pathloss_df.loc[:, ["AntennaDiameter", "AntennaGain", "AntennaModel", "AntennaCode"]] = pd.DataFrame(
            tuple_list).values
        pathloss_df.TXFreq1 = pathloss_df.TXFreq1.apply(lambda freq: '{0:.4f}'.format(freq))
        pathloss_df.Pol1 = pathloss_df.Pol1.apply(lambda pol: pol[-2])

        logger.info(get_logging_message("End Column Transformation"))

        # Merging with it self
        pathloss_df_complete = pd.merge(
            pathloss_df,
            pathloss_df,
            left_on='NA_ENLAZADO',
            right_on='NA_HERTZ',
            suffixes=['_S1', '_S2'],
            how='inner')

        # Remove Duplicated Links
        na_hertz = []
        rows = []
        for index, row in pathloss_df_complete.iterrows():
            if row['NA_HERTZ_S1'] not in na_hertz:
                na_hertz.append(row['NA_HERTZ_S1'])
                na_hertz.append(row['NA_ENLAZADO_S1'])
                rows.append(index)

        pathloss_df_complete = pathloss_df_complete.loc[rows, :]

        # Columns rearrangement
        pathloss_df_complete = pathloss_df_complete.drop(
            columns=['NA_HERTZ_S1', 'NA_HERTZ_S2', 'NA_ENLAZADO_S1', 'NA_ENLAZADO_S2'])
        columns_order = [None] * len(pathloss_df_complete.columns)
        columns_order[::2] = pathloss_df_complete.columns[range(0, 18)]
        columns_order[1::2] = pathloss_df_complete.columns[range(18, 36)]
        pathloss_df_complete = pathloss_df_complete[columns_order]

        # Adding number sequences
        col1 = [str(pos) for pos in range(10, 10 + len(pathloss_df_complete) * 2, 2)]
        col2 = [str(pos) for pos in range(11, 11 + len(pathloss_df_complete) * 2, 2)]
        pathloss_df_complete.SiteName_S1 = pathloss_df_complete.SiteName_S1.map(str) + '-' + col1
        pathloss_df_complete.CallSign_S1 = pathloss_df_complete.CallSign_S1.map(str) + '-' + col1
        pathloss_df_complete.SiteName_S2 = pathloss_df_complete.SiteName_S2.map(str) + '-' + col2
        pathloss_df_complete.CallSign_S2 = pathloss_df_complete.CallSign_S2.map(str) + '-' + col2

        result_file = '{}/{}'.format(result_dir, result_filename)
        pathloss_df_complete.to_csv(result_file, index=False, header=False)

        update_antennas_dict()

        logger.info(get_logging_message("End Transformation"))
        messages += "Transformation Done! look for the file in {}\n".format(result_file)

        messages += "New Antennas Found!!\n" if new_antennas else ""
        messages += "New Diameters Found!!" if new_diameters else ""

    except Exception as err:
        messages += "Ops, An error happened!"
        logger.exception(messages)
    return messages
