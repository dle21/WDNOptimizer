import math
import geopandas as gpd
import plotly.graph_objs as go
import pickle
import plotly.figure_factory as ff
import pandas as pd
import numpy as np

def utmToLatLng(zone, easting, northing, northernHemisphere=True):
    """
    https://stackoverflow.com/questions/343865/how-to-convert-from-utm-to-latlng-in-python-or-javascript
    """
    if not northernHemisphere:
        northing = 10000000 - northing

    a = 6378137
    e = 0.081819191
    e1sq = 0.006739497
    k0 = 0.9996

    arc = northing / k0
    mu = arc / (a * (1 - math.pow(e, 2) / 4.0 - 3 * math.pow(e, 4) / 64.0 - 5 * math.pow(e, 6) / 256.0))

    ei = (1 - math.pow((1 - e * e), (1 / 2.0))) / (1 + math.pow((1 - e * e), (1 / 2.0)))

    ca = 3 * ei / 2 - 27 * math.pow(ei, 3) / 32.0

    cb = 21 * math.pow(ei, 2) / 16 - 55 * math.pow(ei, 4) / 32
    cc = 151 * math.pow(ei, 3) / 96
    cd = 1097 * math.pow(ei, 4) / 512
    phi1 = mu + ca * math.sin(2 * mu) + cb * math.sin(4 * mu) + cc * math.sin(6 * mu) + cd * math.sin(8 * mu)

    n0 = a / math.pow((1 - math.pow((e * math.sin(phi1)), 2)), (1 / 2.0))

    r0 = a * (1 - e * e) / math.pow((1 - math.pow((e * math.sin(phi1)), 2)), (3 / 2.0))
    fact1 = n0 * math.tan(phi1) / r0

    _a1 = 500000 - easting
    dd0 = _a1 / (n0 * k0)
    fact2 = dd0 * dd0 / 2

    t0 = math.pow(math.tan(phi1), 2)
    Q0 = e1sq * math.pow(math.cos(phi1), 2)
    fact3 = (5 + 3 * t0 + 10 * Q0 - 4 * Q0 * Q0 - 9 * e1sq) * math.pow(dd0, 4) / 24

    fact4 = (61 + 90 * t0 + 298 * Q0 + 45 * t0 * t0 - 252 * e1sq - 3 * Q0 * Q0) * math.pow(dd0, 6) / 720

    lof1 = _a1 / (n0 * k0)
    lof2 = (1 + 2 * t0 + Q0) * math.pow(dd0, 3) / 6.0
    lof3 = (5 - 2 * Q0 + 28 * t0 - 3 * math.pow(Q0, 2) + 8 * e1sq + 24 * math.pow(t0, 2)) * math.pow(dd0, 5) / 120
    _a2 = (lof1 - lof2 + lof3) / math.cos(phi1)
    _a3 = _a2 * 180 / math.pi

    latitude = 180 * (phi1 - fact1 * (fact2 + fact3 + fact4)) / math.pi

    if not northernHemisphere:
        latitude = -latitude

    longitude = ((zone > 0) and (6 * zone - 183.0) or 3.0) - _a3

    return latitude, longitude

def network_mapper():
    fig, lats, lons = update_network_map({})
    fig['layout'] = go.Layout(
        showlegend=True,
        height=600,
        margin={"r": 0, "t": 0, "l": 0, "b": 30},
        mapbox={
            'center': {
                'lon': (max(lons) + min(lons)) / 2,
                'lat': (max(lats) + min(lats)) / 2,
            },
            'style': 'open-street-map',
            # TODO autoscaling? 1 shows the world,
            'zoom': 14,
            
        },
    )
    return fig

