from GAProcessor import *


ga = GAProcessor('cwsDP1150-112.inp', 'Optimisation_Cost_Basis.xlsx')
ga.get_initial_costs(20, 10)
ga.run_GA(lambda x: print(x), 50, 20, 10)
ga.export_plot_results('test.obj')

