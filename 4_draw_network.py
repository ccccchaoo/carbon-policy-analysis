# -*- coding: utf-8 -*-
"""
政策主题潜在扩散网络绘制（Source & Adoption 双方向）
=====================================================

针对新生成的 network_metrics 文件夹中的 *_source.xlsx 和 *_adoption.xlsx，
分别绘制每个阈值下的组合网络大图，并输出节点统计和网络统计 Excel。

主要修改：
- 输入目录：results/Qwen3-Embedding-0.6B/network_metrics
- 文件命名：{mission}_source.xlsx 和 {mission}_adoption.xlsx
- 边方向：adopter_file -> source_file（采用者→源）
- 边权重：直接使用 att（source_att 或 adoption_att），不再取负
- diff 直接使用，不再取负
- 中央文件识别：依据 source_type == '中央' 提取 source_file
"""

import os
import re
import warnings

import numpy as np
import pandas as pd
import networkx as nx

import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

warnings.filterwarnings("ignore")

# ============================================================
# 1. 参数设置
# ============================================================

THRESHOLDS = [0.0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65]

# 新输入目录（存放 source 和 adoption 表）
INPUT_DIR = r"results\Qwen3-Embedding-0.6B\network_metrics"

# 输出根目录（按方向区分）
OUTPUT_ROOT = r"results\Qwen3-Embedding-0.6B\network_plots"

# 组合图尺寸
COMBINED_FIGSIZE = (24, 8)
DPI = 600

# ============================================================
# 2. 主题列表与缩写（与之前一致）
# ============================================================

MISSION_NAMES = [
    "Building Materials Industry",
    "Carbon Peak (Overall)",
    "Fiscal Support",
    "Green and Low-Carbon Transition",
    "Green Consumption",
    "Green, Low-Carbon, and Circular",
    "Industrial Sector",
    "New Development Philosophy",
    "Non-ferrous Metals",
    "Pollution and Carbon Reduction",
    "Standards and Metrology",
    "Urban and Rural Development Sec",
]

