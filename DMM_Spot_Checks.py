import time
import wntr
from NetworkEvaluator import NetworkEvaluator
from platypus import Problem, NSGAII, Integer, Archive, nondominated
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl


# Load model
INP_file_name = 'OPTION_2___TONGALA_Masterplanning_2043_Horizon__1' # input('Enter the filename of the network you wish to process: ')
inp_file = f'C:/Users/dmiller-moran/WDNOptimizer/{INP_file_name}.inp'
wn = wntr.network.WaterNetworkModel(inp_file)


pipes = wn.pipe_name_list

# Original Pipe diameters
pipe_info = {}
pipe_names = [wn.get_link(pipe).name for pipe in wn.pipe_name_list]
original_diameter = [wn.get_link(pipe).diameter * 1000 for pipe in wn.pipe_name_list]
pipe_length = [wn.get_link(pipe).length for pipe in wn.pipe_name_list]

pipe_info = {'Pipe_name': pipe_names,'Original_Diameter': original_diameter, 'Length': pipe_length}
pipe_df = pd.DataFrame.from_dict(pipe_info)
pipe_df.to_excel('C:/Users/dmiller-moran/WDNOptimizer/2043_pipes.xlsx')
