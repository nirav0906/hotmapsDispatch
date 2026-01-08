# -*- coding: utf-8 -*-
"""
Analysis Functions for PED Energy System Dispatch

This module contains analysis and reporting functions that were extracted from
the main simpel_dispatch.py file to keep the core optimization code clean.

Created: 2025-01-20
@author: Nirav
"""

import pyomo.environ as pe
import pandas as pd
import numpy as np
import datetime

def check_pv_usage(instance):
    """Analyzes the PV electricity usage and export from the Pyomo model instance."""
    # Get PV capacity information
    pv_existing_cap = pe.value(instance.pv_existing_capacity) if hasattr(instance, 'pv_existing_capacity') else 0
    pv_new_cap = pe.value(instance.pv_new_capacity) if hasattr(instance, 'pv_new_capacity') else 0
    pv_total_cap = pv_existing_cap + pv_new_cap
    
    pv_summary = {
        "Existing PV Capacity (MW)": pv_existing_cap,
        "New PV Capacity (MW)": pv_new_cap,
        "Total PV Capacity (MW)": pv_total_cap,
        "Total PV Generation (MWh)": 0,
        "Total PV Used Locally (MWh)": 0,
        "Total PV Exported (MWh)": 0,
        "PV Used by Technology": {}
    }

    # Initialize usage by technology
    for j in instance.j:
        if pe.value(instance.ec_j[j]) == "electricity":
            pv_summary["PV Used by Technology"][str(j)] = 0

    # Loop through all time periods
    for t in instance.t:
        pv_generation = pe.value(instance.pv_generation_t[t])  # PV generated
        pv_used = pe.value(instance.pv_used_t[t])              # PV used locally
        pv_exported = pe.value(instance.pv_export_t[t])        # PV exported

        # Accumulate totals
        pv_summary["Total PV Generation (MWh)"] += pv_generation
        pv_summary["Total PV Used Locally (MWh)"] += pv_used
        pv_summary["Total PV Exported (MWh)"] += pv_exported

        # Track usage by technology
        for j in instance.j:
            if pe.value(instance.ec_j[j]) == "electricity":
                pv_summary["PV Used by Technology"][str(j)] += pe.value(instance.pv_used_j_t[j,t])

    # Print a detailed summary
    print("=== PV Electricity Usage Summary ===")
    for key, value in pv_summary.items():
        if key != "PV Used by Technology":
            if "Capacity" in key:
                print(f"{key}: {value:.2f} MW")
            else:
                print(f"{key}: {value:.2f} MWh")
        
    print("\nPV Usage by Technology:")
    for tech, amount in pv_summary["PV Used by Technology"].items():
        print(f"  {tech}: {amount:.2f} MWh")

    return pv_summary

