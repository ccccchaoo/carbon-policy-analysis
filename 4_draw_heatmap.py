import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
import os
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.gridspec import GridSpec

def sparse_x_labels(labels, threshold=10):
    """
    当标签数量 >= threshold 时，只保留索引为偶数的标签（即第1,3,5,...个罗马数字）
    其余位置设为空字符串，避免重叠。
    """
    if len(labels) < threshold:
        return labels
    new_labels = []
    for i in range(len(labels)):
        if i % 2 == 0:  # 保留 0,2,4,... 对应 "Ⅰ","Ⅲ","Ⅴ"...
            new_labels.append(labels[i])
        else:
            new_labels.append('')
    return new_labels

def wrap_labels(labels, max_len=8):
    """将标签按每max_len个字符换行"""
    wrapped_labels = []
    for label in labels:
        wrapped = '\n'.join([label[i:i+max_len] for i in range(0, len(label), max_len)])
        wrapped_labels.append(wrapped)
    return wrapped_labels

plt.rcParams['font.family'] = 'SimHei'
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

# 数字映射（保持顺序）
province_mapping_num = {
    "北京": 1, "天津": 2, "河北": 3, "山西": 4, "内蒙": 5,
    "辽宁": 6, "吉林": 7, "黑龙": 8, "上海": 9, "江苏": 10,
    "浙江": 11, "安徽": 12, "福建": 13, "江西": 14, "山东": 15,
    "河南": 16, "湖北": 17, "湖南": 18, "广东": 19, "广西": 20,
    "海南": 21, "重庆": 22, "四川": 23, "贵州": 24, "云南": 25,
    "西藏": 26, "陕西": 27, "甘肃": 28, "青海": 29, "宁夏": 30,
    "新疆": 31,
}

# 缩写映射（用于显示）
province_mapping_abbr = {
    "北京": "BJ", "天津": "TJ", "河北": "HE", "山西": "SX", "内蒙": "NM",
    "辽宁": "LN", "吉林": "JL", "黑龙": "HL", "上海": "SH", "江苏": "JS",
    "浙江": "ZJ", "安徽": "AH", "福建": "FJ", "江西": "JX", "山东": "SD",
    "河南": "HA", "湖北": "HB", "湖南": "HN", "广东": "GD", "广西": "GX",
    "海南": "HI", "重庆": "CQ", "四川": "SC", "贵州": "GZ", "云南": "YN",
    "西藏": "XZ", "陕西": "SN", "甘肃": "GS", "青海": "QH", "宁夏": "NX",
    "新疆": "XJ",
}

# 从数字映射和缩写映射构建数字->缩写字典
num_to_abbr = {}
for prov, num in province_mapping_num.items():
    num_to_abbr[num] = province_mapping_abbr.get(prov, prov)

# 任务名称与字母的映射
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

paragraph_mapping = ["Ⅰ", "Ⅱ", "Ⅲ", "Ⅳ", "Ⅴ","Ⅵ", "Ⅶ", "Ⅷ", "Ⅸ", "Ⅹ","Ⅺ", "Ⅻ", "ⅩⅢ", "ⅩⅣ", "ⅩⅤ"]

input_dir = r"results\Qwen3-Embedding-0.6B\matching_results\summary"
output_dir = r"results\Qwen3-Embedding-0.6B\matching_results\mission_distribute"
os.makedirs(output_dir, exist_ok=True)

files = os.listdir(input_dir)

# 获取文件并按字母顺序排序
sorted_files = sorted(os.listdir(input_dir), key=lambda x: mission_letter_mapping.get(x.split('_')[1], "z"))

# 子图位置（2行6列）
subplot_positions = [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5),
                     (1, 0), (1, 1), (1, 2), (1, 3), (1, 4), (1, 5)]

# --- 语调分布热力图（大图） ---
fig_degree = plt.figure(figsize=(60, 30))
gs_degree = GridSpec(2, 6, figure=fig_degree, width_ratios=[1]*6, height_ratios=[1, 1], hspace=0.3, wspace=0.3)

# 用于语调图的颜色映射
v_max = 2.5
v_min = -2.5
data_range = v_max - v_min
zero_pos = -v_min / data_range
colors_degree = ["#0047AB", "#E0E0F7", "#FFFFFF", "#FFE0E0", "#A50021"]
nodes_degree = [0, zero_pos * 0.5, zero_pos, zero_pos + (1-zero_pos)*0.5, 1]
cmap_degree = LinearSegmentedColormap.from_list("red_white_green", list(zip(nodes_degree, colors_degree)))

