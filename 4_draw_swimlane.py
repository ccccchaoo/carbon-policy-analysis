import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import os

# ============================================================
# 1. 参数设置
# ============================================================
BASE_DIR = r'results\Qwen3-Embedding-0.6B\network_plots'
DIRECTIONS = ['source', 'adoption']

METRICS = [
    ('average_out_weight', 'Average Out Weight', 'o', 'blue', 2),
    ('average_diff',        'Average Diff',       's', 'red',  2),
    ('PageRank',            'PageRank',           '^', 'green', 2),
]

THRESHOLDS = [0.0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35,
              0.4, 0.45, 0.5, 0.55, 0.6, 0.65]
XTICK_VALUES = [0.0, 0.25, 0.5]

SHOW_YGRID = True
CENTRAL_LINEWIDTH = 2.0

# ============================================================
# 2. 省份缩写与排序
# ============================================================
PROVINCE_ABBR = {
    "北京": "BJ", "天津": "TJ", "河北": "HE", "山西": "SX",
    "内蒙古": "NM", "辽宁": "LN", "吉林": "JL", "黑龙江": "HL",
    "上海": "SH", "江苏": "JS", "浙江": "ZJ", "安徽": "AH",
    "福建": "FJ", "江西": "JX", "山东": "SD", "河南": "HA",
    "湖北": "HB", "湖南": "HN", "广东": "GD", "广西": "GX",
    "海南": "HI", "重庆": "CQ", "四川": "SC", "贵州": "GZ",
    "云南": "YN", "西藏": "XZ", "陕西": "SN", "甘肃": "GS",
    "青海": "QH", "宁夏": "NX", "新疆": "XJ",
}
ORDERED_LABELS = ['Central'] + [PROVINCE_ABBR[p] for p in PROVINCE_ABBR.keys()]

