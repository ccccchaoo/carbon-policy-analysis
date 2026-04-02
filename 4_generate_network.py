import numpy as np
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import os
import matplotlib.colors as mcolors
from matplotlib.lines import Line2D
from matplotlib.gridspec import GridSpec

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
plt.rcParams['font.size'] = 14  

province_mapping = {
    "北京": 1,
    "天津": 2,
    "河北": 3,
    "山西": 4,
    "内蒙": 5,
    "辽宁": 6,
    "吉林": 7,
    "黑龙": 8,
    "上海": 9,
    "江苏": 10,
    "浙江": 11,
    "安徽": 12,
    "福建": 13,
    "江西": 14,
    "山东": 15,
    "河南": 16,
    "湖北": 17,
    "湖南": 18,
    "广东": 19,
    "广西": 20,
    "海南": 21,
    "重庆": 22,
    "四川": 23,
    "贵州": 24,
    "云南": 25,
    "西藏": 26,
    "陕西": 27,
    "甘肃": 28,
    "青海": 29,
    "宁夏": 30,
    "新疆": 31,
}

mission_letter_mapping = {
    "Carbon Peak (Overall)": "a",
    "New Development Philosophy": "b",
    "Industrial Sector": "c",
    "Urban and Rural Development Sec": "d",
    "Pollution and Carbon Reduction": "e",
    "Green Consumption": "f",
    "Green, Low-Carbon, and Circular": "g",
    "Green and Low-Carbon Transition": "h",
    "Non-ferrous Metals": "i",
    "Building Materials Industry": "j",
    "Standards and Metrology": "k",
    "Fiscal Support": "l"
}

def extract_province_code(name):
  
    if pd.isna(name):
        return 0
    
    
    first_two = str(name)[:2]
    if first_two in province_mapping:
        return province_mapping[first_two]
    
    
    return 0

def generate_networks(thresholds):
    files = os.listdir("results/metrics")  
    
    if len(files) != 12:
        print(f"警告：找到 {len(files)} 个文件，但期望 12 个")
    
    i = 0

    for file in files:
        threshold = thresholds[i]
        input_path = os.path.join("results/metrics", file)
        print(f"正在处理文件: {input_path}")
        adj_matrix = pd.read_excel(input_path, sheet_name="direct_sim", index_col=0)
        weight_matrix = pd.read_excel(input_path, sheet_name="direct_deg", index_col=0)
        

        original_index = adj_matrix.index.tolist()
        original_columns = adj_matrix.columns.tolist()
        
  
        row_mapping = {}
        for idx in original_index:
            code = extract_province_code(idx)
            row_mapping[idx] = code
        

        col_mapping = {}
        for col in original_columns:
            code = extract_province_code(col)
            col_mapping[col] = code
        

        adj_matrix.index = [row_mapping[idx] for idx in original_index]
        adj_matrix.columns = [col_mapping[col] for col in original_columns]
        
        weight_matrix.index = [row_mapping[idx] for idx in original_index]
        weight_matrix.columns = [col_mapping[col] for col in original_columns]
        
        nodes = adj_matrix.index
        binary_matrix = pd.DataFrame(0.0, index=nodes, columns=nodes)

        for node_col in nodes:
            for node_row in nodes:
                binary_matrix.loc[node_row, node_col] = weight_matrix[node_col][node_row] if (
                    node_col != node_row and 
                    adj_matrix[node_col][node_row] >= threshold) else 0
        
        
  
        output = os.path.join(r"results/network", file.replace("_metric.xlsx", f"_{threshold}_network.xlsx")) 
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            binary_matrix.to_excel(writer, sheet_name='binary_matrix', index=True)

            adj_matrix.to_excel(writer, sheet_name='direct_sim_converted', index=True)
            weight_matrix.to_excel(writer, sheet_name='direct_deg_converted', index=True)
        
        print(f"已生成网络邻接矩阵文件: {output}")
        print(f"行列标签已转换为省份编码（0表示中央）")
        print(f"转换后的行名: {list(binary_matrix.index)}")
        print(f"转换后的列名: {list(binary_matrix.columns)}")
        i += 1


if __name__ == "__main__":

    os.makedirs("results/network", exist_ok=True)
    
    files = ['Building Materials Industry_metric.xlsx', 'Carbon Peak (Overall)_metric.xlsx', 'Fiscal Support_metric.xlsx', 'Green and Low-Carbon Transition_metric.xlsx', 'Green Consumption_metric.xlsx', 'Green, Low-Carbon, and Circular_metric.xlsx', 'Industrial Sector_metric.xlsx', 'New Development Philosophy_metric.xlsx', 'Non-ferrous Metals_metric.xlsx', 'Pollution and Carbon Reduction_metric.xlsx', 'Standards and Metrology_metric.xlsx', 'Urban and Rural Development Sec_metric.xlsx']
    thresholds = [0.78, 0.76, 0.77, 0.77, 0.80, 0.77, 0.75, 0.73, 0.82, 0.75, 0.76, 0.74]

    generate_networks(thresholds)