def check_hydro_usage(instance):
    """Analyzes the hydro electricity usage and export from the Pyomo model instance."""
    hydro_summary = {
        "Total Hydro Available (MWh)": 0,
        "Total Hydro Used Locally (MWh)": 0,
        "Total Hydro Exported (MWh)": 0,
        "Hydro Used by Technology": {},
        "Hydro Cost": {
            "Total Cost (EUR)": 0,
            "Average Price (EUR/MWh)": 0
        },
        "Hourly Data": {
            "Available": {},
            "Used": {},
            "Exported": {},
            "Utilization Rate": {}
        }
    }

    # Get an appropriate reference technology for electricity pricing
    elec_techs = [j for j in instance.j if pe.value(instance.ec_j[j]) == "electricity"]
    if elec_techs:
        ref_tech = elec_techs[0]  # Use first electric technology as reference
    else:
        ref_tech = list(instance.j)[0]
        print("Warning: No electric technology found, using first technology as reference for prices")

    # Initialize usage by technology
    for j in instance.j:
        if pe.value(instance.ec_j[j]) == "electricity":
            hydro_summary["Hydro Used by Technology"][str(j)] = 0

    # Loop through all time periods
    for t in instance.t:
        hydro_available = pe.value(instance.hydro_excess_t[t])  # Hydro available
        hydro_used = pe.value(instance.hydro_used_t[t])         # Hydro used locally
        hydro_exported = pe.value(instance.hydro_export_t[t]) if hasattr(instance, 'hydro_export_t') else 0  # Hydro exported
        
        # Get hydro price from the data files (if direct hydro cost is available, otherwise use 70% of electricity price)
        if hasattr(instance, 'hydro_cost_t'):
            hydro_price = pe.value(instance.hydro_cost_t[t])
        else:
            # Fallback: Hydro price is 70% of standard electricity price
            electricity_price = pe.value(instance.electricity_price_jt[ref_tech, t])
            hydro_price = electricity_price * 0.7
            
        hydro_cost = hydro_used * hydro_price

        # Accumulate totals
        hydro_summary["Total Hydro Available (MWh)"] += hydro_available
        hydro_summary["Total Hydro Used Locally (MWh)"] += hydro_used
        hydro_summary["Total Hydro Exported (MWh)"] += hydro_exported
        hydro_summary["Hydro Cost"]["Total Cost (EUR)"] += hydro_cost

        # Track usage by technology
        for j in instance.j:
            if pe.value(instance.ec_j[j]) == "electricity":
                hydro_summary["Hydro Used by Technology"][str(j)] += pe.value(instance.hydro_used_j_t[j,t])
        
        # Store hourly data
        hydro_summary["Hourly Data"]["Available"][t] = hydro_available
        hydro_summary["Hourly Data"]["Used"][t] = hydro_used
        hydro_summary["Hourly Data"]["Exported"][t] = hydro_exported
        hydro_summary["Hourly Data"]["Utilization Rate"][t] = ((hydro_used + hydro_exported) / hydro_available * 100) if hydro_available > 0 else 0

    # Calculate average price
    if hydro_summary["Total Hydro Used Locally (MWh)"] > 0:
        hydro_summary["Hydro Cost"]["Average Price (EUR/MWh)"] = (
            hydro_summary["Hydro Cost"]["Total Cost (EUR)"] / 
            hydro_summary["Total Hydro Used Locally (MWh)"]
        )

    # Calculate overall utilization rate
    total_hydro_utilized = hydro_summary["Total Hydro Used Locally (MWh)"] + hydro_summary["Total Hydro Exported (MWh)"]
    utilization_rate = (total_hydro_utilized / hydro_summary["Total Hydro Available (MWh)"] * 100) if hydro_summary["Total Hydro Available (MWh)"] > 0 else 0

    # Print a detailed summary
    print("=== Hydro Electricity Usage Summary ===")
    print(f"Total Hydro Available: {hydro_summary['Total Hydro Available (MWh)']:.2f} MWh")
    print(f"Total Hydro Used Locally: {hydro_summary['Total Hydro Used Locally (MWh)']:.2f} MWh")
    print(f"Total Hydro Exported: {hydro_summary['Total Hydro Exported (MWh)']:.2f} MWh")
    print(f"Hydro Utilization Rate: {utilization_rate:.2f}%")
    print(f"Total Hydro Cost: {hydro_summary['Hydro Cost']['Total Cost (EUR)']:.2f} EUR")
    print(f"Average Hydro Price: {hydro_summary['Hydro Cost']['Average Price (EUR/MWh)']:.2f} EUR/MWh")
    
    print("\nHydro Usage by Technology:")
    for tech, amount in hydro_summary["Hydro Used by Technology"].items():
        percentage = (amount / hydro_summary["Total Hydro Used Locally (MWh)"] * 100) if hydro_summary["Total Hydro Used Locally (MWh)"] > 0 else 0
        print(f"  {tech}: {amount:.2f} MWh ({percentage:.2f}%)")
    
    # Find hours with lowest and highest utilization
    if hydro_summary["Hourly Data"]["Utilization Rate"]:
        hours_by_utilization = sorted(hydro_summary["Hourly Data"]["Utilization Rate"].items(), key=lambda x: x[1])
        
        print("\nHours with Lowest Hydro Utilization:")
        for hour, rate in hours_by_utilization[:5]:
            if hydro_summary["Hourly Data"]["Available"][hour] > 0:
                used = hydro_summary["Hourly Data"]["Used"][hour]
                exported = hydro_summary["Hourly Data"]["Exported"][hour]
                available = hydro_summary["Hourly Data"]["Available"][hour]
                print(f"  Hour {hour}: {rate:.2f}% (Available: {available:.2f} MWh, Used: {used:.2f} MWh, Exported: {exported:.2f} MWh)")
        
        print("\nHours with Highest Hydro Utilization:")
        for hour, rate in reversed(hours_by_utilization[-5:]):
            if hydro_summary["Hourly Data"]["Available"][hour] > 0:
                used = hydro_summary["Hourly Data"]["Used"][hour]
                exported = hydro_summary["Hourly Data"]["Exported"][hour]
                available = hydro_summary["Hourly Data"]["Available"][hour]
                print(f"  Hour {hour}: {rate:.2f}% (Available: {available:.2f} MWh, Used: {used:.2f} MWh, Exported: {exported:.2f} MWh)")

    return hydro_summary

