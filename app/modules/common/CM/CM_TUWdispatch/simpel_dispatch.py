# -*- coding: utf-8 -*-
"""
Created on Tue Sep 26 11:52:51 2017
changed on Tue Aug 20 2024 (nirav) - added the ped specific constraints
changes on Tue Jan 07 2025 (nirav) - added the dynamic pef values
changes on Tue Jan 22 2025 (nirav) - added the PV generation and usage constraints
changes on Tue Jan 28 2025 (nirav) - added PV electricity usage allocation for heat pumps and electric boilers
changes on Tue Feb 05 2025 (nirav) - added hydro power excess generation and usage

@author: Nirav
"""
#%% Import needed modules
import pyomo.environ as pe
from datetime import datetime
from pyomo.opt import SolverStatus, TerminationCondition
import os
import sys
import pandas as pd
import numpy as np

path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.
                                                       abspath(__file__))))
if path not in sys.path:
    sys.path.append(path)
from CM.CM_TUWdispatch.preprocessing import preprocessing

#import logging
#logging.getLogger('pyomo.core').setLevel(logging.ERROR)

ped_mode="dynamic"
ped_mode="static"
ped_mode="refurb"

# Define check_pv_usage here so it can be accessed by the run function
def check_pv_usage(instance):
    """ Analyzes the PV electricity usage and export from the Pyomo model instance."""
    pv_summary = {
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
            print(f"{key}: {value:.2f} MWh")
        
    print("\nPV Usage by Technology:")
    for tech, amount in pv_summary["PV Used by Technology"].items():
        print(f"  {tech}: {amount:.2f} MWh")

    return pv_summary

# Define a function to check hydro usage
def check_hydro_usage(instance):
    """ Analyzes the hydro electricity usage and export from the Pyomo model instance."""
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
    # First try to find an electric technology
    elec_techs = [j for j in instance.j if pe.value(instance.ec_j[j]) == "electricity"]
    if elec_techs:
        ref_tech = elec_techs[0]  # Use first electric technology as reference
    else:
        # Fallback to first technology if no electric tech exists
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
    """ Analyzes the grid electricity usage from the Pyomo model instance."""
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
    # First try to find an electric technology
    elec_techs = [j for j in instance.j if pe.value(instance.ec_j[j]) == "electricity"]
    if elec_techs:
        ref_tech = elec_techs[0]  # Use first electric technology as reference
    else:
        # Fallback to first technology if no electric tech exists
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
        # First check if we have direct grid cost parameter, otherwise use electricity price
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
    # For example, print the top 5 hours with highest grid import
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
    import pandas as pd
    import numpy as np

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
        'Heat_Saved_MWh': []  # Amount of heat saved through refurbishment
    }

    # Add technology-specific columns dynamically
    for j in instance.j:
        # Heat Generation (Output)
        hourly_data[f'Heat_Gen_{j}_MWh'] = []

        # Energy Carrier Consumption (Input)
        hourly_data[f'CarrierUse_{j}_MWh'] = [] # e.g., Gas used by Boiler_Gas

        # Primary Energy Consumption (Input weighted by PEF)
        hourly_data[f'PrimaryEnergy_{j}_MWh'] = [] # e.g., Primary Energy for Boiler_Gas

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
        import datetime
        base_date = datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        # Removed the "day-1" which was causing dates to start on Dec 31st
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
        if hasattr(instance, 'grid_import_t'):
            hourly_data['Grid_Import_MWh'].append(pe.value(instance.grid_import_t[t]))
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
    
    # Save the dataframe to CSV
    csv_filename = f'{ped_balance_horizon}_{ped_mode}_dispatch_data_PED.csv'
    dispatch_df.to_csv(csv_filename, index=False)
    print(f"\nDetailed hourly dispatch data saved to {csv_filename}")
    
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
    
    # Return the dataframe for potential further analysis
    return dispatch_df

def run(data,inv_flag,selection=[[],[]],demand_f=1,ped_mode="dynamic", ped_balance_horizon="yearly"):
    #%% Creation of a  Model
    m = pe.AbstractModel()

    #%% Sets - TODO: depends on how the input data looks finally
    val,message = preprocessing(data,demand_f,inv_flag,selection)
    
    if val == "Error1":
        return (val,message)
    elif val == "Error2":
        return (val,message)

    if ped_balance_horizon == 'seasonal':
        def get_season(hour_of_year_1_indexed):
            # Using 2023 as a non-leap year to match 8760 hours.
            # The model uses 1-based indexing for `t`.
            day_of_year = (hour_of_year_1_indexed - 1) // 24
            # Day 0 is Jan 1.
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

    m.j_hp_new = pe.Set(initialize=val["j_hp_new"])
    m.t = pe.RangeSet(1,8760)
    m.j = pe.Set(initialize = val["j"])
    m.j_hp = pe.Set(initialize = val["j_hp"])
    m.j_pth = pe.Set(initialize = val["j_pth"])
    m.j_st = pe.Set(initialize = val["j_st"])
    m.j_waste = pe.Set(initialize = val["j_waste"])
    m.j_chp = pe.Set(initialize = val["j_chp"])
    m.j_bp = pe.Set(initialize = val["j_bp"])
    m.j_wh = pe.Set(initialize = val["j_wh"])
    m.j_gt = pe.Set(initialize = val["j_gt"])
    m.j_hs = pe.Set(initialize = val["j_hs"])
    m.j_air_heat_pump = pe.Set(initialize = val["j_air_heat_pump"])
    m.j_river_heat_pump = pe.Set(initialize = val["j_river_heat_pump"])
    m.j_wastewater_heat_pump = pe.Set(initialize = val["j_wastewater_heat_pump"])
    m.j_wasteheat_heat_pump = pe.Set(initialize = val["j_wasteheat_heat_pump"])
    # m.j_excessheat_heat_pump = pe.Set(initialize = val["j_excessheat_heat_pump"])
    m.all_heat_geneartors = pe.Set(initialize = val["all_heat_geneartors"])
    #%% Parameter - TODO: depends on how the input data looks finally
    m.demand_th_t = pe.Param(m.t,initialize = val["demand_th_t"])
    m.temp_river = pe.Param(m.t,initialize = val["temp_river"])
    m.temp_waste_water = pe.Param(m.t,initialize = val["temp_waste_water"])
    # m.temp_excess_heat = pe.Param(m.t,initialize = val["temp_excess_heat"])
    m.temp_flow = pe.Param(m.t,initialize = val["temp_flow"])
    m.temp_return = pe.Param(m.t,initialize = val["temp_return"])
    m.temp_ambient = pe.Param(m.t,initialize = val["temp_ambient"])
    m.radiation = pe.Param(m.t,initialize = val["radiation"])
    
    max_demad = val["max_demad"]
    m.potential_j = pe.Param(m.j,initialize=val["potential_j"])
    m.pow_cap_j = pe.Param(m.j,initialize=val["pow_cap_j"])
    m.radiation_t = pe.Param(m.t,initialize=val["radiation_t"])
    m.IK_j = pe.Param(m.j,initialize=val["IK_j"])
    m.OP_fix_j = pe.Param(m.j,initialize=val["OP_fix_j"])
    m.n_el_j = pe.Param(m.j ,initialize=val["n_el_j"])
    m.electricity_price_jt = pe.Param(m.j,m.t,initialize=val["electricity_price_jt"])
    m.P_min_el_chp = pe.Param(initialize=val["P_min_el_chp"])
    m.Q_min_th_chp = pe.Param(initialize=val["Q_min_th_chp"])
    m.ratioPMaxFW = pe.Param(initialize=val["ratioPMaxFW"])
    m.ratioPMax = pe.Param(initialize=val["ratioPMax"])
    m.mc_jt = pe.Param(m.j,m.t,initialize= val["mc_jt"])
    m.n_th_jt = pe.Param(m.j,m.t,initialize=val["n_th_jt"])
    m.hp_restriction_factor_jt = pe.Param(m.j,m.t,initialize=val["hp_restriction_factor_jt"])
    m.nom_p_th_j = pe.Param(m.j,initialize=val["nom_p_th_j"])
    m.min_p_th_j = pe.Param(m.j,initialize=val["min_p_th_j"])
    m.x_th_cap_j = pe.Param(m.j,initialize=val["x_th_cap_j"])
