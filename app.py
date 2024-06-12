import os
import dash
# import dash_auth
from dash.dependencies import Input, Output, State
import diskcache
from dash import DiskcacheManager
from utilities import *
from GAProcessor import *
from NetworkEvaluator import NetworkEvaluator
import diskcache
import dash_bootstrap_components as dbc
from NetworkVisualizer import NetworkVisualizer
import pickle
import pandas as pd
import numpy as np


cache = diskcache.Cache("./cache")
background_callback_manager = DiskcacheManager(cache)

app = dash.Dash(__name__,
                external_stylesheets=[dbc.themes.BOOTSTRAP],
                suppress_callback_exceptions=True,
                background_callback_manager=background_callback_manager)


# VALID_USERNAME_PASSWORD_PAIRS = {
#     'test': 'pass'
# }
# auth = dash_auth.BasicAuth(app, VALID_USERNAME_PASSWORD_PAIRS)

app.title = "Charlie"
# nwkv = NetworkVisualizer('TONGALA_Calibration_2022.inp')
# nwkv.generate_gdfs()
# nwkv.pipe_gdf['Activation_P'] = 0
# pickle.dump(nwkv.pipe_gdf, open('assets\\selected_activation.obj', 'wb'))
# initial_network_map = network_mapper()

# @app.callback(Output("proposed_comparison", "options"), Input("proposed_comparison_parent", "n_clicks"))
# def update_options(n):
#     if n:
#         options = os.listdir(os.path.join('assets', 'non-dominated solutions'))
#         return [{'label': options, 'value': options}]



# RUN GAPROCESSOR
@app.callback(
    Output('GA_status', 'children'),
    # Output('pareto_curve', 'children'),
    Input('run_GA', 'n_clicks'),
    State('inp_file_GA', 'value'),
    State('cost_basis', 'value'),
    State('proposed_inp_file', 'value'),
    State('gens', 'value'),
    State('min_p', 'value'),
    State('max_hl', 'value'),
    running=[
        (Output("run_GA", "disabled"), True, False),
        (Output("GA_status", "style"), {"visibility": "hidden"}, {"visibility": "visible"}),
        (Output("GA_progress", "style"), {"visibility": "visible"}, {"visibility": "hidden"}),
        (Output("GA_initialise", "style"), {"visibility": "visible"}, {"visibility": "hidden"}),
    ],
    cancel=[Input("cancel_GA", "n_clicks")],
    progress=[
        Output("GA_initialise", "children"),
        Output("GA_progress", "value"),
        Output("GA_progress", "label")
    ],
    interval=2000,
    background=True,
    prevent_initial_call=True
)
def run_GA(set_progress, n, inp_file, cost_basis, proposed_inp_file, gens, min_p, max_hl):
    if n:
        set_progress(['Initialising processor...', 0, '0 %'])
        ga = GAProcessor(inp_file, cost_basis, proposed_inp_file)
        ga.get_initial_costs(min_p, max_hl)
        ga.run_GA(set_progress, gens, min_p, max_hl)
        ga.export_plot_results('assets\\plotting_results.obj')

        set_progress(['Exporting diameters...', 0, '0 %'])
        nwkv = NetworkVisualizer(inp_file)
        nwkv.generate_gdfs()
        nwkv.export_shp()
        if proposed_inp_file is not None:
            nwkv = NetworkVisualizer(proposed_inp_file)
            nwkv.generate_gdfs()
            nwkv.export_shp()

        nwkv.draw_comparison(set_progress)
        return 'GA run completed!'
        # return 'GA run completed!', dash.dcc.Graph(id='pareto_curve_graph', figure=plot_pareto())


# PARETO CURVE PLOT
@app.callback(
    Output('pareto_curve', 'children'),
    Input('plot_pareto', 'n_clicks'),
    prevent_initial_call=True
)
def plot_pareto_callback(n):
    if n:
        return [dash.dcc.Graph(id='pareto_curve_graph', figure=plot_pareto())]
    else:
        return dash.dcc.Graph(figure=go.Figure().update_layout(go.Layout()))

