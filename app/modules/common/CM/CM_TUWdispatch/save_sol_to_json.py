# -*- coding: utf-8 -*-
"""
Created on Tue Sep 26 11:52:51 2017

@author: root
"""

import os
import json
import numpy as np
import pandas as pd
import copy
import pyomo.environ as pe
from pathlib import Path
path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.
                                                       abspath(__file__))))
#%%
path2solution = os.path.join(path, "AD", "F16_input", "Solution")

def save_sol_to_json (instance,results,inv_flag,path2solution = path2solution):
    unit_dict = {   
            'Anual Investment Cost': 'EUR',
            'Anual Investment Cost (of existing heat storages)': 'EUR',
            'Anual Investment Cost (of existing power plants and heat storages)': 'EUR',
            'Anual Investment Cost (of existing power plants)': 'EUR',
            'Anual Investment Cost Heat Storage': 'EUR',
            'Anual Investment Cost:': 'EUR',
            'Anual Total Costs': 'EUR',
            'Anual Total Costs (with costs of existing power plants and heat storages)': 'EUR',
            'Anual Total Costs (with costs of existing power plants)': 'EUR',
            'CO2 Emission Electricity': 'kg CO2',
            'CO2 Emission Heat': 'kg CO2',
            'CO2 Emission Heat Storages': 'kg CO2',
            'Coldstart Costs': 'EUR',
            'Coldstart Costs:': 'EUR',
            "Coldstart Costs Heat Storages": "EUR",
            'Coldstart Count': '-',
            'Electrical Consumption of Heatpumps and Power to Heat devices': 'MWh',
            'Electrical Peak Load Costs': 'EUR',
            'Electricity Price': 'EUR/MWh',
            'Electricity Production by CHP': 'MWh',
            'Fuel Costs': 'EUR',
            'Fuel Costs Heat Storages': 'EUR',
            'Fuel Costs:': 'EUR',
            'Full Load Hours': 'h',
            'Full Load Hours Heat Storage': 'h',
            'Full Load Hours:': 'h',
            'Grid Electricity Import': 'MWh',
            'PV Electricity Used': 'MWh',
            'PV Electricity Exported': 'MWh',
            'Hydro Electricity Used': 'MWh',
            'Hydro Electricity Exported': 'MWh',
            'HS-Capacities': 'MWh',
            'Heat Demand': 'MW',
            'Heat Price': 'EUR/MWh',
            'Heat Storage Technologies': '-',
            'Installed Capacities': 'MW',
            'Installed Capacities Heat Storages': 'MW',
            'Installed Capacities:': 'MW',
            'LCOH': 'EUR/MWh',
            'LCOH Heat Storage': 'EUR/MWh',
            'LCOH:': 'EUR/MWh',
            'Loading Heat Storage': 'MW',
            'MC': 'EUR/MWh',
            'Marginal Costs': 'EUR/MWh',
            'Marginal Costs:': 'EUR/MWh',
            'Maximum Electrical Load of Heatpumps and Power to Heat devices': 'MW',
            'Mean Value Heat Price': 'EUR/MWh',
            'Mean Value Heat Price (with costs of existing power plants and heat storages)': 'EUR/MWh',
            'Mean Value Heat Price (with costs of existing power plants)': 'EUR/MWh',
            'Median Value Heat Price': 'EUR/MWh',
            'Operation Hours': 'h',
            'Operational Cost': 'EUR',
            'Operational Cost of Heat Storages': 'EUR',
            'Operational Cost:': 'EUR',
            'Ramping Costs': 'EUR',
            "Ramping Costs Heat Storages":"EUR",
            "Ramping Costs:":"EUR",
            'Renewable Share': '-',
            'Revenue From Electricity': 'EUR',
            'Revenue From Electricity:': 'EUR',
            'Revenue from Heat Storages': 'EUR',
            'Seasonal Performance Factor': '-',
            'Specific Capital Costs of Installed Capacities:': 'EUR/MW',
            'Specific Capital Costs of installed Capacities': 'EUR/MW',
            'Specific Capital Costs of installed Heat Storages': 'EUR/MWh',
            'State of Charge': 'MWh',
            'Technologies': '-',
            'Technologies:': '-',
            'Thermal Generation Mix': 'MWh',
            'Thermal Generation Mix:': 'MWh',
            'Thermal Power Energymix': 'MW',
            'Thermal Power Energymix:': 'MW',
            'Thermal Production by CHP': 'MWh',
            'Total CO2 Emission': 'kg CO2',
            'Total CO2 Emission:': 'kg CO2',
            'Total CO2 Emissions': 'kg CO2',
            'Turn Over Rate': '-',
            'Turn Over Rate Heat Storages': '-',
            'Turn Over Rate:': '-',
            'Unloading Heat Storage': 'MW',
            'Unloading Heat Storage over year': 'MW',
            "Variable Cost CHP's": 'EUR',
            'all_heat_geneartors': '-',
            'efficiency': '-',
            "theoretical efficiency":"-",
            "restricted theoretical efficiency":"-",
            'model_Coldstarts': '-',
            "CO2 Costs:":'EUR',
            "CO2 Costs":'EUR',
            "CO2 Costs Heat Storages":"EUR",
            "Total Fuel Costs":"EUR",
            "Total CO2 Costs":"EUR",
            "Total Operational Costs":"EUR",
            "Total Investment Costs":"EUR",
            "Total Thermal Generation":"MWh",
            "Total Electricty Consumption":"MWh",
            "Source Temperature River":"°C",
            "Source Temperature Waset Water": "°C",
            "Flow Temperature":"°C",
            "Return Temperature": "°C",
            "Ambient Temperature": "°C",
            "Radiation": "W/m²",
            "Total Heat Demand":"MWh",
            "max thermal efficiency":"-",
            "Final Energy":"MWh",
            "Final Energy Mix":"MWh",
            "Total Final Energy":"MWh",
            "Total Coldstart Costs":"EUR",
            "Total Ramping Costs":"EUR",
            "Total Investment Costs (of new build plants and heat storages)":"EUR",
            "Total Investment Costs of (of existing power plants and heat storages)":"EUR",
            "Total Costs":"EUR",
            "Total Revenue From Electricity":"EUR",
            "Total LCOH":"EUR/MWh",
            "Peak Load":"MW",
            "Total Cost":"EUR",
            "Total Cost Heat Storage":"EUR",
            "Total Cost:":"EUR",
            "CO2 Price": "EUR/tC02",
            "emission factor": "tCO2/MWh",
            "emission factor heat storages": "tCO2/MWh",
            "emission factor:":"tCO2/MWh",
            "Final Energy Mix By Energy Carrier":"MWh",
            'Total CO2 Emission: By Energy Carrier': 'kg CO2',
            'PV Investment Cost': 'EUR',
            'Refurbishment Cost': 'EUR',
            'Hydro Self-Consumption Rate': '%',
            'Hydro Export Rate': '%',
            'PV Export Rate': '%',
            'PV Self-Consumption Rate': '%',
            'Energy Saved with Refurbishment': 'MWh',
            'PV Export Revenue': 'EUR',
            'Hydro Export Revenue': 'EUR',
            'CHP Revenue': 'EUR',
            'PV O&M Cost': 'EUR'
            }
    try:
#        if os.path.isdir(path2solution) ==False:
#            print("Create Solution Dictionary")
#            os.mkdir(path2solution)
        print("Saving Solver Output ....")



        rev_tot={}

        
        c_inv_stock = {j:instance.x_th_cap_j[j] * instance.IK_j[j] * instance.alpha_j[j] for j in instance.j}
        c_ramp = {j:sum( instance.ramp_jt[j,t]() * instance.c_ramp_j[j] for t in instance.t) for j in instance.j} 
        
        rev_tot = {j:sum(instance.x_el_jt[j,t]()*instance.sale_electricity_price_jt[j,t] for t in instance.t) for j in instance.j}
        
        # Additional revenue from PV exports (hydro treated as grid electricity, no export revenue)
        rev_pv_export = 0.0
        
        if hasattr(instance, 'pv_export_t'):
            if hasattr(instance, 'pv_export_price_t'):
                rev_pv_export = sum(instance.pv_export_t[t]() * instance.pv_export_price_t[t] for t in instance.t)
            else:
                # Fallback to 70% of electricity price (matching optimization code)
                try:
                    _x = list(instance.j_bp)[0] 
                except:
                    _x = list(instance.j)[0]
                rev_pv_export = sum(instance.pv_export_t[t]() * (instance.electricity_price_jt[_x,t] * 0.7) for t in instance.t)

        #FIXME: for modeling reasons this cost are not real costs
