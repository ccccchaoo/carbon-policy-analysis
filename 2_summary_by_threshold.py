import pandas as pd
import numpy as np
import os


#thresholds = [0.2, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95]

thresholds = np.linspace(0.2, 0.95, 16)
step = thresholds[1] - thresholds[0]


def aggregate_by_threshold(input_path, output_path):

    df = pd.read_excel(input_path)
    print(df.columns)  
    writer = pd.ExcelWriter(output_path)

    
    for col in ['direct_sim', 'hidden_sim', 'direct_degree', 'hidden_degree']:
        
        result_df = pd.DataFrame(index=df['file'].unique())
        
        for thresh in thresholds:
            
            filtered_data = df[(df['direct_sim'] > thresh) & (df['direct_sim'] <= thresh+step)]#0.05
            
           
            mean_values = filtered_data.groupby('file')[col].mean()
            
            
            result_df[f'{thresh}'] = mean_values
        
       
        result_df = result_df.fillna(0) 
        
       
        result_df.to_excel(writer, sheet_name=col)

    
    writer.close()


if __name__ == "__main__":
    files = os.listdir("results/sentences")
    for file in files:
        input = os.path.join("results/sentences",file)
        output = os.path.join("results/threshold","threshold_"+file)
        df = aggregate_by_threshold(input,output)