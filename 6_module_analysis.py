import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os
from tqdm import tqdm
import networkx as nx
import community as community_louvain  # python-louvain package
from networkx.algorithms.community.quality import modularity
from networkx.algorithms.community import greedy_modularity_communities


# 设置中文显示
plt.rcParams['font.family'] = 'SimHei'
plt.rcParams['axes.unicode_minus'] = False

def calculate_key_metrics(adj_matrix, weight_matrix, threshold):
   
    nodes = adj_matrix.index
    binary_matrix = pd.DataFrame(0.0, index=nodes, columns=nodes)
    

    for node_col in nodes:
        for node_row in nodes:
            binary_matrix.loc[node_row, node_col] = weight_matrix[node_col][node_row] if (
                node_col != node_row and 
                adj_matrix[node_col][node_row] >= threshold
            ) else 0
    

    G = nx.from_pandas_adjacency(binary_matrix, create_using=nx.DiGraph())
    G_undir = G.to_undirected()  
    
    metrics = {
        'network_density': 0,
        'largest_cc_ratio': 0,
        'modularity': 0
    }
    
    if nx.number_of_nodes(G) > 0:

        metrics['network_density'] = nx.density(G)
        

        if nx.is_directed(G):
            connected_components = list(nx.weakly_connected_components(G))
        else:
            connected_components = list(nx.connected_components(G))
        
        if connected_components:
            largest_cc = max(connected_components, key=len)
            metrics['largest_cc_ratio'] = len(largest_cc) / nx.number_of_nodes(G)
        
        metrics['clustering'] = nx.average_clustering(G)

        if nx.number_of_edges(G_undir) > 0:
            try:
                communities = list(greedy_modularity_communities(G))
                metrics['modularity'] = modularity(G, communities)
            except:
                metrics['modularity'] = 0
        else:
            metrics['modularity'] = 0
    
    return metrics

def find_critical_points(metrics_data):

    thresholds = sorted(metrics_data.keys())
    

    density = [metrics_data[t]['network_density'] for t in thresholds]
    cc_ratio = [metrics_data[t]['largest_cc_ratio'] for t in thresholds]
    clustering = [metrics_data[t]['clustering'] for t in thresholds]
    

    density_diff = np.abs(np.diff(density) / np.diff(thresholds))
    cc_ratio_diff = np.abs(np.diff(cc_ratio) / np.diff(thresholds))
    clustering_diff = np.abs(np.diff(clustering) / np.diff(thresholds))
    

    critical_points = {
        'density_critical': thresholds[np.argmax(density_diff) + 1] if len(density_diff) > 0 else None,
        'cc_ratio_critical': thresholds[np.argmax(cc_ratio_diff) + 1] if len(cc_ratio_diff) > 0 else None,
        'clustering_critical': thresholds[np.argmax(clustering_diff) + 1] if len(clustering_diff) > 0 else None,
        
        'density_max_diff': np.max(density_diff) if len(density_diff) > 0 else 0,
        'cc_ratio_max_diff': np.max(cc_ratio_diff) if len(cc_ratio_diff) > 0 else 0,
        'clustering_max_diff': np.max(clustering_diff) if len(clustering_diff) > 0 else 0
    }
    
    return critical_points

def analyze_key_metrics(input_file, output_dir):

    os.makedirs(output_dir, exist_ok=True)
    
    adj_matrix = pd.read_excel(input_file, sheet_name="direct_sim", index_col=0)
    weight_matrix = pd.read_excel(input_file, sheet_name="direct_deg", index_col=0)
    

    domain = os.path.basename(input_file).replace("_metric.xlsx", "")
    

    thresholds = np.linspace(0.6, 0.95, 50)  # 50个阈值点
    

    metrics_data = {}
    for threshold in tqdm(thresholds, desc=f"分析{domain}"):
        metrics_data[threshold] = calculate_key_metrics(
            adj_matrix, weight_matrix, threshold
        )
    

    critical_points = find_critical_points(metrics_data)
    

    output_excel = os.path.join(output_dir, f"{domain}_key_metrics.xlsx")
    pd.DataFrame.from_dict(metrics_data, orient='index').to_excel(output_excel)
    
    print(f"分析完成! 结果已保存到: {output_dir}")
    
    return {
        'domain': domain,
        **critical_points
    }

# 主程序
if __name__ == "__main__":
    input_dir = "results/metrics"
    output_dir = "results/key_metrics_analysis"
    

    all_results = []
    

    files = os.listdir(input_dir)
    
    for file in files:
        if file.endswith("_metric.xlsx"):
            input_file = os.path.join(input_dir, file)
            result = analyze_key_metrics(input_file, output_dir)
            all_results.append(result)
    

    if all_results:
        summary_df = pd.DataFrame(all_results)
        summary_excel = os.path.join(output_dir, "critical_points_summary.xlsx")
        summary_df.to_excel(summary_excel, index=False)
        print(f"突变点汇总表已保存到: {summary_excel}")