#        c_hs_penalty_load = sum([instance.x_load_hs_t[hs,t]()*5e-2  for hs in instance.j_hs for t in instance.t])      # for modeling reasons
#        c_hs_penalty_unload = sum([instance.x_unload_hs_t[hs,t]()*5e-2  for hs in instance.j_hs for t in instance.t])  # for modeling reasons
#        c_hs = c_hs_penalty_load + c_hs_penalty_unload
        c_tot_inv = instance.cost() + sum ([c_inv_stock[j]  for j in instance.j])# - c_hs

        j_hp_new = [j for j in instance.j_hp_new]
        
        solution={ "Thermal Power Energymix":{j:[instance.x_th_jt[(j,t)]() for t in instance.t] for j in instance.j},
                  "Installed Capacities": {j:instance.Cap_j[j]()  for j in instance.j},
                  "Heat Price": [results.solution(0).constraint["genearation_covers_demand_t["+str(t)+"]"]["Dual"] for t in instance.t],
                    # "Heat Price": [results.solution(0).constraint.get(f"genearation_covers_demand_t[{t}]", {}).get("Dual", 0)
                    # if f"genearation_covers_demand_t[{t}]" in results.solution(0).constraint
                    # else 0
                    #     for t in instance.t],
                  "Electricity Production by CHP" : sum([instance.x_el_jt[(j,t)]() for j in instance.j_chp for t in instance.t]),
                  "Thermal Production by CHP" : sum([instance.x_th_jt[(j,t)]() for j in instance.j_chp for t in instance.t]),
                  "Electrical Consumption of Heatpumps and Power to Heat devices" : {
                                       **{j:sum([instance.x_th_jt[(j,t)]() / instance.n_th_jt[j,t] for t in instance.t])for j in instance.j_hp },
                                       **{j:sum([instance.x_th_jt[(j,t)]() / instance.n_th_jt[j,t] for t in instance.t])for j in instance.j_air_heat_pump},
                                       **{j:sum([instance.x_th_jt[(j,t)]() / instance.n_th_jt[j,t] for t in instance.t])for j in instance.j_river_heat_pump},
                                       **{j:sum([instance.x_th_jt[(j,t)]() / instance.n_th_jt[j,t] for t in instance.t])for j in instance.j_wastewater_heat_pump },
                                       **{j:sum([instance.x_th_jt[(j,t)]() / instance.n_th_jt[j,t] for t in instance.t])for j in instance.j_wasteheat_heat_pump },
                                       **{j:sum([instance.x_th_jt[(j,t)]() / instance.n_th_jt[j,t] for t in instance.t])for j in instance.j_pth }},
                  "Maximum Electrical Load of Heatpumps and Power to Heat devices" : \
                                       max([max(np.array([instance.x_th_jt[(j,t)]() / instance.n_th_jt[j,t] for j in instance.j_hp for t in instance.t]),default=0),
                                            max(np.array([instance.x_th_jt[(j,t)]() / instance.n_th_jt[j,t] for j in instance.j_air_heat_pump for t in instance.t]),default=0),
                                            max(np.array([instance.x_th_jt[(j,t)]() / instance.n_th_jt[j,t] for j in instance.j_river_heat_pump for t in instance.t]),default=0),
                                            max(np.array([instance.x_th_jt[(j,t)]() / instance.n_th_jt[j,t] for j in instance.j_wastewater_heat_pump for t in instance.t]),default=0),
                                            max(np.array([instance.x_th_jt[(j,t)]() / instance.n_th_jt[j,t] for j in instance.j_wasteheat_heat_pump for t in instance.t]),default=0),
                                          max(np.array([instance.x_th_jt[(j,t)]() / instance.n_th_jt[j,t] for j in instance.j_pth for t in instance.t]),default=0)]),
                  "Thermal Generation Mix":{j:sum([instance.x_th_jt[(j,t)]() for t in instance.t]) for j in instance.j}
                  }
                  
        # Add electricity source breakdown if available
        if hasattr(instance, 'grid_import_t'):
            solution["Grid Electricity Import"] = {
                "Hourly": [instance.grid_import_t[t]() for t in instance.t],
                "Total": sum(instance.grid_import_t[t]() for t in instance.t)
            }
            
        if hasattr(instance, 'pv_used_t'):
            solution["PV Electricity Used"] = {
                "Hourly": [instance.pv_used_t[t]() for t in instance.t],
                "Total": sum(instance.pv_used_t[t]() for t in instance.t)
            }
            solution["PV Electricity Exported"] = {
                "Hourly": [instance.pv_export_t[t]() for t in instance.t],
                "Total": sum(instance.pv_export_t[t]() for t in instance.t)
            }
            
        if hasattr(instance, 'hydro_used_t'):
            solution["Hydro Electricity Used"] = {
                "Hourly": [instance.hydro_used_t[t]() for t in instance.t],
                "Total": sum(instance.hydro_used_t[t]() for t in instance.t)
            }

            # Hydro export totals (if variable exists)
            if hasattr(instance, 'hydro_export_t'):
                solution["Hydro Electricity Exported"] = {
                    "Hourly": [instance.hydro_export_t[t]() for t in instance.t],
                    "Total": sum(instance.hydro_export_t[t]() for t in instance.t)
                }

        # ------------------------------------------------------------------
        # Derive utilisation / export rates for hydro and PV
        # ------------------------------------------------------------------
        # PV metrics
        if hasattr(instance, 'pv_generation_t'):
            total_pv_gen = sum(instance.pv_generation_t[t]() for t in instance.t)
            pv_used_tot  = solution.get("PV Electricity Used", {}).get("Total", 0.0)
            pv_exp_tot   = solution.get("PV Electricity Exported", {}).get("Total", 0.0)
            if total_pv_gen > 0:
                solution["PV Self-Consumption Rate"] = 100 * pv_used_tot / total_pv_gen
                solution["PV Export Rate"] = 100 * pv_exp_tot  / total_pv_gen
            else:
                # Ensure keys exist for downstream plotting even when PV generation is zero
                solution["PV Self-Consumption Rate"] = 0.0
                solution["PV Export Rate"] = 0.0

        # Hydro metrics
        if hasattr(instance, 'hydro_excess_t'):
            total_hydro_avail = sum(instance.hydro_excess_t[t] for t in instance.t)
            hydro_used_tot = solution.get("Hydro Electricity Used", {}).get("Total", 0.0)
            hydro_exp_tot  = solution.get("Hydro Electricity Exported", {}).get("Total", 0.0)
            if total_hydro_avail > 0:
                solution["Hydro Self-Consumption Rate"] = 100 * hydro_used_tot / total_hydro_avail
                solution["Hydro Export Rate"]   = 100 * hydro_exp_tot / total_hydro_avail

        # Saved energy from refurbishment (space-heating reduction)
        if hasattr(instance, 'mwh_saved_total'):
            solution["Energy Saved with Refurbishment"] = pe.value(instance.mwh_saved_total) if 'pe' in globals() else instance.mwh_saved_total()

        solution["Final Energy"] = {j:[instance.x_th_jt[(j,t)]()/instance.n_th_jt[j,t] if instance.n_th_jt[j,t]>0 else 0 for t in instance.t] for j in instance.j}
        solution["Final Energy Mix"] = {j:sum(solution["Final Energy"][j]) for j in instance.j}
        solution["Total Final Energy"] = sum(solution["Final Energy Mix"].values())
        solution["efficiency"] = { j: [instance.n_th_jt[j,t]*instance.restriction_factor_jt[j,t] if instance.x_th_jt[j,t]()>0 else 0 for t in instance.t] for j in instance.j } 
        solution["max thermal efficiency"] = {j:max(solution["efficiency"][j]) for j in instance.j}
        
        # because for heat pumps cpacity is electric capacity 

        solution["Ramping Costs"] = c_ramp
        solution["model_Coldstarts"] = { j: sum([instance.coldstart_jt[j,t]() for t in instance.t]) for j in instance.j}
        solution["Coldstart Costs"] = { j: sum([instance.coldstart_jt[j,t]()*instance.c_coldstart_j[j] for t in instance.t]) for j in instance.j}    
                                
        solution["Revenue From Electricity"] = rev_tot
        # If a refurbishment scenario is active, use the reduced demand profile
        refurb_active = hasattr(instance, "include_refurb_cost") and (instance.include_refurb_cost() == 1)

        if refurb_active and hasattr(instance, "demand_th_reduced"):
            solution["Heat Demand"] = [instance.demand_th_reduced[t]() for t in instance.t]
        else:
            solution["Heat Demand"] = [instance.demand_th_t[t] for t in instance.t]

        solution["Total Heat Demand"] = sum(solution["Heat Demand"])
        solution["Peak Load"] = max(solution["Heat Demand"])
        try:
            _x = list(instance.j_bp)[0] 
        except:
            _x = list(instance.j)[0]
        solution["Electricity Price"] = [instance.electricity_price_jt[_x,t] for t in instance.t]
        solution["Mean Value Heat Price"] = np.mean(np.array(solution["Heat Price"]))
        solution["Mean Value Heat Price (with costs of existing power plants)"] =  c_tot_inv/sum([instance.demand_th_t[t] for t in instance.t])
        solution["Median Value Heat Price"] = np.median(np.array(solution["Heat Price"]))
        solution["Operational Cost"]= {j:(instance.Cap_j[j]() * instance.OP_fix_j[j] + sum(instance.x_th_jt[j,t]() * instance.OP_var_j[j]for t in instance.t))for j in instance.j}
        
        # Add PV O&M costs (matching optimization objective)
        pv_om_cost = 0.0
        if hasattr(instance, 'pv_capacity') and hasattr(instance, 'PV_om_fix'):
            pv_om_cost = instance.pv_capacity() * instance.PV_om_fix
        solution["Variable Cost CHP's"]= sum([instance.mc_jt[j,t] * instance.x_th_jt[j,t]() - instance.sale_electricity_price_jt[j,t] * instance.x_el_jt[j,t]() for j in instance.j_chp for t in instance.t])
        # ------------------------------------------------------------------
        # SIMPLIFIED APPROACH: Calculate costs consistently with optimization objective
        # mc_jt = fuel_cost + CO2_cost + excess_heat_cost, so we properly separate them
        # ------------------------------------------------------------------
        
        solution["Fuel Costs"] = {}
        
        for j in instance.j:
            if instance.ec_j[j] == "electricity":
                # For electricity: only PV is free, hydro and grid are charged
                if hasattr(instance, 'grid_import_t'):
                    fuel_cost = 0.0
                    for t in instance.t:
                        elec_need = instance.x_th_jt[j, t]() / instance.n_th_jt[j, t] if instance.n_th_jt[j, t] > 0 else 0.0
                        pv_used   = instance.pv_used_j_t[j, t]()    if hasattr(instance, 'pv_used_j_t')   else 0.0
                        # hydro_used is now treated as grid electricity (charged, not free)
                        grid_and_hydro_import = max(elec_need - pv_used, 0.0)
                        # Use fuel component of mc_jt (excluding CO2)
                        fuel_price = instance.mc_jt[j, t] - (instance.em_j[j] * instance.pco2 / instance.n_th_jt[j, t])
                        fuel_cost += grid_and_hydro_import * fuel_price
                    solution["Fuel Costs"][j] = fuel_cost
                else:
                    # Fallback: use fuel component only
                    solution["Fuel Costs"][j] = sum([(instance.mc_jt[j,t] - instance.em_j[j]*instance.pco2/instance.n_th_jt[j,t]) * instance.x_th_jt[j,t]() for t in instance.t])
            else:
                # For non-electricity: use fuel component of mc_jt
                solution["Fuel Costs"][j] = sum([(instance.mc_jt[j,t] - instance.em_j[j]*instance.pco2/instance.n_th_jt[j,t]) * instance.x_th_jt[j,t]() for t in instance.t])
        # ------------------------------------------------------------------

        solution["MC"] = {j:[instance.mc_jt[j,t] for t in instance.t] for j in instance.j}
        # Calculate CO2 costs consistently with fuel costs (only PV is emission-free)
        solution["CO2 Costs"] = {}
        for j in instance.j:
            if instance.ec_j[j] == "electricity":
                if hasattr(instance, 'grid_import_t'):
                    co2_cost = 0.0
                    for t in instance.t:
                        elec_need = instance.x_th_jt[j, t]() / instance.n_th_jt[j, t] if instance.n_th_jt[j, t] > 0 else 0.0
                        pv_used   = instance.pv_used_j_t[j, t]()    if hasattr(instance, 'pv_used_j_t')   else 0.0
                        # hydro_used is now treated as grid electricity (has emissions, not free)
                        grid_and_hydro_import = max(elec_need - pv_used, 0.0)
                        # CO2 cost for grid and hydro imports
                        co2_cost += grid_and_hydro_import * (instance.em_j[j] * instance.pco2 / instance.n_th_jt[j, t])
                    solution["CO2 Costs"][j] = co2_cost
                else:
                    # Fallback: standard calculation
                    solution["CO2 Costs"][j] = sum([(instance.em_j[j]*instance.pco2/instance.n_th_jt[j,t]) * instance.x_th_jt[j,t]() for t in instance.t])
            else:
                # For non-electricity: standard calculation
                solution["CO2 Costs"][j] = sum([(instance.em_j[j]*instance.pco2/instance.n_th_jt[j,t]) * instance.x_th_jt[j,t]() for t in instance.t])
        solution["CO2 Price"] = instance.pco2()
        solution["emission factor"] = {j:instance.em_j[j] for j in instance.j}
        solution["emission factor heat storages"] = {hs:0 for hs in instance.j_hs}
        solution["emission factor:"] = {**solution["emission factor"],**solution["emission factor heat storages"]} 

        #FIXME
        solution["Anual Total Costs"] = instance.cost()# - c_hs #Operational + Fuel + Ramping + el. Peakload-el. Revenues without Investmentcosts of existing Powerplants
        solution["Anual Total Costs (with costs of existing power plants)"] = c_tot_inv

        solution["Anual Investment Cost"] =  {j:0 for j in instance.j}
        solution["Anual Investment Cost Heat Storage"] = {hs:0 for hs in instance.j_hs}
        if inv_flag:
            solution["Anual Investment Cost"] = {j:(instance.Cap_j[j]() - instance.x_th_cap_j[j])  * instance.IK_j[j] * instance.alpha_j[j] for j in instance.j}
            solution["Anual Investment Cost Heat Storage"] = {hs:(instance.Cap_hs[hs]()-instance.cap_hs[hs])  * instance.IK_hs[hs] * instance.alpha_hs[hs] for hs in instance.j_hs}

        solution["Anual Investment Cost (of existing power plants)"] = c_inv_stock
        solution["Anual Investment Cost (of existing heat storages)"] = {hs:instance.cap_hs[hs] * instance.IK_hs[hs] * instance.alpha_hs[hs] for hs in instance.j_hs}
        solution["Anual Investment Cost (of existing power plants and heat storages)"]={**solution["Anual Investment Cost (of existing power plants)"],
                 **solution["Anual Investment Cost (of existing heat storages)"],
                 }
        solution["Anual Total Costs (with costs of existing power plants and heat storages)"] = \
            solution["Anual Total Costs (with costs of existing power plants)"] + \
            sum(solution["Anual Investment Cost (of existing heat storages)"].values())

        solution["Mean Value Heat Price (with costs of existing power plants and heat storages)"] = solution["Anual Total Costs (with costs of existing power plants and heat storages)"] / sum([instance.demand_th_t[t] for t in instance.t])
   
        solution["Electrical Peak Load Costs"] = 0#instance.P_el_max()*10000
        solution["Specific Capital Costs of installed Capacities"] = {j:instance.IK_j[j] * instance.alpha_j[j] for j in solution["Installed Capacities"].keys() if solution["Installed Capacities"][j] !=0 }
        solution["Technologies"] = [j for j in instance.j]
        solution["Marginal Costs"] = [np.mean([instance.mc_jt[j,t] for t in instance.t]) - instance.n_el_j[j]/np.mean([instance.n_th_jt[j,t] for t in instance.t]) *np.mean([instance.sale_electricity_price_jt[j,t] for t in instance.t]) if j in instance.j_chp else np.mean([instance.mc_jt[j,t] for t in instance.t]) for j in instance.j]
        for i,val in enumerate(instance.j):
            if val in instance.j_chp:
                solution["Marginal Costs"][i] = solution["Marginal Costs"][i] - instance.n_el_j[val]/np.mean([instance.n_th_jt[val,t] for t in instance.t])*np.mean([instance.sale_electricity_price_jt[val,t] for t in instance.t])
        solution["State of Charge"] = {hs:[instance.store_level_hs_t[hs,t]() for t in instance.t] for hs in instance.j_hs}

        solution["HS-Capacities"] = {hs:instance.Cap_hs[hs]() if instance.Cap_hs[hs]() != None else instance.cap_hs[hs] for hs in instance.j_hs }

        solution["Unloading Heat Storage"] =  {hs:[instance.x_load_hs_t[hs,t]()*(-1) if (instance.x_load_hs_t[hs,t]() < 0) else 0.0 for t in instance.t] for hs in instance.j_hs}
        solution["Loading Heat Storage"] =  {hs:[instance.x_load_hs_t[hs,t]() if (instance.x_load_hs_t[hs,t]() >=0) else 0.0 for t in instance.t] for hs in instance.j_hs}
        # pyomo 5.7 ".value" is depracated
        try:
            solution["Heat Storage Technologies"] = list(instance.j_hs.data())
        except:
            print("#*100")
            solution["Heat Storage Technologies"] = list(instance.j_hs.value)
        solution["Unloading Heat Storage over year"] =  {hs:sum([instance.x_load_hs_t[hs,t]()*(-1) if (instance.x_load_hs_t[hs,t]() < 0) else 0.0 for t in instance.t]) for hs in instance.j_hs}
        solution["Revenue from Heat Storages"]  = {hs:0 for hs in instance.j_hs}
        solution["Operational Cost of Heat Storages"]= {hs:solution["HS-Capacities"][hs] * instance.OP_fix_hs[hs] for hs in instance.j_hs }
        solution["Specific Capital Costs of installed Heat Storages"] = {hs:instance.IK_hs[hs] * instance.alpha_hs[hs] for hs in solution["HS-Capacities"].keys() if solution["HS-Capacities"][hs] !=0 }
        solution["Fuel Costs Heat Storages"] = {hs:0 for hs in instance.j_hs}
        solution["CO2 Costs Heat Storages"] = {hs:0 for hs in instance.j_hs}
        # solution["Installed Capacities Heat Storages"] = {hs:instance.unload_cap_hs[hs] if solution["HS-Capacities"][hs]>0 else 0 for hs in instance.j_hs  }
        solution["Installed Capacities Heat Storages"] = {hs:max(max(solution["Unloading Heat Storage"][hs]),max(solution["Loading Heat Storage"][hs])) if solution["HS-Capacities"][hs]>0 else 0 for hs in instance.j_hs  }
        solution["Turn Over Rate Heat Storages"] = {hs: solution["Unloading Heat Storage over year"][hs]  / solution["HS-Capacities"][hs] if solution["HS-Capacities"][hs]>0 else "" for hs in instance.j_hs } 
        solution["Turn Over Rate"] = {j:0 for j in instance.j } 
        solution["Turn Over Rate:"] =  {**solution["Turn Over Rate"] ,**solution["Turn Over Rate Heat Storages"]}  
