import wntr
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from shapely.geometry import Point, LineString
from colour import Color

class NetworkVisualizer:

    def __init__(self, input_network) -> None:
        self.input_network = input_network
        self.wn = wntr.network.WaterNetworkModel(self.input_network)

    def generate_gdfs(self):
        g = self.wn.get_graph()
        node_x = [g.nodes[node]['pos'][0] for node in self.wn.nodes]
        node_y = [g.nodes[node]['pos'][1] for node in self.wn.nodes]

        pipe_gdf = {'id': [], 'Ex_dia': []}
        line_geometry = []
        
        for link in self.wn.links:
            if len(link.split('.')) > 1:
                pipe_gdf['id'].append(link)

                line_x = [g.nodes[link.split('.')[0]]['pos'][0], g.nodes[link.split('.')[1]]['pos'][0]]
                line_y = [g.nodes[link.split('.')[0]]['pos'][1], g.nodes[link.split('.')[1]]['pos'][1]]
                line_geometry.append(LineString(zip(line_x, line_y)))

                if not type(self.wn.get_link(link)) == wntr.network.elements.HeadPump:
                    pipe_gdf['Ex_dia'].append(int(self.wn.get_link(link).diameter * 1000))
                else:
                    pipe_gdf['Ex_dia'].append(np.NaN)
        self.pipe_gdf = gpd.GeoDataFrame(pipe_gdf, geometry=line_geometry)
        self.node_gdf = gpd.GeoDataFrame({'id': self.wn.nodes}, geometry=[Point(xy) for xy in zip(node_x, node_y)])
    
    def export_shp(self):
        self.pipe_gdf.to_file(f'{self.input_network.replace(".inp", "")}_pipes.shp')
        self.node_gdf.to_file(f'{self.input_network.replace(".inp", "")}_nodes.shp')
    
    def plot_network(self):
        plt.scatter(self.node_gdf['geometry'].x, self.node_gdf['geometry'].y, color='b')
        if 'Activation_P' in self.pipe_gdf.columns:
            colors = list(Color("black").range_to(Color("red"), 10))
        for link in self.wn.links:
            if len(link.split('.')) > 1:
                if not type(self.wn.get_link(link)) == wntr.network.elements.HeadPump:
                    row = self.pipe_gdf[self.pipe_gdf['id'] == link]
                    dia = int(row['Ex_dia'].values[0])
                    if 'Activation_P' in self.pipe_gdf.columns:
                        activation_p = row['Activation_P'].values[0]
                        color = str(colors[min(int(activation_p * 10), len(colors) - 1)])
                        label = f'{dia}_{round(activation_p, 2)}'
                    else:
                        color = 'b'
                        label = dia
                    line_x = [a[0] for a in row['geometry'].values[0].coords]
                    line_y = [a[1] for a in row['geometry'].values[0].coords]
                    
                    plt.plot(line_x, line_y, color=color, linewidth=dia / 100)
                    # plt.text((line_x[0] + line_x[1]) / 2, 
                    #     (line_y[0] + line_y[1]) / 2, label)
                else:
                    plt.plot(line_x, line_y, '*-', color=color)
        plt.show()

    def draw_comparison(self, networks):
        comparative_dia = {'id': []}
        id_added = False
        for network in networks:
            comparison_network = wntr.network.WaterNetworkModel(network)
            comparative_dia[network] = []
            for link in self.wn.links:
                if len(link.split('.')) > 1:
                    if not id_added:
                        comparative_dia['id'].append(link)
                    if not type(self.wn.get_link(link)) == wntr.network.elements.HeadPump:
                        comparative_dia[network].append(int(comparison_network.get_link(link).diameter * 1000))
                    else:
                        comparative_dia[network].append(np.NaN)
            id_added = True
        comparative_dia = pd.DataFrame(comparative_dia)
        self.pipe_gdf = self.pipe_gdf.merge(comparative_dia, on='id')
        self.pipe_gdf.to_csv(f'Difference_pipes.csv')        

        for network in networks:
            # self.pipe_gdf[network] = (self.pipe_gdf['Ex_dia'] - self.pipe_gdf[network]).apply(lambda x: 0 if x == 0 or pd.isnull(x) else 1)
            self.pipe_gdf[network] = (self.pipe_gdf['Ex_dia'] - self.pipe_gdf[network]).apply(lambda x: 0 if x == 0 or pd.isnull(x) else 1)
        self.pipe_gdf['Activation_P'] = self.pipe_gdf[networks].sum(axis=1) / len(networks)
        self.pipe_gdf = self.pipe_gdf.drop(networks, axis=1)
        self.pipe_gdf.to_file(f'Difference_pipes.shp')
        print()