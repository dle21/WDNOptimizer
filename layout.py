from dash import dcc, html, dash_table
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
from app import *
from style import *
from textwrap import dedent as d
import os
import plotly.graph_objs as go

sidebar = html.Div(
    [
        html.Img(src=r'assets\GHD1.png', style={'display': 'inline-block'}),
        html.H3("Charlie", className="display-4", style={'fontColor': 'black'}),
        html.Hr(),
        html.P(
            "Charlie", className="lead"
        ),
        dbc.Nav(
            [
                dbc.NavLink("Inputs\n", href="/page-1", id="page-1-link"),
                html.B(),
                dbc.NavLink("Run Model\n", href="/page-2", id="page-2-link"),
                html.B(),
                dbc.NavLink("Results Viewer\n", href="/page-3", id="page-3-link"),
            ],
            vertical='md',
            pills=True,
        ),

    ],
    style=SIDEBAR_STYLE,
)

content = html.Div(id="page-content", style=CONTENT_STYLE)
app.layout = html.Div([dcc.Location(id="url"), sidebar, content])

main = html.Div([
    dcc.ConfirmDialog(
        id='not-found',
        message='File not found',
    ),
    dbc.Row([html.H1("InfoWorks WSPro Export Comparisons")],
             className="row",
             style={'textAlign': "center"}),
    dbc.Row(
        # className="row",
        [
            dbc.Row([
                dbc.Col(
                className="six columns",
                children=[
                    dcc.Input(id='ws_file',
                              value=f'.wspm',
                              style={'margin-bottom': '5px'}),
            ]),
                dbc.Col(
                className="six columns",
                children=[
                    dcc.Input(id='inp_file',
                              value=f'.inp',
                              style={'margin-bottom': '5px'}),
                ]),
            ]),
            dbc.Row([
                html.Button('Plot Errors', id='plot_error'),
            ]),
            dbc.Row([
                dcc.Graph(id="export_relative_error"),
            ])
        ])
    ]
),

styles = {
    'pre': {
        'border': 'thin lightgrey solid',
        'overflowX': 'scroll',
        'overflowY': 'scroll'
    }
}

page2 = html.Div([
    dcc.ConfirmDialog(
        id='not-found',
        message='File not found',
    ),
    
    dbc.Row(
        children=[
        dbc.Col(
            className='twelve columns',
            children=[
                dbc.Row([
                    dbc.Col([
                        dcc.Markdown(d("""
                            **EPA file (.inp)**
                            """)),
                        dcc.Input(id='inp_file_GA',
                                value='TONGALA_Calibration_2022.inp',
                                style={'margin-bottom': '5px',
                                        'width': '300px'}),
                    ], className='four columns'),
                    dbc.Col([
                        dcc.Markdown(d("""
                                **Cost basis spreadsheet**
                                """)),
                        dcc.Input(id='cost_basis',
                                value=f'Optimisation_Cost_Basis.xlsx',
                                style={'margin-bottom': '5px',
                                        'width': '300px'}),
                    ], className='four columns', style={'margin-bottom': '5px'}),
                    dbc.Col([
                        dcc.Markdown(d("""
                                **Optional: proposed EPA file (.inp) for retrospective**
                                """)),
                        dcc.Input(id='proposed_inp_file',
                                value='OPTION_2___TONGALA_Masterplanning_2043_Horizon__1.inp',
                                style={'margin-bottom': '5px',
                                        'width': '300px'}),
                    ], className='four columns', style={'margin-bottom': '5px'}),
                ]),

                dbc.Row([
                    dbc.Col([
                        dcc.Markdown(d("""
                            **Generations**
                            """)),
                        dcc.Input(id='gens',
                                value=50,
                                type="number",
                                style={'margin-bottom': '5px',
                                        'width': '100px'}),
                    ], className='three columns'),
                    dbc.Col([    
                        dcc.Markdown(d("""
                                **Minimum pressure**
                                """)),
                        dcc.Input(id='min_p',
                                value=20,
                                type="number",
                                style={'margin-bottom': '5px',
                                        'width': '100px'}),
                    ], className='three columns'),
                    dbc.Col([
                        dcc.Markdown(d("""
                                **Maximum headloss**
                                """)),
                        dcc.Input(id='max_hl',
                                value=10,
                                type="number",
                                style={'margin-bottom': '5px',
                                        'width': '100px'}),
                    ], className='three columns'),
                    dbc.Col([
                        # dcc.Markdown(d("""
                        #     ****
                        #     """)),
                        html.Button('Run', id='run_GA'),
                        html.Button('Cancel', id='cancel_GA'),
                    ], className='three columns'),
                ], style={'margin-bottom': '5px'}),
                html.P(id='generated_files'),
                dbc.Row([
                    html.P(id='GA_initialise'),
                    dbc.Progress(id="GA_progress", striped=True, value=0, animated=True, style={'visibility': 'hidden'}),
                    html.P(id='GA_status', style={'visibility': 'hidden'})
                ])
            ],
            width=12, style={'height': '20%'}
        ),
    ]),
    dbc.Row(
        children=[
        dbc.Col(className='six columns',
            children=[
                dbc.Row([html.H1("Pareto curve")], style={'textAlign': "center"}),
                html.Div(id='pareto_curve', children=[dcc.Graph(figure=go.Figure().update_layout(go.Layout()))]),
                html.Button('Plot pareto', id='plot_pareto'),
            ], width=6
        ),
        dbc.Col(className='six columns',
            children=[
                dbc.Row([html.H1("Network Plots")], style={'textAlign': "center"}),
                html.Div(id='network_plots', children=[dcc.Graph(figure=go.Figure().update_layout(go.Layout()))]),
                # html.Div(id='network_plots', children=[dcc.Graph(id='network_plot_graph', figure=initial_network_map)]),
            ], width=6
        ),
    ], style={'height': '50%'}),
    dbc.Row(
        children=[html.Div(id='pipes_plot', children=[dcc.Graph(figure=go.Figure().update_layout(go.Layout()))])],
        style={'height': '30%'}
    )
])