#XXX
        solution["Technologies:"] =  solution["Technologies"] + solution["Heat Storage Technologies"]

        solution["Thermal Power Energymix:"] = {**solution["Thermal Power Energymix"],
                                        **solution["Unloading Heat Storage"]}

        solution["Installed Capacities:"] ={**solution["Installed Capacities"],
                                        **solution["Installed Capacities Heat Storages"]}

        solution["Thermal Generation Mix:"] = {**solution["Thermal Generation Mix"],
                                        **solution["Unloading Heat Storage over year"]}

        solution["Marginal Costs:"] = solution["Marginal Costs"]+[1e100]*len(solution["Heat Storage Technologies"])

        solution["Anual Investment Cost:"] =  {**solution["Anual Investment Cost"],
        **solution["Anual Investment Cost Heat Storage"]}

        solution["Revenue From Electricity:"] = {**solution["Revenue From Electricity"],
                **solution["Revenue from Heat Storages"]}


    
        solution["Operational Cost:"] = {**solution["Operational Cost"],
                **solution["Operational Cost of Heat Storages"]}

        solution["Specific Capital Costs of Installed Capacities:"] = {**solution["Specific Capital Costs of installed Capacities"],
                **solution["Specific Capital Costs of installed Heat Storages"]}
        solution["Fuel Costs:"] = {**solution["Fuel Costs"],
                **solution["Fuel Costs Heat Storages"]}
        
        solution["CO2 Costs:"] = {**solution["CO2 Costs"], **solution["CO2 Costs Heat Storages"]}
        try:
            solution["all_heat_geneartors"] = list(instance.all_heat_geneartors.data())
        except:
            solution["all_heat_geneartors"] = list(instance.all_heat_geneartors.value)
        # CO2 Emissions
        solution["Total CO2 Emission"]= {j:1e3*solution["Final Energy Mix"][j]*instance.em_j[j] for j in instance.j} 
        solution["CO2 Emission Heat"] = {j: solution["Total CO2 Emission"][j]*np.mean([instance.n_th_jt[j,t] for t in instance.t])/(np.mean([instance.n_th_jt[j,t] for t in instance.t])+instance.n_el_j[j]) for j in instance.j} 
        solution["CO2 Emission Electricity"] = {j:solution["Total CO2 Emission"][j]*instance.n_el_j[j]/(np.mean([instance.n_th_jt[j,t] for t in instance.t])+instance.n_el_j[j]) for j in instance.j} 
        solution["CO2 Emission Heat Storages"] = {hs:0 for hs in instance.j_hs}
        solution["Total CO2 Emission:"]= {**solution["Total CO2 Emission"],**solution["CO2 Emission Heat Storages"]}
        solution["Total CO2 Emissions"] = sum(solution["Total CO2 Emission:"].values())
        
       
        # Full Load Hours
