import time
from NetworkEvaluator import NetworkEvaluator
from platypus import Problem, NSGAII, Integer, Archive, nondominated
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl

class LoggingArchive(Archive):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, *kwargs)
        self.log = []
    
    def add(self, solution):
        super().add(solution)
        self.log.append(solution)


start_time = time.time()

# inp_file = 'TONGALA_Calibration_2022.inp'
inp_file = 'Optimised_network10000.inp'
input_sheet = 'Optimisation_Cost_Basis.xlsx'
min_p_req = 20
max_hl_req = 10
generations = 10000


fig = plt.figure()
nwke = NetworkEvaluator(inp_file, input_sheet, min_p_req)
existing_totex, existing_capex = nwke.totex_func(0)
existing_penalties = nwke.penalties(min_p_req, max_hl_req)
print(f'\n\nOriginal network cost: ${existing_totex:,.2f}, Penalties: ${existing_penalties:,.2f}')
available_diameters = nwke.pipecosts['Size'].unique()