# ============================================================
# 3. 主循环
# ============================================================
for direction in DIRECTIONS:
    print(f"\n>>> Processing {direction.upper()} direction")
    input_file = os.path.join(BASE_DIR, direction,
                              f'network_statistics_{direction}.xlsx')
    if not os.path.exists(input_file):
        print(f"File not found: {input_file}, skip")
        continue

    df = pd.read_excel(input_file, sheet_name='All_Node_Statistics')
    for col, _, _, _, _ in METRICS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        else:
            raise ValueError(f"Column {col} missing")

    mission_abbrs = sorted(df['mission_abbr'].unique())
    n_mission = len(mission_abbrs)

    node_order_dict = {}
    for mission in mission_abbrs:
        existing = df[df['mission_abbr'] == mission]['node_label'].unique()
        node_order_dict[mission] = [lbl for lbl in ORDERED_LABELS if lbl in existing]

    out_dir = os.path.join(BASE_DIR, direction, 'node_swimlane_1x12')
    os.makedirs(out_dir, exist_ok=True)

    for metric_col, metric_label, marker, color, markersize in METRICS:
        print(f"  Generating {metric_label} (markersize={markersize}) ...")

        # ---------- 全局纵轴范围与刻度（保留 1 位小数） ----------
        all_vals = []
        for mission in mission_abbrs:
            vals = df[(df['mission_abbr'] == mission)][metric_col].dropna().values
            all_vals.extend(vals)

        if all_vals:
            data_min, data_max = float(min(all_vals)), float(max(all_vals))

            if metric_label == "PageRank":
                # PageRank：从 0 到最大值，保留 1 位小数
                y_tick_low = 0.0
                y_tick_high = round(data_max, 1)
            else:
                # 其他指标：最小 / 最大值各自保留 1 位小数
                y_tick_low = round(data_min, 1)
                y_tick_high = round(data_max, 1)

            # 防止上下刻度相同导致纵轴塌缩
            if y_tick_low == y_tick_high:
                y_tick_high = round(y_tick_low + 0.1, 1)

            y_ticks = [y_tick_low, y_tick_high]

            # 纵轴范围：以取整后的刻度为准，留一点边距
            span = y_tick_high - y_tick_low
            margin = 0.08 * span if span > 0 else 0.1
            ymin = y_tick_low - margin
            ymax = y_tick_high + margin
        else:
            ymin, ymax = -1, 1
            y_ticks = [-1.0, 1.0]

        # ---------- 创建大图 ----------
        fig = plt.figure(figsize=(40, 10))
        outer_grid = gridspec.GridSpec(1, n_mission, figure=fig,
                                       wspace=0.4, hspace=0.1)

        for idx, mission in enumerate(mission_abbrs):
            outer_cell = outer_grid[0, idx]
            node_labels = node_order_dict[mission]
            n_nodes = len(node_labels)

            if n_nodes == 0:
                ax = fig.add_subplot(outer_cell)
                ax.text(0.5, 0.5, 'No data', ha='center', va='center')
                ax.set_title(mission, fontsize=14)
                continue

            inner_gs = gridspec.GridSpecFromSubplotSpec(
                n_nodes, 1, subplot_spec=outer_cell, hspace=0.08
            )

            for i, node in enumerate(node_labels):
                ax = fig.add_subplot(inner_gs[i, 0])

                df_node = df[(df['mission_abbr'] == mission) &
                             (df['node_label'] == node)].sort_values('threshold')
                ths = df_node['threshold'].values
                vals = df_node[metric_col].values
                mask = ~np.isnan(vals)
                ths = ths[mask]
                vals = vals[mask]

                if len(ths) > 0:
                    ax.plot(ths, vals, marker=marker, markersize=markersize,
                            linewidth=0.8, color=color, alpha=0.8)

                # 纵轴范围统一（所有泳道一致）
                ax.set_ylim(ymin, ymax)

                # 纵轴刻度：只有最小 / 最大两个位置，且保留 1 位小数
                ax.set_yticks(y_ticks)
                ax.set_yticklabels([f"{y_ticks[0]:.1f}", f"{y_ticks[1]:.1f}"])

                # 只有该主题第一条泳道显示纵轴刻度标签
                if i > 0:
                    ax.tick_params(axis='y', labelleft=False)

                if SHOW_YGRID:
                    ax.grid(axis='y', color='gray', linestyle=':',
                            linewidth=0.3, alpha=0.35)
                    ax.set_axisbelow(True)

                # Central：不加标签，加粗边框
                if node == 'Central':
                    for spine in ax.spines.values():
                        spine.set_linewidth(CENTRAL_LINEWIDTH)
                        spine.set_color('black')
                else:
                    ax.set_ylabel(node, fontsize=14, rotation=0,
                                  labelpad=1, ha='right', va='center')

                if i < n_nodes - 1:
                    ax.set_xticks([])
                    ax.set_xticklabels([])
                else:
                    ax.set_xticks(XTICK_VALUES)
                    ax.set_xlabel('Threshold', fontsize=14)
                ax.tick_params(labelsize=14)

                ax.axhline(0, color='gray', linestyle='--',
                           linewidth=0.4, alpha=0.3)

            title_ax = fig.add_subplot(outer_cell)
            title_ax.axis('off')
            title_ax.text(0.5, 0.98, mission, transform=title_ax.transAxes,
                          ha='center', fontsize=14, fontweight='bold')

        plt.subplots_adjust(left=0.04, right=0.98, top=0.93, bottom=0.06)

        if metric_label == "PageRank":
            fig.suptitle(f'{metric_label}', fontsize=16, y=0.98)
        else:
            if direction == "source":
                fig.suptitle(f'A-to-S Direction: {metric_label}',
                             fontsize=16, y=0.98)
            else:
                fig.suptitle(f'S-to-A Direction: {metric_label}',
                             fontsize=16, y=0.98)

        save_path = os.path.join(out_dir, f'{metric_col}.png')
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close(fig)
        print(f"    Saved: {save_path}")

    print(f"Direction {direction.upper()} completed.")