from lib2to3.pgen2 import driver
from re import S
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import geopandas as gpd
from pyproj import CRS


class fileIO:
    def __init__(self, filepath):
        self.filepath = filepath
        self.data = self.read()

    def read(self):
        if self.filepath.endswith(".csv"):
            self.filename = self.filepath.split(".")[0]
            return pd.read_csv(self.filepath)
        elif self.filepath.endswith(".xlsx") or self.filepath.endswith(".xls"):
            self.filename = self.filepath.split(".")[0]
            return pd.read_excel(self.filepath)
        elif self.filepath.endswith(".shp"):
            self.filename = self.filepath.split(".")[0]
            gdf = gpd.read_file(self.filepath)
            return gdf
        else:
            raise ValueError("File type not supported")

    def write_geo(self, modified_dsm):
        self.data["modified_dsm"] = modified_dsm
        self.data.to_file(
            self.filename + ".geojson",
            driver="GeoJSON",
            encoding="utf-8",
            crs="EPSG:4326",
        )


class modify:
    def __init__(
        self, filePath, threshold=2, mad_threshold=1, savefig=True, export_geo=False
    ):
        df = fileIO(filePath).data
        self.filepath = filePath
        self.df = df
        if export_geo:
            self.FID = df["Id"]
        else:
            self.FID = df["FID"]
        self.dsm = df["nj_dsm"]
        self.ture_data = df["DSM_草场"]
        self.median = df["nj_dsm"].median()
        self.mean = df["nj_dsm"].mean()
        self.std = df["nj_dsm"].std()
        self.title = fileIO(filePath).filename.split("/")[-1]
        self.threshold = threshold
        self.mad_threshold = mad_threshold
        self.mad_var = self.mad()
        self.savefig = savefig
        self.export_geo = export_geo

    def find_near(self, dsm_list, k):
        """Find the fit index that is nearest to index-k limited by threshold and the median of the dsm_list."""
        i = k
        j = k
        while i > 0:
            if abs(dsm_list[i] - self.median) >= self.threshold:
                i -= 1
            else:
                break
        while j < len(dsm_list) - 1:
            if dsm_list[j] - self.median >= self.threshold:
                j += 1
            else:
                break
        if abs(dsm_list[i] - self.median) <= abs(dsm_list[j] - self.median):
            return i
        else:
            return j

    def remove_mutation(self, dsm_list):
        """Remove the mutation in the dsm_list."""
        for i in range(1, len(dsm_list) - 1):
            if dsm_list[i] > dsm_list[i - 1] and dsm_list[i] > dsm_list[i + 1]:
                dsm_list[i] = dsm_list[i - 1]
            elif dsm_list[i] < dsm_list[i - 1] and dsm_list[i] < dsm_list[i + 1]:
                dsm_list[i] = dsm_list[i - 1]
        return dsm_list

    def mad(self):
        median = self.dsm.median()
        median_list = []
        df_list = self.dsm.to_list()
        for x in df_list:
            median_list.append(abs(x - median))
        mad = np.median(median_list)
        return mad * self.mad_threshold

    def process_1(self, dsm_list):
        """找到最近的符合条件的点，并将其值替换该点的值。"""
        for i in range(0, len(dsm_list)):
            if abs(dsm_list[i] - self.median) >= self.threshold:
                dsm_list[i] = dsm_list[self.find_near(dsm_list, i)]
        self.title = self.title + "——中值最近邻法"
        self.plot(dsm_list)

    def process_2(self, dsm_list):
        """找到最近的符合条件的点，并将其值替换该点的值,并去除突变点。"""
        for i in range(0, len(dsm_list)):
            if abs(dsm_list[i] - self.median) >= self.threshold:
                dsm_list[i] = dsm_list[self.find_near(dsm_list, i)]
        self.title = self.title + "——中值最近邻法_去除突变点" + "——median:" + str(self.median)
        result = self.remove_mutation(dsm_list)
        if self.export_geo:
            fileIO(self.filepath).write_geo(result)
        else:
            self.plot(result)

    def process_3(self, dsm_list):
        """找到最近的符合条件的点，并将其值替换该点的值,并去除突变点。针对隧道"""
        for i in range(0, len(dsm_list)):
            if dsm_list[i] - self.median >= self.threshold:
                dsm_list[i] = dsm_list[self.find_near(dsm_list, i)]
        self.title = self.title + "——针对隧道的中值最近邻法_去除突变点"
        result = self.remove_mutation(dsm_list)
        self.plot(result)

    def process_4(self, dsm_list):
        """找到最近的符合条件的点，并将其值替换该点的值,并去除突变点。处理两次"""
        for i in range(0, len(dsm_list)):
            if abs(dsm_list[i] - self.median) >= self.threshold:
                dsm_list[i] = dsm_list[self.find_near(dsm_list, i)]
        self.title = self.title + "——两次中值最近邻法_去除突变点" + "——median:" + str(self.median)
        result = self.remove_mutation(dsm_list)
        for i in range(0, len(result)):
            if abs(result[i] - self.median) >= self.threshold:
                result[i] = result[self.find_near(result, i)]
        self.plot(result)

    def process_mad(self, dsm_list):
        """利用mad进行修正"""
        for i in range(0, len(dsm_list)):
            if dsm_list[i] > self.median + self.mad_var:
                dsm_list[i] = self.median + self.mad_var
            elif dsm_list[i] < self.median - self.mad_var:
                dsm_list[i] = self.median - self.mad_var
            else:
                pass
        self.title = self.title + "——mad法_mad:" + str(self.mad_var)
        self.plot(dsm_list)

    def process_mad2(self, dsm_list):
        """利用mad进行修正,并去除突变点。"""
        for i in range(0, len(dsm_list)):
            if dsm_list[i] > self.median + self.mad_var:
                dsm_list[i] = self.median + self.mad_var
            elif dsm_list[i] < self.median - self.mad_var:
                dsm_list[i] = self.median - self.mad_var
            else:
                pass
        result = self.remove_mutation(dsm_list)
        self.title = self.title + "——mad法_去除突变点_mad:" + str(self.mad_var)
        self.plot(result)

    def plot(self, modified_dsm):
        """
            plot the modified dsm.
        Args:
            modified_dsm (list):
        """
        plt.rcParams["font.family"] = ["SimHei"]
        plt.figure(figsize=(12, 3), dpi=150)
        plt.title(self.title)
        df1 = self.df[~self.df["DSM_草场"].isin([-9999])]

        plt.plot(self.FID.map(lambda x: x * 15), self.df.nj_dsm, "--", marker="o")
        plt.plot(self.FID.map(lambda x: x * 15), modified_dsm, marker="v")
        plt.plot(df1.FID.map(lambda x: x * 15), df1["DSM_草场"], marker="x")

        plt.legend(["未修正", "修正", "相对真值"])
        plt.xlabel("横剖面X(m)")
        plt.ylabel("高程值Y(m)")
        plt.grid()
        if self.savefig == True:
            plt.savefig("result/" + self.title.split("_")[0] + ".png", dpi=300)
        plt.show()