#    m.x_el_cap_j = pe.Param(m.j,initialize=val["x_el_cap_j"])
#    m.pot_j = pe.Param(m.j,initialize=val["pot_j"])
    m.lt_j = pe.Param(m.j,initialize=val["lt_j"])
    m.ec_j = pe.Param(m.j,initialize=val["ec_j"],within=pe.Any)
    renewable_carriers = ["wood pellets", "wood chips", "biomass", "straw", "radiation"]
    print(m.ec_j)
#    m.el_surcharge = pe.Param(m.j,initialize=val[27])  # Taxes for electricity price
    m.ir = pe.Param(initialize=val["ir"])
    m.alpha_j = pe.Param(m.j,initialize=val["alpha_j"])

    m.load_cap_hs  = pe.Param(m.j_hs,initialize=val["load_cap_hs"])
    m.unload_cap_hs  = pe.Param(m.j_hs,initialize=val["unload_cap_hs"])
    m.n_hs = pe.Param(m.j_hs,initialize=val["n_hs"])
    m.loss_hs = pe.Param(m.j_hs,initialize=val["loss_hs"])
    m.IK_hs = pe.Param(m.j_hs,initialize=val["IK_hs"])
    m.cap_hs = pe.Param(m.j_hs,initialize=val["cap_hs"])
    m.c_ramp_j = pe.Param(m.j,initialize =val["c_ramp_j"] ) 
    m.c_coldstart_j = pe.Param(m.j,initialize=val["c_coldstart_j"])
    m.alpha_hs = pe.Param(m.j_hs,initialize=val["alpha_hs"])

    m.rf_j = pe.Param(m.j,initialize=val["rf_j"])
    m.rf_tot = pe.Param(initialize=val["rf_tot"])
    m.OP_var_j = pe.Param(m.j,initialize=val["OP_var_j"])
    
    # Try to initialize temperature_t, but handle errors
    try:
        m.temperature_t = pe.Param(m.t,initialize=val["temperature_t"])
    except KeyError:
        print("Warning: temperature_t not found in data, using temperature instead")
        m.temperature_t = pe.Param(m.t,initialize=val["temperature"])
    
    m.sale_electricity_price_jt = pe.Param(m.j,m.t,initialize=val["sale_electricity_price_jt"])
    m.OP_fix_hs = pe.Param(m.j_hs,initialize=val["OP_fix_hs"])

    m.mr_j = pe.Param(m.j, initialize = val["mr_j"])
    m.em_j = pe.Param(m.j, initialize = val["em_j"])
    m.pco2 = pe.Param(initialize = val["pco2"])
    
    m.cap_losse_hs = pe.Param(m.j_hs,initialize=val["cap_losse_hs"])
    m.n_th_nom_jt = pe.Param(m.j,m.t,initialize=val["n_th_nom_jt"])
    m.restriction_factor_jt = pe.Param(m.j,m.t,initialize=val["restriction_factor_jt"])
    m.min_out_factor_j = pe.Param(m.j,initialize=val["min_out_factor_j"])

    # PV Parameters

    # Define the Excel file path once
    excel_file = "C:\\Users\\Nirav\\OneDrive - TU Wien\\Desktop\\PED_SupplyOptimization\\hotmapsDispatch\\app\\modules\\common\\CM\\CM_TUWdispatch\\Slovenia_hourly_generation_2024.xlsx"
    
    # Check if the Excel file exists
    if not os.path.exists(excel_file):
        raise FileNotFoundError(f"Excel file not found: {excel_file}")

    try:
        # Read all required sheets at once
        excel_data = pd.read_excel(excel_file, sheet_name=['PV', 'PEF_values', 'PED_status', 'PEF', 'Excess Hydro', 'Refurbishment'])
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        raise

    # 1. Process PV parameters - handle the row-based structure
    try:
        pv_df = excel_data['PV']
        print("PV sheet columns:", pv_df.columns.tolist())
        print("PV sheet shape:", pv_df.shape)
        print("First few rows of PV sheet:")
        print(pv_df.head())
        
        # Convert row-based data to a lookup dictionary
        pv_data = {}
        for i, row in pv_df.iterrows():
            key = row.iloc[0]  # First column contains the parameter name
            value = row.iloc[1]  # Second column contains the value
            pv_data[key] = value
        
        print("Available PV data keys:", list(pv_data.keys()))
        
        # Map the actual parameter names to expected values with error handling
        expected_keys = ['performance_ratio', 'area_available', 'panel_efficiency', 'invest_cost', 'alpha', 'om_fix']
        missing_keys = [key for key in expected_keys if key not in pv_data]
        if missing_keys:
            print(f"Missing PV data keys: {missing_keys}")
            print(f"Available keys: {list(pv_data.keys())}")
            raise KeyError(f"Missing required PV parameters: {missing_keys}")
        
        m.pv_performance_ratio = pe.Param(initialize=float(pv_data['performance_ratio']))
        m.pv_area_available = pe.Param(initialize=float(pv_data['area_available']))
        m.pv_efficiency = pe.Param(initialize=float(pv_data['panel_efficiency']), mutable=True)
        m.PV_invest_cost = pe.Param(initialize=float(pv_data['invest_cost']), within=pe.NonNegativeReals)
        m.alpha_pv = pe.Param(initialize=float(pv_data['alpha']), within=pe.NonNegativeReals)
        m.PV_om_fix = pe.Param(initialize=float(pv_data['om_fix']), within=pe.NonNegativeReals)  # Set to 0 if not available
        
    except KeyError as e:
        print(f"KeyError in PV data processing: {e}")
        raise
    except Exception as e:
        print(f"Error processing PV data: {e}")
        raise

    # 2. Process PEF values - handle the row-based structure
    try:
        pef_df = excel_data['PEF_values']
        print("PEF_values sheet columns:", pef_df.columns.tolist())
        print("PEF_values sheet shape:", pef_df.shape)
        print("First few rows of PEF_values sheet:")
        print(pef_df.head())
        
        # Convert row-based data to a lookup dictionary
        pef_data = {}
        for i, row in pef_df.iterrows():
            key = row.iloc[0]  # First column contains the parameter name
            value = row.iloc[1]  # Second column contains the value
            pef_data[key] = value

        print("Available PEF data keys:", list(pef_data.keys()))
        
        # Map the actual parameter names to expected values with error handling
        expected_pef_keys = ['static_electricity_import', 'static_electricity_export', 'CHP_gas', 'fossil_fuel', 
                            'natural_gas', 'straw', 'various', 'waste', 'waste_heat_20', 'waste_heat_40',
                            'wood_chips', 'wood_pellets', 'radiation']
        missing_pef_keys = [key for key in expected_pef_keys if key not in pef_data]
        if missing_pef_keys:
            print(f"Missing PEF data keys: {missing_pef_keys}")
            print(f"Available PEF keys: {list(pef_data.keys())}")
            raise KeyError(f"Missing required PEF parameters: {missing_pef_keys}")

        # Map the actual parameter names to expected values
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
        
    except KeyError as e:
        print(f"KeyError in PEF data processing: {e}")
        raise
    except Exception as e:
        print(f"Error processing PEF data: {e}")
        raise


    # 3. Process PED status
    try:
        ped_df = excel_data['PED_status']
        print("PED_status sheet columns:", ped_df.columns.tolist())
        print("PED_status sheet shape:", ped_df.shape)
        print("PED_status sheet contents:")
        print(ped_df)
        print("PED_status sheet dtypes:")
        print(ped_df.dtypes)
        
        PED_status = None
        
        if PED_status is None and 'PED_status' in ped_df.columns:
            # Look for numeric columns that might contain the value
            for col in ped_df.columns:
                if col != 'PED_status':
                    try:
                        potential_value = float(col)
                        print(f"Case 2 - Found potential PED_status value in column header: {potential_value}")
                        PED_status = potential_value
                        break
                    except (ValueError, TypeError):
                        continue
        
        # Validate and finalize PED_status
        if PED_status is not None:
            if 0 <= PED_status <= 1:
                print(f"PED_status successfully set to: {PED_status}")
            else:
                print(f"Warning: PED_status value {PED_status} is outside range [0,1], using default value of 1.0")
                PED_status = 1.0
        else:
            PED_status = 1.0  # Default value if no valid value found
            print("Warning: Could not find valid PED_status value, using default value of 1.0")
            
    except KeyError as e:
        print(f"KeyError in PED_status processing: {e}")
        PED_status = 1.0
        print("Using default PED_status = 1.0")
    except Exception as e:
        print(f"Error processing PED_status: {e}")
        PED_status = 1.0
        print("Using default PED_status = 1.0")

    # 4. Process hourly PEF data
    try:
        pef_hourly_df = excel_data['PEF']
        print("PEF hourly sheet columns:", pef_hourly_df.columns.tolist())
        print("PEF hourly sheet shape:", pef_hourly_df.shape)
        
        if not {'Hour', 'pef_import', 'pef_export', 'El_cost'}.issubset(pef_hourly_df.columns):
            raise ValueError("The 'PEF' sheet must contain columns: 'Hour', 'pef_import', 'pef_export', 'El_cost'")

        # Convert hourly data to dictionaries
        pef_import_electricity_t = pef_hourly_df.set_index('Hour')['pef_import'].to_dict()
        pef_export_electricity_t = pef_hourly_df.set_index('Hour')['pef_export'].to_dict()
        El_cost_t = pef_hourly_df.set_index('Hour')['El_cost'].to_dict()
        
        # Handle optional columns
        Grid_cost_t = (pef_hourly_df.set_index('Hour')['Grid_cost'].to_dict() 
                      if 'Grid_cost' in pef_hourly_df.columns 
                      else El_cost_t)
        
        PV_export_price_t = (pef_hourly_df.set_index('Hour')['PV_export_price'].to_dict() 
                            if 'PV_export_price' in pef_hourly_df.columns 
                            else {t: El_cost_t[t] * 0.7 for t in El_cost_t})
        
        Hydro_export_price_t = (pef_hourly_df.set_index('Hour')['Hydro_export_price'].to_dict() 
                               if 'Hydro_export_price' in pef_hourly_df.columns 
                               else {t: El_cost_t[t] * 0.7 for t in El_cost_t})
        
        # Zero marginal cost for on-site hydro utilization
        Hydro_cost_t = {t: 0 for t in El_cost_t}
        
    except KeyError as e:
        print(f"KeyError in hourly PEF data processing: {e}")
        raise
    except Exception as e:
        print(f"Error processing hourly PEF data: {e}")
        raise

    # 5. Process hydro excess data - handle the actual column name
    try:
        hydro_df = excel_data['Excess Hydro']
        print("Excess Hydro sheet columns:", hydro_df.columns.tolist())
        print("Excess Hydro sheet shape:", hydro_df.shape)
        
        # Check for the actual column name
        if 'Excess Energy (MWh)' in hydro_df.columns:
            hydro_excess_t = hydro_df.set_index('Hour')['Excess Energy (MWh)'].to_dict()
        elif 'Excess Energy' in hydro_df.columns:
            hydro_excess_t = hydro_df.set_index('Hour')['Excess Energy'].to_dict()
        else:
            print("Warning: Neither 'Excess Energy (MWh)' nor 'Excess Energy' column found in 'Excess Hydro' sheet")
            print("Available columns:", hydro_df.columns.tolist())
            hydro_excess_t = {t: 0 for t in range(1, 8761)}
        
        # Fill any missing hours with zeros
        for t in range(1, 8761):
            if t not in hydro_excess_t:
                hydro_excess_t[t] = 0
            
    except KeyError:
        print("Warning: 'Excess Hydro' sheet not found, using zeros for hydro excess")
        hydro_excess_t = {t: 0 for t in range(1, 8761)}
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

    #%% Variablen
    m.x_th_jt = pe.Var(m.j,m.t,within=pe.NonNegativeReals)
    m.Cap_j = pe.Var(m.j,within=pe.NonNegativeReals)
