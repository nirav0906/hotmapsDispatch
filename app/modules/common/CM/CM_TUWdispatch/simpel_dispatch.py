# -*- coding: utf-8 -*-
"""
Created on Tue Sep 26 11:52:51 2017
changed on Tue Aug 20 2024 (nirav) - added the ped specific constraints
changes on Tue Jan 07 2025 (nirav) - added the dynamic pef values
changes on Tue Jan 22 2025 (nirav) - added the PV generation and usage constraints
changes on Tue Jan 28 2025 (nirav) - added PV electricity usage allocation for heat pumps and electric boilers
changes on Tue Feb 05 2025 (nirav) - added hydro power excess generation and usage
changes on Wed Apr 20 2025 (nirav) - added the renovation constraints

@author: Nirav

CLEANED VERSION - Core optimization functionality only
Analysis functions moved to separate analysis module
"""

import pyomo.environ as pe
from datetime import datetime
from pyomo.opt import SolverStatus, TerminationCondition
import os
import sys
import pandas as pd
import numpy as np

path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if path not in sys.path:
    sys.path.append(path)
from CM.CM_TUWdispatch.preprocessing import preprocessing
from CM.CM_TUWdispatch.analysis_functions import check_pv_usage, check_hydro_usage, check_grid_usage, generate_dispatch_data

# PED Configuration
SELECTED_PED = "kranj"  # Options: "kranj" (Slovenia) or "schoenbrunn" (Germany)

def get_ped_config(ped_name):
    """Get configuration for the selected PED pilot"""
    configs = {
        "kranj": {
            "name": "Kranj - Slovenia",
            "excel_file": "C:\\Users\\Nirav\\OneDrive - TU Wien\\Desktop\\PED_SupplyOptimization\\hotmapsDispatch\\app\\modules\\common\\CM\\CM_TUWdispatch\\Slovenia_hourly_generation_2024.xlsx"
        },
        "schoenbrunn": {
            "name": "Schönbrunn - Germany", 
            "excel_file": "C:\\Users\\Nirav\\OneDrive - TU Wien\\Desktop\\PED_SupplyOptimization\\hotmapsDispatch\\app\\modules\\common\\CM\\CM_TUWdispatch\\Germany_hourly_generation_2024.xlsx"
        }
    }
    
    if ped_name not in configs:
        raise ValueError(f"PED '{ped_name}' not found. Available PEDs: {list(configs.keys())}")
    
    return configs[ped_name]