MISSION_FULL_NAMES = {
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

# ============================================================
# 3. 省份缩写
# ============================================================

PROVINCE_ABBR = {
    "北京": "BJ", "天津": "TJ", "河北": "HE",  # 修正：原为 HB
    "山西": "SX", "内蒙古": "NM", "辽宁": "LN", "吉林": "JL",
    "黑龙江": "HL", "上海": "SH", "江苏": "JS", "浙江": "ZJ",
    "安徽": "AH", "福建": "FJ", "江西": "JX", "山东": "SD",
    "河南": "HA", "湖北": "HB",  # 保持不变
    "湖南": "HN", "广东": "GD", "广西": "GX", "海南": "HI",
    "重庆": "CQ", "四川": "SC", "贵州": "GZ", "云南": "YN",
    "西藏": "XZ", "陕西": "SN",  # 注意：为避免与山西(SX)冲突，取"陕"拼音首字母+后鼻音
    "甘肃": "GS", "青海": "QH", "宁夏": "NX", "新疆": "XJ",
}

# ============================================================
# 4. 字体设置
# ============================================================

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False

# ============================================================
# 5. 辅助函数（识别省份、标签、颜色等）
# ============================================================

def safe_filename(text):
    text = str(text)
    return re.sub(r'[\\/:*?"<>|]', "_", text)

def identify_province_from_filename(filename):
    filename = str(filename)
    province_candidates = [
        "内蒙古", "黑龙江", "广西", "宁夏", "新疆", "西藏",
        "北京", "天津", "河北", "山西", "辽宁", "吉林",
        "上海", "江苏", "浙江", "安徽", "福建", "江西",
        "山东", "河南", "湖北", "湖南", "广东", "海南",
        "重庆", "四川", "贵州", "云南", "陕西", "甘肃", "青海",
    ]
    for province in province_candidates:
        if province in filename:
            return province
    return None

def get_node_label(filename, central_files):
    filename = str(filename)
    if filename in central_files:
        return "Central"
    province = identify_province_from_filename(filename)
    if province is not None:
        return PROVINCE_ABBR.get(province, province)
    return filename

def get_node_type(filename, central_files):
    filename = str(filename)
    if filename in central_files:
        return "Central"
    province = identify_province_from_filename(filename)
    if province is not None:
        return "Province"
    return "Unknown"

def create_blue_white_red_cmap():
    return LinearSegmentedColormap.from_list("blue_white_red", ["blue", "white", "red"], N=256)

BLUE_WHITE_RED = create_blue_white_red_cmap()

def value_to_color(value, max_abs):
    if pd.isna(value):
        return (0.65, 0.65, 0.65, 1.0)
    if max_abs is None or max_abs <= 1e-12:
        return (1.0, 1.0, 1.0, 1.0)
    normalized = np.clip(value / max_abs, -1, 1)
    cmap_value = (normalized + 1) / 2
    return BLUE_WHITE_RED(cmap_value)

# ============================================================
# 6. 读取指定方向的数据
# ============================================================

def read_mission_data(mission_name, direction):
    """
    读取新生成的 network_metrics 中的 *_source.xlsx 或 *_adoption.xlsx
    direction: 'source' 或 'adoption'
    返回 DataFrame 和中央文件集合。
    """
    file_name = f"{mission_name}_{direction}.xlsx"
    file_path = os.path.join(INPUT_DIR, file_name)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"找不到文件：{file_path}")

    print()
    print("=" * 80)
    print(f"读取主题：{mission_name}，方向：{direction}")
    print(f"文件：{file_path}")
    print("=" * 80)

    df = pd.read_excel(file_path, sheet_name=0)

    # 新表应包含的列
    required_cols = ["domain", "adopter_file", "source_file", "source_type",
                     f"{direction}_sim", f"{direction}_att", f"{direction}_diff", "p_a_s", "k"]
    # 检查列存在
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"{mission_name} 缺少列：{missing}")

    # 统一列名：将 sim/att/diff 统一为 sim, att, diff
    df = df.rename(columns={
        f"{direction}_sim": "sim",
        f"{direction}_att": "att",
        f"{direction}_diff": "diff"
    })

    # 转为数值
    for col in ["sim", "att", "diff", "p_a_s"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # 去除缺失关键字段的行
    df = df.dropna(subset=["adopter_file", "source_file", "p_a_s"]).copy()
    df["adopter_file"] = df["adopter_file"].astype(str).str.strip()
    df["source_file"] = df["source_file"].astype(str).str.strip()
    df["source_type"] = df["source_type"].astype(str).str.strip()

    # 识别中央文件：所有 source_type == '中央' 对应的 source_file
    central_files = set()
    central_mask = df["source_type"] == "中央"
    if central_mask.any():
        central_files = set(df.loc[central_mask, "source_file"].unique())
    print(f"识别到中央文件：{list(central_files)}")
    return df, central_files

# ============================================================
# 7. 网络构建（与之前类似，但调整了权重和方向）
# ============================================================

def aggregate_edges(filtered):
    """
    按 (adopter_file, source_file) 聚合，计算平均 sim, att, diff, p_a_s
    边权重直接使用 att（不再取负）
    """
    if len(filtered) == 0:
        return pd.DataFrame(columns=[
            "adopter_file", "source_file", "sim", "att", "diff", "p_a_s", "weight"
        ])
    grouped = filtered.groupby(["adopter_file", "source_file"], as_index=False).agg({
        "sim": "mean",
        "att": "mean",
        "diff": "mean",
        "p_a_s": "mean",
    })
    # 边权重直接使用 att（adopter - source 的平均值）
    grouped["weight"] = grouped["att"]
    return grouped

def build_network(df, threshold):
    """
    根据 p_a_s 阈值筛选，构建有向图（adopter -> source）
    """
    filtered = df[df["p_a_s"] >= threshold].copy()
    filtered = filtered.dropna(subset=["adopter_file", "source_file", "att"])
    edge_df = aggregate_edges(filtered)

    G = nx.DiGraph()
    if len(edge_df) > 0:
        nodes = set(edge_df["adopter_file"].tolist() + edge_df["source_file"].tolist())
        G.add_nodes_from(nodes)

    for _, row in edge_df.iterrows():
        source = row["source_file"]
        target = row["adopter_file"]   # 注意：边 direction: adopter -> source，但 networkx 中 edge 是 (u, v) 其中 u=adopter, v=source
        # 我们采用 (adopter, source) 作为有向边
        u = target
        v = source
        if u == v:
            continue
        G.add_edge(
            u, v,
            weight=float(row["weight"]),
            avg_sim=float(row["sim"]),
            avg_att=float(row["att"]),
            avg_diff=float(row["diff"]),
            avg_p_a_s=float(row["p_a_s"])
        )
    return G, edge_df, filtered

# ============================================================
# 8. 节点统计和网络统计（调整 diff 处理）
# ============================================================

def calculate_pagerank(G):
    if G.number_of_nodes() == 0:
        return {}
    unweighted_G = nx.DiGraph()
    unweighted_G.add_nodes_from(G.nodes())
    unweighted_G.add_edges_from(G.edges())
    try:
        pagerank = nx.pagerank(unweighted_G, alpha=0.85)
    except Exception as e:
        print(f"PageRank 计算失败：{e}")
        n = unweighted_G.number_of_nodes()
        pagerank = {node: 1.0 / n for node in unweighted_G.nodes()}
    return pagerank

def calculate_node_statistics(G, pagerank, central_files):
    rows = []
    for node in G.nodes():
        in_edges = list(G.in_edges(node, data=True))   # 指向 node 的边（即 node 作为 source 被采纳）
        out_edges = list(G.out_edges(node, data=True)) # 从 node 出发的边（即 node 作为 adopter 采纳别人）
        incident_edges = in_edges + out_edges

        # 平均相似度（所有关联边）
        sim_values = []
        for _, _, data in incident_edges:
            value = data.get("avg_sim", np.nan)
            if not pd.isna(value):
                sim_values.append(float(value))
        avg_similarity = np.mean(sim_values) if sim_values else np.nan

        # 入边权重平均（别人采纳本节点的平均 att）
        in_weights = []
        for _, _, data in in_edges:
            value = data.get("weight", np.nan)
            if not pd.isna(value):
                in_weights.append(float(value))
        avg_in_weight = np.mean(in_weights) if in_weights else np.nan

        # 出边权重平均（本节点采纳别人的平均 att）
        out_weights = []
        for _, _, data in out_edges:
            value = data.get("weight", np.nan)
            if not pd.isna(value):
                out_weights.append(float(value))
        avg_out_weight = np.mean(out_weights) if out_weights else np.nan

        # 出边 diff 的平均（直接使用 diff，不再取负）
        diff_values = []
        for _, _, data in out_edges:
            d = data.get("avg_diff", np.nan)
            if not pd.isna(d):
                diff_values.append(float(d))
        avg_diff = np.mean(diff_values) if diff_values else np.nan

        pr = pagerank.get(node, 0.0)
        node_label = get_node_label(node, central_files)
        node_type = get_node_type(node, central_files)

        rows.append({
            "node_file": node,
            "node_label": node_label,
            "node_type": node_type,
            "average_similarity": avg_similarity,
            "average_in_weight": avg_in_weight,
            "average_out_weight": avg_out_weight,
            "average_diff": avg_diff,          # 直接使用 diff 平均
            "PageRank": pr,
            "in_degree": G.in_degree(node),
            "out_degree": G.out_degree(node),
            "degree": G.degree(node),
        })
    return pd.DataFrame(rows)

def calculate_network_density(G):
    n = G.number_of_nodes()
    m = G.number_of_edges()
    if n <= 1:
        return 0.0
    return m / (n * (n - 1))

def calculate_modularity(G):
    if G.number_of_nodes() == 0 or G.number_of_edges() == 0:
        return np.nan
    UG = nx.Graph()
    UG.add_nodes_from(G.nodes())
    UG.add_edges_from(G.edges())
    if UG.number_of_edges() == 0:
        return np.nan
    try:
        communities = nx.community.greedy_modularity_communities(UG)
        modularity = nx.community.modularity(UG, communities)
        return modularity
    except Exception as e:
        print(f"模块度计算失败：{e}")
        return np.nan

# ============================================================
# 9. 子图绘制（修改节点颜色基于 average_diff）
# ============================================================

def plot_network_on_ax(ax, G, node_stats, edge_df, central_files, mission_name, threshold):
    if G.number_of_nodes() == 0:
        ax.text(0.5, 0.5, "No network", ha='center', va='center', fontsize=12, color='gray')
        ax.set_title(MISSION_FULL_NAMES.get(mission_name, mission_name), fontsize=14, fontweight='bold')
        ax.set_axis_off()
        return

    pos = nx.spring_layout(G, k=3, iterations=150, seed=42)

    # 节点大小按 PageRank
    pr_vals = node_stats["PageRank"].values.astype(float)
    if len(pr_vals) > 0:
        min_pr, max_pr = np.min(pr_vals), np.max(pr_vals)
        if max_pr > min_pr:
            sizes = 80 + 200 * (pr_vals - min_pr) / (max_pr - min_pr)
        else:
            sizes = np.full(len(pr_vals), 150)
    else:
        sizes = [150] * G.number_of_nodes()

    # 节点颜色：基于 average_diff（直接使用 diff 平均）
    node_colors = []
    for node in G.nodes():
        row = node_stats[node_stats["node_file"] == node]
        if len(row) == 0:
            node_colors.append((0.65, 0.65, 0.65, 1.0))
            continue
        value = row.iloc[0]["average_diff"]
        if pd.isna(value):
            node_colors.append((0.65, 0.65, 0.65, 1.0))
        elif abs(value) <= 1e-12:
            node_colors.append((1.0, 1.0, 1.0, 1.0))
        else:
            vals = node_stats["average_diff"].dropna()
            max_abs = max(abs(vals.min()), abs(vals.max())) if len(vals) > 0 else 0.0
            node_colors.append(value_to_color(value, max_abs))

    # 边颜色与宽度基于 weight（即 att）
    edge_weights = [data["weight"] for _, _, data in G.edges(data=True)]
    if edge_weights:
        max_abs_edge = max(abs(min(edge_weights)), abs(max(edge_weights)))
    else:
        max_abs_edge = 0.0

    edge_colors, edge_widths = [], []
    for _, _, data in G.edges(data=True):
        w = data["weight"]
        color = value_to_color(w, max_abs_edge)
        color = (color[0], color[1], color[2], 0.72)
        edge_colors.append(color)
        if max_abs_edge > 1e-12:
            width = 0.3 + 1.2 * abs(w) / max_abs_edge
        else:
            width = 0.3
        edge_widths.append(width)

    # 绘图
    if G.number_of_edges() > 0:
        nx.draw_networkx_edges(
            G, pos, ax=ax,
            edge_color=edge_colors, width=edge_widths,
            alpha=0.75, arrowstyle="->", arrowsize=10,
            connectionstyle="arc3,rad=0.08",
            min_source_margin=4, min_target_margin=4
        )

    nx.draw_networkx_nodes(
        G, pos, ax=ax,
        node_color=node_colors, node_size=sizes,
        edgecolors="black", linewidths=0.6, alpha=0.95
    )

    # 标签
    labels = {node: get_node_label(node, central_files) for node in G.nodes()}
    x_vals = [p[0] for p in pos.values()]
    y_vals = [p[1] for p in pos.values()]
    x_range = max(x_vals) - min(x_vals) if x_vals else 1
    y_range = max(y_vals) - min(y_vals) if y_vals else 1
    offset_x = max(0.01, x_range * 0.02)
    offset_y = max(0.01, y_range * 0.02)
    label_pos = {node: (x + offset_x, y + offset_y) for node, (x, y) in pos.items()}
    nx.draw_networkx_labels(
        G, label_pos, labels=labels, ax=ax,
        font_size=9, font_weight='bold', font_color='black'
    )

    ax.set_title(MISSION_FULL_NAMES.get(mission_name, mission_name), fontsize=14, fontweight='bold')
    ax.set_axis_off()

# ============================================================
# 10. 组合大图绘制
# ============================================================

def draw_combined_network(threshold, missions_data, direction, output_dir):
    """
    missions_data: list of dict, 每个包含 mission_name, G, node_stats, edge_df, central_files
    direction: 'source' 或 'adoption'
    """
    fig, axes = plt.subplots(2, 6, figsize=COMBINED_FIGSIZE)
    fig.suptitle("", fontsize=24, y=0.96)
    fig.text(0.5, 0.92, rf"$p_{{a,s}} \geq {threshold:.2f}$", fontsize=18, ha='center', va='top')

    # 按字母顺序排序
    sorted_mission_names = sorted(MISSION_NAMES, key=lambda x: MISSION_FULL_NAMES[x])

    for idx, mission_name in enumerate(sorted_mission_names):
        row = idx // 6
        col = idx % 6
        ax = axes[row, col]

        data = next((d for d in missions_data if d["mission_name"] == mission_name), None)
        if data is None:
            ax.text(0.5, 0.5, "No data", ha='center', va='center', fontsize=12, color='gray')
            ax.set_title(MISSION_FULL_NAMES.get(mission_name, mission_name), fontsize=14, fontweight='bold')
            ax.set_axis_off()
            continue

        plot_network_on_ax(
            ax,
            data["G"],
            data["node_stats"],
            data["edge_df"],
            data["central_files"],
            data["mission_name"],
            threshold
        )

    plt.subplots_adjust(left=0.02, right=0.98, bottom=0.02, top=0.88, wspace=0.15, hspace=0.25)

    # 保存
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"combined_{direction}_threshold_{threshold:.2f}.png")
    plt.savefig(output_file, dpi=DPI, bbox_inches='tight', pad_inches=0.1)
    plt.close()
    print(f"已保存组合图：{output_file}")