#        solution["Full Load Hours"] = {j:solution["Thermal Generation Mix"][j]/solution["Installed Capacities"][j] if solution["Installed Capacities"][j]!=0 else 0 for j in instance.j}
#        solution["Full Load Hours Heat Storage"] = {hs: solution["Unloading Heat Storage over year"][hs]/solution["Installed Capacities Heat Storages"][hs] if solution["Installed Capacities Heat Storages"][hs]!=0 else 0 for hs in instance.j_hs}
        solution["Operation Hours"] = { j: int(sum(np.array(solution["Thermal Power Energymix"][j])>0)) for j in instance.j} 
        solution["Full Load Hours"] = { j: int(solution["Thermal Generation Mix"][j] / solution["Installed Capacities"][j]) if solution["Installed Capacities"][j]>0 else 0 for j in instance.j } 
        #fix full load hours for heat pumps
        solution["Seasonal Performance Factor"] = { j: 0.0 for j in instance.j}
        solution["Coldstart Count"] = {}
   
        for j in instance.j:
            solution["Coldstart Count"][j] = 1
            for t in range(1,8759):
                 if(solution["Thermal Power Energymix"][j][t] == 0 and solution["Thermal Power Energymix"][j][t+1]  > 0):
                     solution["Coldstart Count"][j]+=1

        try:
            ecl = "Electrical Consumption of Heatpumps and Power to Heat devices"
            for j in instance.j_hp:
                _ecl = solution[ecl][j]
                solution["Seasonal Performance Factor"][j] = solution["Thermal Generation Mix"][j]/_ecl if _ecl else 0
                # solution["Full Load Hours"][j] = int(solution["Thermal Generation Mix"][j] / solution["Installed Capacities"][j] / solution["Seasonal Performance Factor"][j])  
    #            #only for Thesis Purpose, Works only with One HP per scenario
    #            solution["Seasonal Performance Factor of HP"] = solution["Seasonal Performance Factor"][j]
    #            solution["Full Load Hours of HP"] = solution["Full Load Hours"][j]
    #            solution["Operating Hours of HP"] = solution["Operation Hours"][j]
    #            solution["Coldstart Count of HP"] = solution["Coldstart Count"][j]
            for j in instance.j_air_heat_pump:
                _ecl = solution[ecl][j]
                solution["Seasonal Performance Factor"][j] = solution["Thermal Generation Mix"][j]/_ecl if _ecl else 0
                # solution["Full Load Hours"][j] = int(solution["Thermal Generation Mix"][j] / solution["Installed Capacities"][j] / solution["Seasonal Performance Factor"][j])  
           
            for j in instance.j_river_heat_pump:
                _ecl = solution[ecl][j]
                solution["Seasonal Performance Factor"][j] = solution["Thermal Generation Mix"][j]/_ecl if _ecl else 0
                # solution["Full Load Hours"][j] = int(solution["Thermal Generation Mix"][j] / solution["Installed Capacities"][j] / solution["Seasonal Performance Factor"][j])  
    
            for j in instance.j_wastewater_heat_pump:
                _ecl = solution[ecl][j]
                solution["Seasonal Performance Factor"][j] = solution["Thermal Generation Mix"][j]/_ecl if _ecl else 0
                # solution["Full Load Hours"][j] = int(solution["Thermal Generation Mix"][j] / solution["Installed Capacities"][j] / solution["Seasonal Performance Factor"][j])  
    
            for j in instance.j_wasteheat_heat_pump:
                _ecl = solution[ecl][j]
                solution["Seasonal Performance Factor"][j] = solution["Thermal Generation Mix"][j]/_ecl if _ecl else 0
                # solution["Full Load Hours"][j] = int(solution["Thermal Generation Mix"][j] / solution["Installed Capacities"][j] / solution["Seasonal Performance Factor"][j])  


        except:
            pass

       
        solution["Ramping Costs Heat Storages"] = {hs:0 for hs in instance.j_hs} 
        solution["Coldstart Costs Heat Storages"] = {hs:0 for hs in instance.j_hs}
        
        solution["Ramping Costs:"] = {**solution["Ramping Costs"],**solution["Ramping Costs Heat Storages"]}
        solution["Coldstart Costs:"] = {**solution["Coldstart Costs"],**solution["Coldstart Costs Heat Storages"]}     
        
        solution["Full Load Hours Heat Storage"] = {hs: int(sum(np.array(solution["Unloading Heat Storage"][hs])>0)) for hs in instance.j_hs} 
        solution["Full Load Hours:"] = {**solution["Full Load Hours"],**solution["Full Load Hours Heat Storage"]}
        solution["Total Cost"] = {j:solution["Anual Investment Cost"][j]+solution["Anual Investment Cost (of existing power plants)"][j]+solution["Operational Cost"][j]+solution["Fuel Costs"][j] + solution["CO2 Costs"][j] + solution["Ramping Costs"][j] + solution["Coldstart Costs"][j] for j in instance.j  } 
        solution["Total Cost Heat Storage"] =  {hs:solution["Anual Investment Cost Heat Storage"][hs]+solution["Anual Investment Cost (of existing heat storages)"][hs]+solution["Operational Cost of Heat Storages"][hs]+solution["Fuel Costs Heat Storages"][hs] + solution["CO2 Costs Heat Storages"][hs] +solution["Ramping Costs Heat Storages"][hs] + solution["Coldstart Costs Heat Storages"][hs] for hs in instance.j_hs  } 
        solution["Total Cost:"] = {**solution["Total Cost"],**solution["Total Cost Heat Storage"]}

        solution["LCOH"] =  {j:(solution["Total Cost"][j]-solution["Revenue From Electricity"][j])/solution["Thermal Generation Mix"][j] if solution["Thermal Generation Mix"][j]>0 else 0 for j in instance.j  } 
        solution["LCOH Heat Storage"] =  {hs:(solution["Total Cost Heat Storage"][hs]-solution["Revenue from Heat Storages"][hs])/solution["Unloading Heat Storage over year"][hs] if solution["Unloading Heat Storage over year"][hs]>0 else 0 for hs in instance.j_hs  } 
        solution["LCOH:"] = {**solution["LCOH"] ,**solution["LCOH Heat Storage"]} 
        solution["Renewable Share"] = 100*sum([sum([(instance.x_th_jt[j,t]()+instance.x_el_jt[j,t]()) for t in instance.t])*instance.rf_j[j] for j in instance.j]) / sum([sum([(instance.x_th_jt[j,t]()+instance.x_el_jt[j,t]()) for t in instance.t])for j in instance.j]) 
        solution["theoretical efficiency"] = { j: [instance.n_th_jt[j,t] for t in instance.t] for j in instance.j }         
        solution["restricted theoretical efficiency"] = { j: [instance.n_th_jt[j,t]*instance.restriction_factor_jt[j,t] for t in instance.t] for j in instance.j }         