#     m.Cap_nom_j = pe.Var(m.j,within=pe.NonNegativeReals)
    m.x_el_jt = pe.Var(m.j,m.t,within=pe.NonNegativeReals)
#     m.P_el_max = pe.Var(within=pe.NonNegativeReals)

    m.x_load_hs_t = pe.Var(m.j_hs,m.t,within=pe.Reals)
#    m.x_unload_hs_t = pe.Var(m.j_hs,m.t,within=pe.NonNegativeReals)
    m.Cap_hs = pe.Var(m.j_hs,within=pe.NonNegativeReals)
    m.store_level_hs_t = pe.Var(m.j_hs,m.t,within=pe.NonNegativeReals)

    m.ramp_jt = pe.Var(m.j, m.t,within=pe.NonNegativeReals) 

    m.coldstart_jt = pe.Var(m.j, m.t, within = pe.Boolean)
    
    m.Active_jt = pe.Var(m.j,m.t, within = pe.Boolean)
    # m.Active2_jt = pe.Var(m.j,m.t, within = pe.Binary)
    # m.Active3_jt = pe.Var(m.j,m.t, within = pe.Binary)
#    m.Storage_load_hs_jt = pe.Var(m.j_hs,m.t, within = pe.Boolean)
#    m.Storage_unload_hs_jt = pe.Var(m.j_hs,m.t, within = pe.Boolean)
#    m.cop_HP_jt = pe.Var(m.j,m.t,within=pe.NonNegativeReals)

    #  PED specific variables
    m.E_import = pe.Var(m.t, within=pe.NonNegativeReals)  # Imported energy 
    m.E_export = pe.Var(m.t, within=pe.NonNegativeReals)  # Exported energy
    m.pv_capacity = pe.Var(within=pe.NonNegativeReals)  # PV capacity (max 5 MW)
    m.pv_generation_t = pe.Var(m.t, within=pe.NonNegativeReals)  # PV generation at time t
    m.pv_export_t = pe.Var(m.t, within=pe.NonNegativeReals)  # PV generation exported at time t

    
    # New variables for PV electricity usage allocation
    m.pv_used_t = pe.Var(m.t, within=pe.NonNegativeReals)  # Total PV electricity used locally at time t
    m.pv_used_j_t = pe.Var(m.j, m.t, within=pe.NonNegativeReals)  # PV electricity used by generator j at time t
    
    # New variables for hydro electricity usage allocation
    m.hydro_used_t = pe.Var(m.t, within=pe.NonNegativeReals)  # Total hydro electricity used at time t
    m.hydro_used_j_t = pe.Var(m.j, m.t, within=pe.NonNegativeReals)  # Hydro electricity used by generator j at time t
    m.hydro_export_t = pe.Var(m.t, within=pe.NonNegativeReals)  # Hydro electricity exported at time t
    
    # New variable for grid electricity import
    m.grid_import_t = pe.Var(m.t, within=pe.NonNegativeReals)  # Grid electricity imported at time t
    
    if ped_mode in ["static", "dynamic"]:
        m.include_refurb_cost = pe.Param(initialize=0)
    elif ped_mode == "refurb":
        m.include_refurb_cost = pe.Param(initialize=1)

    # 1) In your data or code, define the fraction of total demand that is space heating
    space_heat_fraction = 0.80   # or read from data

    # 2) Read refurbishment data from Excel file
    refurb_df = excel_data['Refurbishment']
    
    # Convert refurbishment data to dictionaries
    blocks_list = refurb_df['blocks'].dropna().astype(int).tolist()
    block_width_dict = {}
    cost_dict = {}
    
    for i, block_num in enumerate(blocks_list):
        if i < len(refurb_df):
            block_width_dict[block_num] = float(refurb_df['block_width_data'].iloc[i])
            cost_dict[block_num] = float(refurb_df['cost_data'].iloc[i])

    # Define blocks and parameters
    m.blocks = pe.Set(initialize=blocks_list)
    m.block_width = pe.Param(m.blocks, initialize=block_width_dict)
    m.block_cost  = pe.Param(m.blocks, initialize=cost_dict)

    # 3) Decision variables for how much fraction to use from each block
    def block_bounds_rule(m, i):
        return (0, m.block_width[i])  # each block can be used from 0..0.1
    m.x_save_fraction = pe.Var(m.blocks, within=pe.NonNegativeReals,initialize=0, bounds=block_bounds_rule)

    # 4) Expressions for total fraction saved and cost
    def fraction_saved_rule(m):
        return sum(m.x_save_fraction[i] for i in m.blocks)
    m.fraction_saved = pe.Expression(rule=fraction_saved_rule)

    def space_heating_demand_original_rule(m):
        # sum over t might be more complicated, but let's keep it simple
        # if your demand_th_t[t] is total, space+dhw, we do:
        # (we assume each time step has the same ratio for space heating)
        # but we can just do the total annual or so.
        # For a time-resolved approach, see below
        return sum(m.demand_th_t[t] for t in m.t) * space_heat_fraction
    m.space_heating_demand_original = pe.Expression(rule=space_heating_demand_original_rule)

    def mwh_saved_total_rule(m):
        return m.space_heating_demand_original * m.fraction_saved
    m.mwh_saved_total = pe.Expression(rule=mwh_saved_total_rule)

    def refurbishment_cost_rule(m):
        cost_sum = 0
        for i in m.blocks:
            # fraction used in block i
            frac_i = m.x_save_fraction[i]
            # MWh saved from that block
            block_mwh = m.space_heating_demand_original * frac_i
            # cost
            cost_sum += block_mwh * m.block_cost[i]
        return cost_sum
    m.refurbishment_cost = pe.Expression(rule=refurbishment_cost_rule)

    def demand_th_reduced_rule(m, t):
    # assume e.g. 80% is space heat, so only that portion is reducible
        space_portion = space_heat_fraction * m.demand_th_t[t]
    # we save fraction_saved from that portion
        saved_t = m.fraction_saved * space_portion
    # the 20% (DHW) remains
        return m.demand_th_t[t] - saved_t
    m.demand_th_reduced = pe.Expression(m.t, rule=demand_th_reduced_rule)

    #%% Nebenbedingungen
    def potential_restriction_rule_j(m,j):
        if m.potential_j[j] > 0: 
            rule = sum (m.x_th_jt[j,t] for t in m.t) <= m.potential_j[j]
        else:
            rule = pe.Constraint.Skip
        return rule
    m.potential_restriction_rule = pe.Constraint(m.j,rule=potential_restriction_rule_j) 
    
    def power_restriction_jt_rule(m,j,t):
        if m.pow_cap_j[j]>0:
            rule = m.x_th_jt[j,t] <=  m.pow_cap_j[j]
        else:
            rule = pe.Constraint.Skip            
        return rule
    m.power_restriction_jt = pe.Constraint(m.j,m.t,rule=power_restriction_jt_rule)    

    #% thermal output to electrical use (NEW)

    # def jt_el_consumption_rule(m,j,t):
    #     # only possible to HP and E-boiler tech
    #     if m.ec_j[j] == "electricity":
    #         return m.x_th_jt[j,t] == m.n_th_jt[j,t] * m.el_use_jt[j,t]
    #     else:
    #         return pe.Constraint.Skip
    # m.jt_el_consumption = pe.Constraint(m.j,m.t,rule=jt_el_consumption_rule)

    #% electircal power generation
    def gen_el_jt_rule(m,j,t):
        if j not in m.j_chp or m.n_th_jt[j,t] != 0:
            return m.x_el_jt[j,t] == m.x_th_jt[j,t] / m.n_th_jt[j,t] * m.n_el_j[j]
        else:
            return pe.Constraint.Skip
    m.gen_el_jt = pe.Constraint(m.j,m.t,rule=gen_el_jt_rule)

    #%  At any time, the heating generation must cover the actual heating demand
    if ped_mode == "refurb":
        def actual_demand_rule(m, t):
            return m.demand_th_reduced[t]
    else:
        def actual_demand_rule(m, t):
            return m.demand_th_t[t]
    m.actual_demand = pe.Expression(m.t, rule=actual_demand_rule)

    def genearation_covers_demand_t_rule(m,t):
        rule = sum([m.x_th_jt[j,t] for j in m.j]) - \
                    sum([m.x_load_hs_t[hs,t]  for hs in m.j_hs]) == demand_f * m.actual_demand[t]
        return rule
    m.genearation_covers_demand_t = pe.Constraint(m.t,rule=genearation_covers_demand_t_rule)

    def capacity_restriction_max_j_rule (m,j):
        #% ToDo: Define upper bound
        if inv_flag:
            rule = m.Cap_j[j]  <= demand_f*max_demad
        else:
            rule = m.Cap_j[j] == m.x_th_cap_j[j]
        return rule
    m.capacity_restriction_max_j = pe.Constraint(m.j,rule=capacity_restriction_max_j_rule)

    def capacity_restriction_min_j_rule (m,j):
        return m.Cap_j[j] >= m.x_th_cap_j[j]
    m.capacity_restriction_min_j = pe.Constraint(m.j,rule=capacity_restriction_min_j_rule)
    
    #% The amount of heat energy generated must not exceed the installed capacities
    def generation_restriction_jt_rule(m,j,t):
        rule = m.x_th_jt[j,t] <= m.Cap_j[j] / m.n_th_nom_jt[j,t] * m.n_th_jt[j,t]  * m.Active_jt[j,t] * m.restriction_factor_jt[j,t]
        return rule
    m.generation_restriction_jt = pe.Constraint(m.j,m.t,rule=generation_restriction_jt_rule)
    
    #% All Generators have a minimum Operating Power
    def generation_minimum_hp_jt_rule(m,j,t):
        rule = m.x_th_jt[j,t] >= m.Cap_j[j] / m.n_th_nom_jt[j,t] * m.n_th_jt[j,t]  * m.Active_jt[j,t] * m.min_out_factor_j[j]
        return rule
    m.generation_minimum_hp_jt = pe.Constraint(m.j,m.t,rule=generation_minimum_hp_jt_rule)


    def must_run_jt_rule(m,j,t):
        rule = m.x_th_jt[j,t] >= m.mr_j[j] * m.Cap_j[j] / m.n_th_nom_jt[j,t] * m.n_th_jt[j,t] * m.restriction_factor_jt[j,t] #  * m.Active3_jt[j,t]
        return rule
    m.mr_jt = pe.Constraint(m.j,m.t,rule=must_run_jt_rule)

    # def must_run_jt_rule2(m,j,t):
    #     rule = m.x_th_jt[j,t] >= m.demand_th_t[t]  * m.Active2_jt[j,t]
    #     return rule
    # m.mr_jt2 = pe.Constraint(m.j,m.t,rule=must_run_jt_rule2)
    
    # def must_run_jt_rule3(m,j,t):
    #     return m.Active2_jt[j,t] + m.Active3_jt[j,t] == 1
    # m.mr_jt3 = pe.Constraint(m.j,m.t,rule=must_run_jt_rule3) 
     #% mr specifies the amaount of capacity that has to run all the time. (0-1)

    #% The solar gains depend on the installed capacity and the solar radiation
    #% 1000 represent the radiation at wich the solar plant has maximal power 
    def solar_restriction_jt_rule(m,j,t):
        rule = m.x_th_jt[j,t] <=  m.Cap_j[j]*m.radiation_t[t] / max(val["radiation_t"].values())
        return rule
    m.solar_restriction_jt = pe.Constraint(m.j_st,m.t,rule=solar_restriction_jt_rule)
    
    
     # PV generation constraint
    def pv_generation_rule(m, t):
        rule = m.pv_generation_t[t] == m.pv_capacity * m.pv_performance_ratio * m.radiation_t[t] / max(val["radiation_t"].values())
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

        # Capacity-limit constraint
    def pv_area_limit_rule(m):
        # installed capacity ≤ usable area × power density
        return m.pv_capacity <= (m.pv_area_available * m.pv_efficiency)/1000
    m.pv_area_limit = pe.Constraint(rule=pv_area_limit_rule)

    # Hydro electricity usage constraints
    
    # Hydro electricity balance constraint (similar to PV balance)
    def hydro_balance_rule(m, t):
        return m.hydro_excess_t[t] == m.hydro_used_t[t] + m.hydro_export_t[t]
    m.hydro_balance = pe.Constraint(m.t, rule=hydro_balance_rule)
    
    # Total hydro used locally equals sum of hydro used by all generators
    def hydro_used_total_rule(m, t):
        return m.hydro_used_t[t] == sum(m.hydro_used_j_t[j, t] for j in m.j if m.ec_j[j] == "electricity")
    m.hydro_used_total = pe.Constraint(m.t, rule=hydro_used_total_rule)
    
    # Limit hydro used by each generator to its electricity consumption
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
    
    # Ensure the sum of PV and hydro used by each generator doesn't exceed its electricity consumption
    def combined_renewable_limit_rule(m, j, t):
        if m.ec_j[j] == "electricity":
            return m.pv_used_j_t[j, t] + m.hydro_used_j_t[j, t] <= m.x_th_jt[j, t] / m.n_th_jt[j, t]
        else:
            return pe.Constraint.Skip
    m.combined_renewable_limit = pe.Constraint(m.j, m.t, rule=combined_renewable_limit_rule)


    #% No investment in waste incineration plants possible,thus geneartion cant exeed already installed capacities
    def waste_incineration_restriction_jt_rule(m,j,t):
        rule = m.x_th_jt[j,t] <=  m.x_th_cap_j[j]
        return rule
    m.waste_incineration_restriction_jt = pe.Constraint(m.j_waste,m.t,rule=waste_incineration_restriction_jt_rule)

    #% With full heat extraction, a loss of power can occur which, only reduces the maximum power.
    def chp_geneartion_restriction1_jt_rule(m,j,t):
        if j in val["j_chp_se"]:
            sv_chp = (m.ratioPMaxFW - m.ratioPMax) / (m.ratioPMax*m.ratioPMaxFW)
            rule = m.x_el_jt[j,t] <= m.Cap_j[j]/m.ratioPMax - sv_chp * m.x_th_jt[j,t]
        else:
            rule = pe.Constraint.Skip
        return rule
    m.chp_geneartion_restriction1_jt = pe.Constraint(m.j_chp,m.t,rule=chp_geneartion_restriction1_jt_rule)   # should be adopted using binary variables

    def chp_geneartion_restriction2_jt_rule(m,j,t):
        rule = m.P_min_el_chp <=  m.x_el_jt[j,t]
        return rule
    m.chp_geneartion_restriction2_jt = pe.Constraint(m.j_chp,m.t,rule=chp_geneartion_restriction2_jt_rule)

    def chp_geneartion_restriction5_jt_rule(m,j,t):
        rule = m.Q_min_th_chp <=  m.x_th_jt[j,t]
        return rule
