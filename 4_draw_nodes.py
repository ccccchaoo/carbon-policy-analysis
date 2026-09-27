import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import os

# ============================================================
# 1. 参数设置
# ============================================================
BASE_DIR = r'results\Qwen3-Embedding-0.6B\network_plots'
DIRECTIONS = ['source', 'adoption']

COL_OUT = 'average_out_weight'
COL_DIFF = 'average_diff'
COL_PR = 'PageRank'

LEGEND_LABELS = {
    COL_OUT: 'out_weight',
    COL_DIFF: 'diff',
    COL_PR: 'PageRank'
}

# ============================================================
# 2. 省份缩写与排序（中央排第一，其后按省份字典顺序）
# ============================================================
PROVINCE_ABBR = {
    "北京": "BJ", "天津": "TJ", "河北": "HE",
    "山西": "SX", "内蒙古": "NM", "辽宁": "LN", "吉林": "JL",
    "黑龙江": "HL", "上海": "SH", "江苏": "JS", "浙江": "ZJ",
    "安徽": "AH", "福建": "FJ", "江西": "JX", "山东": "SD",
    "河南": "HA", "湖北": "HB", "湖南": "HN", "广东": "GD",
    "广西": "GX", "海南": "HI", "重庆": "CQ", "四川": "SC",
    "贵州": "GZ", "云南": "YN", "西藏": "XZ", "陕西": "SN",
    "甘肃": "GS", "青海": "QH", "宁夏": "NX", "新疆": "XJ",
}

ORDERED_LABELS = ['Central'] + [PROVINCE_ABBR[p] for p in PROVINCE_ABBR.keys()]

