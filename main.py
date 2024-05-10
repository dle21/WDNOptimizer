import time
from NetworkEvaluator import NetworkEvaluator
from platypus import Problem, NSGAII, Integer, nondominated
import pandas as pd

start_time = time.time()

# inp_file = 'TONGALA_Calibration_2022.inp'
inp_file = 'OPTION_2___TONGALA_Masterplanning_2043_Horizon__1.inp'
input_sheet = 'Optimisation_Cost_Basis.xlsx'
min_p_req = 20
generations = 10000

nwke = NetworkEvaluator(inp_file, input_sheet, min_p_req)
print(f'\n\nOriginal network cost: ${nwke.total_annual_expenditure_func():,.2f}')
available_diameters = nwke.pipecosts['Size'].unique()

s = time.time()
print("GA optimisation in process…")

def Min_Cost_GA(x):
    indexers = {"indexer_%d"%idx: val for idx, val in enumerate(x)}
    
    for idx, pipe in enumerate(nwke.pipes):
        nwke.wn.get_link(pipe).diameter = available_diameters[indexers["indexer_%d"%idx]]/1000
    # nwke.export_inp('wip.inp')
    run_passed = nwke.run_sim()
    if run_passed:
        min_p = nwke.min_p_func()
        total_annual_expenditure = nwke.total_annual_expenditure_func()
        return [total_annual_expenditure], [min_p - min_p_req]
    else:
        return [float("inf"), float("-inf")]

problem = Problem(len(nwke.pipes), 1 , 1) # (Decisions variables, objectives, constraints)
problem.types[:] = Integer(0, len(available_diameters)-1)
problem.constraints[:] = ">=0"
problem.function = Min_Cost_GA
problem.directions[0] = Problem.MINIMIZE
algorithm = NSGAII(problem, population_size=100)
algorithm.run(generations)  

end_time = time.time()

# Results
non_dominated_soln = nondominated(algorithm.result)

diameters_result = [available_diameters[indexer] for indexer in
[problem.types[0].decode(binary_result) for binary_result in non_dominated_soln[0].variables]]

network_cost_result = non_dominated_soln[0].objectives[0]

min_p_result = non_dominated_soln[0].constraints[0] + min_p_req

print('The Nondominated Solution has the following decision variables:')
# for pipe, diameter in enumerate(diameters_result):
#     print(f'Pipe {pipe} diameter = {diameter}mm')
print(f'\nThe total annual expenditure for this network configuration is ${network_cost_result:,.2f}')
print(f'The Minimum Pressure in the network is: {min_p_result:.2f}mwc')
print(f'\nExecution time = {(end_time - start_time)/60:.2f} minutes')

# Creating the Optimised network
for idx, pipe in enumerate(nwke.pipes):
    nwke.wn.get_link(pipe).diameter = diameters_result[idx]/1000
nwke.export_inp(f'Optimised_network{generations}.inp')

# This code exports the final population to the clipboard for further inspection in MS excel 
results_dict = {f'Pipe_{pipe}_diameters': [available_diameters[indexer] for indexer in 
                [problem.types[0].decode(binary_result) for binary_result in 
                [solution.variables[idx] for solution in algorithm.result]]] for idx, pipe in enumerate(nwke.pipes)}

results_dict['objectives'] = [solution.objectives[0] for solution in algorithm.result]
results_dict['constraints'] = [solution.constraints[0] for solution in algorithm.result]

results_df = pd.DataFrame.from_dict(results_dict).to_csv(f'NSGA_Pipe_Diameter_{generations}.csv')