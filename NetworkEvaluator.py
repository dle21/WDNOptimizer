import wntr
import pandas as pd
import math

class NetworkEvaluator:

    def __init__(self, input_network, input_sheet=None) -> None:
        self.wn = wntr.network.WaterNetworkModel(input_network)
        
        # Setting global energy options
        if input_sheet is not None:
            self.input_sheet = input_sheet
            self._get_cost_basis()
            self.wn.options.energy.global_efficiency = 75.0
            self.wn.options.energy.global_price = self.opex.loc[self.opex['Variable'] == 'Energy Price', 'Value'].values[0]/(3.6*10**6) #converting € 0.15 per kWh into €  per joules 
            self.wn.options.energy.global_pattern = None
        
        self.junctions = self.wn.junction_name_list
        self.pipes = self.wn.pipe_name_list
        self.tanks = self.wn.tank_name_list
        self.reservoirs = self.wn.reservoir_name_list
        self.valves = self.wn.valve_name_list
        self.pumps = self.wn.pump_name_list

        self.original_results = None
        self.run_sim()
    
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
        #Running Sim and collecting network info
        sim = wntr.sim.EpanetSimulator(self.wn)
        try:
            self.results = sim.run_sim()
            self.pressure_results = self.results.node['pressure']
            self.head_results = self.results.node['head']
            self.flowrate_results = self.results.link['flowrate']
            self.headloss_results = self.results.link['headloss'][self.pipes]
            return True
        except Exception as error:
            self.export_inp('Failed_run.inp')
            print(f'EPANET did not run: {error}')
            return False

    def capex(self):
        # PIPES
        pipe_dict = {
            "Pipe_Name": self.pipes,
            "Size": [self.wn.get_link(pipe).diameter * 1000 for pipe in self.pipes],
            "Pipe_Length\n(m)": [self.wn.get_link(pipe).length for pipe in self.pipes],
        }
        
        pipe_df = pd.DataFrame.from_dict(pipe_dict)
        self.pipecosts = self.pipecosts.sort_values(by='Size')
        pipe_df = pipe_df.sort_values(by="Size")
        self.pipe_df = pd.merge_asof(pipe_df, self.pipecosts, left_on="Size", right_on="Size", direction="nearest")
        self.pipe_df['Total Cost\n($ USD)'] = self.pipe_df['PS4 - TDC $/m'] * self.pipe_df['Pipe_Length\n(m)']
        total_pipe_inv_cost = self.pipe_df["Total Cost\n($ USD)"].sum()
        
        #PUMPS
        pump_df = pd.DataFrame.from_dict({'Capacity (l/s)': [self.wn.get_link(pump).get_design_flow() * 1000 / 2 for pump in self.pumps]})
        self.pump_cost = self.pump_cost.sort_values(by='Capacity (l/s)')
        pump_df = pump_df.sort_values(by="Capacity (l/s)")
        pump_df = pd.merge_asof(pump_df, self.pump_cost, left_on="Capacity (l/s)", right_on="Capacity (l/s)", direction="nearest")
        # TODO remove /2
        total_pump_inv_cost = pump_df["TPC $/Item"].sum() / 2
        
        #VALVES
        total_valve_inv_cost = sum([(1000.0 + 30 * (self.wn.get_link(valve).diameter * 1000)) for valve in self.valves])
        
        #TANKS
        total_tank_inv_cost = sum([300_000 + 150 * math.pi * self.wn.get_node(tank).diameter ** 2 / 4 * self.wn.get_node(tank).max_level for tank in self.tanks])
        
        return [total_pipe_inv_cost, total_pump_inv_cost, total_valve_inv_cost, total_tank_inv_cost]
    
    def proposed_capex(self, old_pipes):
        # PIPES
        pipe_dict = {
            "Pipe_Name": self.pipes,
            "Size": [self.wn.get_link(pipe).diameter * 1000 for pipe in self.pipes],
            "Pipe_Length\n(m)": [self.wn.get_link(pipe).length for pipe in self.pipes],
        }
        
        pipe_df = pd.DataFrame.from_dict(pipe_dict)
        self.pipecosts = self.pipecosts.sort_values(by='Size')
        pipe_df = pipe_df.sort_values(by="Size")
        self.pipe_df = pd.merge_asof(pipe_df, self.pipecosts, left_on="Size", right_on="Size", direction="nearest")
        self.pipe_df['Total Cost\n($ USD)'] = self.pipe_df['PS4 - TDC $/m'] * self.pipe_df['Pipe_Length\n(m)']
        # total_pipe_inv_cost = self.pipe_df["Total Cost\n($ USD)"].sum()
        merged_df = self.pipe_df.merge(old_pipes, on='Pipe_Name', how='left', suffixes=('_Proposed', '_Existing'))
        total_pipe_inv_cost = merged_df[(merged_df['Size_Proposed'] - merged_df['Size_Existing']).round(1) != 0.0]['Total Cost\n($ USD)_Proposed'].sum()
        #PUMPS
        pump_df = pd.DataFrame.from_dict({'Capacity (l/s)': [self.wn.get_link(pump).get_design_flow() * 1000 / 2 for pump in self.pumps]})
        self.pump_cost = self.pump_cost.sort_values(by='Capacity (l/s)')
        pump_df = pump_df.sort_values(by="Capacity (l/s)")
        pump_df = pd.merge_asof(pump_df, self.pump_cost, left_on="Capacity (l/s)", right_on="Capacity (l/s)", direction="nearest")
        # TODO remove /2
        total_pump_inv_cost = pump_df["TPC $/Item"].sum() / 2
        
        #VALVES
        total_valve_inv_cost = sum([(1000.0 + 30 * (self.wn.get_link(valve).diameter * 1000)) for valve in self.valves])
        
        #TANKS
        total_tank_inv_cost = sum([300_000 + 150 * math.pi * self.wn.get_node(tank).diameter ** 2 / 4 * self.wn.get_node(tank).max_level for tank in self.tanks])
        return [total_pipe_inv_cost, total_pump_inv_cost, total_valve_inv_cost, total_tank_inv_cost]

    def totex_func(self, old_pipes=None):
        if old_pipes is not None:
            total_pipe_inv_cost, total_pump_inv_cost, total_valve_inv_cost, total_tank_inv_cost = self.proposed_capex(old_pipes)
        else:
            total_pipe_inv_cost, total_pump_inv_cost, total_valve_inv_cost, total_tank_inv_cost = self.capex()
        inv_cost = total_pipe_inv_cost + total_pump_inv_cost + total_valve_inv_cost + total_tank_inv_cost
        
        #OPERATIONAL COST
        # Energy Calculations
        pump_flowrate = self.flowrate_results.loc[:, self.wn.pump_name_list]
        pump_energy = wntr.metrics.pump_energy(pump_flowrate, self.head_results, self.wn)
        pump_cost = wntr.metrics.pump_cost(pump_energy, self.wn)
        
        self.wn.options.time.hydraulic_timestep
        annual_pump_cost = pump_cost.sum().sum() * 365 * 86400 / self.wn.options.time.duration
        
        # OM Costs as percentage of CAPEX 
        total_OM =  annual_pump_cost + \
                    (self.capex()[0] * self.om.loc[self.om['Component'] == 'Pipes', 'Percentage of CAPEX '].values[0] + \
                    total_pump_inv_cost * self.om.loc[self.om['Component'] == 'Pump stations', 'Percentage of CAPEX '].values[0] + \
                    total_valve_inv_cost * self.om.loc[self.om['Component'] == 'Valves', 'Percentage of CAPEX '].values[0] + \
                    total_tank_inv_cost * self.om.loc[self.om['Component'] == 'Tanks', 'Percentage of CAPEX '].values[0])
        
        # Annuity
        n = self.opex.loc[self.opex['Variable'] == 'Payback period', 'Value'].values[0]
        r = self.opex.loc[self.opex['Variable'] == 'Annual Interest rate', 'Value'].values[0]
        annuity = (r*(1+r)**n)/((1+r)**n-1)*(total_pipe_inv_cost)
        
        # Total Annual Expenditure
        total_annual_expenditure = total_OM + annuity
        # print(annuity, annual_pump_cost, total_OM)
        return total_annual_expenditure, inv_cost
    
    def penalties(self, min_p_req, max_hl_req):
        # min_p = self.pressure_results.loc[:, self.incl_nodes].loc[:, [j for j in self.junctions if j in self.incl_nodes[self.incl_nodes]]].min()
        p_penalty = self.pressure_results.min()[self.pressure_results.min() < min_p_req].apply(lambda x: 400 if x < 0 else (min_p_req - x) * 20).sum()
        
        # min_hl = self.headloss_results.loc[:, [j for j in self.junctions if j in self.incl_nodes[self.incl_nodes]]].min()
        hl_penalty = ((self.headloss_results.max() * 1000 - max_hl_req) * 20).apply(lambda x: max(x, 0)).sum()

        # CUSTOM TYPES OF PENALTIES WITH OPTIONAL PARAMETERS
        # Override specific pipes (s) with additional cost or user-defined cost curve
        # Ignore certain pipes from the list and don't penalise them
        return p_penalty + hl_penalty
        
    # def min_p_func(self):
    #     min_p = self.pressure_results.loc[:, self.incl_nodes].loc[:, [j for j in self.junctions if j in self.incl_nodes[self.incl_nodes]]].min()
    #     return min_p
    
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