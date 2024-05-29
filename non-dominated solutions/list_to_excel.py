# -*- coding: utf-8 -*-
"""
Created on Wed May 29 16:14:30 2024

@author: dmiller-moran
"""

import os
import pandas as pd

def list_files_to_excel(directory, output_excel_file):
    # Get a list of files in the specified directory
    files = os.listdir(directory)
    
    # Create a DataFrame with the list of files
    df = pd.DataFrame(files, columns=["File Name"])
    
    # Save the DataFrame to an Excel file
    df.to_excel(output_excel_file, index=False)

# Specify the directory and output Excel file
directory = 'C:/Users/dmiller-moran/WDNOptimizer/non-dominated solutions'  # Replace with your directory path
output_excel_file = 'file_list.xlsx'  # Replace with your desired output file name

# Call the function to list files and save to Excel
list_files_to_excel(directory, output_excel_file)

print(f"List of files in {directory} has been saved to {output_excel_file}")