# =============================================================================
#         only sum effective energy -> producton of solar thermal over  heat
#         demand is not shown in the Thermal Generation mix
# =============================================================================

        # matrix = pd.DataFrame(solution["Thermal Power Energymix:"]).values
        # sum_matrix = matrix.sum(1)
        # demand = solution["Heat Demand"]

        # dif = sum_matrix - demand
        # mask = sum_matrix > demand
        # reduce = mask*dif

        # _dic = copy.deepcopy(solution)
        # try:
        #     for j in instance.j_st:
        #         _dic["Thermal Power Energymix:"][j] = list(np.array(solution["Thermal Power Energymix:"][j]) - reduce)
        #         null = np.array(solution["Thermal Power Energymix:"][j])
        #         null *= null > 0
        #         _dic["Thermal Power Energymix:"][j] = list(null)
        #         solution["Thermal Generation Mix:"]  = pd.DataFrame(_dic["Thermal Power Energymix:"]).sum().to_dict()
        # except:
        #     pass
# =============================================================================

        solution["Total Electricty Consumption"] = sum(solution["Electrical Consumption of Heatpumps and Power to Heat devices"].values())
        
        solution["Total Coldstart Costs"]= sum(solution["Coldstart Costs:"].values())
        solution["Total Ramping Costs"] = sum(solution["Ramping Costs:"].values())
        solution["Total Operational Costs"] = sum(solution["Operational Cost:"].values()) + pv_om_cost
        solution["Total Fuel Costs"] = sum(solution["Fuel Costs:"].values())
        solution["Total CO2 Costs"] = sum(solution["CO2 Costs:"].values())
        # ------------------------------------------------------------------
        # Add PV investment and refurbishment cost (if any) to the investment
        # tally of NEW assets so that downstream totals capture them.
        # ------------------------------------------------------------------
        pv_inv_cost = 0.0
        if hasattr(instance, "pv_capacity"):
            pv_inv_cost = instance.pv_capacity() * instance.PV_invest_cost * instance.alpha_pv
            solution["PV Investment Cost"] = pv_inv_cost

        refurb_cost = 0.0
        if refurb_active and hasattr(instance, "refurbishment_cost"):
            refurb_cost = instance.refurbishment_cost()
        
        # Always include Refurbishment Cost in the solution, even if 0
        solution["Refurbishment Cost"] = refurb_cost

        solution["Total Investment Costs (of new build plants and heat storages)"] = \
            sum(solution["Anual Investment Cost:"].values()) + pv_inv_cost + refurb_cost

        solution["Total Investment Costs of (of existing power plants and heat storages)"] = sum(solution["Anual Investment Cost (of existing power plants and heat storages)"].values())

        solution["Total Costs"] = solution["Total Coldstart Costs"] +\
                                 solution["Total Ramping Costs"] +\
                                 solution["Total Operational Costs"] +\
                                 solution["Total Fuel Costs"] +\
                                solution["Total CO2 Costs"] +\
                                solution["Total Investment Costs (of new build plants and heat storages)"] +\
                                 solution["Total Investment Costs of (of existing power plants and heat storages)"]
                                 
        solution["Total Revenue From Electricity"] = sum(solution["Revenue From Electricity:"].values()) + rev_pv_export
        
        # Add detailed breakdown for transparency
        solution["PV Export Revenue"] = rev_pv_export
        solution["Hydro Export Revenue"] = 0.0  # Hydro treated as grid electricity, no export revenue
        solution["CHP Revenue"] = sum(solution["Revenue From Electricity:"].values())
        solution["PV O&M Cost"] = pv_om_cost
        
        solution["Total Thermal Generation"] = sum(solution["Thermal Generation Mix:"].values())
        
        solution["Total LCOH"] = (solution["Total Costs"] - solution["Total Revenue From Electricity"]) / solution["Total Heat Demand"]
        
        solution["Source Temperature River"] = [instance.temp_river[t] for t in instance.t]
        solution["Source Temperature Waset Water"] = [instance.temp_waste_water[t] for t in instance.t]
        solution["Flow Temperature"] = [instance.temp_flow[t] for t in instance.t]
        solution["Return Temperature"] = [instance.temp_return[t] for t in instance.t]
        solution["Ambient Temperature"] = [instance.temp_ambient[t] for t in instance.t]
        solution["Radiation"] = [instance.radiation[t] for t in instance.t]
         
        for key in ["Final Energy Mix","Total CO2 Emission:"]:
                add_energy_carrier_key(key,solution,instance)

