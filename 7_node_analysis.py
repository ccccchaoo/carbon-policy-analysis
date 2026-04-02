import numpy as np
import pandas as pd
import networkx as nx
import os

def analyze_network_metrics_simple(network_file):


    binary_matrix = pd.read_excel(network_file, sheet_name='binary_matrix', index_col=0)
    

    all_nodes = list(range(32))
    

    binary_matrix = binary_matrix.reindex(index=all_nodes, columns=all_nodes, fill_value=0)
      

    metrics = {}
    

    out_degree = []

    in_degree = []

    total_degree = []
    
    for node in all_nodes:

        out_row = binary_matrix.loc[node].copy()
        out_row.at[node] = 0  
        out_deg = (out_row != 0).sum()
        out_degree.append(out_deg)
        

        in_col = binary_matrix[node].copy()
        in_col.at[node] = 0  
        in_deg = (in_col != 0).sum()
        in_degree.append(in_deg)
        

        total_degree.append(out_deg + in_deg)
    
    metrics['out_degree'] = out_degree
    metrics['in_degree'] = in_degree
    metrics['degree'] = total_degree
    

    out_weight_sum = []

    in_weight_sum = []

    total_weight_sum = []
    
    for node in all_nodes:

        out_row = binary_matrix.loc[node].copy()
        out_row.at[node] = 0  
        out_weight = out_row.sum()
        out_weight_sum.append(out_weight)
        

        in_col = binary_matrix[node].copy()
        in_col.at[node] = 0  
        in_weight = in_col.sum()
        in_weight_sum.append(in_weight)
        

        total_weight_sum.append(in_weight - out_weight)
    
    metrics['out_weight_sum'] = out_weight_sum
    metrics['in_weight_sum'] = in_weight_sum
    metrics['total_weight_sum'] = total_weight_sum
    


    try:

        G = nx.DiGraph()
        

        for node in all_nodes:
            G.add_node(node)
        

        has_edges = {node: False for node in all_nodes}  
        
        for source in all_nodes:
            for target in all_nodes:
                weight = binary_matrix.loc[source, target]
                if weight > 0 and source != target: 
                    G.add_edge(source, target, weight=weight)
                    has_edges[source] = True
                    has_edges[target] = True
        

        pagerank_standard = nx.pagerank(G, weight='weight')
        

        pagerank_modified = {}
        for node in all_nodes:
            if has_edges[node]:  
                pagerank_modified[node] = pagerank_standard.get(node, 0)
            else:  
                pagerank_modified[node] = 0
        

        total_pr = sum(pagerank_modified.values())
        if total_pr > 0:
            for node in pagerank_modified:
                if pagerank_modified[node] > 0:
                    pagerank_modified[node] = pagerank_modified[node] / total_pr
        
        metrics['pagerank'] = [pagerank_modified.get(node, 0) for node in all_nodes]
    except Exception as e:
        print(f"PageRank error: {e}")
        metrics['pagerank'] = [0 for _ in all_nodes]
    

    critical_thresholds = []
    
    try:

        sim_matrix = pd.read_excel(network_file, sheet_name='direct_sim_converted', index_col=0)
    except:
        try:

            original_file = os.path.join("results/metrics", 
                                        os.path.basename(network_file).replace("_network.xlsx", "_metric.xlsx"))
            sim_matrix = pd.read_excel(original_file, sheet_name="direct_sim", index_col=0)
            

            def extract_province_code(name):
                province_mapping = {
                    "北京": 1, "天津": 2, "河北": 3, "山西": 4, "内蒙": 5,
                    "辽宁": 6, "吉林": 7, "黑龙": 8, "上海": 9, "江苏": 10,
                    "浙江": 11, "安徽": 12, "福建": 13, "江西": 14, "山东": 15,
                    "河南": 16, "湖北": 17, "湖南": 18, "广东": 19, "广西": 20,
                    "海南": 21, "重庆": 22, "四川": 23, "贵州": 24, "云南": 25,
                    "西藏": 26, "陕西": 27, "甘肃": 28, "青海": 29, "宁夏": 30,
                    "新疆": 31,
                }
                if pd.isna(name):
                    return 0
                first_two = str(name)[:2]
                return province_mapping.get(first_two, 0)
            
            original_index = sim_matrix.index.tolist()
            original_columns = sim_matrix.columns.tolist()
            sim_matrix.index = [extract_province_code(idx) for idx in original_index]
            sim_matrix.columns = [extract_province_code(col) for col in original_columns]
        except Exception as e:
            print(f"can't read sim metrix: {e}")
            sim_matrix = None
    
    if sim_matrix is not None:

        sim_matrix = sim_matrix.reindex(index=all_nodes, columns=all_nodes, fill_value=0)
        
        for node in all_nodes:

            row_values = sim_matrix.loc[node].drop(node).values

            col_values = sim_matrix[node].drop(node).values
            
            all_similarities = np.concatenate([row_values, col_values])
            if len(all_similarities) > 0:
                max_similarity = np.max(all_similarities)
            else:
                max_similarity = 0
            
            critical_thresholds.append(max_similarity)
    else:
        critical_thresholds = [0 for _ in all_nodes]
    
    metrics['critical_threshold'] = critical_thresholds
    
    return metrics, all_nodes