page3 = html.Div([
    dbc.Row([html.H1("Model comparisons")],
             className="row",
             style={'textAlign': "center"}),
    dbc.Row(
        [
            dbc.Col(
                className='six columns',
                children=[
                    dcc.Markdown(d("""
                            **Existing (.inp)**
                            """)),
                        dcc.Input(id='existing_comparison',
                                value=f'TONGALA_Calibration_2022.inp',
                                style={'margin-bottom': '5px',
                                        'width': '500px'}),
                    html.Div(id='existing_comparison_plot', children=[dcc.Graph(figure=go.Figure().update_layout(go.Layout()))]),
                ],
                width=6
            ),

            dbc.Col(
                className="six columns",
                children=[
                    html.Div(id='proposed_comparison_parent',
                        children=[dcc.Markdown(d("""
                        **Proposed (.inp)**
                        """)),
                        dcc.Dropdown(os.listdir(os.path.join('assets', 'non-dominated solutions')),
                        id='proposed_comparison',
                        value=None,
                        style={'margin-bottom': '5px',
                                'width': '500px'})]),
                    html.Div(id='proposed_comparison_plot', children=[dcc.Graph(figure=go.Figure().update_layout(go.Layout()))])
                ], width=6
            ),
        ]
    ),
    dbc.Row([
        dbc.Col([
            dcc.Markdown(d("""
                **Pump curves**
                """)),
            html.Div(id='pump_curves', children=[dcc.Graph(figure=go.Figure().update_layout(go.Layout()))]),
        ], width=4),
        dbc.Col([
            dcc.Markdown(d("""
                **Pressure distribution**
                """)),
            html.Div(id='pressure_density', children=[dcc.Graph(figure=go.Figure().update_layout(go.Layout()))])
        ], width=4),
        dbc.Col([
            dcc.Markdown(d("""
                **Headloss distribution**
                """)),
            html.Div(id='HL_density', children=[dcc.Graph(figure=go.Figure().update_layout(go.Layout()))])
        ], width=4),
    ]),
    dbc.Row([dcc.Markdown(d("""
                **Manual (.inp)**
                """)),
            dcc.Input(id='manual_comparison',
                    value=f'OPTION_2___TONGALA_Masterplanning_2043_Horizon__1.inp',
                    style={'margin-bottom': '5px',
                            'width': '500px'}),]),
    dbc.Row([
        dbc.Col([dash_table.DataTable(
            id='diameters_table',
            style_cell={'textAlign': 'left'},
            style_header={'backgroundColor': 'black', 'color': 'white', 'fontWeight': 'bold'}, 
            style_data_conditional=[{'if': {'column_id': 'Diameter (mm)'},'backgroundColor': 'black', 'color': 'white', 'fontWeight': 'bold'}]
        )], width=4),
        dbc.Col([dash_table.DataTable(
            id='pressures_table',
            style_cell={'textAlign': 'left'},
            style_header={'backgroundColor': 'black', 'color': 'white', 'fontWeight': 'bold'}, 
            style_data_conditional=[{'if': {'column_id': 'Pressure (m)'},'backgroundColor': 'black', 'color': 'white', 'fontWeight': 'bold'}]
        )], width=4),
        dbc.Col([dash_table.DataTable(
            id='headloss_table',
            style_cell={'textAlign': 'left'},
            style_header={'backgroundColor': 'black', 'color': 'white', 'fontWeight': 'bold'}, 
            style_data_conditional=[{'if': {'column_id': 'Headloss (m/km)'},'backgroundColor': 'black', 'color': 'white', 'fontWeight': 'bold'}]
        )], width=4),
    ])
])

@app.callback(Output("page-content", "children"), [Input("url", "pathname")])
def render_page_content(pathname):
    if pathname in ["/", "/page-1"]:
        return main
    elif pathname == "/page-2":
        return page2
    elif pathname == "/page-3":
        page3.children[1].children[1].children[0].children[1].options = os.listdir(os.path.join('assets', 'non-dominated solutions'))
        return page3
    # If the user tries to reach a different page, return a 404 message
    return html.Div(
        [
            html.H1("404: Not found", className="text-danger"),
            html.Hr(),
            html.P(f"The pathname {pathname} was not recognised..."),
        ]
    )