for idx, file in enumerate(sorted_files):
    if idx >= 12:
        break

    input_file = os.path.join(input_dir, file)
    parts = file.split('_')
    extracted_text = parts[1]

    # 读取语调数据
    df_degree = pd.read_excel(input_file, sheet_name='Structure_direct_degree', index_col=0)
    # 先添加排序键
    df_degree['sort_key'] = df_degree.index.map(lambda x: province_mapping_num.get(x[:2], 0))
    # 按数字排序
    df_degree = df_degree.sort_values('sort_key')
    # 替换 index 为缩写
    df_degree.index = df_degree.index.map(lambda x: province_mapping_abbr.get(x[:2], x[:2]))
    # 删除辅助列
    df_degree = df_degree.drop('sort_key', axis=1)
    # 去除第一列（原代码中的操作）
    df_degree = df_degree.iloc[1:, 1:]
    df_degree.columns = [paragraph_mapping[i] for i in range(len(df_degree.columns))]

    # 标签处理
    wrapped_index = wrap_labels([str(x) for x in df_degree.index.tolist()])
    wrapped_columns = wrap_labels(df_degree.columns.tolist())
    sparse_columns = sparse_x_labels(wrapped_columns, threshold=10)

    # ----- 绘制大图子图 -----
    row, col = subplot_positions[idx]
    sub = gs_degree[row, col].subgridspec(2, 1, height_ratios=[1, 4], hspace=0.05)
    
    # 上方：箱型图
    ax_box = fig_degree.add_subplot(sub[0])
    sns.boxplot(data=df_degree, ax=ax_box, color='#FFA500', width=0.6)  # 更明亮的橙色
    ax_box.set_ylim(-5, 5)  # 统一箱型图y轴范围
    ax_box.set_xticklabels([])  # 隐藏x轴标签
    ax_box.set_ylabel('Rel Att', fontsize=25, labelpad=14)
    # 调大y轴刻度标签
    ax_box.tick_params(axis='y', labelsize=25)
    # 添加y=0基准线
    ax_box.axhline(y=0, color='grey', linestyle='--', linewidth=1)

    # 下方：热力图
    ax = fig_degree.add_subplot(sub[1])
    sns.heatmap(df_degree,
                cmap=cmap_degree,
                annot=False,
                linewidths=0.5,
                linecolor='lightgray',
                cbar=False,
                vmin=v_min, vmax=v_max,
                ax=ax)
    ax.set_xticklabels(sparse_columns, rotation=0, ha='center', fontsize=30)
    ax.set_yticklabels(wrapped_index, rotation=0, fontsize=30)

    letter = mission_letter_mapping.get(extracted_text, "")
    ax.text(0.5, 1.02, letter, transform=ax.transAxes,
            fontsize=50, fontweight='bold', va='bottom', ha='center')

    # ----- 保存单独的语调热力图 -----
    fig_single = plt.figure(figsize=(12, 12))
    gs_single = GridSpec(2, 1, figure=fig_single, height_ratios=[1, 4], hspace=0.1)
    
    ax_box_single = fig_single.add_subplot(gs_single[0])
    sns.boxplot(data=df_degree, ax=ax_box_single, color='#FFA500', width=0.6)
    ax_box_single.set_ylim(-5, 5)
    ax_box_single.set_xticklabels([])
    ax_box_single.set_ylabel('Rel Att', fontsize=16)
    # 调大y轴刻度标签
    ax_box_single.tick_params(axis='y', labelsize=16)
    # 添加y=0基准线
    ax_box_single.axhline(y=0, color='grey', linestyle='--', linewidth=1)

    ax_single = fig_single.add_subplot(gs_single[1])
    sns.heatmap(df_degree,
                cmap=cmap_degree,
                annot=False,
                linewidths=0.5,
                linecolor='lightgray',
                cbar=False,
                cbar_kws={"label": "relative degree", "ticks": [v_min, 0, v_max]},
                vmin=v_min, vmax=v_max,
                ax=ax_single)
    ax_single.set_xticklabels(sparse_columns, rotation=0, ha='center', fontsize=25)
    ax_single.set_yticklabels(wrapped_index, rotation=0, fontsize=25)
    plt.tight_layout()
    single_path = os.path.join(output_dir, f"{extracted_text}_tone.png")
    plt.savefig(single_path, dpi=600, bbox_inches='tight')
    plt.close(fig_single)
    print(f"已保存单独图: {single_path}")

# 为大图添加统一颜色条
cbar_height = 0.7
cbar_bottom = (1 - cbar_height) / 2
cbar_ax_degree = fig_degree.add_axes([0.92, cbar_bottom, 0.015, cbar_height])
norm_degree = plt.Normalize(v_min, v_max)
sm_degree = plt.cm.ScalarMappable(cmap=cmap_degree, norm=norm_degree)
sm_degree.set_array([])
cbar_degree = fig_degree.colorbar(sm_degree, cax=cbar_ax_degree)
cbar_degree.set_ticks([v_min, 0, v_max])
cbar_degree.set_ticklabels([f"{v_min:.1f}", "0", f"{v_max:.1f}"], fontsize=34)
cbar_degree.set_label('relative attitude', fontsize=34)

plt.subplots_adjust(left=0.05, right=0.9, top=0.95, bottom=0.08)
output_path_degree = os.path.join(output_dir, "all_missions_tone_combined.png")
plt.savefig(output_path_degree, dpi=300, bbox_inches='tight')
plt.close(fig_degree)
print(f"已保存合并语调大图: {output_path_degree}")

# 单独导出语调热力图的颜色条
fig_cbar_degree = plt.figure(figsize=(1.5, 6))
ax_cbar_degree = fig_cbar_degree.add_axes([0.3, 0.1, 0.2, 0.8])

norm_degree = plt.Normalize(v_min, v_max)
sm_degree = plt.cm.ScalarMappable(cmap=cmap_degree, norm=norm_degree)
sm_degree.set_array([])
cbar_degree = fig_cbar_degree.colorbar(sm_degree, cax=ax_cbar_degree, orientation='vertical')
cbar_degree.set_ticks([v_min, 0, v_max])
cbar_degree.set_ticklabels([f"{v_min:.1f}", "0", f"{v_max:.1f}"], fontsize=20)
cbar_degree.set_label('relative attitude', fontsize=20)

plt.savefig(os.path.join(output_dir, "colorbar_tone.png"), dpi=300, bbox_inches='tight', transparent=True)
plt.close(fig_cbar_degree)
print("已单独保存语调颜色条: colorbar_tone.png")

print(f"所有图像已保存至: {output_dir}")