import wntr
import pandas as pd
import numpy as np
import math

class NetworkEvaluator:

    def __init__(self, input_network, input_sheet, min_p_req) -> None:
        self.input_sheet = input_sheet
        self.wn = wntr.network.WaterNetworkModel(input_network)

        self.junctions = self.wn.junction_name_list
        self.pipes = self.wn.pipe_name_list
        self.tanks = self.wn.tank_name_list
        self.reservoirs = self.wn.reservoir_name_list
        self.valves = self.wn.valve_name_list
        self.pumps = self.wn.pump_name_list

        self.min_p_req = min_p_req
        self._get_cost_basis()
        self.run_sim()
        self.incl_nodes = self.pressure_results.min() >= self.min_p_req
    
    def _get_cost_basis(self):
        self.pipecosts = pd.read_excel(self.input_sheet, sheet_name='Pipes')
        self.pipecosts['Size'] = self.pipecosts['Size'].astype(float)
        self.pump_cost = pd.read_excel(self.input_sheet, sheet_name='Pumps', skiprows=1)
        self.pump_cost['Capacity (l/s)'] = self.pump_cost['Capacity (l/s)'].astype(float)
        self.valve_cost = pd.read_excel(self.input_sheet, sheet_name='Valves')
        self.tank_cost = pd.read_excel(self.input_sheet, sheet_name='Tanks')
        self.om = pd.read_excel(self.input_sheet, sheet_name='Maintenance', skiprows=1)
        self.opex = pd.read_excel(self.input_sheet, sheet_name='Opex', skiprows=1)

    def run_sim(self):
        # Setting global energy options
        self.wn.options.energy.global_efficiency = 75.0
        self.wn.options.energy.global_price = self.opex.loc[self.opex['Variable'] == 'Energy Price', 'Value'].values[0]/(3.6*10**6) #converting € 0.15 per kWh into €  per joules 
        self.wn.options.energy.global_pattern = None 
        
        #Running Sim and collecting network info
        sim = wntr.sim.EpanetSimulator(self.wn)
        try:
            self.results = sim.run_sim()

            self.pressure_results = self.results.node['pressure']
            self.head_results = self.results.node['head']
            self.flowrate_results = self.results.link['flowrate']
            return True
        except Exception as error:
            self.export_inp('Failed_run.inp')
            print(f'EPANET did not run: {error}')
            # exit()
            return False

    def total_annual_expenditure_func(self):
        
        # PIPES
        pipe_dict = {
            "Pipe_Name": self.pipes,
            "Size": [self.wn.get_link(pipe).diameter * 1000 for pipe in self.pipes],
            "Pipe_Length\n(m)": [self.wn.get_link(pipe).length for pipe in self.pipes],
        }
        
        pipe_df = pd.DataFrame.from_dict(pipe_dict)
        self.pipecosts = self.pipecosts.sort_values(by='Size')
        pipe_df = pipe_df.sort_values(by="Size")
        pipe_df = pd.merge_asof(pipe_df, self.pipecosts, left_on="Size", right_on="Size", direction="nearest")
        pipe_df['Total Cost\n($ USD)'] = pipe_df['PS4 - TDC $/m'] * pipe_df['Pipe_Length\n(m)']
        total_pipe_inv_cost = pipe_df["Total Cost\n($ USD)"].sum()
        
        #PUMPS
        pump_df = pd.DataFrame.from_dict({'Capacity (l/s)': [self.wn.get_link(pump).get_design_flow() * 1000 / 2 for pump in self.pumps]})
        self.pump_cost = self.pump_cost.sort_values(by='Capacity (l/s)')
        pump_df = pump_df.sort_values(by="Capacity (l/s)")
        pump_df = pd.merge_asof(pump_df, self.pump_cost, left_on="Capacity (l/s)", right_on="Capacity (l/s)", direction="nearest")
        # TODO remove /2
        total_pump_inv_cost = pump_df["TPC $/Item"].sum() / 2
        
        #VALVES
        total_valve_inv_cost = sum([(1000.0 + 30* (self.wn.get_link(valve).diameter * 1000)) for valve in self.valves])
        
        #TANKS
        total_tank_inv_cost = sum([300_000 + 150 * math.pi * self.wn.get_node(tank).diameter ** 2 / 4 * self.wn.get_node(tank).max_level for tank in self.tanks])
        
        #TOTAL INVESTMENT COST
        grand_total_inv_cost = total_pipe_inv_cost + total_pump_inv_cost + total_valve_inv_cost + total_tank_inv_cost
        
        #OPERATIONAL COST
        # Energy Calculations
        pump_flowrate = self.flowrate_results.loc[:, self.wn.pump_name_list]
        pump_energy = wntr.metrics.pump_energy(pump_flowrate, self.head_results, self.wn)
        pump_cost = wntr.metrics.pump_cost(pump_energy, self.wn)
        
        annual_pump_cost = pump_cost[0:24].sum().sum()*3600*365
        
        # OM Costs as percentage of CAPEX 
        total_OM = (total_pipe_inv_cost * self.om.loc[self.om['Component'] == 'Pipes', 'Percentage of CAPEX '].values[0] + \
                    total_pump_inv_cost * self.om.loc[self.om['Component'] == 'Pump stations', 'Percentage of CAPEX '].values[0] + \
                    total_tank_inv_cost * self.om.loc[self.om['Component'] == 'Tanks', 'Percentage of CAPEX '].values[0])
        
        # Annuity
        n = self.opex.loc[self.opex['Variable'] == 'Payback period', 'Value'].values[0]
        r = self.opex.loc[self.opex['Variable'] == 'Annual Interest rate', 'Value'].values[0]
        annuity = (r/100*(1+r/100)**n)/((1+r/100)**n-1)*grand_total_inv_cost
        
        #Total Annual Expenditure
        total_annual_expenditure = annual_pump_cost + total_OM + annuity
        print(f'Annual pump cost: {annual_pump_cost}, total OM: {total_OM}, annuity: {annuity}')
        return total_annual_expenditure
    
    def min_p_func(self):
        min_p = self.pressure_results.loc[:, self.incl_nodes].loc[:, [j for j in self.junctions if j in self.incl_nodes[self.incl_nodes]]].min().min()
        return min_p
    
    def todini_func(self, Pstar):
        flowrate = self.flowrate_results.loc[:, self.wn.pump_name_list]
        
        todini_results = wntr.metrics.hydraulic.todini_index(self.head_results, self.pressure_results, self.results.node['demand'], 
                                                             flowrate, self.wn, Pstar) 
        todini_min = todini_results.min()
        
        return todini_min

    def export_inp(self, fname):
        inp_f = wntr.epanet.io.InpFile()
        inp_f.write(fname, self.wn)
        print(f'Network exported to {fname}')