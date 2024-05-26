import time
from NetworkEvaluator import NetworkEvaluator
from platypus import Problem, NSGAII, Integer, Archive, nondominated, Generator, Solution
import random
import pandas as pd
import matplotlib.pyplot as plt
import pickle

from sklearn.cluster import KMeans
import numpy as np

class LoggingArchive(Archive):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, *kwargs)
        self.log = []
    
    def add(self, solution):
        super().add(solution)
        self.log.append(solution)

class CustomGenerator(Generator):
    def __init__(self, original_diameters, prop_random_p=0.2, prop_pop_random_p=0.2):
        super().__init__()
        self.original_diameters = original_diameters
        self.prop_random_p = prop_random_p
        self.prop_pop_random_p = prop_pop_random_p

    def generate(self, problem):
        solution = Solution(problem)
        if random.random() < self.prop_random_p:
            solution.variables = [x.rand() if random.random() < self.prop_pop_random_p else self.original_diameters[i] for i, x in enumerate(problem.types)]
        else:
            solution.variables = self.original_diameters
        return solution


start_time = time.time()

inp_file = 'TONGALA_Calibration_2022.inp'
input_sheet = 'Optimisation_Cost_Basis.xlsx'
min_p_req = 20
max_hl_req = 10
generations = 10000

# fig = plt.figure()
nwke = NetworkEvaluator(inp_file, input_sheet)
nwke.totex_func()
existing_totex, existing_capex = nwke.totex_func(nwke.pipe_df)
existing_penalties = nwke.penalties(min_p_req, max_hl_req)
print()
print()
print(f'\n\nOriginal network cost: ${existing_totex:,.2f}, Penalties: ${existing_penalties:,.2f}')
available_diameters = nwke.pipecosts['Size'].unique()

inp_file = 'OPTION_2___TONGALA_Masterplanning_2043_Horizon__1.inp'
nwkp = NetworkEvaluator(inp_file, input_sheet)
manual_totex, manual_capex = nwkp.totex_func(nwke.pipe_df)
manual_penalties = nwkp.penalties(min_p_req, max_hl_req)
print(f'Manual network upgrade cost: ${manual_totex:,.2f}, Penalties: ${manual_penalties:,.2f}')
available_diameters = nwkp.pipecosts['Size'].unique()

problem_type = Integer(0, len(available_diameters)-1)
original_diameters = [problem_type.encode(np.where(available_diameters == round(nwkp.wn.get_link(pipe).diameter * 1000, 0))[0][0]) for pipe in nwkp.pipes]

print("GA optimisation in process…")

def Min_Cost_GA(x):

    indexers = {"indexer_%d"%idx: val for idx, val in enumerate(x)}
    for idx, pipe in enumerate(nwkp.pipes):
        nwkp.wn.get_link(pipe).diameter = available_diameters[indexers["indexer_%d"%idx]]/1000

    if x == original_diameters and not nwkp.original_results is None:
        return nwkp.original_results
    else:
        run_passed = nwkp.run_sim()
        if run_passed:
            penalty = nwkp.penalties(min_p_req, max_hl_req)
            totex, _ = nwkp.totex_func(nwke.pipe_df)
            if x == original_diameters and nwkp.original_results is None:
                nwkp.original_results = [totex, penalty]
            return [totex, penalty]
        else:
            return [float("inf"), float("inf")]

problem = Problem(len(nwkp.pipes), 2 , 0) # (Decisions variables, objectives, constraints)
problem.types[:] = Integer(0, len(available_diameters)-1)
problem.constraints[:] = ">=0"
problem.function = Min_Cost_GA
problem.directions[:] = Problem.MINIMIZE
log_archive = LoggingArchive()
# algorithm = NSGAII(problem, population_size=50, generator=CustomGenerator(original_diameters), archive=log_archive)
# algorithm.run(generations)

# Plot the results
# # All dominated solutions
non_dominated_soln = pickle.load(open('nds.obj', 'rb'))
algorithm = pickle.load(open('algo.obj', 'rb'))