def generate_metrics_table_simple():


    output_dir = "results/metrics_tables"
    os.makedirs(output_dir, exist_ok=True)
    

    network_files = [f for f in os.listdir("results/network") ]
    

    network_files.sort(key=lambda x: x.split('_')[0])
    

    all_metrics = {}
    
    for network_file in network_files:
        file_path = os.path.join("results/network", network_file)
        
        mission_name = network_file.split('_')[0]
        

        metrics, nodes = analyze_network_metrics_simple(file_path)
        

        all_metrics[mission_name] = {
            'metrics': metrics,
            'nodes': nodes
        }
    

    output_file = os.path.join(output_dir, f"network_metrics_threshold_simple.xlsx")
    
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:

        metric_names = ['degree', 'out_degree', 'in_degree', 'total_weight_sum', 
                       'out_weight_sum', 'in_weight_sum', 'pagerank', 'critical_threshold']
        
        for metric_name in metric_names:

            df_data = {}
            

            df_data['node'] = list(range(32))
            

            for mission_name, data in all_metrics.items():
                if metric_name in data['metrics']:
                    df_data[mission_name] = data['metrics'][metric_name]
                else:
                    df_data[mission_name] = [0] * 32
            

            df = pd.DataFrame(df_data)
            

            df.set_index('node', inplace=True)
            

            sheet_name = metric_name
            if len(sheet_name) > 31: 
                sheet_name = sheet_name[:31]
            df.to_excel(writer, sheet_name=sheet_name)
            

            summary_df = df.copy()
            summary_df.loc['avg'] = df.mean()
            summary_df.loc['SD'] = df.std()
            summary_df.loc['max'] = df.max()
            summary_df.loc['min'] = df.min()
            summary_df.loc['medium'] = df.median()

            summary_sheet_name = f"{metric_name}_summary"
            if len(summary_sheet_name) > 31:
                summary_sheet_name = summary_sheet_name[:31]
            summary_df.to_excel(writer, sheet_name=summary_sheet_name)
        

        overview_data = {}
        for mission_name, data in all_metrics.items():
            row_data = []
            for metric_name in metric_names:
                if metric_name in data['metrics']:

                    avg_value = np.mean(data['metrics'][metric_name])
                    row_data.append(avg_value)
                else:
                    row_data.append(0)
            
            overview_data[mission_name] = row_data
        
        overview_df = pd.DataFrame(overview_data, index=metric_names)
        overview_df.to_excel(writer, sheet_name="overview")
    
    print(f"save in: {output_file}")
    


    for mission_name, data in all_metrics.items():
        metrics = data['metrics']

        for i in range(32):
            if metrics['degree'][i] != metrics['out_degree'][i] + metrics['in_degree'][i]:
                print(f"warn: {mission_name} node{i} degree inconsistent")
                print(f"  total degree: {metrics['degree'][i]}, out degree: {metrics['out_degree'][i]}, in degree: {metrics['in_degree'][i]}")
        

        for i in range(32):
            if abs(metrics['total_weight_sum'][i] - (metrics['in_weight_sum'][i] - metrics['out_weight_sum'][i])) > 1e-10:
                print(f"warn: {mission_name} node{i} weight inconsistent")
                print(f"  total weight: {metrics['total_weight_sum'][i]}, out weight: {metrics['out_weight_sum'][i]}, in weight: {metrics['in_weight_sum'][i]}")
    
    return output_file

# 主程序
if __name__ == "__main__":

    output_file = generate_metrics_table_simple()
    print(f"Finish! Save in: {output_file}")