#    m.chp_geneartion_restriction5_jt = pe.Constraint(m.j_chp,m.t,rule=chp_geneartion_restriction5_jt_rule)

#    % The ratio of the maximum heat decoupling to the maximum electrical power determines the decrease in the maximum heat decoupling
#    with the produced electrical net power.
    def chp_geneartion_restriction3_jt_rule(m,j,t):
        if j in val["j_chp_se"]:
            rule = m.x_el_jt[j,t] >= m.x_th_jt[j,t] / m.ratioPMaxFW    # should be adopted using binary variables
        else:
            rule = m.x_el_jt[j,t] == m.x_th_jt[j,t] / m.n_th_jt[j,t] * m.n_el_j[j]
        return rule
    m.chp_geneartion_restriction3_jt = pe.Constraint(m.j_chp,m.t,rule=chp_geneartion_restriction3_jt_rule)

#   Seting cap for chp generation
    def chp_geneartion_restriction4_jt_rule(m,j,t):
        rule = m.x_th_jt[j,t] <= m.demand_th_t[t] + sum(m.x_load_hs_t[hs,t] for hs in m.j_hs)
        return rule
    m.chp_geneartion_restriction4_jt = pe.Constraint(m.j_chp,m.t,rule=chp_geneartion_restriction4_jt_rule)

    # The heat storage level = old_level + pumping  - turbining
    def storage_state_hs_t_rule(m,hs,t): 
        if t == 1: 
            return m.store_level_hs_t[hs,t] == m.store_level_hs_t[hs,8760]
        else: 
            return m.store_level_hs_t[hs,t] == m.store_level_hs_t[hs,t-1]*(1-m.cap_losse_hs[hs]) + m.x_load_hs_t[hs,t-1]*m.n_hs[hs] 
    m.storage_state_hs_t = pe.Constraint(m.j_hs,m.t,rule=storage_state_hs_t_rule) 

    
    # installed capcities must be greater or equeal pre installed capacities
    def storage_capacity_restriction_hs_rule(m,hs):
        if inv_flag:
            return m.Cap_hs[hs]  >= m.cap_hs[hs]
        else:
            return m.Cap_hs[hs]  == m.cap_hs[hs]
    m.storage_capacity_restriction_hs = pe.Constraint(m.j_hs,rule=storage_capacity_restriction_hs_rule)


    # The storage_level is restricted by the installed capcities
    def storage_state_capacity_restriction_hs_t_rule(m,hs,t):
        return m.store_level_hs_t[hs,t] <= m.Cap_hs[hs]
    m.storage_state_capacity_restriction_hs_t = pe.Constraint(m.j_hs,m.t,rule=storage_state_capacity_restriction_hs_t_rule)


    # The discharge and charge amounts are limited
    def load_hs_t_restriction_rule (m,hs,t):
        return m.x_load_hs_t[hs,t] <=   m.load_cap_hs[hs]
    m.load_hs_t_restriction = pe.Constraint(m.j_hs,m.t,rule=load_hs_t_restriction_rule)

    def unload_hs_t_restriction_rule (m,hs,t,flag):

        if flag:
            return m.x_load_hs_t[hs,t] >=  -  m.unload_cap_hs[hs]
        else:
            return m.x_load_hs_t[hs,t] >=  -  m.store_level_hs_t[hs,t]

    m.unload_hs_t_restriction = pe.Constraint(m.j_hs,m.t,[True,False],rule=unload_hs_t_restriction_rule)
    
    #%
    def ramp_cost_jt_rule (m,j,t): 
        if t==1: 
            return m.ramp_jt[j,t] == 0 
        else: 
            return m.ramp_jt[j,t] >= m.x_th_jt[j,t] - m.x_th_jt[j,t-1] 
    m.ramp_cost_jt = pe.Constraint(m.j,m.t,rule=ramp_cost_jt_rule) 
    
    def coldstart_j_t_rule (m,j,t):
        if t==1:
            return  m.coldstart_jt[j,t] == 1
        else:
            return m.coldstart_jt[j,t] >= m.Active_jt[j,t] - m.Active_jt[j,t-1] # puts out True only for Coldstart
    m.coldstart_rule_jt = pe.Constraint(m.j,m.t,rule=coldstart_j_t_rule)
    
    
    def renewable_factor_j_rule (m):
        if (sum(m.rf_j[j] for j in m.j) == 0):
            return pe.Constraint.Skip
        rule = sum([sum([(m.x_th_jt[j,t]+m.x_el_jt[j,t]) for t in m.t])*m.rf_j[j] for j in m.j]) >=  m.rf_tot * sum([sum([(m.x_th_jt[j,t]+m.x_el_jt[j,t]) for t in m.t])for j in m.j])
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

        
    #%% Zielfunktion
    def cost_rule(m):
        if inv_flag:
            c_inv = sum([(m.Cap_j[j] - m.x_th_cap_j[j])  * m.IK_j[j] * m.alpha_j[j] for j in m.j]) + sum([(m.Cap_hs[hs] - m.cap_hs[hs])*m.IK_hs[hs]* m.alpha_hs[hs] for hs in m.j_hs]) + (m.pv_capacity * m.PV_invest_cost * m.alpha_pv)
            c_op_fix = sum([m.Cap_j[j] * m.OP_fix_j[j] for j in m.j]) + \
                        sum([m.Cap_hs[hs] * m.OP_fix_hs[hs] for hs in m.j_hs]) + \
                        m.pv_capacity * m.PV_om_fix
        else:
            c_inv = 0
            c_op_fix = sum([m.Cap_j[j] * m.OP_fix_j[j] for j in m.j]) + \
                       sum([m.Cap_hs[hs] * m.OP_fix_hs[hs] for hs in m.j_hs]) + \
                       m.pv_capacity * m.PV_om_fix

        c_op_var = sum([m.x_th_jt[j,t]* m.OP_var_j[j] for j in m.j for t in m.t])
        
        # Variable costs for all energy carriers, with special handling for electricity
        c_var = sum([
            # For non-electricity generators, use the standard calculation
            m.x_th_jt[j,t]/m.n_th_jt[j,t] * m.mc_jt[j,t] 
            for j in m.j for t in m.t if m.ec_j[j] != "electricity"
        ])
        
        # Get an appropriate reference technology for electricity pricing
        # First try to find an electric technology
        elec_techs = [j for j in m.j if pe.value(m.ec_j[j]) == "electricity"]
        if elec_techs:
            ref_tech = elec_techs[0]  # Use first electric technology as reference
            # Cost for grid electricity import - use mc_jt which includes all electricity price factors
            c_grid = sum([m.grid_import_t[t] * m.mc_jt[ref_tech, t] for t in m.t])
        else:
            # Fallback to first technology if no electric technologies exist
            ref_tech = list(m.j)[0]
            print("Warning: No electric technology found, using first technology as reference for prices")
            # Use electricity_price_jt instead of mc_jt since we don't have a proper electric reference
            c_grid = sum([m.grid_import_t[t] * m.electricity_price_jt[ref_tech, t] for t in m.t])
            
        # On-site hydro utilisation: zero marginal cost
        c_hydro = 0.0

        c_peak_el = 0.0 #m.P_el_max*10000
        c_ramp = sum ([m.ramp_jt[j,t] * m.c_ramp_j[j] for j in m.j for t in m.t]) 
        c_cold = sum([(m.coldstart_jt[j,t]*m.c_coldstart_j[j]) for j in m.j for t in m.t]) #Counts up coldstarts and multiplies with Coldstart cost
        c_refurb = m.include_refurb_cost * (m.refurbishment_cost if hasattr(m, 'refurbishment_cost') else 0)