# NETWORK PLOT UPDATES
@app.callback(
    Output('network_plots', 'children'),
    Input('pareto_curve_graph', 'selectedData'),
    Input('pareto_curve_graph', 'clickData'),
    State('inp_file_GA', 'value'),
    prevent_initial_call=True
)
def plot_result_graph(selected, clicked, inp_file):
    if selected is not None or clicked is not None:
        if dash.callback_context.triggered[0]['prop_id'] == 'pareto_curve_graph.selectedData':
            po = selected
        else:
            po = clicked
        networks = [os.path.join('assets', 'non-dominated solutions', f'C_{round(p["x"], 2)}_HP_{round(p["y"], 2)}.inp') for p in po['points']]
        networks = list(set([n for n in networks if os.path.exists(n)]))
        
        if len(networks) > 0:
            nwkv = NetworkVisualizer(inp_file)

            nwkv.generate_activation_shp(networks)

            # return update_network_map(initial_network_map)[0]
            return [dash.dcc.Graph(id='network_plots_graph', figure=network_mapper(networks))]
        else:
            # return initial_network_map
            return dash.dcc.Graph(figure=go.Figure().update_layout(go.Layout()))
    else:
        # return initial_network_map
        return dash.dcc.Graph(figure=go.Figure().update_layout(go.Layout()))

# PIPE PLOT UPDATES
@app.callback(
    Output('pipes_plot', 'children'),
    Input('network_plots_graph', 'selectedData'),
    Input('network_plots_graph', 'clickData'),
    State('inp_file_GA', 'value'),
    prevent_initial_call=True
)
def plot_result_graph(selected, clicked, inp_file):
    if selected is not None or clicked is not None:
        if dash.callback_context.triggered[0]['prop_id'] == 'network_plots_graph.selectedData':
            po = selected
        else:
            po = clicked
        nwkv = NetworkVisualizer(inp_file)
        x, y = nwkv.get_pareto_diameters(po)
        return [dash.dcc.Graph(figure=plot_diameters(x, y))]
    else:
        return dash.dcc.Graph(figure=go.Figure().update_layout(go.Layout()))

# EXISTING NETWORK COMPARISON PLOT
@app.callback(
    Output('existing_comparison_plot', 'children'),
    Output('proposed_comparison_plot', 'children'),
    Output('pump_curves', 'children'),
    Output('HL_density', 'children'),
    Output('pressure_density', 'children'),
    Output('diameters_table', 'data'),
    Output('pressures_table', 'data'),
    Output('headloss_table', 'data'),
    Input('existing_comparison', 'value'),
    Input('proposed_comparison', 'value'),
    Input('manual_comparison', 'value'),
)
def plot_existing_comparison_graph(existing_inp_file, proposed_inp_file, manual_inp_file):
    data_tables = None
    existing_figure = go.Figure().update_layout(go.Layout())
    proposed_figures = [
        go.Figure().update_layout(go.Layout()),
        go.Figure().update_layout(go.Layout()),
        go.Figure().update_layout(go.Layout()),
        go.Figure().update_layout(go.Layout())
    ]

    if existing_inp_file:
        nwke = NetworkEvaluator(existing_inp_file)
        ex_tables = get_table_results(nwke, 'Existing')
        data_tables = ex_tables
        existing_figure = network_hydraulics_mapper(existing_inp_file, nwke)

    if manual_inp_file:
        nwkm = NetworkEvaluator(manual_inp_file)
        man_tables = get_table_results(nwkm, 'Manual')
        if data_tables:
            data_tables = join_data_tables(data_tables, man_tables)
        else:
            data_tables = man_tables

    if proposed_inp_file:
        if not os.path.exists('assets\\gis\\' + proposed_inp_file.replace('.inp', '_pipes.shp')):
            nwkv = NetworkVisualizer(os.path.join('assets', 'non-dominated solutions', proposed_inp_file))
            nwkv.generate_gdfs()
            nwkv.export_shp()
        nwkp = NetworkEvaluator('assets\\non-dominated solutions\\' + proposed_inp_file)
        proposed_figures = [
            network_hydraulics_mapper(proposed_inp_file, nwkp), 
            get_pump_curves(nwke, nwkp),
            headloss_density(nwke, nwkp), 
            pressure_density(nwke, nwkp)
        ]

        prop_tables = get_table_results(nwkp, 'Proposed')
        if data_tables:
            data_tables = join_data_tables(data_tables, prop_tables)
        else:
            data_tables = prop_tables

    return [dash.dcc.Graph(id='existing_comparison_graph', figure=existing_figure)], \
        [dash.dcc.Graph(id='proposed_comparison_graph', figure=proposed_figures[0])], \
        [dash.dcc.Graph(id='pump_curves', figure=proposed_figures[1])], \
        [dash.dcc.Graph(id='HL_density_graph', figure=proposed_figures[2])], \
        [dash.dcc.Graph(id='pressure_density_graph', figure=proposed_figures[3])], \
        data_tables[0].to_dict('records'), \
        data_tables[1].to_dict('records'), \
        data_tables[2].to_dict('records')