def update_network_map(fig):
    df = pickle.load(open('assets\\selected_activation.obj', 'rb'))
    scatter_groups = {}
    lons = []
    lats = []
    if len(df) > 0:
        fig['data'] = []
        middle_node_trace = go.Scattermapbox(
            lon=[],
            lat=[],
            text=[],
            mode='markers',
            hoverinfo='text',
            marker=go.scattermapbox.Marker(
                opacity=0,
                color=[]
            ),
            customdata=[]
        )
        
        for i in range(len(df)):
            po_lats = []
            po_lons = []
            for j in range(len(df['geometry'][i].coords)):
                lat, lon = utmToLatLng(55, df['geometry'][i].coords[j][0], df['geometry'][i].coords[j][1], False)
                po_lons.append(lon)
                po_lats.append(lat)
            color = f'rgb({int(df["Activation_P"][i] * 255)},0,0)'
            # fig['data'].append(go.Scattermapbox(
            #     name=df['id'][i],
            #     mode='lines+markers',
            #     lon=po_lons,
            #     lat=po_lats,
            #     customdata=[df['id'][i]],
            #     hoverinfo="skip",
            #     marker=go.scattermapbox.Marker(
            #         color=f'rgb({strength},0,0)',
            #     ),
            # ))
            middle_node_trace['lon'] += tuple([sum(po_lons) / len(po_lons)])
            middle_node_trace['lat'] += tuple([sum(po_lats) / len(po_lats)])
            middle_node_trace['text'] += 'ID: ' + str(df['id'][i]) + '<br>P: ' + str(df['Activation_P'][i]),
            middle_node_trace['marker']['color'] += color,
            middle_node_trace['customdata'] += df['id'][i],
            
            if color not in scatter_groups.keys():
                scatter_groups[color] = {}
                scatter_groups[color]['lats'] = []
                scatter_groups[color]['lons'] = []
            
            scatter_groups[color]['lats'] += po_lats + [None]
            scatter_groups[color]['lons'] += po_lons + [None]
            
            lats += po_lats
            lons += po_lons
        for color in scatter_groups.keys():
            fig['data'].append(go.Scattermapbox(
                    name=color,
                    mode='lines+markers',
                    lat=scatter_groups[color]['lats'],
                    lon=scatter_groups[color]['lons'],
                    # customdata=[df['id'][i]],
                    hoverinfo="skip",
                    marker=go.scattermapbox.Marker(
                        color=color,
                    ),
                ))
        fig['data'].append(middle_node_trace)
    return fig, lats, lons

def plot_pareto():
    plot_results = pickle.load(open('assets\\plotting_results.obj', 'rb'))
    fig = {
            'data': [
                go.Scatter(
                    x=plot_results['costs'],
                    y=plot_results['h_penalties'],
                    hoverinfo='skip',
                    name='Trialed solutions',
                    mode='markers',
                    opacity=0.2
                ),
                go.Scatter(
                    x=plot_results['pareto_costs'],
                    y=plot_results['pareto_h_penalties'],
                    hoverinfo='x+y',
                    name='Pareto front solutions',
                    mode='markers'
                ),
            ],
            'layout': go.Layout(
                title=f'Pareto curve ({plot_results["generations"]} generations)',
                xaxis={'title': 'Costs ($)', 'range': plot_results['xlim']},
                yaxis={'title': 'Penalties ($)', 'range': plot_results['ylim']},
                margin={'b': 30, 'l': 60, 'r': 60, 't': 60},
                legend={
                    'yanchor': "top",
                    'y': 0.99,
                    'xanchor': "right",
                    'x': 0.99
                }
            )
    }

    if 'manual_totex' in plot_results.keys():
        fig['data'].append(
            go.Scatter(
                x=[plot_results['manual_totex']],
                y=[plot_results['manual_penalties']],
                hoverinfo='x+y',
                name='Manual',
                mode='markers',
                marker={'size': 12, 'color': 'red'}
            ))
    fig['data'].append(
        go.Scatter(
            x=[plot_results['existing_totex']],
            y=[plot_results['existing_penalties']],
            hoverinfo='x+y',
            name='Do Nothing',
            mode='markers',
            marker={'size': 12, 'color': 'blue'}
        ),
    )
    return fig

def plot_diameters(x, y):
    plot = {'data': [], 
            'layout': go.Layout(
                title=f'Diameters at each pareto solution',
                xaxis_title='Solution',
                yaxis_title='Diameter (mm)',
                margin={'b': 30, 'l': 60, 'r': 60, 't': 60}
            )}
    for id in y.keys():
        plot['data'].append(go.Scatter(
            x=x,
            y=y[id],
            name=id,
            mode='lines+markers',
        ))
    return plot

