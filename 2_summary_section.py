import os
import pandas as pd
from collections import defaultdict

def aggregate_results(input_excel_path, output_excel_path):
    # Read the input Excel match_file
    df = pd.read_excel(input_excel_path)
    
    # 1. Article-level aggregation (average by match_file)
    article_df = df.groupby('match_file').agg({
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
    unique_structures = df['query_section'].unique()
    
    # Create a dictionary to store DataFrames for each metric
    structure_dfs = {
        'direct_sim': pd.DataFrame(index=df['match_file'].unique(), columns=unique_structures),
        'hidden_sim': pd.DataFrame(index=df['match_file'].unique(), columns=unique_structures),
        'direct_degree': pd.DataFrame(index=df['match_file'].unique(), columns=unique_structures),
        'hidden_degree': pd.DataFrame(index=df['match_file'].unique(), columns=unique_structures)
    }
    
    # Populate the DataFrames
    for match_file in df['match_file'].unique():
        match_file_data = df[df['match_file'] == match_file]
        for structure in unique_structures:
            structure_data = match_file_data[match_file_data['query_section'] == structure]
            if not structure_data.empty:
                structure_dfs['direct_sim'].loc[match_file, structure] = structure_data['direct_sim'].mean()
                structure_dfs['hidden_sim'].loc[match_file, structure] = structure_data['hidden_sim'].mean()
                structure_dfs['direct_degree'].loc[match_file, structure] = structure_data['direct_degree'].mean()
                structure_dfs['hidden_degree'].loc[match_file, structure] = structure_data['hidden_degree'].mean()
    
    # 3. Save all results to Excel
    with pd.ExcelWriter(output_excel_path) as writer:
        # Save article-level results
        article_df.to_excel(writer, sheet_name='Article_Summary', index=False)
        
        # Save structure-based results
        for metric, metric_df in structure_dfs.items():
            metric_df.to_excel(writer, sheet_name=f'Structure_{metric}')
    
    print(f"Results saved to {output_excel_path}")

# Example usage
if __name__ == "__main__":
    match_files = os.listdir(r"results\Qwen3-Embedding-0.6B\matching_results\section")
    for match_file in match_files:
        input = os.path.join(r"results\Qwen3-Embedding-0.6B\matching_results\section", match_file)
        output = os.path.join(r"results\Qwen3-Embedding-0.6B\matching_results\summary", "summary_" + match_file.replace(".xlsx", "_sentence.xlsx"))
        df = aggregate_results(input, output)
        print(df)