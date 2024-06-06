from GAProcessor import *


ga = GAProcessor('TONGALA_Calibration_2022.inp', 'Optimisation_Cost_Basis.xlsx', 'test.inp')
ga.get_initial_costs(20, 10)
ga.run_GA(lambda x: print(x), 50, 20, 10)