#        c_hs_penalty_load = sum([m.x_load_hs_t[hs,t]*5e-2  for hs in m.j_hs for t in m.t])      # for modeling reasons
#        c_hs_penalty_unload = sum([m.x_unload_hs_t[hs,t]*5e-2  for hs in m.j_hs for t in m.t])  # for modeling reasons
        c_tot = c_inv + c_var + c_op_fix + c_op_var + c_cold + c_ramp + c_refurb + c_hydro + c_grid
        # + c_el_import #+c_hs_penalty_load + c_hs_penalty_unload

        # Revenue from electricity generation by CHP
        rev_gen_electricity = sum([m.x_el_jt[j,t]*(m.sale_electricity_price_jt[j,t]) for j in m.j for t in m.t])
        
        # Revenue from PV export (using direct export price if available)
        if hasattr(m, 'pv_export_price_t'):
            rev_pv_electricity = sum([m.pv_export_t[t] * m.pv_export_price_t[t] for t in m.t])
        else:
            # Fallback to 50% of electricity price
            rev_pv_electricity = sum([m.pv_export_t[t] * (m.electricity_price_jt[ref_tech, t] * 0.7) for t in m.t])

        # Revenue from hydro export using dedicated price parameter
        if hasattr(m, 'hydro_export_price_t'):
            rev_hydro_electricity = sum([m.hydro_export_t[t] * m.hydro_export_price_t[t] for t in m.t])
        else:
            # Fallback to 70% of electricity price
            rev_hydro_electricity = sum([m.hydro_export_t[t] * (m.electricity_price_jt[ref_tech, t] * 0.7) for t in m.t])

        rev_tot = rev_gen_electricity + rev_pv_electricity + rev_hydro_electricity
        
        rule = (c_tot - rev_tot)
        return rule
    m.cost = pe.Objective(rule=cost_rule)
    # m.maximize_weight_factor = pe.Objective(expr=m.max_weight_factor, sense=pe.maximize)

    # m.cost.deactivate()
    # m.maximize_weight_factor.activate()

    #%% Compile Model
    #print("*****************\ntime to load data: " + str(datetime.now()-solv_start)+"\n*****************")
    print("*****************\nCreating Model...\n*****************")
    solv_start = datetime.now()
    instance = m.create_instance(report_timing= False)  #TODO
    print("*****************\ntime to create model: " + str(datetime.now()-solv_start)+"\n*****************")
    solv_start = datetime.now()
    print("*****************\nSolving...\n*****************")

    opt = pe.SolverFactory("gurobi")
    opt.options['MIPGap'] = 1e-3
    opt.options["MIPFocus"] = 0
    opt.options["TimeLimit"] = 1200
    opt.options['NodefileStart']=0.5
    # opt.options['Threads'] = 0
    #TODO 4
    tee = True
    results = opt.solve(instance, load_solutions=False,tee=tee,suffixes=['.*'])   # tee= Solver Progress, Suffix um z.B Duale Variablen anzuzeigen -> '.*' für alle
    print("*****************\ntime for solving: " + str(datetime.now()-solv_start)+"\n*****************")

    solv_start = datetime.now()
    if results.solver.termination_condition == TerminationCondition.maxTimeLimit:
        return (None,results.solver.message)
        print("Time Limit reached, set MIPGap=0.05 and try solving...")
        opt.options['MIPGap'] = 0.05
        results = opt.solve(instance, load_solutions=False,tee=tee,suffixes=['.*'])   # tee= Solver Progress, Suffix um z.B Duale Variablen anzuzeigen -> '.*' für alle
        print("*****************\ntime for solving: " + str(datetime.now()-solv_start)+"\n*****************")
        if results.solver.termination_condition == TerminationCondition.maxTimeLimit:
            solv_start = datetime.now()
            print("Time Limit reached, set MIPFocus=1 to find any feasible solution....")
            opt.options['MIPFocus'] = 1
            opt.options["TimeLimit"] = 260
            results = opt.solve(instance, load_solutions=False,tee=tee,suffixes=['.*'])   # tee= Solver Progress, Suffix um z.B Duale Variablen anzuzeigen -> '.*' für alle
            print("*****************\ntime for solving: " + str(datetime.now()-solv_start)+"\n*****************")
            if results.solver.termination_condition == TerminationCondition.maxTimeLimit:
                solv_start = datetime.now()
                print("Time Limit reached, set MIPFocus=0 one more time solving....")
                opt.options['MIPFocus'] = 0
                results = opt.solve(instance, load_solutions=False,tee=tee,suffixes=['.*']) 
                print("*****************\ntime for resolving: " + str(datetime.now()-solv_start)+"\n*****************")

    if (results.solver.status == SolverStatus.ok) and (results.solver.termination_condition == TerminationCondition.optimal):
        instance.solutions.load_from(results)
        instance.solutions.store_to(results)

        # ... (after model.solve(...) is complete) ...

        # Retrieve the refurbishment-related values:
        total_fraction_saved = pe.value(instance.fraction_saved)
        saved_mwh = pe.value(instance.mwh_saved_total)
        total_refurb_cost = pe.value(instance.refurbishment_cost)
        # max_weight_factor = pe.value(instance.max_weight_factor)

        print("=== Refurbishment Results ===")
        print("Total fraction saved: {:.2%}".format(total_fraction_saved))
        print("Total MWh saved:      {:.2f} MWh".format(saved_mwh))
        print("Total refurbishment cost: {:.2f} EUR".format(total_refurb_cost))
        # print("Max weight factor: {:.2f}".format(max_weight_factor))

        # Print block usage details:
        print("\nBlock Usage (each block is 10% potential):")
        for i in instance.blocks:
            block_usage = pe.value(instance.x_save_fraction[i])
            print(f"  Block {i}: {block_usage*100:.1f}% used")

        # (Optional) To see the effect on demand:
        for t in sorted(instance.t):
            effective_demand = pe.value(instance.demand_th_reduced[t])
            original = pe.value(instance.demand_th_t[t])
            # For brevity, you might only print for a few time steps or aggregate.
            # For example, print the first hour:
            if t == 1:
                print(f"\nTime step {t}: Original demand = {original:.2f} MWh, Reduced demand = {effective_demand:.2f} MWh")
                break
        
         # Print PV capacity and cost:
        if hasattr(instance, 'pv_capacity'):
            pv_cap = pe.value(instance.pv_capacity)
            print(f"Optimal PV capacity = {pv_cap:.2f} MW")

            # If you have a capital cost parameter and annuity factor, compute annualized cost:
            pv_invest_cost = pe.value(instance.PV_invest_cost)   # EUR/MW
            alpha_pv       = pe.value(instance.alpha_pv)         # dimensionless factor
            pv_om_fix      = pe.value(instance.PV_om_fix)        # EUR/(MW·year) if relevant

            invest_cost_annual = pv_cap * pv_invest_cost * alpha_pv
            om_cost_annual     = pv_cap * pv_om_fix
            total_pv_cost      = invest_cost_annual + om_cost_annual

            print(f"Annualized PV investment cost = {invest_cost_annual:,.2f} EUR/yr")
            print(f"Annual PV O&M cost           = {om_cost_annual:,.2f} EUR/yr")
            print(f"Total annual PV cost         = {total_pv_cost:,.2f} EUR/yr")
        else:
            print("No PV capacity variable found in model.")

            print("*****************\nFixing Binary and resolving...\n*****************") 

        
        # to get Dual Variables the binary variables had to be fixed and then resolved again  
        instance.Active_jt.fix() 
        # instance.Active2_jt.fix() 
        # instance.Active3_jt.fix() 
