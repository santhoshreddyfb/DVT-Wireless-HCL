
"""
This script:
1. collects the test case csv filenames into a list
2. reads each csv file into a dataframe
3. convert Series to a dictionary, adds data sources to json
4. adds specified charts
5. save data series to json file for visualization
# Sample usage
    cv = CtfVisualization(path=<path to test case files directory>)
    cv.create_json()
Note: Remove any non test case csv files from directory before running to prevent conflict 
or extraneous data from being included in the visualization.
"""

import glob
import os

import pandas as pd

from ctf_json_data import CtfJsonData


class CtfVisualization:
    """Interface to create the visualization data json file from csv results files"""
    _description: str  # not currently used
    _name: str
    _path: str
    _data_sources: list

    def __init__(self, description: str = "Visualize test case csv files", name: str = "ctf_cmw.json", path: str = ""):
        self._description = description
        self._name = name
        self._path = path
        self._data_sources = []

    def create_json(self):
        # CTF create data blob
        ctf_json = CtfJsonData(name=self._name, path=self._path)

        all_csv_files = glob.glob(os.path.join(self._path, "CMW_VERDICT_*.csv"))
        for fn in all_csv_files:
            df = pd.read_csv(fn, sep=',', na_filter=False)

            # CTF add data source and table
            ctf_data_source = os.path.basename(fn)
            self._data_sources.append(ctf_data_source)
            ctf_json.add_data_source(ctf_data_source)
            ctf_columns = (', '.join(df))
            ctf_json.add_table(title=ctf_data_source, columns=ctf_columns, data_source_list=ctf_data_source)

            # CTF add data to source
            df_dict_ctf = df.T.to_dict()
            for row in df_dict_ctf:
                ctf_json.add_data_to_source(ctf_data_source, [df_dict_ctf[row]])

        # CTF dump to JSON file
        ctf_json.save_data()


# Sample usage
if __name__ == "__main__":
    cv = CtfVisualization(path="C:\Test\DVT-Wireless-HCL\{2}\Logs_folder\LTE_*")
    cv.create_json