def run(data, inv_flag, selection=[[],[]], demand_f=1, ped_mode="dynamic", ped_balance_horizon="yearly", debug_objective=True, force_no_refurb=False):
    """
    Main optimization function for PED energy system dispatch
    
    Parameters:
    -----------
    data : dict
        Input data for the optimization
    inv_flag : bool
        Investment flag - whether to allow new investments
    selection : list
        Selection criteria for technologies
    demand_f : float
        Demand factor (default: 1)
    ped_mode : str
        PED mode - "static", "dynamic", or "refurb" (default: "dynamic")
    ped_balance_horizon : str
        Balance horizon - "yearly", "seasonal", or "daily" (default: "yearly")
    debug_objective : bool
        Whether to print detailed objective breakdown (default: True)
    force_no_refurb : bool
        Force no refurbishment in refurb mode (default: False)
        
    Returns:
    --------
    tuple
        (instance, results) if successful, (error_code, message) if failed
    """
    
    #%% Creation of a Model
    m = pe.AbstractModel()

    #%% Sets - TODO: depends on how the input data looks finally
    val, message = preprocessing(data, demand_f, inv_flag, selection)
    
    if val == "Error1":
        return (val, message)
    elif val == "Error2":
        return (val, message)

    # Define seasonal sets if needed
    if ped_balance_horizon == 'seasonal':
        def get_season(hour_of_year_1_indexed):
            day_of_year = (hour_of_year_1_indexed - 1) // 24
            date = datetime(2023, 1, 1).date() + pd.Timedelta(days=day_of_year)
            month = date.month
            if month in [12, 1, 2]:
                return 'winter'
            elif month in [3, 4, 5]:
                return 'spring'
            elif month in [6, 7, 8]:
                return 'summer'
            else: # 9, 10, 11
                return 'autumn'

        all_hours = list(range(1, 8761))
        winter_hours = [t for t in all_hours if get_season(t) == 'winter']
        spring_hours = [t for t in all_hours if get_season(t) == 'spring']
        summer_hours = [t for t in all_hours if get_season(t) == 'summer']
        autumn_hours = [t for t in all_hours if get_season(t) == 'autumn']
        
        m.winter_hours = pe.Set(initialize=winter_hours)
        m.spring_hours = pe.Set(initialize=spring_hours)
        m.summer_hours = pe.Set(initialize=summer_hours)
        m.autumn_hours = pe.Set(initialize=autumn_hours)
    
    elif ped_balance_horizon == 'daily':
        m.days = pe.RangeSet(1, 365)

    # Initialize sets
    m.j_hp_new = pe.Set(initialize=val["j_hp_new"])
    m.t = pe.RangeSet(1, 8760)
    m.j = pe.Set(initialize=val["j"])
    m.j_hp = pe.Set(initialize=val["j_hp"])
    m.j_pth = pe.Set(initialize=val["j_pth"])
    m.j_st = pe.Set(initialize=val["j_st"])
    m.j_waste = pe.Set(initialize=val["j_waste"])
    m.j_chp = pe.Set(initialize=val["j_chp"])
    m.j_bp = pe.Set(initialize=val["j_bp"])
    m.j_wh = pe.Set(initialize=val["j_wh"])
    m.j_gt = pe.Set(initialize=val["j_gt"])
    m.j_hs = pe.Set(initialize=val["j_hs"])
    m.j_air_heat_pump = pe.Set(initialize=val["j_air_heat_pump"])
    m.j_river_heat_pump = pe.Set(initialize=val["j_river_heat_pump"])
    m.j_wastewater_heat_pump = pe.Set(initialize=val["j_wastewater_heat_pump"])
    m.j_wasteheat_heat_pump = pe.Set(initialize=val["j_wasteheat_heat_pump"])
    m.all_heat_geneartors = pe.Set(initialize=val["all_heat_geneartors"])

    #%% Parameters
    m.demand_th_t = pe.Param(m.t, initialize=val["demand_th_t"])
    m.temp_river = pe.Param(m.t, initialize=val["temp_river"])
    m.temp_waste_water = pe.Param(m.t, initialize=val["temp_waste_water"])
    m.temp_flow = pe.Param(m.t, initialize=val["temp_flow"])
    m.temp_return = pe.Param(m.t, initialize=val["temp_return"])
    m.temp_ambient = pe.Param(m.t, initialize=val["temp_ambient"])
    m.radiation = pe.Param(m.t, initialize=val["radiation"])
    
    max_demad = val["max_demad"]
    m.potential_j = pe.Param(m.j, initialize=val["potential_j"])
    m.pow_cap_j = pe.Param(m.j, initialize=val["pow_cap_j"])
    m.radiation_t = pe.Param(m.t, initialize=val["radiation_t"])
    m.IK_j = pe.Param(m.j, initialize=val["IK_j"])
    m.OP_fix_j = pe.Param(m.j, initialize=val["OP_fix_j"])
    m.n_el_j = pe.Param(m.j, initialize=val["n_el_j"])
    m.electricity_price_jt = pe.Param(m.j, m.t, initialize=val["electricity_price_jt"])
    m.P_min_el_chp = pe.Param(initialize=val["P_min_el_chp"])
    m.Q_min_th_chp = pe.Param(initialize=val["Q_min_th_chp"])
    m.ratioPMaxFW = pe.Param(initialize=val["ratioPMaxFW"])
    m.ratioPMax = pe.Param(initialize=val["ratioPMax"])
    m.mc_jt = pe.Param(m.j, m.t, initialize=val["mc_jt"])
    m.n_th_jt = pe.Param(m.j, m.t, initialize=val["n_th_jt"])
    m.hp_restriction_factor_jt = pe.Param(m.j, m.t, initialize=val["hp_restriction_factor_jt"])
    m.nom_p_th_j = pe.Param(m.j, initialize=val["nom_p_th_j"])
    m.min_p_th_j = pe.Param(m.j, initialize=val["min_p_th_j"])
    m.x_th_cap_j = pe.Param(m.j, initialize=val["x_th_cap_j"])
    m.lt_j = pe.Param(m.j, initialize=val["lt_j"])
    m.ec_j = pe.Param(m.j, initialize=val["ec_j"], within=pe.Any)
    renewable_carriers = ["wood pellets", "wood chips", "biomass", "straw", "radiation"]
    m.ir = pe.Param(initialize=val["ir"])
    m.alpha_j = pe.Param(m.j, initialize=val["alpha_j"])

    # Storage parameters
    m.load_cap_hs = pe.Param(m.j_hs, initialize=val["load_cap_hs"])
    m.unload_cap_hs = pe.Param(m.j_hs, initialize=val["unload_cap_hs"])
    m.n_hs = pe.Param(m.j_hs, initialize=val["n_hs"])
    m.loss_hs = pe.Param(m.j_hs, initialize=val["loss_hs"])
    m.IK_hs = pe.Param(m.j_hs, initialize=val["IK_hs"])
    m.cap_hs = pe.Param(m.j_hs, initialize=val["cap_hs"])
    m.c_ramp_j = pe.Param(m.j, initialize=val["c_ramp_j"]) 
    m.c_coldstart_j = pe.Param(m.j, initialize=val["c_coldstart_j"])
    m.alpha_hs = pe.Param(m.j_hs, initialize=val["alpha_hs"])

    m.rf_j = pe.Param(m.j, initialize=val["rf_j"])
    m.rf_tot = pe.Param(initialize=val["rf_tot"])
    m.OP_var_j = pe.Param(m.j, initialize=val["OP_var_j"])
    
    # Temperature parameter with error handling
    try:
        m.temperature_t = pe.Param(m.t, initialize=val["temperature_t"])
    except KeyError:
        print("Warning: temperature_t not found in data, using temperature instead")
        m.temperature_t = pe.Param(m.t, initialize=val["temperature"])
    
    m.sale_electricity_price_jt = pe.Param(m.j, m.t, initialize=val["sale_electricity_price_jt"])
    m.OP_fix_hs = pe.Param(m.j_hs, initialize=val["OP_fix_hs"])

    m.mr_j = pe.Param(m.j, initialize=val["mr_j"])
    m.em_j = pe.Param(m.j, initialize=val["em_j"])
    m.pco2 = pe.Param(initialize=val["pco2"])
    
    m.cap_losse_hs = pe.Param(m.j_hs, initialize=val["cap_losse_hs"])
    m.n_th_nom_jt = pe.Param(m.j, m.t, initialize=val["n_th_nom_jt"])
    m.restriction_factor_jt = pe.Param(m.j, m.t, initialize=val["restriction_factor_jt"])
    m.min_out_factor_j = pe.Param(m.j, initialize=val["min_out_factor_j"])

    #%% Load PED-specific data from Excel
    ped_config = get_ped_config(SELECTED_PED)
    excel_file = ped_config["excel_file"]
    
    print(f"Loading data for: {ped_config['name']}")
    print(f"Excel file: {excel_file}")
    
    if not os.path.exists(excel_file):
        raise FileNotFoundError(f"Excel file not found: {excel_file}")

    try:
        excel_data = pd.read_excel(excel_file, sheet_name=['PV', 'PEF_values', 'PED_status', 'PEF', 'Excess Hydro', 'Refurbishment'])
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        raise

    # Process PV parameters
    try:
        pv_df = excel_data['PV']
        pv_data = {}
        for i, row in pv_df.iterrows():
            key = row.iloc[0]
            value = row.iloc[1]
            pv_data[key] = value
        
        expected_keys = ['performance_ratio', 'area_available', 'panel_efficiency', 'invest_cost', 'alpha', 'om_fix', 'existing_capacity']
        missing_keys = [key for key in expected_keys if key not in pv_data]
        if missing_keys:
            raise KeyError(f"Missing required PV parameters: {missing_keys}")
        
        m.pv_performance_ratio = pe.Param(initialize=float(pv_data['performance_ratio']))
        m.pv_area_available = pe.Param(initialize=float(pv_data['area_available']))
        m.pv_efficiency = pe.Param(initialize=float(pv_data['panel_efficiency']), mutable=True)
        m.PV_invest_cost = pe.Param(initialize=float(pv_data['invest_cost']), within=pe.NonNegativeReals)
        m.alpha_pv = pe.Param(initialize=float(pv_data['alpha']), within=pe.NonNegativeReals)
        m.PV_om_fix = pe.Param(initialize=float(pv_data['om_fix']), within=pe.NonNegativeReals)
        m.pv_existing_capacity = pe.Param(initialize=float(pv_data['existing_capacity']), within=pe.NonNegativeReals)
        
    except Exception as e:
        print(f"Error processing PV data: {e}")
        raise

    # Process PEF values
    try:
        pef_df = excel_data['PEF_values']
        pef_data = {}
        for i, row in pef_df.iterrows():
            key = row.iloc[0]
            value = row.iloc[1]
            pef_data[key] = value

        expected_pef_keys = ['static_electricity_import', 'static_electricity_export', 'CHP_gas', 'fossil_fuel', 
                            'natural_gas', 'straw', 'various', 'waste', 'waste_heat_20', 'waste_heat_40',
                            'wood_chips', 'wood_pellets', 'radiation']
        missing_pef_keys = [key for key in expected_pef_keys if key not in pef_data]
        if missing_pef_keys:
            raise KeyError(f"Missing required PEF parameters: {missing_pef_keys}")

        m.pef_import_electricity = pe.Param(initialize=float(pef_data['static_electricity_import']))
        m.pef_export_electricity = pe.Param(initialize=float(pef_data['static_electricity_export']))
        m.pef_CHP_gas = pe.Param(initialize=float(pef_data['CHP_gas']))
        m.pef_fossil_fuel = pe.Param(initialize=float(pef_data['fossil_fuel']))
        m.pef_natural_gas = pe.Param(initialize=float(pef_data['natural_gas']))
        m.pef_straw = pe.Param(initialize=float(pef_data['straw']))
        m.pef_various = pe.Param(initialize=float(pef_data['various']))
        m.pef_waste = pe.Param(initialize=float(pef_data['waste']))
        m.pef_waste_heat_20 = pe.Param(initialize=float(pef_data['waste_heat_20']))
        m.pef_waste_heat_40 = pe.Param(initialize=float(pef_data['waste_heat_40']))
        m.pef_wood_chips = pe.Param(initialize=float(pef_data['wood_chips']))
        m.pef_wood_pellets = pe.Param(initialize=float(pef_data['wood_pellets']))
        m.pef_radiation = pe.Param(initialize=float(pef_data['radiation']))
        
    except Exception as e:
        print(f"Error processing PEF data: {e}")
        raise

    # Process PED status
    try:
        ped_df = excel_data['PED_status']
        PED_status = None
        
        if PED_status is None and 'PED_status' in ped_df.columns:
            for col in ped_df.columns:
                if col != 'PED_status':
                    try:
                        potential_value = float(col)
                        PED_status = potential_value
                        break
                    except (ValueError, TypeError):
                        continue
        
        if PED_status is not None:
            if 0 <= PED_status <= 1:
                print(f"PED_status successfully set to: {PED_status}")
            else:
                print(f"Warning: PED_status value {PED_status} is outside range [0,1], using default value of 1.0")
                PED_status = 1.0
        else:
            PED_status = 1.0
            print("Warning: Could not find valid PED_status value, using default value of 1.0")
            
    except Exception as e:
        print(f"Error processing PED_status: {e}")
        PED_status = 1.0

    # Process hourly PEF data
    try:
        pef_hourly_df = excel_data['PEF']
        if not {'Hour', 'pef_import', 'pef_export', 'El_cost'}.issubset(pef_hourly_df.columns):
            raise ValueError("The 'PEF' sheet must contain columns: 'Hour', 'pef_import', 'pef_export', 'El_cost'")

        pef_import_electricity_t = pef_hourly_df.set_index('Hour')['pef_import'].to_dict()
        pef_export_electricity_t = pef_hourly_df.set_index('Hour')['pef_export'].to_dict()
        El_cost_t = pef_hourly_df.set_index('Hour')['El_cost'].to_dict()
        
        Grid_cost_t = (pef_hourly_df.set_index('Hour')['Grid_cost'].to_dict() 
                      if 'Grid_cost' in pef_hourly_df.columns 
                      else El_cost_t)
        
        PV_export_price_t = (pef_hourly_df.set_index('Hour')['PV_export_price'].to_dict() 
                            if 'PV_export_price' in pef_hourly_df.columns 
                            else {t: El_cost_t[t] * 0.7 for t in El_cost_t})
        
        Hydro_export_price_t = (pef_hourly_df.set_index('Hour')['Hydro_export_price'].to_dict() 
                               if 'Hydro_export_price' in pef_hourly_df.columns 
                               else {t: El_cost_t[t] * 0.7 for t in El_cost_t})
        
        Hydro_cost_t = {t: 0 for t in El_cost_t}
        
    except Exception as e:
        print(f"Error processing hourly PEF data: {e}")
        raise

    # Process hydro excess data
    try:
        hydro_df = excel_data['Excess Hydro']
        if 'Excess Energy (MWh)' in hydro_df.columns:
            hydro_excess_t = hydro_df.set_index('Hour')['Excess Energy (MWh)'].to_dict()
        elif 'Excess Energy' in hydro_df.columns:
            hydro_excess_t = hydro_df.set_index('Hour')['Excess Energy'].to_dict()
        else:
            print("Warning: Neither 'Excess Energy (MWh)' nor 'Excess Energy' column found")
            hydro_excess_t = {t: 0 for t in range(1, 8761)}
        
        for t in range(1, 8761):
            if t not in hydro_excess_t:
                hydro_excess_t[t] = 0
            
    except Exception as e:
        print(f"Error processing hydro excess data: {e}")
        hydro_excess_t = {t: 0 for t in range(1, 8761)}

    # Add parameters to the model
    m.pef_import_electricity_t = pe.Param(m.t, initialize=pef_import_electricity_t, within=pe.Reals)
    m.pef_export_electricity_t = pe.Param(m.t, initialize=pef_export_electricity_t, within=pe.Reals)
    m.El_cost_t = pe.Param(m.t, initialize=El_cost_t, within=pe.Reals)
    m.hydro_excess_t = pe.Param(m.t, initialize=hydro_excess_t, within=pe.NonNegativeReals)
    m.grid_cost_t = pe.Param(m.t, initialize=Grid_cost_t, within=pe.Reals)
    m.hydro_cost_t = pe.Param(m.t, initialize=Hydro_cost_t, within=pe.Reals)
    m.pv_export_price_t = pe.Param(m.t, initialize=PV_export_price_t, within=pe.Reals)
    m.hydro_export_price_t = pe.Param(m.t, initialize=Hydro_export_price_t, within=pe.Reals)

    #%% Variables
    m.x_th_jt = pe.Var(m.j, m.t, within=pe.NonNegativeReals)
    m.Cap_j = pe.Var(m.j, within=pe.NonNegativeReals)
    m.x_el_jt = pe.Var(m.j, m.t, within=pe.NonNegativeReals)

    m.x_load_hs_t = pe.Var(m.j_hs, m.t, within=pe.Reals)
    m.Cap_hs = pe.Var(m.j_hs, within=pe.NonNegativeReals)
    m.store_level_hs_t = pe.Var(m.j_hs, m.t, within=pe.NonNegativeReals)

    m.ramp_jt = pe.Var(m.j, m.t, within=pe.NonNegativeReals) 
    m.coldstart_jt = pe.Var(m.j, m.t, within=pe.Boolean)
    m.Active_jt = pe.Var(m.j, m.t, within=pe.Boolean)

    # PED specific variables
    m.E_import = pe.Var(m.t, within=pe.NonNegativeReals)
    m.E_export = pe.Var(m.t, within=pe.NonNegativeReals)
    m.pv_new_capacity = pe.Var(within=pe.NonNegativeReals)  # New PV capacity to be installed
    m.pv_generation_t = pe.Var(m.t, within=pe.NonNegativeReals)
    m.pv_export_t = pe.Var(m.t, within=pe.NonNegativeReals)
    
    # PV and hydro electricity usage allocation
    m.pv_used_t = pe.Var(m.t, within=pe.NonNegativeReals)
    m.pv_used_j_t = pe.Var(m.j, m.t, within=pe.NonNegativeReals)
    
    m.hydro_used_t = pe.Var(m.t, within=pe.NonNegativeReals)
    m.hydro_used_j_t = pe.Var(m.j, m.t, within=pe.NonNegativeReals)
    m.hydro_export_t = pe.Var(m.t, within=pe.NonNegativeReals)
    
    m.grid_import_t = pe.Var(m.t, within=pe.NonNegativeReals)
    
    # Refurbishment parameters and variables
    if ped_mode in ["static", "dynamic"]:
        m.include_refurb_cost = pe.Param(initialize=0)
    elif ped_mode == "refurb":
        m.include_refurb_cost = pe.Param(initialize=1)

    space_heat_fraction = 0.80
    refurb_df = excel_data['Refurbishment']
    
    blocks_list = refurb_df['blocks'].dropna().astype(int).tolist()
    block_width_dict = {}
    cost_dict = {}
    
    for i, block_num in enumerate(blocks_list):
        if i < len(refurb_df):
            block_width_dict[block_num] = float(refurb_df['block_width_data'].iloc[i])
            cost_dict[block_num] = float(refurb_df['cost_data'].iloc[i])

    m.blocks = pe.Set(initialize=blocks_list)
    m.block_width = pe.Param(m.blocks, initialize=block_width_dict)
    m.block_cost = pe.Param(m.blocks, initialize=cost_dict)

    def block_bounds_rule(m, i):
        return (0, m.block_width[i])
    m.x_save_fraction = pe.Var(m.blocks, within=pe.NonNegativeReals, initialize=0, bounds=block_bounds_rule)

    def fraction_saved_rule(m):
        return sum(m.x_save_fraction[i] for i in m.blocks)
    m.fraction_saved = pe.Expression(rule=fraction_saved_rule)

    def space_heating_demand_original_rule(m):
        return sum(m.demand_th_t[t] for t in m.t) * space_heat_fraction
    m.space_heating_demand_original = pe.Expression(rule=space_heating_demand_original_rule)

    def mwh_saved_total_rule(m):
        return m.space_heating_demand_original * m.fraction_saved
    m.mwh_saved_total = pe.Expression(rule=mwh_saved_total_rule)

    def refurbishment_cost_rule(m):
        cost_sum = 0
        for i in m.blocks:
            frac_i = m.x_save_fraction[i]
            block_mwh = m.space_heating_demand_original * frac_i
            cost_sum += block_mwh * m.block_cost[i]
        return cost_sum
    m.refurbishment_cost = pe.Expression(rule=refurbishment_cost_rule)

    def demand_th_reduced_rule(m, t):
        space_portion = space_heat_fraction * m.demand_th_t[t]
        saved_t = m.fraction_saved * space_portion
        return m.demand_th_t[t] - saved_t
    m.demand_th_reduced = pe.Expression(m.t, rule=demand_th_reduced_rule)

    #%% Constraints
    
    # Potential restriction
    def potential_restriction_rule_j(m, j):
        if m.potential_j[j] > 0: 
            rule = sum(m.x_th_jt[j, t] for t in m.t) <= m.potential_j[j]
        else:
            rule = pe.Constraint.Skip
        return rule
    m.potential_restriction_rule = pe.Constraint(m.j, rule=potential_restriction_rule_j) 
    
    # Power restriction
    def power_restriction_jt_rule(m, j, t):
        if m.pow_cap_j[j] > 0:
            rule = m.x_th_jt[j, t] <= m.pow_cap_j[j]
        else:
            rule = pe.Constraint.Skip            
        return rule
    m.power_restriction_jt = pe.Constraint(m.j, m.t, rule=power_restriction_jt_rule)    

    # Electrical power generation
    def gen_el_jt_rule(m, j, t):
        if j not in m.j_chp or m.n_th_jt[j, t] != 0:
            return m.x_el_jt[j, t] == m.x_th_jt[j, t] / m.n_th_jt[j, t] * m.n_el_j[j]
        else:
            return pe.Constraint.Skip
    m.gen_el_jt = pe.Constraint(m.j, m.t, rule=gen_el_jt_rule)

    # Heat demand coverage
    if ped_mode == "refurb":
        def actual_demand_rule(m, t):
            return m.demand_th_reduced[t]
    else:
        def actual_demand_rule(m, t):
            return m.demand_th_t[t]
    m.actual_demand = pe.Expression(m.t, rule=actual_demand_rule)

    def genearation_covers_demand_t_rule(m, t):
        rule = sum([m.x_th_jt[j, t] for j in m.j]) - \
                    sum([m.x_load_hs_t[hs, t] for hs in m.j_hs]) == demand_f * m.actual_demand[t]
        return rule
    m.genearation_covers_demand_t = pe.Constraint(m.t, rule=genearation_covers_demand_t_rule)

    # Capacity restrictions
    def capacity_restriction_max_j_rule(m, j):
        if inv_flag:
            rule = m.Cap_j[j] <= demand_f * max_demad
        else:
            rule = m.Cap_j[j] == m.x_th_cap_j[j]
        return rule
    m.capacity_restriction_max_j = pe.Constraint(m.j, rule=capacity_restriction_max_j_rule)

    def capacity_restriction_min_j_rule(m, j):
        return m.Cap_j[j] >= m.x_th_cap_j[j]
    m.capacity_restriction_min_j = pe.Constraint(m.j, rule=capacity_restriction_min_j_rule)
    
    # Generation restrictions
    def generation_restriction_jt_rule(m, j, t):
        rule = m.x_th_jt[j, t] <= m.Cap_j[j] / m.n_th_nom_jt[j, t] * m.n_th_jt[j, t] * m.Active_jt[j, t] * m.restriction_factor_jt[j, t]
        return rule
    m.generation_restriction_jt = pe.Constraint(m.j, m.t, rule=generation_restriction_jt_rule)
    
    # Minimum operating power
    def generation_minimum_hp_jt_rule(m, j, t):
        rule = m.x_th_jt[j, t] >= m.Cap_j[j] / m.n_th_nom_jt[j, t] * m.n_th_jt[j, t] * m.Active_jt[j, t] * m.min_out_factor_j[j]
        return rule
    m.generation_minimum_hp_jt = pe.Constraint(m.j, m.t, rule=generation_minimum_hp_jt_rule)

    # Must run constraint
    def must_run_jt_rule(m, j, t):
        rule = m.x_th_jt[j, t] >= m.mr_j[j] * m.Cap_j[j] / m.n_th_nom_jt[j, t] * m.n_th_jt[j, t] * m.restriction_factor_jt[j, t]
        return rule
    m.mr_jt = pe.Constraint(m.j, m.t, rule=must_run_jt_rule)

    # Solar thermal restrictions
    def solar_restriction_jt_rule(m, j, t):
        rule = m.x_th_jt[j, t] <= m.Cap_j[j] * m.radiation_t[t] / max(val["radiation_t"].values())
        return rule
    m.solar_restriction_jt = pe.Constraint(m.j_st, m.t, rule=solar_restriction_jt_rule)
    
    # PV generation constraint (existing + new capacity)
    def pv_generation_rule(m, t):
        total_pv_capacity = m.pv_existing_capacity + m.pv_new_capacity
        rule = m.pv_generation_t[t] == total_pv_capacity * m.pv_performance_ratio * m.radiation_t[t] / max(val["radiation_t"].values())
        return rule
    m.pv_generation = pe.Constraint(m.t, rule=pv_generation_rule)

    # PV electricity balance constraint
    def pv_balance_rule(m, t):
        return m.pv_generation_t[t] == m.pv_used_t[t] + m.pv_export_t[t]
    m.pv_balance = pe.Constraint(m.t, rule=pv_balance_rule)
    
    # Total PV used locally equals sum of PV used by all generators
    def pv_used_total_rule(m, t):
        return m.pv_used_t[t] == sum(m.pv_used_j_t[j, t] for j in m.j if m.ec_j[j] == "electricity")
    m.pv_used_total = pe.Constraint(m.t, rule=pv_used_total_rule)
    
    # Limit PV used by each generator to its electricity consumption
    def pv_used_j_limit_rule(m, j, t):
        if m.ec_j[j] == "electricity":
            return m.pv_used_j_t[j, t] <= m.x_th_jt[j, t] / m.n_th_jt[j, t]
        else:
            return m.pv_used_j_t[j, t] == 0
    m.pv_used_j_limit = pe.Constraint(m.j, m.t, rule=pv_used_j_limit_rule)

    # PV area limit constraint (only for new capacity)
    def pv_area_limit_rule(m):
        return m.pv_new_capacity <= (m.pv_area_available * m.pv_efficiency) / 1000
    m.pv_area_limit = pe.Constraint(rule=pv_area_limit_rule)
    
    # PV investment constraint - only allow new PV capacity if investment flag is on
    def pv_investment_constraint_rule(m):
        if inv_flag:
            return pe.Constraint.Skip  # No constraint when investment is allowed
        else:
            return m.pv_new_capacity == 0  # Force new PV capacity to zero when no investment
    m.pv_investment_constraint = pe.Constraint(rule=pv_investment_constraint_rule)

    # Hydro electricity constraints
    def hydro_balance_rule(m, t):
        return m.hydro_excess_t[t] == m.hydro_used_t[t] + m.hydro_export_t[t]
    m.hydro_balance = pe.Constraint(m.t, rule=hydro_balance_rule)
    
    def hydro_used_total_rule(m, t):
        return m.hydro_used_t[t] == sum(m.hydro_used_j_t[j, t] for j in m.j if m.ec_j[j] == "electricity")
    m.hydro_used_total = pe.Constraint(m.t, rule=hydro_used_total_rule)
    
    def hydro_used_j_limit_rule(m, j, t):
        if m.ec_j[j] == "electricity":
            return m.hydro_used_j_t[j, t] <= m.x_th_jt[j, t] / m.n_th_jt[j, t]
        else:
            return m.hydro_used_j_t[j, t] == 0
    m.hydro_used_j_limit = pe.Constraint(m.j, m.t, rule=hydro_used_j_limit_rule)
    
    # Site-wide electricity balance constraint
    def elec_balance_rule(m, t):
        demand_t = sum(m.x_th_jt[j, t] / m.n_th_jt[j, t] for j in m.j if m.ec_j[j] == "electricity")
        return m.pv_used_t[t] + m.hydro_used_t[t] + m.grid_import_t[t] == demand_t
    m.elec_balance = pe.Constraint(m.t, rule=elec_balance_rule)
    
    # Combined renewable limit
    def combined_renewable_limit_rule(m, j, t):
        if m.ec_j[j] == "electricity":
            return m.pv_used_j_t[j, t] + m.hydro_used_j_t[j, t] <= m.x_th_jt[j, t] / m.n_th_jt[j, t]
        else:
            return pe.Constraint.Skip
    m.combined_renewable_limit = pe.Constraint(m.j, m.t, rule=combined_renewable_limit_rule)

    # Waste incineration restriction
    def waste_incineration_restriction_jt_rule(m, j, t):
        rule = m.x_th_jt[j, t] <= m.x_th_cap_j[j]
        return rule
    m.waste_incineration_restriction_jt = pe.Constraint(m.j_waste, m.t, rule=waste_incineration_restriction_jt_rule)

    # CHP generation restrictions
    def chp_geneartion_restriction1_jt_rule(m, j, t):
        if j in val["j_chp_se"]:
            sv_chp = (m.ratioPMaxFW - m.ratioPMax) / (m.ratioPMax * m.ratioPMaxFW)
            rule = m.x_el_jt[j, t] <= m.Cap_j[j] / m.ratioPMax - sv_chp * m.x_th_jt[j, t]
        else:
            rule = pe.Constraint.Skip
        return rule
    m.chp_geneartion_restriction1_jt = pe.Constraint(m.j_chp, m.t, rule=chp_geneartion_restriction1_jt_rule)

    def chp_geneartion_restriction2_jt_rule(m, j, t):
        rule = m.P_min_el_chp <= m.x_el_jt[j, t]
        return rule
    m.chp_geneartion_restriction2_jt = pe.Constraint(m.j_chp, m.t, rule=chp_geneartion_restriction2_jt_rule)

    def chp_geneartion_restriction3_jt_rule(m, j, t):
        if j in val["j_chp_se"]:
            rule = m.x_el_jt[j, t] >= m.x_th_jt[j, t] / m.ratioPMaxFW
        else:
            rule = m.x_el_jt[j, t] == m.x_th_jt[j, t] / m.n_th_jt[j, t] * m.n_el_j[j]
        return rule
    m.chp_geneartion_restriction3_jt = pe.Constraint(m.j_chp, m.t, rule=chp_geneartion_restriction3_jt_rule)

    def chp_geneartion_restriction4_jt_rule(m, j, t):
        rule = m.x_th_jt[j, t] <= m.demand_th_t[t] + sum(m.x_load_hs_t[hs, t] for hs in m.j_hs)
        return rule
    m.chp_geneartion_restriction4_jt = pe.Constraint(m.j_chp, m.t, rule=chp_geneartion_restriction4_jt_rule)

    # Storage constraints
    def storage_state_hs_t_rule(m, hs, t): 
        if t == 1: 
            return m.store_level_hs_t[hs, t] == m.store_level_hs_t[hs, 8760]
        else: 
            return m.store_level_hs_t[hs, t] == m.store_level_hs_t[hs, t-1] * (1 - m.cap_losse_hs[hs]) + m.x_load_hs_t[hs, t-1] * m.n_hs[hs] 
    m.storage_state_hs_t = pe.Constraint(m.j_hs, m.t, rule=storage_state_hs_t_rule) 

    def storage_capacity_restriction_hs_rule(m, hs):
        if inv_flag:
            return m.Cap_hs[hs] >= m.cap_hs[hs]
        else:
            return m.Cap_hs[hs] == m.cap_hs[hs]
    m.storage_capacity_restriction_hs = pe.Constraint(m.j_hs, rule=storage_capacity_restriction_hs_rule)

    def storage_state_capacity_restriction_hs_t_rule(m, hs, t):
        return m.store_level_hs_t[hs, t] <= m.Cap_hs[hs]
    m.storage_state_capacity_restriction_hs_t = pe.Constraint(m.j_hs, m.t, rule=storage_state_capacity_restriction_hs_t_rule)

    def load_hs_t_restriction_rule(m, hs, t):
        return m.x_load_hs_t[hs, t] <= m.load_cap_hs[hs]
    m.load_hs_t_restriction = pe.Constraint(m.j_hs, m.t, rule=load_hs_t_restriction_rule)

    def unload_hs_t_restriction_rule(m, hs, t, flag):
        if flag:
            return m.x_load_hs_t[hs, t] >= -m.unload_cap_hs[hs]
        else:
            return m.x_load_hs_t[hs, t] >= -m.store_level_hs_t[hs, t]
    m.unload_hs_t_restriction = pe.Constraint(m.j_hs, m.t, [True, False], rule=unload_hs_t_restriction_rule)
    
    # Ramp and cold start constraints
    def ramp_cost_jt_rule(m, j, t): 
        if t == 1: 
            return m.ramp_jt[j, t] == 0 
        else: 
            return m.ramp_jt[j, t] >= m.x_th_jt[j, t] - m.x_th_jt[j, t-1] 
    m.ramp_cost_jt = pe.Constraint(m.j, m.t, rule=ramp_cost_jt_rule) 
    
    def coldstart_j_t_rule(m, j, t):
        if t == 1:
            return m.coldstart_jt[j, t] == 1
        else:
            return m.coldstart_jt[j, t] >= m.Active_jt[j, t] - m.Active_jt[j, t-1]
    m.coldstart_rule_jt = pe.Constraint(m.j, m.t, rule=coldstart_j_t_rule)
    
    # Renewable factor constraint
    def renewable_factor_j_rule(m):
        if (sum(m.rf_j[j] for j in m.j) == 0):
            return pe.Constraint.Skip
        rule = sum([sum([(m.x_th_jt[j, t] + m.x_el_jt[j, t]) for t in m.t]) * m.rf_j[j] for j in m.j]) >= m.rf_tot * sum([sum([(m.x_th_jt[j, t] + m.x_el_jt[j, t]) for t in m.t]) for j in m.j])
        return rule
    m.renewable_factor = pe.Constraint(rule=renewable_factor_j_rule)

    # PED-specific constraints
    def get_pef_import(m, t):
        if ped_mode == "static":
            return m.pef_import_electricity
        else:
            return m.pef_import_electricity_t[t]

    def get_pef_export(m, t):
        if ped_mode == "static":
            return m.pef_export_electricity
        else:
            return m.pef_export_electricity_t[t]

    def ped_import_rule(m, t):
        non_elec_import = sum(
            (m.x_th_jt[j, t] / m.n_th_jt[j, t]) *
            (m.pef_CHP_gas if m.ec_j[j] == "CHP gas"
                else m.pef_fossil_fuel if m.ec_j[j] == "gas/oil"
                else m.pef_natural_gas if m.ec_j[j] == "natural gas"
                else m.pef_straw if m.ec_j[j] == "straw"
                else m.pef_various if m.ec_j[j] == "various"
                else m.pef_waste if m.ec_j[j] == "waste"
                else m.pef_waste_heat_20 if m.ec_j[j] == "waste heat 20°"
                else m.pef_waste_heat_40 if m.ec_j[j] == "waste heat 40°"
                else m.pef_wood_chips if m.ec_j[j] == "wood chips"
                else m.pef_wood_pellets if m.ec_j[j] == "wood pellets"
                else m.pef_radiation if m.ec_j[j] == "radiation"
                else 0)
            for j in m.j if m.ec_j[j] != "electricity")

        elec_import = m.grid_import_t[t] * get_pef_import(m, t)
        return m.E_import[t] == elec_import + non_elec_import
    m.ped_import = pe.Constraint(m.t, rule=ped_import_rule)

    def ped_export_rule(m, t):
        chp_export = sum(m.x_el_jt[j, t] * get_pef_export(m, t) for j in m.j if m.ec_j[j] in renewable_carriers)
        pv_export = m.pv_export_t[t] * get_pef_export(m, t)
        hydro_export = m.hydro_export_t[t] * get_pef_export(m, t)
        return m.E_export[t] == chp_export + pv_export + hydro_export
    m.ped_export = pe.Constraint(m.t, rule=ped_export_rule)

    # PED balance constraints based on horizon
    if ped_balance_horizon == 'yearly':
        def ped_primary_energy_balance_rule(m):
            return sum(m.E_export[t] for t in m.t) >= PED_status * sum(m.E_import[t] for t in m.t)
        m.ped_primary_energy_balance = pe.Constraint(rule=ped_primary_energy_balance_rule)

    elif ped_balance_horizon == 'seasonal':
        def winter_balance_rule(m):
            return sum(m.E_export[t] for t in m.winter_hours) >= PED_status * sum(m.E_import[t] for t in m.winter_hours)
        m.winter_balance = pe.Constraint(rule=winter_balance_rule)

        def spring_balance_rule(m):
            return sum(m.E_export[t] for t in m.spring_hours) >= PED_status * sum(m.E_import[t] for t in m.spring_hours)
        m.spring_balance = pe.Constraint(rule=spring_balance_rule)

        def summer_balance_rule(m):
            return sum(m.E_export[t] for t in m.summer_hours) >= PED_status * sum(m.E_import[t] for t in m.summer_hours)
        m.summer_balance = pe.Constraint(rule=summer_balance_rule)

        def autumn_balance_rule(m):
            return sum(m.E_export[t] for t in m.autumn_hours) >= PED_status * sum(m.E_import[t] for t in m.autumn_hours)
        m.autumn_balance = pe.Constraint(rule=autumn_balance_rule)

    elif ped_balance_horizon == 'daily':
        def daily_balance_rule(m, d):
            start_hour = (d - 1) * 24 + 1
            end_hour = d * 24
            daily_hours = list(range(start_hour, end_hour + 1))
            return sum(m.E_export[t] for t in daily_hours) >= PED_status * sum(m.E_import[t] for t in daily_hours)
        m.daily_balance = pe.Constraint(m.days, rule=daily_balance_rule)

    #%% Objective Function
    def cost_rule(m):
        if inv_flag:
            c_inv = sum([(m.Cap_j[j] - m.x_th_cap_j[j]) * m.IK_j[j] * m.alpha_j[j] for j in m.j]) + \
                    sum([(m.Cap_hs[hs] - m.cap_hs[hs]) * m.IK_hs[hs] * m.alpha_hs[hs] for hs in m.j_hs]) + \
                    (m.pv_new_capacity * m.PV_invest_cost * m.alpha_pv)  # Only new PV capacity
            c_op_fix = sum([m.Cap_j[j] * m.OP_fix_j[j] for j in m.j]) + \
                        sum([m.Cap_hs[hs] * m.OP_fix_hs[hs] for hs in m.j_hs]) + \
                        (m.pv_existing_capacity + m.pv_new_capacity) * m.PV_om_fix  # O&M for total capacity
        else:
            c_inv = 0
            c_op_fix = sum([m.Cap_j[j] * m.OP_fix_j[j] for j in m.j]) + \
                       sum([m.Cap_hs[hs] * m.OP_fix_hs[hs] for hs in m.j_hs]) + \
                       (m.pv_existing_capacity + m.pv_new_capacity) * m.PV_om_fix  # O&M for total capacity

        c_op_var = sum([m.x_th_jt[j, t] * m.OP_var_j[j] for j in m.j for t in m.t])
        
        # Variable costs for all non-electric energy carriers
        c_var = sum([
            m.x_th_jt[j, t] * m.mc_jt[j, t]
            for j in m.j for t in m.t if m.ec_j[j] != "electricity"
        ])
        
        # Grid import cost
        elec_techs = [j for j in m.j if pe.value(m.ec_j[j]) == "electricity"]
        if elec_techs:
            ref_tech = elec_techs[0]
            c_grid = sum([m.grid_import_t[t] * m.electricity_price_jt[ref_tech, t] for t in m.t])
        else:
            ref_tech = list(m.j)[0]
            print("Warning: No electric technology found, using first technology as reference for prices")
            c_grid = sum([m.grid_import_t[t] * m.electricity_price_jt[ref_tech, t] for t in m.t])
            
        c_hydro = 0.0
        c_peak_el = 0.0
        c_ramp = sum([m.ramp_jt[j, t] * m.c_ramp_j[j] for j in m.j for t in m.t]) 
        c_cold = sum([(m.coldstart_jt[j, t] * m.c_coldstart_j[j]) for j in m.j for t in m.t])
        c_refurb = m.include_refurb_cost * (m.refurbishment_cost if hasattr(m, 'refurbishment_cost') else 0)
        c_tot = c_inv + c_var + c_op_fix + c_op_var + c_cold + c_ramp + c_refurb + c_hydro + c_grid

        # Revenue from electricity generation by CHP
        rev_gen_electricity = sum([m.x_el_jt[j, t] * (m.sale_electricity_price_jt[j, t]) for j in m.j for t in m.t])
        
        # Revenue from PV export
        if hasattr(m, 'pv_export_price_t'):
            rev_pv_electricity = sum([m.pv_export_t[t] * m.pv_export_price_t[t] for t in m.t])
        else:
            rev_pv_electricity = sum([m.pv_export_t[t] * (m.electricity_price_jt[ref_tech, t] * 0.7) for t in m.t])

        # Revenue from hydro export
        if hasattr(m, 'hydro_export_price_t'):
            rev_hydro_electricity = sum([m.hydro_export_t[t] * m.hydro_export_price_t[t] for t in m.t])
        else:
            rev_hydro_electricity = sum([m.hydro_export_t[t] * (m.electricity_price_jt[ref_tech, t] * 0.7) for t in m.t])

        rev_tot = rev_gen_electricity + rev_pv_electricity + rev_hydro_electricity
        
        rule = (c_tot - rev_tot)
        return rule
    m.cost = pe.Objective(rule=cost_rule)

    #%% Compile and Solve Model
    print("*****************\nCreating Model...\n*****************")
    solv_start = datetime.now()
    instance = m.create_instance(report_timing=False)

    # Optionally force no refurbishment in refurb mode for comparison
    if force_no_refurb and ped_mode == "refurb":
        try:
            for i in instance.blocks:
                instance.x_save_fraction[i].fix(0)
            instance.preprocess()
            print("Refurbishment forced to zero (all x_save_fraction fixed to 0).")
        except Exception as e:
            print(f"Warning: could not fix refurbishment variables: {e}")
            
    print("*****************\ntime to create model: " + str(datetime.now()-solv_start)+"\n*****************")
    solv_start = datetime.now()
    print("*****************\nSolving...\n*****************")

    opt = pe.SolverFactory("gurobi")
    opt.options['MIPGap'] = 1e-3
    opt.options["MIPFocus"] = 0
    opt.options["TimeLimit"] = 1200
    opt.options['NodefileStart'] = 0.5
    
    tee = True
    results = opt.solve(instance, load_solutions=False, tee=tee, suffixes=['.*'])
    print("*****************\ntime for solving: " + str(datetime.now()-solv_start)+"\n*****************")

    solv_start = datetime.now()
    if results.solver.termination_condition == TerminationCondition.maxTimeLimit:
        return (None, results.solver.message)

    if (results.solver.status == SolverStatus.ok) and (results.solver.termination_condition == TerminationCondition.optimal):
        instance.solutions.load_from(results)
        instance.solutions.store_to(results)

        # Print refurbishment results
        total_fraction_saved = pe.value(instance.fraction_saved)
        saved_mwh = pe.value(instance.mwh_saved_total)
        total_refurb_cost = pe.value(instance.refurbishment_cost)

        print("=== Refurbishment Results ===")
        print("Total fraction saved: {:.2%}".format(total_fraction_saved))
        print("Total MWh saved:      {:.2f} MWh".format(saved_mwh))
        print("Total refurbishment cost: {:.2f} EUR".format(total_refurb_cost))

        print("\nBlock Usage (each block is 10% potential):")
        for i in instance.blocks:
            block_usage = pe.value(instance.x_save_fraction[i])
            print(f"  Block {i}: {block_usage*100:.1f}% used")

        # Print PV capacity and cost
        if hasattr(instance, 'pv_new_capacity'):
            pv_existing_cap = pe.value(instance.pv_existing_capacity)
            pv_new_cap = pe.value(instance.pv_new_capacity)
            pv_total_cap = pv_existing_cap + pv_new_cap
            
            print(f"Existing PV capacity         = {pv_existing_cap:.2f} MW")
            if inv_flag:
                print(f"Optimal new PV capacity      = {pv_new_cap:.2f} MW")
            else:
                print(f"New PV capacity              = {pv_new_cap:.2f} MW (Investment disabled)")
            print(f"Total PV capacity            = {pv_total_cap:.2f} MW")

            pv_invest_cost = pe.value(instance.PV_invest_cost)
            alpha_pv = pe.value(instance.alpha_pv)
            pv_om_fix = pe.value(instance.PV_om_fix)

            invest_cost_annual = pv_new_cap * pv_invest_cost * alpha_pv  # Only for new capacity
            om_cost_annual = pv_total_cap * pv_om_fix  # For total capacity
            total_pv_cost = invest_cost_annual + om_cost_annual

            print(f"Annualized new PV investment cost = {invest_cost_annual:,.2f} EUR/yr")
            print(f"Annual total PV O&M cost         = {om_cost_annual:,.2f} EUR/yr")
            print(f"Total annual PV cost             = {total_pv_cost:,.2f} EUR/yr")

        print("*****************\nFixing Binary and resolving...\n*****************") 
        
        # Fix binary variables and resolve for dual variables
        instance.Active_jt.fix() 
        instance.coldstart_jt.fix()
        instance.preprocess()  
        results = opt.solve(instance, load_solutions=False, tee=tee, suffixes=['.*'])
        instance.solutions.load_from(results) 
        instance.solutions.store_to(results) 
        print("*****************\ntime for resolving fixed variables: " + str(datetime.now()-solv_start)+"\n*****************")
        
        # Detailed objective breakdown
        if debug_objective:
            try:
                # Calculate cost components
                if inv_flag:
                    c_inv = sum([(pe.value(instance.Cap_j[j]) - pe.value(instance.x_th_cap_j[j])) * pe.value(instance.IK_j[j]) * pe.value(instance.alpha_j[j]) for j in instance.j]) \
                            + sum([(pe.value(instance.Cap_hs[hs]) - pe.value(instance.cap_hs[hs])) * pe.value(instance.IK_hs[hs]) * pe.value(instance.alpha_hs[hs]) for hs in instance.j_hs]) \
                            + (pe.value(instance.pv_new_capacity) * pe.value(instance.PV_invest_cost) * pe.value(instance.alpha_pv))  # Only new PV capacity
                    c_op_fix = sum([pe.value(instance.Cap_j[j]) * pe.value(instance.OP_fix_j[j]) for j in instance.j]) \
                               + sum([pe.value(instance.Cap_hs[hs]) * pe.value(instance.OP_fix_hs[hs]) for hs in instance.j_hs]) \
                               + (pe.value(instance.pv_existing_capacity) + pe.value(instance.pv_new_capacity)) * pe.value(instance.PV_om_fix)  # O&M for total capacity
                else:
                    c_inv = 0.0
                    c_op_fix = sum([pe.value(instance.Cap_j[j]) * pe.value(instance.OP_fix_j[j]) for j in instance.j]) \
                               + sum([pe.value(instance.Cap_hs[hs]) * pe.value(instance.OP_fix_hs[hs]) for hs in instance.j_hs]) \
                               + (pe.value(instance.pv_existing_capacity) + pe.value(instance.pv_new_capacity)) * pe.value(instance.PV_om_fix)  # O&M for total capacity

                c_op_var = sum([pe.value(instance.x_th_jt[j, t]) * pe.value(instance.OP_var_j[j]) for j in instance.j for t in instance.t])

                c_var = sum([
                    pe.value(instance.x_th_jt[j, t]) * pe.value(instance.mc_jt[j, t])
                    for j in instance.j for t in instance.t if pe.value(instance.ec_j[j]) != "electricity"
                ])

                elec_techs = [j for j in instance.j if pe.value(instance.ec_j[j]) == "electricity"]
                if elec_techs:
                    ref_tech = elec_techs[0]
                    c_grid = sum([pe.value(instance.grid_import_t[t]) * pe.value(instance.electricity_price_jt[ref_tech, t]) for t in instance.t])
                else:
                    ref_tech = list(instance.j)[0]
                    c_grid = sum([pe.value(instance.grid_import_t[t]) * pe.value(instance.electricity_price_jt[ref_tech, t]) for t in instance.t])

                c_hydro = 0.0
                c_ramp = sum([pe.value(instance.ramp_jt[j, t]) * pe.value(instance.c_ramp_j[j]) for j in instance.j for t in instance.t])
                c_cold = sum([pe.value(instance.coldstart_jt[j, t]) * pe.value(instance.c_coldstart_j[j]) for j in instance.j for t in instance.t])
                c_refurb = pe.value(instance.include_refurb_cost) * (pe.value(instance.refurbishment_cost) if hasattr(instance, 'refurbishment_cost') else 0.0)

                c_tot = c_inv + c_var + c_op_fix + c_op_var + c_cold + c_ramp + c_refurb + c_hydro + c_grid

                # Revenues
                rev_gen_electricity = sum([pe.value(instance.x_el_jt[j, t]) * pe.value(instance.sale_electricity_price_jt[j, t]) for j in instance.j for t in instance.t])
                if hasattr(instance, 'pv_export_price_t'):
                    rev_pv_electricity = sum([pe.value(instance.pv_export_t[t]) * pe.value(instance.pv_export_price_t[t]) for t in instance.t])
                else:
                    rev_pv_electricity = sum([pe.value(instance.pv_export_t[t]) * (pe.value(instance.electricity_price_jt[ref_tech, t]) * 0.7) for t in instance.t])

                if hasattr(instance, 'hydro_export_price_t'):
                    rev_hydro_electricity = sum([pe.value(instance.hydro_export_t[t]) * pe.value(instance.hydro_export_price_t[t]) for t in instance.t])
                else:
                    rev_hydro_electricity = sum([pe.value(instance.hydro_export_t[t]) * (pe.value(instance.electricity_price_jt[ref_tech, t]) * 0.7) for t in instance.t])

                rev_tot = rev_gen_electricity + rev_pv_electricity + rev_hydro_electricity
                net_obj = c_tot - rev_tot

                print("\n=== Objective Breakdown ===")
                print(f"Objective value (instance.cost)        : {pe.value(instance.cost):,.2f}")
                print(f"c_inv (annualized capex)               : {c_inv:,.2f}")
                print(f"c_op_fix (fixed O&M)                   : {c_op_fix:,.2f}")
                print(f"c_op_var (var O&M on heat)             : {c_op_var:,.2f}")
                print(f"c_var (fuel for non-elec)              : {c_var:,.2f}")
                print(f"c_grid (grid import)                   : {c_grid:,.2f}")
                print(f"c_ramp                                  : {c_ramp:,.2f}")
                print(f"c_cold                                  : {c_cold:,.2f}")
                print(f"c_refurb                                : {c_refurb:,.2f}")
                print(f"c_hydro                                 : {c_hydro:,.2f}")
                print(f"c_tot                                   : {c_tot:,.2f}")
                print(f"rev_gen_electricity                     : {rev_gen_electricity:,.2f}")
                print(f"rev_pv_electricity                      : {rev_pv_electricity:,.2f}")
                print(f"rev_hydro_electricity                   : {rev_hydro_electricity:,.2f}")
                print(f"rev_tot                                 : {rev_tot:,.2f}")
                print(f"Net (c_tot - rev_tot)                  : {net_obj:,.2f}")
            except Exception as e:
                print(f"Warning: failed to compute objective breakdown: {e}")
        
        print("\nCalculating PV electricity usage and export...")
        # Call the check_pv_usage function
        if hasattr(instance, 'pv_new_capacity') and hasattr(instance, 'pv_used_t') and hasattr(instance, 'pv_export_t'):
            check_pv_usage(instance)
            
        print("\nCalculating Hydro electricity usage and export...")
        # Call the check_hydro_usage function
        if hasattr(instance, 'hydro_excess_t') and hasattr(instance, 'hydro_used_t'):
            check_hydro_usage(instance)
        
        print("\nCalculating Grid electricity usage...")
        # Call the check_grid_usage function
        if hasattr(instance, 'grid_import_t'):
            check_grid_usage(instance)
        
        # Generate and save detailed hourly dispatch data
        print("\nGenerating detailed hourly dispatch data...")
        dispatch_df = generate_dispatch_data(instance, ped_balance_horizon, ped_mode)
        
        return instance, results
        
    else: 
        print("Here")
        print(results.solver.status)
        print(results.solver.termination_condition)
        print("something else is wrong")
        return (None, results.solver.message)

if __name__ == "__main__":
    print('Main: Simpel Dispatch Module - Clean Version')
