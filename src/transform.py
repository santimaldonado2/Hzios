import pandas as pd
import pickle
import re
import json
import logging

with open('config/antennas_diameter_dict.json') as config_file:
    antennas_diameter_dict = json.load(config_file)

with open('config/antennas_info_dict.json') as config_file:
    antennas_info_dict = json.load(config_file)


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
    if re.match(r'P \d[.,]?[\d+]?M', antenna_desc):
        diameter = re.findall(r'P \d[.,]?[\d+]?M', antenna_desc)[0]
        diameter = diameter.replace('P ', '')
        diameter = diameter.replace('M', '')
        diameter = diameter.strip()
    elif re.match(r'.*\d,?\d? metros*.', antenna_desc):
        diameter = re.findall(r'\d,?\d? metros', antenna_desc)[0]
        diameter = diameter.replace(',', '.')
        diameter = diameter.replace('metros', '')
        diameter = diameter.strip()
    elif antenna_desc in antennas_diameter_dict:
        diameter = antennas_diameter_dict[antenna_desc]
    else:
        antennas_diameter_dict[antenna_desc] = antenna_desc
    return diameter


def get_antenna_code(diameter):
    global antennas_info_dict
    diameter = str(diameter)
    if diameter in antennas_info_dict and 'code' in antennas_info_dict[diameter]:
        return antennas_info_dict[diameter]['code']
    elif diameter in antennas_info_dict:
        antennas_info_dict[diameter]['code'] = diameter
    else:
        antennas_info_dict[diameter] = {'code': diameter}
    return diameter


def get_antenna_gain(diameter):
    global antennas_info_dict
    diameter = str(diameter)
    if diameter in antennas_info_dict and 'gain' in antennas_info_dict[diameter]:
        return antennas_info_dict[diameter]['gain']
    elif diameter in antennas_info_dict:
        antennas_info_dict[diameter]['gain'] = diameter
    else:
        antennas_info_dict[diameter] = {'gain': diameter}
    return diameter


def update_dicts():
    with open('config/antennas_diameter_dict.json', 'w') as config_file:
        json.dump(antennas_diameter_dict, config_file, indent=4)

    with open('config/antennas_info_dict.json', 'w') as config_file:
        json.dump(antennas_info_dict, config_file, indent=4)


def transform(import_file, result_dir, result_filename):
    try:
        logging.info(
            "Starting Transform input_file=[{}], result_dir=[{}], result_filename=[{}]".format(import_file, result_dir,
                                                                                               result_filename))

        with open('config/pathloss_columns.pkl', 'rb') as file:
            pathloss_columns = pickle.load(file)

        with open('config/enacom_selected_columns.pkl', 'rb') as file:
            enacom_selected_columns = pickle.load(file)

        messages = ""
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

        logging.info("Start Column Transformation")
        # Columns Transformation
        pathloss_df = enacom_antenas_info.copy()
        pathloss_df.loc[pathloss_df.SiteName.isna(), 'SiteName'] = pathloss_df.SiteName.mode()[0]
        pathloss_df.loc[pathloss_df.CallSign.isna(), 'CallSign'] = pathloss_df.CallSign.mode()[0]
        pathloss_df.SiteName = pathloss_df.SiteName.apply(lambda name: '{0:.0f}'.format(name))
        pathloss_df.CallSign = pathloss_df.CallSign.apply(lambda name: '{0:.0f}'.format(name))
        pathloss_df.Latitude = pathloss_df.Latitude.apply(lat_transformation)
        pathloss_df.Longitude = pathloss_df.Longitude.apply(lon_transformation)
        pathloss_df.AntennaDiameter = pathloss_df.AntennaDiameter.fillna("")
        pathloss_df.AntennaDiameter = pathloss_df.AntennaDiameter.apply(get_diameter)
        pathloss_df.AntennaModel = pathloss_df.AntennaDiameter.apply(get_antenna_code)
        pathloss_df.AntennaCode = pathloss_df.AntennaDiameter.apply(get_antenna_code)
        pathloss_df.AntennaGain = pathloss_df.AntennaDiameter.apply(get_antenna_gain)
        pathloss_df.TXFreq1 = pathloss_df.TXFreq1.apply(lambda freq: '{0:.4f}'.format(freq))
        pathloss_df.Pol1 = pathloss_df.Pol1.apply(lambda pol: pol[-2])

        logging.info("End Column Transformation")

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

        update_dicts()

        logging.info("End Transformation")
        messages += "Transformation Done! look for the file in {}\n".format(result_file)
    except Exception as err:
        messages = "Ops, An error happened!"
        logging.exception(messages)
    return messages