def check_grid_usage(instance):
    """Analyzes the grid electricity usage from the Pyomo model instance."""
    grid_summary = {
        "Total Grid Import (MWh)": 0,
        "Total Electricity Demand (MWh)": 0,
        "Electricity Sources": {
            "Grid Import (MWh)": 0,
            "PV Used (MWh)": 0,
            "Hydro Used (MWh)": 0
        },
        "Electricity Costs": {
            "Grid Import Cost (EUR)": 0,
            "Hydro Cost (EUR)": 0,
            "Average Grid Price (EUR/MWh)": 0,
            "Average Hydro Price (EUR/MWh)": 0,
        },
        "Grid Import by Hour": {}
    }

    # Get an appropriate reference technology for electricity pricing
    elec_techs = [j for j in instance.j if pe.value(instance.ec_j[j]) == "electricity"]
    if elec_techs:
        ref_tech = elec_techs[0]  # Use first electric technology as reference
    else:
        ref_tech = list(instance.j)[0]
        print("Warning: No electric technology found, using first technology as reference for prices")

    # Loop through all time periods
    for t in instance.t:
        grid_import = pe.value(instance.grid_import_t[t])
        pv_used = pe.value(instance.pv_used_t[t]) if hasattr(instance, 'pv_used_t') else 0
        hydro_used = pe.value(instance.hydro_used_t[t]) if hasattr(instance, 'hydro_used_t') else 0
        
        # Calculate total electricity demand for this hour
        elec_demand = sum(pe.value(instance.x_th_jt[j, t]) / pe.value(instance.n_th_jt[j, t]) 
                          for j in instance.j if pe.value(instance.ec_j[j]) == "electricity")
        
        # Get electricity prices based on available parameters
        if hasattr(instance, 'grid_cost_t'):
            electricity_price = pe.value(instance.grid_cost_t[t])
        else:
            electricity_price = pe.value(instance.electricity_price_jt[ref_tech, t])
        
        # Get hydro price - either from direct parameter or calculate as 70% of electricity price
        if hasattr(instance, 'hydro_cost_t'):
            hydro_price = pe.value(instance.hydro_cost_t[t])
        else:
            hydro_price = electricity_price * 0.7  # Hydro is 70% of electricity price
        
        # Calculate costs
        grid_cost = grid_import * electricity_price
        hydro_cost = hydro_used * hydro_price
        
        # Accumulate totals
        grid_summary["Total Grid Import (MWh)"] += grid_import
        grid_summary["Total Electricity Demand (MWh)"] += elec_demand
        grid_summary["Electricity Sources"]["Grid Import (MWh)"] += grid_import
        grid_summary["Electricity Sources"]["PV Used (MWh)"] += pv_used
        grid_summary["Electricity Sources"]["Hydro Used (MWh)"] += hydro_used
        grid_summary["Electricity Costs"]["Grid Import Cost (EUR)"] += grid_cost
        grid_summary["Electricity Costs"]["Hydro Cost (EUR)"] += hydro_cost
        
        # Store hourly data (for potential time-series analysis)
        grid_summary["Grid Import by Hour"][t] = grid_import

    # Calculate average prices
    if grid_summary["Electricity Sources"]["Grid Import (MWh)"] > 0:
        grid_summary["Electricity Costs"]["Average Grid Price (EUR/MWh)"] = (
            grid_summary["Electricity Costs"]["Grid Import Cost (EUR)"] / 
            grid_summary["Electricity Sources"]["Grid Import (MWh)"]
        )
    
    if grid_summary["Electricity Sources"]["Hydro Used (MWh)"] > 0:
        grid_summary["Electricity Costs"]["Average Hydro Price (EUR/MWh)"] = (
            grid_summary["Electricity Costs"]["Hydro Cost (EUR)"] / 
            grid_summary["Electricity Sources"]["Hydro Used (MWh)"]
        )

    # Print a detailed summary
    print("=== Grid Electricity Usage Summary ===")
    print(f"Total Electricity Demand: {grid_summary['Total Electricity Demand (MWh)']:.2f} MWh")
    print(f"Total Grid Import: {grid_summary['Total Grid Import (MWh)']:.2f} MWh")
    print(f"Grid Import Share: {(grid_summary['Total Grid Import (MWh)']/grid_summary['Total Electricity Demand (MWh)']*100) if grid_summary['Total Electricity Demand (MWh)'] > 0 else 0:.2f}%")
    
    print("\nElectricity Sources:")
    for source, amount in grid_summary["Electricity Sources"].items():
        percentage = (amount / grid_summary["Total Electricity Demand (MWh)"] * 100) if grid_summary["Total Electricity Demand (MWh)"] > 0 else 0
        print(f"  {source}: {amount:.2f} MWh ({percentage:.2f}%)")
    
    print("\nElectricity Costs:")
    for cost_type, cost in grid_summary["Electricity Costs"].items():
        print(f"  {cost_type}: {cost:.2f}")
    
    # Compare prices to understand dispatch decisions
    print("\nPrice Comparison:")
    print(f"  Average Grid Price: {grid_summary['Electricity Costs']['Average Grid Price (EUR/MWh)']:.2f} EUR/MWh")
    print(f"  Average Hydro Price: {grid_summary['Electricity Costs']['Average Hydro Price (EUR/MWh)']:.2f} EUR/MWh")
    print(f"  PV Price: 0.00 EUR/MWh (assumed zero marginal cost)")
    
    # Optional: Print hourly data for specific hours of interest
    print("\nTop 5 Hours with Highest Grid Import:")
    top_hours = sorted(grid_summary["Grid Import by Hour"].items(), key=lambda x: x[1], reverse=True)[:5]
    for hour, amount in top_hours:
        print(f"  Hour {hour}: {amount:.2f} MWh")
    
    return grid_summary