# ============================================================
# 3. 主循环：分别处理 source 和 adoption
# ============================================================
for direction in DIRECTIONS:
    print(f"\n>>> Processing direction: {direction.upper()} <<<")
    
    input_file = os.path.join(BASE_DIR, direction, f'network_statistics_{direction}.xlsx')
    if not os.path.exists(input_file):
        print(f"File not found: {input_file}, skipping.")
        continue
    
    df = pd.read_excel(input_file, sheet_name='All_Node_Statistics')
    
    # 确保数值列正确
    for col in [COL_OUT, COL_DIFF, COL_PR]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        else:
            raise ValueError(f"Column '{col}' missing in {input_file}")
    
    mission_abbrs = sorted(df['mission_abbr'].unique())
    thresholds = sorted(df['threshold'].unique())
    
    # ---- 为每个任务确定节点顺序（基于全局排序过滤） ----
    base_order_dict = {}
    for mission in mission_abbrs:
        df_mission = df[df['mission_abbr'] == mission]
        existing_labels = df_mission['node_label'].unique()
        base_order = [label for label in ORDERED_LABELS if label in existing_labels]
        base_order_dict[mission] = base_order
    
    # ---- 创建输出目录 ----
    output_dir = os.path.join(BASE_DIR, direction, 'node_scatter')
    os.makedirs(output_dir, exist_ok=True)
    
    # ---- 图例元素 ----
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', markerfacecolor='blue', markersize=8, label=LEGEND_LABELS[COL_OUT]),
        Line2D([0], [0], marker='s', color='w', markerfacecolor='red', markersize=8, label=LEGEND_LABELS[COL_DIFF]),
        Line2D([0], [0], marker='^', color='w', markerfacecolor='green', markersize=8, label=LEGEND_LABELS[COL_PR])
    ]
    
    # ---- 对每个阈值生成 2×6 大图 ----
    n_rows, n_cols = 2, 6
    fig_width = n_cols * 4.5
    fig_height = n_rows * 3.8
    
    for th in thresholds:
        # ---- 收集当前阈值下所有任务的指标值（有效值），用于计算全局轴范围 ----
        all_out = []
        all_diff = []
        all_pr = []
        for mission in mission_abbrs:
            df_th = df[(df['mission_abbr'] == mission) & (df['threshold'] == th)]
            all_out.extend(df_th[COL_OUT].dropna().values)
            all_diff.extend(df_th[COL_DIFF].dropna().values)
            all_pr.extend(df_th[COL_PR].dropna().values)
        
        # 左轴范围（out_weight 和 diff）
        if all_out and all_diff:
            ymin_l = min(min(all_out), min(all_diff))
            ymax_l = max(max(all_out), max(all_diff))
        elif all_out:
            ymin_l, ymax_l = min(all_out), max(all_out)
        elif all_diff:
            ymin_l, ymax_l = min(all_diff), max(all_diff)
        else:
            ymin_l, ymax_l = -1, 1
        margin_l = 0.1 * (ymax_l - ymin_l) if ymax_l != ymin_l else 0.5
        ymin_l -= margin_l
        ymax_l += margin_l
        
        # 右轴范围（PageRank）
        if all_pr:
            ymin_r, ymax_r = min(all_pr), max(all_pr)
        else:
            ymin_r, ymax_r = 0, 1
        margin_r = 0.1 * (ymax_r - ymin_r) if ymax_r != ymin_r else 0.1
        ymin_r -= margin_r
        ymax_r += margin_r
        
        # ---- 创建子图 ----
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(fig_width, fig_height))
        axes_flat = axes.flatten()
        
        for idx, mission in enumerate(mission_abbrs):
            ax = axes_flat[idx]
            base_labels = base_order_dict[mission]
            n_nodes = len(base_labels)
            x = np.arange(n_nodes)
            
            # 获取当前阈值数据
            df_th = df[(df['mission_abbr'] == mission) & (df['threshold'] == th)]
            label_to_out = dict(zip(df_th['node_label'], df_th[COL_OUT]))
            label_to_diff = dict(zip(df_th['node_label'], df_th[COL_DIFF]))
            label_to_pr = dict(zip(df_th['node_label'], df_th[COL_PR]))
            
            # 构建完整列表（含 NaN）
            out_vals = [label_to_out.get(lbl, np.nan) for lbl in base_labels]
            diff_vals = [label_to_diff.get(lbl, np.nan) for lbl in base_labels]
            pr_vals = [label_to_pr.get(lbl, np.nan) for lbl in base_labels]
            
            # ----- 左轴：out_weight 和 diff（仅画非NaN点） -----
            out_x = [x[i] for i, v in enumerate(out_vals) if not np.isnan(v)]
            out_y = [v for v in out_vals if not np.isnan(v)]
            if out_x:
                ax.scatter(out_x, out_y, color='blue', marker='o', s=18)
            
            diff_x = [x[i] for i, v in enumerate(diff_vals) if not np.isnan(v)]
            diff_y = [v for v in diff_vals if not np.isnan(v)]
            if diff_x:
                ax.scatter(diff_x, diff_y, color='red', marker='s', s=18)
            
            ax.axhline(0, color='gray', linestyle='--', linewidth=0.6, alpha=0.5)
            ax.set_ylim(ymin_l, ymax_l)   # 统一左轴范围
            ax.set_ylabel('out-weight / diff', fontsize=9)
            ax.tick_params(axis='y', labelsize=9)
            
            # ----- 右轴：PageRank（仅画非NaN点） -----
            ax2 = ax.twinx()
            pr_x = [x[i] for i, v in enumerate(pr_vals) if not np.isnan(v)]
            pr_y = [v for v in pr_vals if not np.isnan(v)]
            if pr_x:
                ax2.scatter(pr_x, pr_y, color='green', marker='^', s=22)
            ax2.set_ylim(ymin_r, ymax_r)   # 统一右轴范围
            ax2.set_ylabel('PageRank', color='green', fontsize=9)
            ax2.tick_params(axis='y', labelcolor='green', labelsize=9)
            
            # ----- x 轴设置（保留所有泳道） -----
            ax.set_xticks(x)
            ax.set_xticklabels(base_labels, rotation=90, fontsize=9)
            ax.set_xlim(-0.6, n_nodes - 0.4)
            ax.set_title(f'{mission}', fontsize=16)
        
        # 隐藏多余子图（若主题数不足12）
        for j in range(len(mission_abbrs), len(axes_flat)):
            fig.delaxes(axes_flat[j])

       
        
        # 全局图例和标题
        fig.legend(handles=legend_elements, loc='upper left', fontsize=10,
                   bbox_to_anchor=(0.02, 0.98), frameon=True)
        if direction == "source":
            fig.suptitle(f'A-to-S Direction ', fontsize=16)
        else:
            fig.suptitle(f'S-to-A Direction ', fontsize=16)
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        
        # 保存图片
        save_name = f'threshold_{th:.2f}.png' if th % 1 != 0 else f'threshold_{int(th)}.png'
        save_path = os.path.join(output_dir, save_name)
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close(fig)
        print(f"  Saved: {save_path}")
    
    print(f"Direction {direction.upper()} completed. Output in: {output_dir}")

print("\nAll tasks completed.")