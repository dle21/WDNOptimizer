import os
import pickle
import wntr
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from shapely.geometry import Point, LineString
from colour import Color

class NetworkVisualizer:

    def __init__(self, input_network) -> None:
        self.wn = wntr.network.WaterNetworkModel(input_network)
        self.input_network = input_network.split('\\')[-1]

    def get_network(self):
        g = self.wn.get_graph()
        print()

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
        self.pipe_gdf.to_file(os.path.join('assets', 'gis', f'{self.input_network.replace(".inp", "")}_pipes.shp'))
        self.node_gdf.to_file(os.path.join('assets', 'gis', f'{self.input_network.replace(".inp", "")}_nodes.shp'))
    
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
                    
                    plt.plot(line_x, line
                    , linewidth=dia / 100)
                    # plt.text((line_x[0]
                    #  2, 
                    #     (line_y[0] + li
                    # abel)
                else:
                    plt.plot(line_x, line_y, '*-', color=color)
        plt.show()

    def draw_comparison(self, set_progress):
        networks = [os.path.join('assets', 'non-dominated solutions', f) for f in os.listdir(os.path.join('assets', 'non-dominated solutions')) if os.path.splitext(f)[-1] == '.inp']
        comparative_dia = {'id': []}
        id_added = False
        for i, network in enumerate(networks):
            set_progress(['Generating pipe diameter summaries...', (i + 1) / len(networks) * 100, f'{int((i + 1) / len(networks) * 100)} %'])
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
        pickle.dump(self.pipe_gdf, open(os.path.join('assets', 'difference_pipes.obj'), 'wb'))
    
    def generate_activation_shp(self, networks):
        self.pipe_gdf = pickle.load(open(os.path.join('assets', 'difference_pipes.obj'), 'rb'))

        # Filter on selected networks
        self.pipe_gdf = self.pipe_gdf[[c for c in self.pipe_gdf.columns if 'assets' not in c or c in networks]]
        pickle.dump(self.pipe_gdf, open(os.path.join('assets', 'selected_diameters.obj'), 'wb'))
        for network in networks:
            # self.pipe_gdf[network] = (self.pipe_gdf['Ex_dia'] - self.pipe_gdf[network]).apply(lambda x: 0 if x == 0 or pd.isnull(x) else 1)
            self.pipe_gdf[network] = (self.pipe_gdf['Ex_dia'] - self.pipe_gdf[network]).apply(lambda x: 0 if x == 0 or pd.isnull(x) else 1)
        self.pipe_gdf['Activation_P'] = self.pipe_gdf[networks].sum(axis=1) / len(networks)
        self.pipe_gdf.to_clipboard()
        self.pipe_gdf = self.pipe_gdf.drop(networks, axis=1)
        pickle.dump(self.pipe_gdf, open(os.path.join('assets', 'selected_activation.obj'), 'wb'))
    
    def get_pareto_diameters(self, points):
        df = pickle.load(open(os.path.join('assets', 'selected_diameters.obj'), 'rb'))
        # [p['customdata'] for p in points['points'] if 'customdata' in p.keys()]
        points_df = df.loc[df['id'].isin([p['customdata'] for p in points['points'] if 'customdata' in p.keys()])]
        
        y = {}
        x = [c.split('\\')[-1].strip('.inp') for c in df.columns[3:].values]
        x = ['Existing'] + ['C: ' + c.split('_')[1] + '<br>HP: '+ c.split('_')[-1] for c in x]
        for i, row in points_df.iterrows():
            if not all(row['Ex_dia'] == row[df.columns[3:]].values):
                y[row['id']] = row[['Ex_dia'] + list(df.columns[3:].values)]
        return x, y