def generate_dispatch_data(instance, ped_balance_horizon="yearly", ped_mode="dynamic"):
    """Exports detailed hourly dispatch data including primary energy, storage,
    and technology-specific carrier and primary energy consumption.

    Generates a comprehensive CSV file with hourly data for all energy flows
    including primary energy weighted by PEF, technologies dispatch,
    storage operation, carrier usage, and primary energy usage per technology.
    """
    
    # Create a dictionary to store all hourly data
    hourly_data = {
        'Hour': list(instance.t),
        'Date': [],  # Add datetime for easier analysis
        'Import_PrimaryEnergy_MWh': [], # Overall PED import
        'Export_PrimaryEnergy_MWh': [], # Overall PED export
        'Net_PrimaryEnergy_MWh': [],   # Overall PED net balance
        'PV_Generation_MWh': [],
        'PV_Used_Locally_MWh': [],
        'PV_Exported_MWh': [],
        'Hydro_Available_MWh': [],
        'Hydro_Used_MWh': [],
        'Hydro_Exported_MWh': [],
        'Grid_Import_MWh': [],
        'Demand_Heat_MWh': [],
        'Demand_Heat_Reduced_MWh': [],  # After-refurbishment heat demand
        'Heat_Saved_MWh': [],  # Amount of heat saved through refurbishment
        
        # Economic data - costs and revenues at time t
        'Grid_Import_Cost_EUR': [],  # Cost of grid electricity import
        'Grid_Import_Price_EUR_MWh': [],  # Price of grid electricity
        'PV_Export_Revenue_EUR': [],  # Revenue from PV electricity export
        'PV_Export_Price_EUR_MWh': [],  # Price for PV export
        'Hydro_Used_Cost_EUR': [],  # Cost of hydro electricity used
        'Hydro_Used_Price_EUR_MWh': [],  # Price of hydro electricity
        'Hydro_Export_Revenue_EUR': [],  # Revenue from hydro electricity export
        'Hydro_Export_Price_EUR_MWh': [],  # Price for hydro export
        'CHP_Electricity_Revenue_EUR': [],  # Revenue from CHP electricity sales
        'Total_Fuel_Cost_EUR': [],  # Total fuel costs for all technologies
        'Total_Electricity_Cost_EUR': [],  # Total electricity costs (grid + hydro)
        'Total_Electricity_Revenue_EUR': [],  # Total electricity revenues (PV + hydro + CHP)
        'Net_Electricity_Cost_EUR': []  # Net electricity cost (costs - revenues)
    }

    # Add technology-specific columns dynamically
    for j in instance.j:
        # Heat Generation (Output)
        hourly_data[f'Heat_Gen_{j}_MWh'] = []

        # Energy Carrier Consumption (Input)
        hourly_data[f'CarrierUse_{j}_MWh'] = [] # e.g., Gas used by Boiler_Gas

        # Primary Energy Consumption (Input weighted by PEF)
        hourly_data[f'PrimaryEnergy_{j}_MWh'] = [] # e.g., Primary Energy for Boiler_Gas
        
        # Fuel cost for each technology
        hourly_data[f'FuelCost_{j}_EUR'] = [] # Fuel cost for each technology

        # Add specific columns for electric technologies if needed elsewhere
        if pe.value(instance.ec_j[j]) == "electricity":
            hourly_data[f'Elec_Use_{j}_MWh'] = [] # Gross electricity use
            hourly_data[f'PV_Used_By_{j}_MWh'] = [] # PV part of electricity use
            hourly_data[f'Hydro_Used_By_{j}_MWh'] = [] # Hydro part of electricity use

    # Add storage-related columns
    for hs in instance.j_hs:
        hourly_data[f'Storage_{hs}_Level_MWh'] = []
        hourly_data[f'Storage_{hs}_Flow_MWh'] = []  # Positive for charge, negative for discharge

    # Determine if dynamic PEFs are used
    use_dynamic_pef = hasattr(instance, 'pef_import_electricity_t')

    # For each hour, collect all the data
    for t in instance.t:
        # Convert hour to datetime
        hour_of_year = t - 1
        day = hour_of_year // 24
        hour = hour_of_year % 24
        date_str = f"2024-01-01 00:00:00"  # Starting date, January 1st 2024
        base_date = datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        current_date = base_date + datetime.timedelta(days=day, hours=hour)
        hourly_data['Date'].append(current_date.strftime("%Y-%m-%d %H:%M:%S"))
        
        # Primary energy flows
        hourly_data['Import_PrimaryEnergy_MWh'].append(pe.value(instance.E_import[t]))
        hourly_data['Export_PrimaryEnergy_MWh'].append(pe.value(instance.E_export[t]))
        hourly_data['Net_PrimaryEnergy_MWh'].append(pe.value(instance.E_export[t]) - pe.value(instance.E_import[t]))
        
        # PV data
        if hasattr(instance, 'pv_generation_t'):
            hourly_data['PV_Generation_MWh'].append(pe.value(instance.pv_generation_t[t]))
            hourly_data['PV_Used_Locally_MWh'].append(pe.value(instance.pv_used_t[t]))
            hourly_data['PV_Exported_MWh'].append(pe.value(instance.pv_export_t[t]))
        else:
            hourly_data['PV_Generation_MWh'].append(0)
            hourly_data['PV_Used_Locally_MWh'].append(0)
            hourly_data['PV_Exported_MWh'].append(0)
        
        # Hydro data
        if hasattr(instance, 'hydro_excess_t'):
            hourly_data['Hydro_Available_MWh'].append(pe.value(instance.hydro_excess_t[t]))
            hourly_data['Hydro_Used_MWh'].append(pe.value(instance.hydro_used_t[t]))
            hourly_data['Hydro_Exported_MWh'].append(pe.value(instance.hydro_export_t[t]))
        else:
            hourly_data['Hydro_Available_MWh'].append(0)
            hourly_data['Hydro_Used_MWh'].append(0)
            hourly_data['Hydro_Exported_MWh'].append(0)
        
        # Grid import data
        grid_import = 0
        if hasattr(instance, 'grid_import_t'):
            grid_import = pe.value(instance.grid_import_t[t])
            hourly_data['Grid_Import_MWh'].append(grid_import)
        else:
            hourly_data['Grid_Import_MWh'].append(0)
        
        # Heat demand (original and after refurbishment)
        original_demand = pe.value(instance.demand_th_t[t])
        hourly_data['Demand_Heat_MWh'].append(original_demand)
        
        # After-refurbishment heat demand
        if hasattr(instance, 'demand_th_reduced'):
            reduced_demand = pe.value(instance.demand_th_reduced[t])
            hourly_data['Demand_Heat_Reduced_MWh'].append(reduced_demand)
            hourly_data['Heat_Saved_MWh'].append(original_demand - reduced_demand)
        else:
            # If no refurbishment model, reduced demand equals original demand
            hourly_data['Demand_Heat_Reduced_MWh'].append(original_demand)
            hourly_data['Heat_Saved_MWh'].append(0)
        
        # Economic calculations - get reference technology for pricing
        elec_techs = [j for j in instance.j if pe.value(instance.ec_j[j]) == "electricity"]
        ref_tech = elec_techs[0] if elec_techs else list(instance.j)[0]
        
        # Grid electricity cost
        if hasattr(instance, 'grid_cost_t'):
            grid_price = pe.value(instance.grid_cost_t[t])
        elif hasattr(instance, 'electricity_price_jt'):
            grid_price = pe.value(instance.electricity_price_jt[ref_tech, t])
        else:
            grid_price = 0
        
        grid_cost = grid_import * grid_price
        hourly_data['Grid_Import_Cost_EUR'].append(grid_cost)
        hourly_data['Grid_Import_Price_EUR_MWh'].append(grid_price)
        
        # PV export revenue
        pv_exported = pe.value(instance.pv_export_t[t]) if hasattr(instance, 'pv_export_t') else 0
        if hasattr(instance, 'pv_export_price_t'):
            pv_export_price = pe.value(instance.pv_export_price_t[t])
        else:
            pv_export_price = grid_price * 0.7  # Assume 70% of grid price
        
        pv_export_revenue = pv_exported * pv_export_price
        hourly_data['PV_Export_Revenue_EUR'].append(pv_export_revenue)
        hourly_data['PV_Export_Price_EUR_MWh'].append(pv_export_price)
        
        # Hydro electricity cost and revenue
        hydro_used = pe.value(instance.hydro_used_t[t]) if hasattr(instance, 'hydro_used_t') else 0
        hydro_exported = pe.value(instance.hydro_export_t[t]) if hasattr(instance, 'hydro_export_t') else 0
        
        if hasattr(instance, 'hydro_cost_t'):
            hydro_price = pe.value(instance.hydro_cost_t[t])
        else:
            hydro_price = 0  # Assume free hydro
        
        if hasattr(instance, 'hydro_export_price_t'):
            hydro_export_price = pe.value(instance.hydro_export_price_t[t])
        else:
            hydro_export_price = grid_price * 0.7  # Assume 70% of grid price
        
        hydro_cost = hydro_used * hydro_price
        hydro_export_revenue = hydro_exported * hydro_export_price
        
        hourly_data['Hydro_Used_Cost_EUR'].append(hydro_cost)
        hourly_data['Hydro_Used_Price_EUR_MWh'].append(hydro_price)
        hourly_data['Hydro_Export_Revenue_EUR'].append(hydro_export_revenue)
        hourly_data['Hydro_Export_Price_EUR_MWh'].append(hydro_export_price)
        
        # CHP electricity revenue
        chp_revenue = 0
        if hasattr(instance, 'j_chp') and hasattr(instance, 'sale_electricity_price_jt'):
            for j in instance.j_chp:
                chp_elec_gen = pe.value(instance.x_el_jt[j, t])
                chp_price = pe.value(instance.sale_electricity_price_jt[j, t])
                chp_revenue += chp_elec_gen * chp_price
        
        hourly_data['CHP_Electricity_Revenue_EUR'].append(chp_revenue)
        
        # Total fuel costs for all technologies
        total_fuel_cost = 0
        if hasattr(instance, 'mc_jt'):
            for j in instance.j:
                if pe.value(instance.ec_j[j]) != "electricity":  # Non-electric technologies have fuel costs
                    fuel_cost = pe.value(instance.x_th_jt[j, t]) * pe.value(instance.mc_jt[j, t])
                    total_fuel_cost += fuel_cost
        
        hourly_data['Total_Fuel_Cost_EUR'].append(total_fuel_cost)
        
        # Total costs and revenues
        total_elec_cost = grid_cost + hydro_cost
        total_elec_revenue = pv_export_revenue + hydro_export_revenue + chp_revenue
        net_elec_cost = total_elec_cost - total_elec_revenue
        
        hourly_data['Total_Electricity_Cost_EUR'].append(total_elec_cost)
        hourly_data['Total_Electricity_Revenue_EUR'].append(total_elec_revenue)
        hourly_data['Net_Electricity_Cost_EUR'].append(net_elec_cost)
        
        # Technology dispatch
        for j in instance.j:
            hourly_data[f'Heat_Gen_{j}_MWh'].append(pe.value(instance.x_th_jt[j, t]))
            
            # For electric technologies, add electricity consumption
            if pe.value(instance.ec_j[j]) == "electricity":
                elec_consumption = pe.value(instance.x_th_jt[j, t]) / pe.value(instance.n_th_jt[j, t])
                hourly_data[f'Elec_Use_{j}_MWh'].append(elec_consumption)
                
                # PV used by this technology
                if hasattr(instance, 'pv_used_j_t'):
                    hourly_data[f'PV_Used_By_{j}_MWh'].append(pe.value(instance.pv_used_j_t[j, t]))
                else:
                    hourly_data[f'PV_Used_By_{j}_MWh'].append(0)
                    
                # Hydro used by this technology
                if hasattr(instance, 'hydro_used_j_t'):
                    hourly_data[f'Hydro_Used_By_{j}_MWh'].append(pe.value(instance.hydro_used_j_t[j, t]))
                else:
                    hourly_data[f'Hydro_Used_By_{j}_MWh'].append(0)
            
            # Energy Carrier Consumption
            carrier_use = pe.value(instance.x_th_jt[j, t]) / pe.value(instance.n_th_jt[j, t])
            hourly_data[f'CarrierUse_{j}_MWh'].append(carrier_use)
            
            # Primary Energy Consumption
            if pe.value(instance.ec_j[j]) == "electricity":
                if use_dynamic_pef:
                    pef = pe.value(instance.pef_import_electricity_t[t])
                else:
                    pef = pe.value(instance.pef_import_electricity)
                primary_energy = carrier_use * pef
            elif pe.value(instance.ec_j[j]) == "biomass":
                pef = pe.value(instance.pef_biomass)
                primary_energy = carrier_use * pef
            elif pe.value(instance.ec_j[j]) == "natural gas":
                pef = pe.value(instance.pef_natural_gas)
                primary_energy = carrier_use * pef
            elif pe.value(instance.ec_j[j]) == "straw":
                pef = pe.value(instance.pef_straw)
                primary_energy = carrier_use * pef
            elif pe.value(instance.ec_j[j]) == "radiation":
                pef = pe.value(instance.pef_radiation)
                primary_energy = carrier_use * pef
            elif pe.value(instance.ec_j[j]) == "wood chips":
                pef = pe.value(instance.pef_wood_chips)
                primary_energy = carrier_use * pef
            elif pe.value(instance.ec_j[j]) == "wood pellets":
                pef = pe.value(instance.pef_wood_pellets)
                primary_energy = carrier_use * pef
            elif pe.value(instance.ec_j[j]) == "waste":
                pef = pe.value(instance.pef_waste)
                primary_energy = carrier_use * pef
            elif pe.value(instance.ec_j[j]) == "waste heat 20":
                pef = pe.value(instance.pef_waste_heat_20)
                primary_energy = carrier_use * pef
            elif pe.value(instance.ec_j[j]) == "waste heat 40":
                pef = pe.value(instance.pef_waste_heat_40)
                primary_energy = carrier_use * pef
            else:
                pef = pe.value(instance.pef_various)
                primary_energy = carrier_use * pef
            
            hourly_data[f'PrimaryEnergy_{j}_MWh'].append(primary_energy)
            
            # Fuel cost for this technology
            if pe.value(instance.ec_j[j]) != "electricity" and hasattr(instance, 'mc_jt'):
                fuel_cost = pe.value(instance.x_th_jt[j, t]) * pe.value(instance.mc_jt[j, t])
            else:
                fuel_cost = 0  # Electric technologies don't have fuel costs
            hourly_data[f'FuelCost_{j}_EUR'].append(fuel_cost)
        
        # Storage data
        for hs in instance.j_hs:
            hourly_data[f'Storage_{hs}_Level_MWh'].append(pe.value(instance.store_level_hs_t[hs, t]))
            hourly_data[f'Storage_{hs}_Flow_MWh'].append(pe.value(instance.x_load_hs_t[hs, t]))
    
    # Create a DataFrame with all the data
    dispatch_df = pd.DataFrame(hourly_data)
    
    # Calculate primary energy factors used for each hour
    if use_dynamic_pef:
        # If using dynamic PEF
        dispatch_df['PEF_Import_Electricity'] = [pe.value(instance.pef_import_electricity_t[t]) for t in instance.t]
        dispatch_df['PEF_Export_Electricity'] = [pe.value(instance.pef_export_electricity_t[t]) for t in instance.t]
    else:
        # If using static PEF
        dispatch_df['PEF_Import_Electricity'] = pe.value(instance.pef_import_electricity)
        dispatch_df['PEF_Export_Electricity'] = pe.value(instance.pef_export_electricity)
    
    # Add some aggregate statistics as additional columns
    dispatch_df['Total_Heat_Generation'] = dispatch_df[[col for col in dispatch_df.columns if col.startswith('Heat_Gen_')]].sum(axis=1)
    
    if any(col.startswith('Elec_Use_') for col in dispatch_df.columns):
        dispatch_df['Total_Electricity_Consumption'] = dispatch_df[[col for col in dispatch_df.columns if col.startswith('Elec_Use_')]].sum(axis=1)
    
    if any(col.startswith('PV_Used_By_') for col in dispatch_df.columns):
        dispatch_df['Total_PV_Used_By_Technologies'] = dispatch_df[[col for col in dispatch_df.columns if col.startswith('PV_Used_By_')]].sum(axis=1)
    
    if any(col.startswith('Hydro_Used_By_') for col in dispatch_df.columns):
        dispatch_df['Total_Hydro_Used_By_Technologies'] = dispatch_df[[col for col in dispatch_df.columns if col.startswith('Hydro_Used_By_')]].sum(axis=1)
    
    # Calculate the PED balance for each hour (>0 means positive energy district)
    dispatch_df['Hourly_PED_Balance'] = dispatch_df['Export_PrimaryEnergy_MWh'] - dispatch_df['Import_PrimaryEnergy_MWh']
    
    # Save the dataframe to CSV in output folder
    import os
    output_dir = 'output'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    csv_filename = f'{ped_balance_horizon}_{ped_mode}_dispatch_data_CC_kranj.csv'
    csv_filepath = os.path.join(output_dir, csv_filename)
    dispatch_df.to_csv(csv_filepath, index=False)
    
    print(f"\nDetailed hourly dispatch data saved to {csv_filepath}")
    
    # Generate summary statistics
    print("\n=== Dispatch Summary Statistics ===")
    print(f"Total Heat Demand (Original): {dispatch_df['Demand_Heat_MWh'].sum():.2f} MWh")
    print(f"Total Heat Demand (After Refurbishment): {dispatch_df['Demand_Heat_Reduced_MWh'].sum():.2f} MWh")
    print(f"Total Heat Saved through Refurbishment: {dispatch_df['Heat_Saved_MWh'].sum():.2f} MWh")
    if dispatch_df['Demand_Heat_MWh'].sum() > 0:
        savings_percentage = (dispatch_df['Heat_Saved_MWh'].sum() / dispatch_df['Demand_Heat_MWh'].sum()) * 100
        print(f"Heat Demand Reduction: {savings_percentage:.2f}%")
        print("Note: Refurbishment savings = Original Demand - Reduced Demand (excludes system losses)")
    print(f"Total Heat Generation: {dispatch_df['Total_Heat_Generation'].sum():.2f} MWh")
    
    # Heat balance analysis - explain why generation exceeds demand
    heat_generation = dispatch_df['Total_Heat_Generation'].sum() 
    heat_demand = dispatch_df['Demand_Heat_Reduced_MWh'].sum()
    system_losses = heat_generation - heat_demand
    loss_percentage = (system_losses / heat_generation * 100) if heat_generation > 0 else 0
    
    print(f"\n--- Energy Balance ---")
    print(f"Heat Generation: {heat_generation:.2f} MWh")
    print(f"Heat Demand (Reduced): {heat_demand:.2f} MWh") 
    print(f"System Losses: {system_losses:.2f} MWh ({loss_percentage:.3f}%)")
    print("Note: Generation > Demand due to storage/conversion efficiency losses.")
    
    if 'Total_Electricity_Consumption' in dispatch_df.columns:
        print(f"Total Electricity Consumption: {dispatch_df['Total_Electricity_Consumption'].sum():.2f} MWh")
    
    if 'PV_Generation_MWh' in dispatch_df.columns:
        pv_gen = dispatch_df['PV_Generation_MWh'].sum()
        pv_used = dispatch_df['PV_Used_Locally_MWh'].sum()
        print(f"Total PV Generation: {pv_gen:.2f} MWh")
        print(f"Total PV Used Locally: {pv_used:.2f} MWh")
        print(f"PV Self-Consumption Ratio: {(pv_used/pv_gen*100) if pv_gen > 0 else 0:.2f}%")
    
    if 'Hydro_Available_MWh' in dispatch_df.columns:
        hydro_available = dispatch_df['Hydro_Available_MWh'].sum()
        hydro_used = dispatch_df['Hydro_Used_MWh'].sum()
        hydro_exported = dispatch_df['Hydro_Exported_MWh'].sum() if 'Hydro_Exported_MWh' in dispatch_df.columns else 0
        total_hydro_utilized = hydro_used + hydro_exported
        print(f"Total Hydro Available: {hydro_available:.2f} MWh")
        print(f"Total Hydro Used Locally: {hydro_used:.2f} MWh")
        print(f"Total Hydro Exported: {hydro_exported:.2f} MWh")
        print(f"Hydro Utilization Ratio: {(total_hydro_utilized/hydro_available*100) if hydro_available > 0 else 0:.2f}%")
    
    if 'Grid_Import_MWh' in dispatch_df.columns:
        grid_import = dispatch_df['Grid_Import_MWh'].sum()
        print(f"Total Grid Import: {grid_import:.2f} MWh")
        if 'Total_Electricity_Consumption' in dispatch_df.columns:
            total_elec = dispatch_df['Total_Electricity_Consumption'].sum()
            print(f"Grid Import Share: {(grid_import/total_elec*100) if total_elec > 0 else 0:.2f}% of total electricity")
    
    print(f"Total Primary Energy Import: {dispatch_df['Import_PrimaryEnergy_MWh'].sum():.2f} MWh")
    print(f"Total Primary Energy Export: {dispatch_df['Export_PrimaryEnergy_MWh'].sum():.2f} MWh")
    print(f"Net Primary Energy Balance: {(dispatch_df['Export_PrimaryEnergy_MWh'].sum() - dispatch_df['Import_PrimaryEnergy_MWh'].sum()):.2f} MWh")
    
    # Economic summary
    print(f"\n--- Economic Summary ---")
    print(f"Total Grid Import Cost: {dispatch_df['Grid_Import_Cost_EUR'].sum():.2f} EUR")
    print(f"Average Grid Price: {dispatch_df['Grid_Import_Price_EUR_MWh'].mean():.2f} EUR/MWh")
    
    if dispatch_df['PV_Export_Revenue_EUR'].sum() > 0:
        print(f"Total PV Export Revenue: {dispatch_df['PV_Export_Revenue_EUR'].sum():.2f} EUR")
        print(f"Average PV Export Price: {dispatch_df['PV_Export_Price_EUR_MWh'].mean():.2f} EUR/MWh")
    
    if dispatch_df['Hydro_Used_Cost_EUR'].sum() > 0:
        print(f"Total Hydro Cost: {dispatch_df['Hydro_Used_Cost_EUR'].sum():.2f} EUR")
        print(f"Average Hydro Price: {dispatch_df['Hydro_Used_Price_EUR_MWh'].mean():.2f} EUR/MWh")
    
    if dispatch_df['Hydro_Export_Revenue_EUR'].sum() > 0:
        print(f"Total Hydro Export Revenue: {dispatch_df['Hydro_Export_Revenue_EUR'].sum():.2f} EUR")
        print(f"Average Hydro Export Price: {dispatch_df['Hydro_Export_Price_EUR_MWh'].mean():.2f} EUR/MWh")
    
    if dispatch_df['CHP_Electricity_Revenue_EUR'].sum() > 0:
        print(f"Total CHP Electricity Revenue: {dispatch_df['CHP_Electricity_Revenue_EUR'].sum():.2f} EUR")
    
    print(f"Total Fuel Costs: {dispatch_df['Total_Fuel_Cost_EUR'].sum():.2f} EUR")
    print(f"Total Electricity Costs: {dispatch_df['Total_Electricity_Cost_EUR'].sum():.2f} EUR")
    print(f"Total Electricity Revenues: {dispatch_df['Total_Electricity_Revenue_EUR'].sum():.2f} EUR")
    print(f"Net Electricity Cost: {dispatch_df['Net_Electricity_Cost_EUR'].sum():.2f} EUR")
    print(f"Total Energy Costs (Fuel + Net Electricity): {(dispatch_df['Total_Fuel_Cost_EUR'].sum() + dispatch_df['Net_Electricity_Cost_EUR'].sum()):.2f} EUR")
    
    # Price analysis
    if dispatch_df['Grid_Import_MWh'].sum() > 0:
        avg_grid_price = dispatch_df['Grid_Import_Cost_EUR'].sum() / dispatch_df['Grid_Import_MWh'].sum()
        print(f"Weighted Average Grid Price: {avg_grid_price:.2f} EUR/MWh")
    
    # Find hours with highest and lowest electricity costs
    print(f"\n--- Peak Cost Hours ---")
    top_cost_hours = dispatch_df.nlargest(5, 'Net_Electricity_Cost_EUR')[['Hour', 'Date', 'Net_Electricity_Cost_EUR', 'Grid_Import_Price_EUR_MWh']]
    print("Top 5 hours with highest net electricity cost:")
    for _, row in top_cost_hours.iterrows():
        print(f"  Hour {int(row['Hour'])}: {row['Net_Electricity_Cost_EUR']:.2f} EUR (Grid price: {row['Grid_Import_Price_EUR_MWh']:.2f} EUR/MWh)")
    
    # Return the dataframe for potential further analysis
    return dispatch_df
