import os
import json


class CtfJsonData:
    """Interface to create and manage the data json file used for visualization"""
    _name: str
    _path: str
    _ctf_data: list
    _ctf_tables: list
    _ctf_charts: list
    _blob: dict

    def __init__(self, name: str = "ctf.json", path: str = ""):
        self._name = name
        self._path = path
        self._ctf_data = []
        self._ctf_tables = []
        self._ctf_charts = []
        self._blob = {"ctf_data": self._ctf_data, "ctf_tables": self._ctf_tables, "ctf_charts": self._ctf_charts}

    @property
    def name(self) -> str:
        return self._name

    @property
    def path(self) -> str:
        return self._path

    @property
    def blob(self) -> dict:
        self._blob["ctf_data"] = self._ctf_data
        self._blob["ctf_tables"] = self._ctf_tables
        self._blob["ctf_charts"] = self._ctf_charts
        return self._blob

    @blob.setter
    def blob(self, blob: dict) -> None:
        self._blob = blob

    def save_data(self):
        with open(os.path.join(self._path, self._name), 'w') as outfile:
            json.dump(self.blob, outfile, indent=4)

    def add_data_source(self, data_source: str) -> None:
        self._ctf_data.append({"data_source": data_source, "data_list": []})

    def add_data_to_source(self, data_source: str, data_list: list) -> None:
        """
            Args:
                data_source - the data source name to add data to
                data_list - list of dictionary data
        """
        for ds in self._ctf_data:
            if "data_source" in ds and data_source == ds["data_source"]:
                if "data_list" in ds:
                    ds["data_list"] += data_list
                    break

    def add_table(self, title: str, columns: str, data_source_list: str, table_type: str = "static") -> None:
        """
            Args:
                title - the title of the table
                columns - comma separated list of columns (name cannot contain a comma)
                data_source_list - comma separated list of data sources
                table_type - "static" or "dynamic"
        """
        self._ctf_tables.append({"title": title,
                                 "table_type": table_type,
                                 "columns": columns,
                                 "data_source_list": data_source_list})

    def add_chart(self, title: str, options: dict, axes: dict, chart_type: str = "static") -> None:
        """
            Args:
                title - the title of the chart
                options - dictionary of options (ie {"chart_display_type": "line", "tension": "True"})
                axes - dictionary of dictionaries (containing axes and options)
                chart_type - "static" or "dynamic"
        """
        self._ctf_charts.append({"title": title,
                                 "chart_type": chart_type,
                                 "options": options,
                                 "axes": axes})

    def add_chart_axes(self, title: str, axes: dict) -> None:
        """
            Args:
                title - the title of the chart to add axes to
                axes - dictionary of dictionaries (containing axes and options)
        """
        for ch in self._ctf_charts:
            if "title" in ch and title == ch["title"]:
                d1 = ch["axes"]
                # print(d1, axes)
                ch["axes"] = dict(list(d1.items()) + list(axes.items()))
                break


# Sample usage
if __name__ == "__main__":
    ctf_blob = CtfJsonData(name="ctf_blob.json", path="C:\Test\Logs_folder\*")
    ctf_blob.add_data_source("test1")
    ctf_blob.add_data_to_source("test1", {"a": 1, "b": 2, "c": 3})
    ctf_blob.add_data_to_source("test1", [{"a": 1, "b": 2, "c": 3}])
    ctf_blob.add_data_source("test2")
    ctf_blob.add_data_to_source("test2", [{"g": "4", "h": "5", "i": "6"}])
    ctf_blob.add_data_to_source("test1", [{"d": 4, "e": 5, "f": 6}])
    ctf_blob.add_table(title="table1", table_type="static", data_source_list="test1,test2", columns="column1,column2")
    ctf_blob.add_table(title="table2", table_type="static", data_source_list="test1,test2", columns="column1,column2")
    ctf_blob.add_chart(title="chart1",
                       chart_type="static",
                       options={"chart_display_type": "line", "tension": "True"},
                       axes={})
    ctf_blob.add_chart_axes("chart1", {"x_axis1": {}, "y_axis1": {}})
    ctf_blob.add_chart(title="chart2",
                       chart_type="static",
                       options={"chart_display_type": "line", "tension": "True"},
                       axes={})
    ctf_blob.add_chart_axes("chart1", {"x_axis2": {}, "y_axis2": {}})
    ctf_blob.add_chart_axes("chart2", {"x_axis2": {}, "y_axis2": {}})
    ctf_blob.save_data()
