import pandas as pd
import numpy as np
import os
from tqdm import tqdm
import warnings
warnings.filterwarnings('ignore')


METRICS_DIR = "results/metrics"
OUTPUT_DIR = "results/distributions"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def create_deg_bins():
    

    neg_bins = np.arange(-5, 0.5, 0.5)  
    

    pos_bins = np.arange(0, 5.5, 0.5)  
    

    bins = list(neg_bins) + list(pos_bins[1:])  
    bins = [-np.inf] + bins + [np.inf]
    return bins

def create_deg_labels(bins):
    
    labels = []
    for i in range(len(bins)-1):

        if bins[i] == -np.inf:
            labels.append(f"(-∞, {bins[i+1]})")

        elif bins[i+1] == np.inf:
            if bins[i] == 5:
                labels.append(f"({bins[i]}, +∞)")
            else:
                labels.append(f"[{bins[i]}, +∞)")

        else:

            if bins[i] < 0:

                if bins[i] == -5 and bins[i+1] == -4.5:
                    labels.append(f"[-5, -4.5)")

                elif bins[i+1] < 0:
                    labels.append(f"[{bins[i]}, {bins[i+1]})")

                elif bins[i] == -0.5 and bins[i+1] == 0:
                    labels.append(f"[-0.5, 0)")

            elif bins[i] >= 0:

                if bins[i] == 0 and bins[i+1] == 0.5:
                    labels.append(f"(0, 0.5]")

                elif bins[i] == 0.5 and bins[i+1] == 1.0:
                    labels.append(f"(0.5, 1.0]")

                elif bins[i] > 0:
                    labels.append(f"({bins[i]}, {bins[i+1]}]")
    
    return labels

def create_sim_bins():

    return np.arange(0.5, 1.05, 0.05)  

def create_sim_labels(bins):

    labels = []
    for i in range(len(bins)-1):
        if i == 0:
            labels.append(f"({bins[i]}, {bins[i+1]}]")
        else:
            labels.append(f"({bins[i]}, {bins[i+1]}]")
    return labels

def analyze_distributions(domain):

    input_file = os.path.join(METRICS_DIR, f"{domain}_metric.xlsx")
    output_file = os.path.join(OUTPUT_DIR, f"{domain}_distributions.xlsx")
    
    print(f"处理 {domain}...")
    

    df_direct_sim = pd.read_excel(input_file, sheet_name='direct_sim', index_col=0)
    df_direct_deg = pd.read_excel(input_file, sheet_name='direct_deg', index_col=0)
    

    print("  分析deg分布...")
    deg_values = df_direct_deg.values.flatten()

    deg_non_zero = deg_values[deg_values != 0]
    

    deg_bins = create_deg_bins()
    deg_labels = create_deg_labels(deg_bins)
    

    deg_categories = pd.cut(deg_non_zero, bins=deg_bins, labels=deg_labels, right=False)
    deg_counts = deg_categories.value_counts().sort_index()
    deg_percentages = (deg_counts / len(deg_non_zero) * 100).round(2)
    

    deg_dist_df = pd.DataFrame({
        'range': deg_counts.index,
        'num': deg_counts.values,
        'propotion(%)': deg_percentages.values
    })
    

    print("  分析sim分布...")
    sim_values = df_direct_sim.values.flatten()

    sim_non_zero = sim_values[sim_values != 0]
    

    sim_bins = create_sim_bins()
    sim_labels = create_sim_labels(sim_bins)
    

    sim_categories = pd.cut(sim_non_zero, bins=sim_bins, labels=sim_labels)
    sim_counts = sim_categories.value_counts().sort_index()
    sim_percentages = (sim_counts / len(sim_non_zero) * 100).round(2)
    

    sim_dist_df = pd.DataFrame({
        'range': sim_counts.index,
        'num': sim_counts.values,
        'propotion(%)': sim_percentages.values
    })
    

    print("  生成(deg, sim)展平结果...")

    flat_results = []
    for i in range(df_direct_deg.shape[0]):
        for j in range(df_direct_deg.shape[1]):
            deg_val = df_direct_deg.iloc[i, j]
            sim_val = df_direct_sim.iloc[i, j]

            if deg_val != 0 and sim_val != 0:
                flat_results.append({
                    'deg': deg_val,
                    'sim': sim_val,
                    'row_index': df_direct_deg.index[i],
                    'col_index': df_direct_deg.columns[j]
                })
    

    flat_df = pd.DataFrame(flat_results)
    

    print(f"  保存结果到 {output_file}")
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:

        deg_dist_df.to_excel(writer, sheet_name='deg', index=False)
        

        sim_dist_df.to_excel(writer, sheet_name='sim', index=False)
        

        flat_df.to_excel(writer, sheet_name='(deg,sim)', index=False)
        
    
    return {
        'deg_dist': deg_dist_df,
        'sim_dist': sim_dist_df,
        'flat': flat_df,
    }

def main():
    """主函数：处理所有domain"""

    metric_files = [f for f in os.listdir(METRICS_DIR) if f.endswith('_metric.xlsx')]
    
    if not metric_files:
        print(f"在 {METRICS_DIR} 目录中未找到metric文件")
        return
    
    print(f"找到 {len(metric_files)} 个metric文件")
    

    domains = [f.replace('_metric.xlsx', '') for f in metric_files]
    

    results = {}
    for domain in tqdm(domains, desc="处理domain"):
        try:
            result = analyze_distributions(domain)
            results[domain] = result
        except Exception as e:
            print(f"处理 {domain} 时出错: {e}")
    
    print("\n所有处理完成！")

if __name__ == "__main__":
    main()