# ============================================================
# 11. 分析一个主题（返回各阈值数据）
# ============================================================

def analyze_mission(mission_name, direction):
    df, central_files = read_mission_data(mission_name, direction)
    all_node_stats = []
    all_net_stats = []
    threshold_data = []

    for threshold in THRESHOLDS:
        print()
        print("-" * 80)
        print(f"主题：{mission_name}，方向：{direction}，阈值：{threshold:.2f}")
        print("-" * 80)

        G, edge_df, filtered = build_network(df, threshold)
        print(f"筛选后原始记录：{len(filtered)}")
        print(f"聚合后边数：{G.number_of_edges()}")
        print(f"节点数：{G.number_of_nodes()}")

        pagerank = calculate_pagerank(G)
        node_stats = calculate_node_statistics(G, pagerank, central_files)

        # 添加 mission 信息
        node_stats.insert(0, "mission", mission_name)
        node_stats.insert(1, "mission_abbr", MISSION_FULL_NAMES.get(mission_name, mission_name))
        node_stats.insert(2, "threshold", threshold)
        node_stats.insert(3, "direction", direction)

        density = calculate_network_density(G)
        modularity = calculate_modularity(G)
        network_stats = pd.DataFrame([{
            "mission": mission_name,
            "mission_abbr": MISSION_FULL_NAMES.get(mission_name, mission_name),
            "threshold": threshold,
            "direction": direction,
            "nodes": G.number_of_nodes(),
            "edges": G.number_of_edges(),
            "density": density,
            "modularity": modularity,
            "central_files": "; ".join(sorted(central_files)),
        }])

        all_node_stats.append(node_stats)
        all_net_stats.append(network_stats)

        threshold_data.append({
            "threshold": threshold,
            "G": G,
            "node_stats": node_stats,
            "edge_df": edge_df,
            "central_files": central_files,
            "mission_name": mission_name,
        })

    return pd.concat(all_node_stats, ignore_index=True), pd.concat(all_net_stats, ignore_index=True), threshold_data