def network_hydraulics_mapper(results_file, results):

    min_p_colors = {
        (float('-inf'), 20): 'rgb(255,0,0)',
        (20, 25): 'rgb(255,255,0)',
        (25, 30): 'rgb(0,255,0)',
        (30, 35): 'rgb(0,255,255)',
        (35, float('inf')): 'rgb(0,0,255)',
    }

    max_hl_colors = {
        (float('-inf'), 3): 'rgb(0,0,255)',
        (3, 5): 'rgb(0,255,0)',
        (5, 10): 'rgb(255,165,0)',
        (10, float('inf')): 'rgb(255,0,0)',
    }

    node_df = gpd.read_file('assets\\gis\\' + results_file.replace('.inp', '_nodes.shp'))
    pipe_df = gpd.read_file('assets\\gis\\' + results_file.replace('.inp', '_pipes.shp'))

    max_hl = results.headloss_results.max() * 1000
    min_p = results.pressure_results.min()
    lons = []
    lats = []
    fig = {}
    if len(pipe_df) > 0:
        fig['data'] = []

        middle_node_trace = go.Scattermapbox(
            lon=[],
            lat=[],
            text=[],
            mode='markers',
            hoverinfo='text',
            marker=go.scattermapbox.Marker(
                opacity=0,
                color=[],
            )
        )

        scatter_groups = {}
        for i in range(len(pipe_df)):
            if pipe_df['id'][i] in max_hl.index:
                # strength = int((1 - max_hl.rank()[i] / len(max_hl)) * 255)
                
                color = max_hl_colors[list(max_hl_colors.keys())[[k[1] > max_hl[i] and max_hl[i] >= k[0] for k in max_hl_colors.keys()].index(True)]]
                text = str(round(max_hl[pipe_df['id'][i]], 2))
            else:
                color = f'rgb(0,0,0)'
                text = 'NA'
            po_lats = []
            po_lons = []
            for j in range(len(pipe_df['geometry'][i].coords)):
                lat, lon = utmToLatLng(55, pipe_df['geometry'][i].coords[j][0], pipe_df['geometry'][i].coords[j][1], False)
                po_lons.append(lon)
                po_lats.append(lat)
            # fig.add_trace(go.Scattermapbox(
            #     name=pipe_df['id'][i],
            #     mode='lines',
            #     lon=po_lons,
            #     lat=po_lats,
            #     customdata=[pipe_df['id'][i]],
            #     # text=text,
            #     hoverinfo="skip",
            #     marker=go.scattermapbox.Marker(
            #         color=color,
            #     ),
            # ))

            middle_node_trace['lon'] += tuple([(po_lons[0] + po_lons[1]) / 2])
            middle_node_trace['lat'] += tuple([(po_lats[0] + po_lats[1]) / 2])
            middle_node_trace['text'] += 'ID: ' + str(pipe_df['id'][i]) + '<br>HL: ' + text,
            middle_node_trace['marker']['color'] += color,
            
            if color not in scatter_groups.keys():
                scatter_groups[color] = {}
                scatter_groups[color]['lats'] = []
                scatter_groups[color]['lons'] = []
            
            scatter_groups[color]['lats'] += po_lats + [None]
            scatter_groups[color]['lons'] += po_lons + [None]

            lats += po_lats
            lons += po_lons
        for color in scatter_groups.keys():
            fig['data'].append(go.Scattermapbox(
                name=color,
                mode='lines+markers',
                lon=scatter_groups[color]['lons'],
                lat=scatter_groups[color]['lats'],
                # customdata=[pipe_df['id'][i]],
                # text=text,
                hoverinfo="skip",
                marker=go.scattermapbox.Marker(
                    color=color,
                ),
            ))

        fig['data'].append(middle_node_trace)

        node_lons = []
        node_lats = []
        node_text = []
        node_colors = []
        for node in min_p.index:
            row = node_df.loc[node_df['id'] == node]['geometry']
            lat, lon = utmToLatLng(55, row.x.values[0], row.y.values[0], False)
            node_lons.append(lon)
            node_lats.append(lat)
            node_text.append('ID: ' + node + '<br>P: ' + str(round(min_p[node], 2)))
            node_colors.append(min_p_colors[list(min_p_colors.keys())[[k[1] > min_p[node] and min_p[node] >= k[0] for k in min_p_colors.keys()].index(True)]])

        fig['data'].append(go.Scattermapbox(
            lon=node_lons,
            lat=node_lats,
            text=node_text,
            mode='markers',
            hoverinfo='text',
            marker=go.scattermapbox.Marker(
                color=node_colors,
            )
        ))

        fig['layout'] = go.Layout(
            showlegend=True,
            height=600,
            margin={"r": 0, "t": 0, "l": 0, "b": 30},
            mapbox={
                'center': {
                    'lon': (max(lons) + min(lons)) / 2,
                    'lat': (max(lats) + min(lats)) / 2,
                },
                'style': 'open-street-map',
                # TODO autoscaling? 1 shows the world,
                # TODO 10 shows SDLAM (0.7 lon range, 0.23 lat)
                'zoom': 14,
            },
        )
    return fig

def pressure_density(existing_results, proposed_results):
    ex_min_p = existing_results.pressure_results.min()
    p_min_p = proposed_results.pressure_results.min()

    return ff.create_distplot([ex_min_p, p_min_p], ['Existing', 'Proposed'], show_hist=False, show_rug=False) \
        .update_layout(xaxis_title='Pressure (m)', yaxis_title='Probability Density', margin={'b': 30, 'l': 60, 'r': 60, 't': 60})

