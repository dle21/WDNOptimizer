import wntr
from NetworkEvaluator import NetworkEvaluator
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# Load existing model
Ex_INP_file_name = 'TONGALA_Calibration_2022' 
Ex_inp_file = f'C:/Users/dmiller-moran/WDNOptimizer/{Ex_INP_file_name}.inp'
wn = wntr.network.WaterNetworkModel(Ex_inp_file)



# NetEval_existing = NetworkEvaluator(Ex_inp_file, r"C:\Users\dmiller-moran\WDNOptimizer\Optimisation_Cost_Basis.xlsx")

# # Load future model
# INP_file_name = 'OPTION_2___TONGALA_Masterplanning_2043_Horizon__1' 
# inp_file = f'C:/Users/dmiller-moran/WDNOptimizer/{INP_file_name}.inp'

# NetEval_future = NetworkEvaluator(inp_file, r"C:\Users\dmiller-moran\WDNOptimizer\Optimisation_Cost_Basis.xlsx")

# NetEval_existing.capex()

# NetEval_future.totex_func(NetEval_existing.pipe_df)

# pumps = NetEval_future.wn.pump_name_list
# print([wn.get_link(pump).get_design_flow() * 1000 / 2 for pump in pumps])


nodes = wn.node_name_list

pipes = wn.pipe_name_list

# Original Pipe diameters
pipe_info = {}
pipe_names = [wn.get_link(pipe).name for pipe in wn.pipe_name_list]
original_diameter = [wn.get_link(pipe).diameter * 1000 for pipe in wn.pipe_name_list]
pipe_length = [wn.get_link(pipe).length for pipe in wn.pipe_name_list]

pipe_info = {'Pipe_name': pipe_names,'Original_Diameter': original_diameter, 'Length': pipe_length}
pipe_df = pd.DataFrame.from_dict(pipe_info)
pipe_df.to_excel('C:/Users/dmiller-moran/WDNOptimizer/2043_pipes.xlsx')

valves = wn.valve_name_list

# Original Pipe diameters
valve_info = {}
valve_names = [wn.get_link(valve).name for valve in wn.valve_name_list]
original_diameter = [wn.get_link(valve).diameter * 1000 for valve in wn.valve_name_list]
# pipe_length = [wn.get_link(pipe).length for pipe in wn.pipe_name_list]

valve_info = {'Valve_name': valve_names,'Original_Diameter': original_diameter}
valve_df = pd.DataFrame.from_dict(valve_info)
valve_df.to_excel('C:/Users/dmiller-moran/WDNOptimizer/2043_valves.xlsx')