# ============================================================
# 12. 保存 Excel（分方向）
# ============================================================

def make_sheet_name(mission_name, threshold, direction):
    short_name = {
        "Building Materials Industry": "BuildingMaterials",
        "Carbon Peak (Overall)": "CarbonPeak",
        "Fiscal Support": "FiscalSupport",
        "Green and Low-Carbon Transition": "GreenTransition",
        "Green Consumption": "GreenConsumption",
        "Green, Low-Carbon, and Circular": "GreenCircular",
        "Industrial Sector": "Industrial",
        "New Development Philosophy": "NewDevelopment",
        "Non-ferrous Metals": "Nonferrous",
        "Pollution and Carbon Reduction": "PollutionCarbon",
        "Standards and Metrology": "Standards",
        "Urban and Rural Development Sec": "UrbanRural",
    }
    base = short_name.get(mission_name, mission_name)
    sheet_name = f"{base}_{direction}_t{threshold:.2f}"
    return sheet_name[:31]

def save_results_to_excel(all_node_stats, all_net_stats, direction, output_dir):
    excel_path = os.path.join(output_dir, f"network_statistics_{direction}.xlsx")
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        all_node_stats.to_excel(writer, sheet_name="All_Node_Statistics", index=False)
        all_net_stats.to_excel(writer, sheet_name="All_Network_Statistics", index=False)
        for mission_name in MISSION_NAMES:
            mission_df = all_node_stats[all_node_stats["mission"] == mission_name].copy()
            if len(mission_df) == 0:
                continue
            for threshold in THRESHOLDS:
                threshold_df = mission_df[np.isclose(mission_df["threshold"], threshold)].copy()
                if len(threshold_df) == 0:
                    continue
                sheet_name = make_sheet_name(mission_name, threshold, direction)
                threshold_df.to_excel(writer, sheet_name=sheet_name, index=False)
    print(f"Excel 已保存：{excel_path}")