#        instance.Storage_load_hs_jt.fix() 
#        instance.Storage_unload_hs_jt.fix()
        instance.coldstart_jt.fix()
        instance.preprocess()  
        results = opt.solve(instance, load_solutions=False,tee=tee,suffixes=['.*'])   # tee= Solver Progress, Suffix um z.B Duale Variablen anzuzeigen -> '.*' für alle    
        instance.solutions.load_from(results) 

        instance.solutions.store_to(results) 
        print("*****************\ntime for resolving fixed variables: " + str(datetime.now()-solv_start)+"\n*****************")
        
        # --- Analysis and Output ---
        print("\nCalculating PV electricity usage and export...")
        # Call the check_pv_usage function
        if hasattr(instance, 'pv_capacity') and hasattr(instance, 'pv_used_t') and hasattr(instance, 'pv_export_t'):
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
        print ("something else is wrong")
        return (None,results.solver.message)
    
    if (results.solver.status == SolverStatus.ok) and (results.solver.termination_condition == TerminationCondition.optimal):
        print ("this is feasible and optimal")
        return(instance,results)
    elif results.solver.termination_condition == TerminationCondition.infeasible:
         print ("infeasible")
         return("Error3","Error3")
    else:
        print ("something else is wrong")
        return (None,results.solver.message)
     
     
    

if __name__ == "__main__":
    print('Main: Simpel Dispatch Module')