def headloss_density(existing_results, proposed_results):
    ex_max_hl = existing_results.headloss_results.max() * 1000
    p_max_hl = proposed_results.headloss_results.max() * 1000

    return ff.create_distplot([ex_max_hl, p_max_hl], ['Existing', 'Proposed'], show_hist=False, show_rug=False) \
        .update_layout(xaxis_title='Headloss (m/km)', yaxis_title='Probability Density', margin={'b': 30, 'l': 60, 'r': 60, 't': 60})


def get_table_results(network, scenario):
    diameters = pd.DataFrame([int(network.wn.get_link(pipe).diameter * 1000) for pipe in network.pipes]).value_counts().sort_index()
    diameters.index = [a[0] for a in diameters.index]
    diameters = pd.DataFrame({'Diameter (mm)': diameters.index, f'{scenario} diameters': diameters.values})
    
    pressure_bins = pd.cut(network.pressure_results.min(), [float('-inf'), 20, 25, 30, 35, float('inf')]).value_counts().sort_index()
    pressure_bins.index = ['< ' + str(int(pressure_bins.index[0].right))] + [str(int(a.left)) + ' - ' + str(int(a.right)) for a in pressure_bins.index[1:-1]] + [str(int(pressure_bins.index[-2].right)) + '+']
    pressure_bins = pd.DataFrame({'Pressure (m)': pressure_bins.index, f'{scenario} pressures': pressure_bins.values})
    
    hl_bins = pd.cut(network.headloss_results.max() * 1000, [float('-inf'), 3, 5, 10, float('inf')]).value_counts().sort_index()
    hl_bins.index = ['< ' + str(int(hl_bins.index[0].right))] + [str(int(a.left)) + ' - ' + str(int(a.right)) for a in hl_bins.index[1:-1]] + [str(int(hl_bins.index[-2].right)) + '+']
    hl_bins = pd.DataFrame({'Headloss (m/km)': hl_bins.index, f'{scenario} headloss': hl_bins.values})

    return [diameters, pressure_bins, hl_bins]

def join_data_tables(current, new_columns):
    first_columns = [current[i].iloc[:, 0] for i in range(len(current))]
    merged_dfs = [current[i].merge(new_columns[i], 'outer').fillna(0) for i in range(len(current))]
    return [merged_dfs[0]] + [merged_dfs[i].iloc[[merged_dfs[i].index[merged_dfs[i].iloc[:, 0] == cat].values[0] for cat in first_columns[i].values], :] for i in range(1, len(current))]

def get_pump_curves(existing_results, proposed_results):
    import matplotlib.pyplot as plt
    colors = plt.rcParams['axes.prop_cycle'].by_key()['color']
    return {
        'data': [
            go.Scatter(
                # x=np.linspace(0, 2 * results.wn.get_link(pump).get_pump_curve().points[0][0] * 1000),
                # y=
                # 4/3 * results.wn.get_link(pump).get_pump_curve().points[0][1] - 
                # results.wn.get_link(pump).get_pump_curve().points[0][1] / (3 * (results.wn.get_link(pump).get_pump_curve().points[0][0] * 1000) ** 2) *
                # np.linspace(0, 2 * results.wn.get_link(pump).get_pump_curve().points[0][0] * 1000) ** 2,
                x=[a[0] * 1000 for a in results.wn.get_link(pump).get_pump_curve().points],
                y=[a[1] for a in results.wn.get_link(pump).get_pump_curve().points],
                
                name=f'{pump} {title}',
                mode='lines',
                line={'dash': 'dash', 'color': colors[i]}
            )
        if title == 'Prop' else
            go.Scatter(
                x=[a[0] * 1000 for a in results.wn.get_link(pump).get_pump_curve().points],
                y=[a[1] for a in results.wn.get_link(pump).get_pump_curve().points],
                name=f'{pump} {title}',
                mode='lines',
                line={'color': colors[i]}
            )
        for title, results in [('Ex', existing_results), ('Prop', proposed_results)] 
        # for title, results in [('Ex', existing_results), ('Prop', proposed_results)] 
        for i, pump in enumerate(results.pumps)],
        'layout': go.Layout(
            xaxis_title='Costs ($)',
            yaxis_title='Head (m)',
            margin={'b': 30, 'l': 60, 'r': 60, 't': 60},
            legend={
                'yanchor': "top",
                'y': 0.99,
                'xanchor': "right",
                'x': 0.99
            }
        )
    }