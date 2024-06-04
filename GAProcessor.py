import time
from NetworkEvaluator import NetworkEvaluator
from platypus import Problem, NSGAII, Integer, Archive, nondominated, Generator, Solution
import random
import pandas as pd
import pickle

import numpy as np
import glob
import os

class GAProcessor:
    def __init__(self, inp_file, cost_basis, proposed_inp_file=None) -> None:
        self.nwke = NetworkEvaluator(inp_file, cost_basis)
        self.proposed_inp_file = proposed_inp_file
        if self.proposed_inp_file is not None:
            self.nwk = NetworkEvaluator(proposed_inp_file, cost_basis)
        else:
            self.nwk = self.nwke

    def get_initial_costs(self, min_p, max_hl):
        self.nwke.totex_func()
        self.existing_totex, existing_capex = self.nwke.totex_func(self.nwke.pipe_df)
        self.existing_penalties = self.nwke.penalties(min_p, max_hl)
        print(f'\n\nOriginal network cost: ${self.existing_totex:,.2f}, Penalties: ${self.existing_penalties:,.2f}')
        available_diameters = self.nwke.pipecosts['Size'].unique()

        if self.proposed_inp_file is not None:
            self.manual_totex, manual_capex = self.nwk.totex_func(self.nwke.pipe_df)
            self.manual_penalties = self.nwk.penalties(min_p, max_hl)
            print(f'Manual network upgrade cost: ${self.manual_totex:,.2f}, Penalties: ${self.manual_penalties:,.2f}')
        self.available_diameters = self.nwk.pipecosts['Size'].unique()
        problem_type = Integer(0, len(available_diameters)-1)
        self.original_diameters = [problem_type.encode(np.where(available_diameters == round(self.nwk.wn.get_link(pipe).diameter * 1000, 0))[0][0]) for pipe in self.nwk.pipes]

    def run_GA(self, set_progress, gens, min_p, max_hl):
        self.set_progress = set_progress
        self.gens = gens
        self.min_p = min_p
        self.max_hl = max_hl
        self.run_no = 0
        start_time = time.time()

        self.problem = Problem(len(self.nwk.pipes), 2 , 0) # (Decisions variables, objectives, constraints)
        self.problem.types[:] = Integer(0, len(self.available_diameters)-1)
        self.problem.constraints[:] = ">=0"
        self.problem.function = self.Min_Cost_GA
        self.problem.directions[:] = Problem.MINIMIZE
        log_archive = LoggingArchive()
        self.algorithm = NSGAII(self.problem, population_size=50, generator=CustomGenerator(self.original_diameters), archive=log_archive)
        self.algorithm.run(gens)
        print(f'\nExecution time = {(time.time() - start_time)/60:.2f} minutes')
    
    def export_plot_results(self, output_obj):
        for file in [f for f in glob.glob('assets\\*') if not os.path.isdir(f) and not f == 'assets\\GHD1.PNG'] + glob.glob('assets\\non-dominated solutions\\*'):
            os.remove(file)
        # # All dominated solutions

        non_dominated_soln = nondominated(self.algorithm.result)
        dominated_soln = [s for s in self.algorithm.archive.log if s not in non_dominated_soln]
        costs = [s.objectives[0] for s in dominated_soln]
        h_penalties = [s.objectives[1] for s in dominated_soln]

        # Pareto
        pareto_costs = [s.objectives[0] for s in non_dominated_soln]
        pareto_h_penalties = [s.objectives[1] for s in non_dominated_soln]

        plotting_results_export = {
            'generations': self.gens,

            'costs': costs,
            'h_penalties': h_penalties,
            
            'pareto_costs': pareto_costs,
            'pareto_h_penalties': pareto_h_penalties,

            'manual_totex': self.manual_totex,
            'manual_penalties': self.manual_penalties,

            'existing_totex': self.existing_totex,
            'existing_penalties': self.existing_penalties,

            'xlim': [min(self.existing_totex, self.manual_totex, min(pareto_costs)) * 0.9, max(self.existing_totex, self.manual_totex, max(pareto_costs)) * 1.1],
            'ylim': [min(self.manual_penalties, self.existing_penalties, min(pareto_h_penalties)) * 0.9, max(self.manual_penalties, self.existing_penalties, max(pareto_h_penalties)) * 1.1],
        }
        if self.proposed_inp_file is not None:
            plotting_results_export['manual_totex'] = self.manual_totex
            plotting_results_export['manual_penalties'] = self.manual_penalties

        pickle.dump(plotting_results_export, open(output_obj, 'wb'))

        for sol_idx in range(len(non_dominated_soln)):
            output = f'assets\\non-dominated solutions\\C_{round(pareto_costs[sol_idx], 2)}_HP_{round(pareto_h_penalties[sol_idx], 2)}.inp'
            if not os.path.exists(output):
                diameters_result = [self.available_diameters[indexer] for indexer in
                [self.problem.types[0].decode(binary_result) for binary_result in non_dominated_soln[sol_idx].variables]]

                # Creating the Optimised network
                for idx, pipe in enumerate(self.nwk.pipes):
                    self.nwk.wn.get_link(pipe).diameter = diameters_result[idx]/1000

                self.nwk.export_inp(f'assets\\non-dominated solutions\\C_{round(pareto_costs[sol_idx], 2)}_HP_{round(pareto_h_penalties[sol_idx], 2)}.inp')
    
    def Min_Cost_GA(self, x):
        self.run_no += 1
        self.set_progress(['Running GA...', int(self.run_no / self.gens * 100), f'{int(self.run_no / self.gens * 100)} %'])
        indexers = {"indexer_%d"%idx: val for idx, val in enumerate(x[:])}
        for idx, pipe in enumerate(self.nwk.pipes):
            self.nwk.wn.get_link(pipe).diameter = self.available_diameters[indexers["indexer_%d"%idx]]/1000

        if x == self.original_diameters and not self.nwk.original_results is None:
            return self.nwk.original_results
        else:
            run_passed = self.nwk.run_sim()
            if run_passed:
                penalty = self.nwk.penalties(self.min_p, self.max_hl)
                totex, _ = self.nwk.totex_func(self.nwke.pipe_df)
                if x == self.original_diameters and self.nwk.original_results is None:
                    self.nwk.original_results = [totex, penalty]
                return [totex, penalty]
            else:
                return [float("inf"), float("inf")]


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
        if prop_random_p < 0 or prop_random_p > 1:
            raise ValueError("prop_random_p must be within the range [0, 1]")
        if prop_pop_random_p < 0 or prop_pop_random_p > 1:
            raise ValueError("prop_pop_random_p must be within the range [0, 1]")
        self.original_diameters = original_diameters
        self.prop_random_p = prop_random_p
        self.prop_pop_random_p = prop_pop_random_p

    def generate(self, problem):
        if len(self.original_diameters) != len(problem.types):
            raise ValueError("original list must have the same length as the number of variables in the problem")
        solution = Solution(problem)
        if random.random() < self.prop_random_p:
            solution.variables = [x.rand() if random.random() < self.prop_pop_random_p else self.original_diameters[i] for i, x in enumerate(problem.types)]
        else:
            solution.variables = self.original_diameters
        return solution