#        solfile = os.path.join(path2solution, "solution.json")
#        with open(solfile, "w") as f:
#            json.dump(solution, f)
#        print("Done ! ,\nsaved to: <"+solfile+r"> ...")
        
        
        solution["unit"] = unit_dict
        
        print("Done !")

        return solution
    except Exception as e:
        print("Error in creating JSON")
        print(e)
        return "Error3#"
#%%
        # ------------------------------------------------------------------
        # Derive utilisation / export rates for hydro and PV
        # ------------------------------------------------------------------
        # PV metrics
        if hasattr(instance, 'pv_generation_t'):
            total_pv_gen = sum(instance.pv_generation_t[t]() for t in instance.t)
            pv_used_tot  = solution.get("PV Electricity Used", {}).get("Total", 0.0)
            pv_exp_tot   = solution.get("PV Electricity Exported", {}).get("Total", 0.0)
            if total_pv_gen > 0:
                solution["PV Self-Consumption Rate"] = 100 * pv_used_tot / total_pv_gen
                solution["PV Export Rate"] = 100 * pv_exp_tot  / total_pv_gen

        # Hydro metrics
        if hasattr(instance, 'hydro_excess_t'):
            total_hydro_avail = sum(instance.hydro_excess_t[t] for t in instance.t)
            hydro_used_tot = solution.get("Hydro Electricity Used", {}).get("Total", 0.0)
            hydro_exp_tot  = solution.get("Hydro Electricity Exported", {}).get("Total", 0.0)
            if total_hydro_avail > 0:
                solution["Hydro Self-Consumption Rate"] = 100 * hydro_used_tot / total_hydro_avail
                solution["Hydro Export Rate"]   = 100 * hydro_exp_tot / total_hydro_avail

        # Saved energy from refurbishment (space-heating reduction)
        if hasattr(instance, 'mwh_saved_total'):
            solution["Energy Saved with Refurbishment"] = pe.value(instance.mwh_saved_total) if 'pe' in globals() else instance.mwh_saved_total()

        return solution
    except Exception as e:
        print("Error in creating JSON")
        print(e)
        return "Error3#"
#%%
def json2xlsx(data,output_path,scenario_flag=False,tidy=False):

    json_data = copy.deepcopy(data)
    unit_dict = json_data.pop("unit")
    try:
#         TODO: find solution: when no heat storages hourly data for loading and unloading are stored in "Generator Data (single values)" (delete)
        # df5 = pd.DataFrame(json_data.pop("efficiency"))  
        y = [pd.DataFrame([val],columns=list(val),index=[key]).T for key,val in json_data.items() if type(val)==dict and bool(val)]
        anual_per_tec_values= dict()
        y_i = []
        for k,i in enumerate(y):
            if i[i.columns[0]].dtypes == object:
                key = f"{i.columns[0]} ({unit_dict[i.columns[0]].replace('/',' per ')})"