# ============================================================
# 13. 主程序（同时处理两个方向）
# ============================================================

def main():
    print()
    print("=" * 100)
    print("政策主题网络绘制（Source & Adoption 双方向）")
    print("=" * 100)
    print(f"阈值：{THRESHOLDS}")
    print(f"输入目录：{INPUT_DIR}")

    # 处理 source 和 adoption 两个方向
    for direction in ["source", "adoption"]:
        print(f"\n\n>>> 开始处理方向：{direction.upper()} <<<\n")
        output_dir = os.path.join(OUTPUT_ROOT, direction)
        os.makedirs(output_dir, exist_ok=True)

        all_node_stats = []
        all_net_stats = []
        threshold_data_dict = {th: [] for th in THRESHOLDS}

        for mission_name in MISSION_NAMES:
            try:
                node_stats, net_stats, mission_threshold_data = analyze_mission(mission_name, direction)
                all_node_stats.append(node_stats)
                all_net_stats.append(net_stats)

                for item in mission_threshold_data:
                    th = item["threshold"]
                    threshold_data_dict[th].append({
                        "mission_name": mission_name,
                        "G": item["G"],
                        "node_stats": item["node_stats"],
                        "edge_df": item["edge_df"],
                        "central_files": item["central_files"],
                    })
            except FileNotFoundError as e:
                print(f"[警告] {mission_name} 文件不存在：{e}")
                continue
            except Exception as e:
                print(f"[错误] 处理主题 {mission_name} 失败：{repr(e)}")
                continue

        if len(all_node_stats) == 0:
            print(f"方向 {direction} 没有生成任何结果。")
            continue

        all_node_stats = pd.concat(all_node_stats, ignore_index=True)
        all_net_stats = pd.concat(all_net_stats, ignore_index=True)
        all_node_stats = all_node_stats.sort_values(["mission", "threshold", "PageRank"],
                                                    ascending=[True, True, False]).reset_index(drop=True)
        all_net_stats = all_net_stats.sort_values(["mission", "threshold"]).reset_index(drop=True)

        # 保存 Excel
        save_results_to_excel(all_node_stats, all_net_stats, direction, output_dir)

        # 绘制组合大图
        for threshold in THRESHOLDS:
            missions_data = threshold_data_dict[threshold]
            if not missions_data:
                print(f"警告：阈值 {threshold} 没有数据，跳过组合图。")
                continue
            draw_combined_network(threshold, missions_data, direction, output_dir)

        print(f"\n方向 {direction.upper()} 完成。")
        print(f"图片目录：{output_dir}")

    print("\n" + "=" * 100)
    print("全部分析完成！")
    print("=" * 100)

if __name__ == "__main__":
    main()