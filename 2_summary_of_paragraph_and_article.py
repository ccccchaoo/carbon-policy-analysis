import os
import pandas as pd
from collections import defaultdict

def aggregate_results(input_excel_path, output_excel_path):
    # Read the input Excel file
    df = pd.read_excel(input_excel_path)
    
    # 1. Article-level aggregation (average by file)
    article_df = df.groupby('file').agg({
        'direct_sim': 'mean',
        'hidden_sim': 'mean',
        'direct_degree': 'mean',
        'hidden_degree': 'mean'
    }).reset_index()
    
    # Rename columns for clarity
    article_df = article_df.rename(columns={
        'direct_sim': 'avg_direct_sim',
        'hidden_sim': 'avg_hidden_sim',
        'direct_degree': 'avg_direct_degree',
        'hidden_degree': 'avg_hidden_degree'
    })
    
    # 2. Create structure-based worksheets
    # First extract unique query structures
    unique_structures = df['query_structure'].unique()
    
    # Create a dictionary to store DataFrames for each metric
    structure_dfs = {
        'direct_sim': pd.DataFrame(index=df['file'].unique(), columns=unique_structures),
        'hidden_sim': pd.DataFrame(index=df['file'].unique(), columns=unique_structures),
        'direct_degree': pd.DataFrame(index=df['file'].unique(), columns=unique_structures),
        'hidden_degree': pd.DataFrame(index=df['file'].unique(), columns=unique_structures)
    }
    
    # Populate the DataFrames
    for file in df['file'].unique():
        file_data = df[df['file'] == file]
        for structure in unique_structures:
            structure_data = file_data[file_data['query_structure'] == structure]
            if not structure_data.empty:
                structure_dfs['direct_sim'].loc[file, structure] = structure_data['direct_sim'].mean()
                structure_dfs['hidden_sim'].loc[file, structure] = structure_data['hidden_sim'].mean()
                structure_dfs['direct_degree'].loc[file, structure] = structure_data['direct_degree'].mean()
                structure_dfs['hidden_degree'].loc[file, structure] = structure_data['hidden_degree'].mean()
    
    # 3. Save all results to Excel
    with pd.ExcelWriter(output_excel_path) as writer:
        # Save article-level results
        article_df.to_excel(writer, sheet_name='Article_Summary', index=False)
        
        # Save structure-based results
        for metric, metric_df in structure_dfs.items():
            metric_df.to_excel(writer, sheet_name=f'Structure_{metric}')
    
    print(f"Results saved to {output_excel_path}")


if __name__ == "__main__":
    files = os.listdir("results/sentences")
    for file in files:
        input = os.path.join("results/sentences",file)
        output = os.path.join("results/summary","summary_"+file)
        df = aggregate_results(input,output)
        print(df)