#                if scenario_flag:
#                    key = f"{i.columns[0]}" 
                anual_per_tec_values[key] = i[i.columns[0]].apply(pd.Series).T
            else:
                y_i.append(k)
        # Worksheet technology data
        y = [y[i] for i in y_i]
        df = y[0][:]
        for i in y[1:]:
            df = pd.concat([df,i],axis=1, sort = True)
        # Worksheet: anual data
        df2 = pd.DataFrame({key:val for key,val in json_data.items() if type(val)==list and len(val)==8760})
        # More Data
        df3 = pd.DataFrame([{key:val for key,val in json_data.items() if type(val)!=list and type(val)!=dict}],index=["value"]).T
        
#        if not scenario_flag:
        df.columns = df.columns.str.cat([f' [{unit_dict[x]}]' for x in df.columns])
        df2.columns = df2.columns.str.cat([f' [{unit_dict[x]}]' for x in df2.columns])
        df3.index = df3.index.str.cat([f' [{unit_dict[x]}]' for x in df3.index])
        
        dfs = {"Generator Data (single values)":df,
              "Anual Data":df2,
              "More Data":df3,
              **anual_per_tec_values,}
              # "efficiency":df5,}
        
        if scenario_flag:
            return dfs
        
        if tidy:
            out = dict()
            for sheetname,_data in tidy_disaptch_dataFrames(dfs).items():
                _path = Path(output_path)  
                _name,_ = _path.name.split(".")
                # _data.to_csv(_path.parent.joinpath(f"{_name}_{sheetname}.csv"))
                out[sheetname] = _data
                _data.to_excel(_path.parent.joinpath(f"{_name}_{sheetname}.xlsx"))
                
            return out
                
            
            
#              "Loading Heat Storage (MW)":df5,} # TODO: delete !, not needed ?
        # alichaudry from stackoverflow
        # https://stackoverflow.com/questions/17326973/is-there-a-way-to-auto-adjust-excel-column-widths-with-pandas-excelwriter/32679806#32679806
        writer = pd.ExcelWriter(output_path,engine='xlsxwriter')

        for sheetname, df in dfs.items():  # loop through `dict` of dataframes
            sheetname=sheetname.replace(":","")
            sheetname = sheetname[:31] # Excel worksheet name must be <= 31 chars
            df.to_excel(writer, sheet_name=sheetname)  # send df to writer
            worksheet = writer.sheets[sheetname]  # pull worksheet object
            for idx, col in enumerate(df):  # loop through all columns
                series = df[col]
                max_len = max((
                    series.astype(str).map(len).max(),  # len of largest item
                    len(str(series.name))  # len of column name/header
                    )) + 1  # adding a little extra space
                worksheet.set_column(idx, idx, max_len)  # set column width
        writer.save()
        print("JSON to EXCEL Done")
#        print("Saved to"+output_path)
        
    except Exception as e:
        print(e)
        print("Error @ json2xlsx")
#%%
def tidyDF(df,index_name,topic_name):
    return df.reset_index().rename(columns={"index":index_name[0]}).melt(id_vars=index_name,var_name=topic_name,value_name="value")
    
def tidy_disaptch_dataFrames(dfs):
    z= dict()
    for sheet,df in dfs.items():
        if sheet == "Anual Data":
            # continue
            new_name = "Data (hourly values)"
            z[new_name] = tidyDF(df,["time"],"topic")
        elif sheet == "Generator Data (single values)":
            z[sheet] = tidyDF(df,["heat generator"],"topic") 
        elif sheet == "More Data":
            new_name = "Data (single values)"
            z[new_name] = df.reset_index().rename(columns={"index":"topic"})
        else:
            # continue
            new_name = "Generator Data (hourly values)"
            df["topic"] = sheet
            z[new_name] = pd.concat([z.get(new_name,pd.DataFrame()),tidyDF(df,["time","topic"],"heat generator")])
    return z

def scenarioJson2xlsx(scneario_mapper,solutions,output_path):
    print("Creating Scenario Excel File...")
    data = {}
    out = dict()
#    writer = pd.ExcelWriter(output_path,engine='xlsxwriter')
    print("Tidying scenario data...")
    l = sum(len(x) for _,x in scneario_mapper.items())
    i=0    
    for sc,sub_sc_list in scneario_mapper.items():
        for sub_sc in sub_sc_list:
            i +=1
            print(f"{i}/{l}...{sc}:{sub_sc}") 
            x = solutions[sc][sub_sc] 
            if x != None:
                dfs=json2xlsx(x,"",scenario_flag=True)
                dfs = tidy_disaptch_dataFrames(dfs)
                for sheet,df in dfs.items():
                    data[sheet] = {**data.get(sheet,{}), **{(sc,sub_sc):df}}
    print("Merging scenarios...")  # TODO: costly operation...
    for sheetname,_data in data.items():
        if sheetname in ["Generator Data (hourly values)","Data (hourly values)"]:
            continue
        print(f"{sheetname}....",end="")
        sheetname = sheetname[:31] # Excel worksheet name must be <= 31 chars
        df = pd.concat(_data)
        df.index.names = ["Scenario","Sub Scenario","ID"]  
        df = df.reorder_levels(["ID","Scenario","Sub Scenario"])
        df = df.droplevel("ID")
        out[sheetname] = df
        # df.to_csv(Path(output_path).joinpath(f"{sheetname}.csv"))
        df.to_excel(Path(output_path).joinpath(f"{sheetname}.xlsx"),merge_cells=False)
        print("Done")

# =============================================================================
#         Large Excel File Creation takes a lot of time, switch to csv files (8 min)
#         Thus commetn row 477 and 498 - 507
# =============================================================================
#        df.to_excel(writer, sheet_name=sheetname,merge_cells=False)  # send df to writer
#        worksheet = writer.sheets[sheetname]  # pull worksheet object
#        for idx, col in enumerate(df):  # loop through all columns
#            series = df[col]
#            max_len = max((
#                series.astype(str).map(len).max(),  # len of largest item
#                len(str(series.name))  # len of column name/header
#                )) + 1  # adding a little extra space
#            worksheet.set_column(idx, idx, max_len)  # set column width
#    writer.save()
    
    print("Creating Scenario Excel File Done")       

    return out

def add_energy_carrier_key(key,solution,instance):
    key_new = f"{key} By Energy Carrier"
    solution[key_new] = dict()
    for j in instance.j:
        solution[key_new][instance.ec_j[j]] = solution[key_new].get(instance.ec_j[j],0) + solution[key][j]
    solution[key_new] = {i:v for i,v in solution[key_new].items()}
    return None
