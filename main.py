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

inp_file = 'TONGALA_Calibration_2022.inp'
inp_file = 'OPTION_2___TONGALA_Masterplanning_2043_Horizon__1.inp'
input_sheet = 'Optimisation_Cost_Basis.xlsx'
min_p_req = 20
max_hl_req = 10
generations = 10000


# fig = plt.figure()
nwke = NetworkEvaluator(inp_file, input_sheet, min_p_req)
existing_totex, existing_capex = nwke.totex_func(0)
existing_penalties = nwke.penalties(min_p_req, max_hl_req)
print(f'\n\nOriginal network cost: ${existing_totex:,.2f}, Penalties: ${existing_penalties:,.2f}')
available_diameters = nwke.pipecosts['Size'].unique()

# s = time.time()
# print("GA optimisation in process…")

def Min_Cost_GA(x):
    indexers = {"indexer_%d"%idx: val for idx, val in enumerate(x)}
    
    for idx, pipe in enumerate(nwke.pipes):
        nwke.wn.get_link(pipe).diameter = available_diameters[indexers["indexer_%d"%idx]]/1000
    # nwke.export_inp('wip.inp')
    run_passed = nwke.run_sim()
    if run_passed:
        penalty = nwke.penalties(min_p_req, max_hl_req)
        totex, _ = nwke.totex_func(existing_capex)
        return [totex, penalty]
    else:
        return [float("inf"), float("inf")]

problem = Problem(len(nwke.pipes), 2 , 0) # (Decisions variables, objectives, constraints)
problem.types[:] = Integer(0, len(available_diameters)-1)
problem.constraints[:] = ">=0"
problem.function = Min_Cost_GA
problem.directions[:] = Problem.MINIMIZE
log_archive = LoggingArchive()
algorithm = NSGAII(problem, population_size=50, archive=log_archive)
algorithm.run(generations)

# Plot the results
# Manual
plt.scatter(existing_totex, existing_penalties, 20, 'r', 'd')

# # All dominated solutions
# non_dominated_soln = pickle.load(open('nds.obj', 'rb'))
# algorithm = pickle.load(open('algo.obj', 'rb'))
non_dominated_soln = nondominated(algorithm.result)
dominated_soln = [s for s in algorithm.archive.log if s not in non_dominated_soln]
costs = [s.objectives[0] for s in dominated_soln]
h_penalties = [s.objectives[1] for s in dominated_soln]
plt.scatter(costs, h_penalties, color='k', alpha=0.2)

# Pareto
pareto_costs = [s.objectives[0] for s in non_dominated_soln]
pareto_h_penalties = [s.objectives[1] for s in non_dominated_soln]
plt.scatter(pareto_costs, pareto_h_penalties, s=50, color='g', marker='x')

plt.gca().set_yticklabels(['${:,.0f}'.format(x) for x in plt.gca().get_yticks()])
plt.gca().set_xticklabels(['${:,.0f}'.format(x) for x in plt.gca().get_xticks()])
plt.title(f'Pareto Front {generations} gens')
plt.xlabel('Cost ($)')
plt.ylabel('Hydraulic Penalties ($)')
plt.legend(['Manual', 'Trialed solutions', 'Pareto front solutions'])
end_time = time.time()

# import pickle
# pickle.dump(non_dominated_soln, open('nds.obj', 'wb'))
# pickle.dump(algorithm, open('algo.obj', 'wb'))
from sklearn.cluster import KMeans
import numpy as np
kmeans = KMeans(n_clusters=3)
kmeans.fit(np.array(pareto_h_penalties).reshape(-1, 1))
plt.plot([pareto_costs[i] for i, g in enumerate(kmeans.labels_) if g == 0],
         [pareto_h_penalties[i] for i, g in enumerate(kmeans.labels_) if g == 0], 'r.')
plt.plot([pareto_costs[i] for i, g in enumerate(kmeans.labels_) if g == 1],
         [pareto_h_penalties[i] for i, g in enumerate(kmeans.labels_) if g == 1], 'b.')
plt.plot([pareto_costs[i] for i, g in enumerate(kmeans.labels_) if g == 2],
         [pareto_h_penalties[i] for i, g in enumerate(kmeans.labels_) if g == 2], 'm.')

# Results

for cluster in set(kmeans.labels_):
    cluster_solutions = [i for i, g in enumerate(kmeans.labels_) if g == cluster]
    print(len(cluster_solutions))
    for sol_idx in cluster_solutions:
        diameters_result = [available_diameters[indexer] for indexer in
        [problem.types[0].decode(binary_result) for binary_result in non_dominated_soln[sol_idx].variables]]

        network_cost_result = non_dominated_soln[sol_idx].objectives[0]

    # print('The Nondominated Solution has the following decision variables:')
    # # for pipe, diameter in enumerate(diameters_result):
    # #     print(f'Pipe {pipe} diameter = {diameter}mm')
    # print(f'\nThe total annual expenditure for this network configuration is ${network_cost_result:,.2f}')
    # print(f'\nExecution time = {(end_time - start_time)/60:.2f} minutes')

        # Creating the Optimised network
        for idx, pipe in enumerate(nwke.pipes):
            nwke.wn.get_link(pipe).diameter = diameters_result[idx]/1000
        nwke.export_inp(f'non-dominated solutions\\Cl_{cluster}_S_{sol_idx}__C_{round(pareto_costs[sol_idx], 2)}_HL_{round(pareto_h_penalties[sol_idx], 2)}.inp')

# This code exports the final population to the csv for further inspection in MS excel 
results_dict = {f'Pipe_{pipe}_diameters': [available_diameters[indexer] for indexer in 
                [problem.types[0].decode(binary_result) for binary_result in 
                [solution.variables[idx] for solution in algorithm.result]]] for idx, pipe in enumerate(nwke.pipes)}

results_dict['objectives'] = [solution.objectives[0] for solution in algorithm.result]

results_df = pd.DataFrame.from_dict(results_dict).to_csv(f'NSGA_Pipe_Diameter_{generations}.csv')