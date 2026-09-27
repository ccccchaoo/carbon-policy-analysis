import os
import numpy as np
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
from networkx.algorithms.community import greedy_modularity_communities, modularity

# ================== 配置 ==================
DOMAINS = [
    "Carbon Peak (Overall)",
    "New Development Philosophy",
    "Industrial Sector",
    "Urban and Rural Development Sec",
    "Pollution and Carbon Reduction",
    "Green Consumption",
    "Green, Low-Carbon, and Circular",
    "Green and Low-Carbon Transition",
    "Non-ferrous Metals",
    "Building Materials Industry",
    "Standards and Metrology",
    "Fiscal Support"
]

MISSION_SHORT = {
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
    "Fiscal Support": "l",
}

BASE_PATH = r"results\Qwen3-Embedding-0.6B\network_metrics"
THRESHOLDS = np.arange(0.0, 1.005, 0.01)

# ================== 核心计算函数 ==================
def compute_metrics(df, att_col='adoption_att', diff_col='adoption_diff'):
    """
    计算给定DataFrame在各阈值下的指标。
    返回DataFrame包含：threshold, n_edges, avg_att, avg_diff, modularity
    """
    edges = df[['source_file', 'adopter_file', 'p_a_s', att_col, diff_col]].drop_duplicates()
    results = []
    for t in THRESHOLDS:
        sub = edges[edges['p_a_s'] > t]
        n_edges = len(sub)
        if n_edges == 0:
            avg_att = np.nan
            avg_diff = np.nan
            mod = 0.0
        else:
            avg_att = sub[att_col].mean()
            avg_diff = sub[diff_col].mean()
            # 构建仅含活跃边的无向图
            G = nx.Graph()
            for _, row in sub.iterrows():
                G.add_edge(row['source_file'], row['adopter_file'])
            try:
                comms = greedy_modularity_communities(G)
                mod = modularity(G, comms)
            except:
                mod = 0.0
        results.append({
            'threshold': t,
            'n_edges': n_edges,
            'avg_att': avg_att,
            'avg_diff': avg_diff,
            'modularity': mod
        })
    return pd.DataFrame(results)

# ================== 处理所有领域 ==================
all_domain_data = {}  # domain -> dict with keys: 'adpt' and 'src', each a DataFrame

# 先统一计算全局坐标范围
global_left_max = 0
global_right_min = float('inf')
global_right_max = -float('inf')

for domain in DOMAINS:
    # 读取adoption文件
    df_adpt = pd.read_excel(os.path.join(BASE_PATH, f"{domain}_adoption.xlsx"))
    df_src = pd.read_excel(os.path.join(BASE_PATH, f"{domain}_source.xlsx"))
    # source文件列名不同，重命名
    if 'source_att' in df_src.columns:
        df_src = df_src.rename(columns={'source_att': 'adoption_att', 'source_diff': 'adoption_diff'})
    # 计算
    res_adpt = compute_metrics(df_adpt, 'adoption_att', 'adoption_diff')
    res_src = compute_metrics(df_src, 'adoption_att', 'adoption_diff')
    all_domain_data[domain] = {'adpt': res_adpt, 'src': res_src}

    # 更新全局坐标（边数取任意一个即可）
    left_max = res_adpt['n_edges'].max()
    if left_max > global_left_max:
        global_left_max = left_max

    # 右轴：包含模块度、adpt_att, adpt_diff, src_att, src_diff
    right_vals = pd.concat([
        res_adpt['modularity'],
        res_adpt['avg_att'], res_adpt['avg_diff'],
        res_src['avg_att'], res_src['avg_diff']
    ], ignore_index=True).dropna()
    if len(right_vals) > 0:
        rmin, rmax = right_vals.min(), right_vals.max()
        if rmin < global_right_min:
            global_right_min = rmin
        if rmax > global_right_max:
            global_right_max = rmax

# 调整右轴范围
if global_right_min == float('inf'):
    global_right_min = 0
if global_right_max == -float('inf'):
    global_right_max = 1
padding = (global_right_max - global_right_min) * 0.05
global_right_min -= padding
global_right_max += padding
if global_right_min < -0.1:
    global_right_min = -0.1
if global_right_max < 0.1:
    global_right_max = 0.1
global_right_max = 1
global_right_min = -1


# ================== 绘图 ==================
fig, axes = plt.subplots(2, 6, figsize=(24, 10))

# 颜色和线型定义
colors = {
    'n_edges': 'blue',
    'modularity': 'green',
    'att': 'red',
    'diff': 'orange'
}
linestyles = {
    'adpt': '-',
    'src': '--'
}

# 标签（用于图例）
legend_lines = []

for idx, domain in enumerate(DOMAINS):
    row = idx // 6
    col = idx % 6
    ax = axes[row, col]

    res_adpt = all_domain_data[domain]['adpt']
    res_src = all_domain_data[domain]['src']

    # --- 左轴：边数（只画一次） ---
    ln1, = ax.plot(res_adpt['threshold'], res_adpt['n_edges'],
                   color=colors['n_edges'], label='Edge Count')
    ax.set_xlim(0, 1)
    ax.set_ylim(0, global_left_max * 1.05 if global_left_max > 0 else 1)
    ax.set_xlabel('Threshold (p_a_s > t)', fontsize=10)
    ax.set_ylabel('Edge Count', fontsize=10, color=colors['n_edges'])
    ax.tick_params(axis='y', labelcolor=colors['n_edges'], labelsize=9)
    ax.tick_params(axis='x', labelsize=9)

    # --- 右轴：模块度 + 四条att/diff线 ---
    ax2 = ax.twinx()
    # 模块度（绿色，实线）
    ln2, = ax2.plot(res_adpt['threshold'], res_adpt['modularity'],
                    color=colors['modularity'], linestyle='-', label='Modularity')
    # att: adpt (红色实线), src (红色虚线)
    ln3, = ax2.plot(res_adpt['threshold'], res_adpt['avg_att'],
                    color=colors['att'], linestyle=linestyles['adpt'], label='Adpt_att')
    ln4, = ax2.plot(res_src['threshold'], res_src['avg_att'],
                    color=colors['att'], linestyle=linestyles['src'], label='Src_att')
    # diff: adpt (橙色实线), src (橙色虚线)
    ln5, = ax2.plot(res_adpt['threshold'], res_adpt['avg_diff'],
                    color=colors['diff'], linestyle=linestyles['adpt'], label='Adpt_diff')
    ln6, = ax2.plot(res_src['threshold'], res_src['avg_diff'],
                    color=colors['diff'], linestyle=linestyles['src'], label='Src_diff')

    ax2.set_ylim(global_right_min, global_right_max)
    ax2.set_ylabel('Metrics', fontsize=10)
    ax2.tick_params(axis='y', labelsize=9)

    # 小标题
    ax.set_title(MISSION_SHORT[domain], fontsize=12, fontweight='bold')

    # 收集图例句柄（只取第一个子图的）
    if idx == 0:
        legend_lines = [ln1, ln2, ln3, ln4, ln5, ln6]

# 设置图例（放在大图左上角）
fig.legend(handles=legend_lines,
           labels=['Edge Count', 'Modularity', 'S-to-A Att', 'A-to-S Att', 'S-to-A Diff', 'A-to-S Diff'],
           loc='upper left', bbox_to_anchor=(0.02, 0.98), fontsize=10, frameon=True)

plt.tight_layout(rect=[0, 0, 1, 0.95])
plt.savefig("combined_adoption_source_metrics.png", dpi=300, bbox_inches='tight')
plt.show()