non_dominated_soln = nondominated(algorithm.result)
dominated_soln = [s for s in algorithm.archive.log if s not in non_dominated_soln]
costs = [s.objectives[0] for s in dominated_soln]
h_penalties = [s.objectives[1] for s in dominated_soln]
plt.scatter(costs, h_penalties, color='k', alpha=0.2)

# Pareto
pareto_costs = [s.objectives[0] for s in non_dominated_soln]
pareto_h_penalties = [s.objectives[1] for s in non_dominated_soln]
plt.scatter(pareto_costs, pareto_h_penalties, s=50, color='g', marker='x')
# Manual
plt.scatter(manual_totex, manual_penalties, 20, 'r', 'd')
plt.scatter(nwke.totex_func(nwke.pipe_df)[0], existing_penalties, 20, 'b', 'd')
plt.title(f'Pareto Front {generations} gens')

all_solutions = pd.DataFrame({'cost': [s.objectives[0] for s in algorithm.archive.log], 'h_penalties': [s.objectives[1] for s in algorithm.archive.log]})

xlim_df = all_solutions[(abs((all_solutions - all_solutions.mean()) / all_solutions.std())['cost'] < 5)]['cost']
ylim_df = all_solutions[(abs((all_solutions - all_solutions.mean()) / all_solutions.std())['h_penalties'] < 0.2)]['h_penalties']

# plt.xlim([min(existing_totex, manual_totex, xlim_df.min()), max(existing_totex, manual_totex, xlim_df.max())])
plt.xlim([min(existing_totex, manual_totex, xlim_df.min()), max(existing_totex, manual_totex, xlim_df.max())])
plt.ylim([ylim_df.min(), ylim_df.max()])
plt.yticks(plt.gca().get_yticks(), labels=['${:,.0f}'.format(x) for x in plt.gca().get_yticks()])
plt.xticks(plt.gca().get_xticks(), labels=['${:,.0f}'.format(x) for x in plt.gca().get_xticks()])
plt.xlabel('Cost ($)')
plt.ylabel('Hydraulic Penalties ($)')
plt.legend(['Trialed solutions', 'Pareto front solutions', 'Manual', 'Do Nothing'])
plt.savefig('Pareto_curve.jpg')
end_time = time.time()
print(f'\nExecution time = {(end_time - start_time)/60:.2f} minutes')
plt.show()
print()
import pickle
pickle.dump(non_dominated_soln, open('nds.obj', 'wb'))
pickle.dump(algorithm, open('algo.obj', 'wb'))
kmeans = KMeans(n_clusters=4)
kmeans.fit(np.array(pareto_h_penalties).reshape(-1, 1))

# # Results
# for cluster in set(kmeans.labels_):
#     cluster_solutions = [i for i, g in enumerate(kmeans.labels_) if g == cluster]
#     print(len(cluster_solutions))
#     for sol_idx in cluster_solutions:
#         diameters_result = [available_diameters[indexer] for indexer in
#         [problem.types[0].decode(binary_result) for binary_result in non_dominated_soln[sol_idx].variables]]
#         network_cost_result = non_dominated_soln[sol_idx].objectives[0]

#         # Creating the Optimised network
#         for idx, pipe in enumerate(nwkp.pipes):
#             nwkp.wn.get_link(pipe).diameter = diameters_result[idx]/1000
#         nwkp.export_inp(f'non-dominated solutions\\C_{round(pareto_costs[sol_idx], 2)}_HL_{round(pareto_h_penalties[sol_idx], 2)}_Cl_{cluster}_S_{sol_idx}.inp')

# # This code exports the final population to the csv for further inspection in MS excel 
# results_dict = {f'Pipe_{pipe}_diameters': [available_diameters[indexer] for indexer in 
#                 [problem.types[0].decode(binary_result) for binary_result in 
#                 [solution.variables[idx] for solution in algorithm.result]]] for idx, pipe in enumerate(nwke.pipes)}

# results_dict['objectives'] = [solution.objectives[0] for solution in algorithm.result]

# results_df = pd.DataFrame.from_dict(results_dict).to_csv(f'NSGA_Pipe_Diameter_{generations}.csv')