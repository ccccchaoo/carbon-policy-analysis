import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Patch


# ============================================================
# 0. Publication-style global settings
# ============================================================

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": [
        "Arial",
        "Helvetica",
        "DejaVu Sans"
    ],

    "font.size": 9.5,
    "axes.titlesize": 11,
    "axes.labelsize": 10,
    "xtick.labelsize": 8,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,

    "axes.linewidth": 0.8,

    "xtick.major.width": 0.8,
    "ytick.major.width": 0.8,
    "xtick.major.size": 3.5,
    "ytick.major.size": 3.5,

    "figure.dpi": 150,
    "savefig.dpi": 600,

    # 保证 PDF / SVG 中的文字尽可能保持可编辑
    "pdf.fonttype": 42,
    "ps.fonttype": 42,

    "axes.unicode_minus": False
})


# ============================================================
# 1. Read data
# ============================================================

file_path = (
    r"results\Qwen3-Embedding-0.6B"
    r"\validity_experiment\valid_results.xlsx"
)

df = pd.read_excel(file_path)


# ============================================================
# 2. Basic checks
# ============================================================

required_cols = [
    "direct_degree",
    "type_表1",
    "type_表2"
]

missing_cols = [
    col for col in required_cols
    if col not in df.columns
]

if missing_cols:
    raise ValueError(
        f"Missing required columns: {missing_cols}"
    )


# 四种人工标签的固定顺序
LABEL_ORDER = [-2, -1, 1, 2]


# 检查是否真的只有这四类
for col in ["type_表1", "type_表2"]:

    values = set(
        df[col]
        .dropna()
        .unique()
    )

    unexpected = (
        values - set(LABEL_ORDER)
    )

    if unexpected:
        raise ValueError(
            f"{col} contains unexpected values: "
            f"{unexpected}"
        )


# ============================================================
# 3. Define direct_degree bins
# ============================================================

# ------------------------------------------------------------
# 用户要求：
#
# [-inf, -5),
# [-5, -4.5),
# [-4.5, -4.0),
# ...
# [4.5, 5),
# [5, +inf)
#
# 中间步长 = 0.5
# ------------------------------------------------------------

middle_edges = np.arange(
    -5,
    5.0 + 0.5,
    0.5
)

threshold_edges = np.concatenate([
    [-np.inf],
    middle_edges,
    [np.inf]
])


print("Threshold edges:")
print(threshold_edges)


# ============================================================
# 4. Numeric-style x-axis labels
# ============================================================

# ------------------------------------------------------------
# 一共：
# 1 个 <-5 区间
# 20 个 0.5 宽区间
# 1 个 >=5 区间
#
# 为了避免显示：
# "-5.0 to -4.5"
#
# 横轴直接显示数值。
#
# 中间区间的数字使用区间左边界：
#
# ≤−5
# −4.5
# −4.0
# ...
# 4.5
# ≥5
#
# 图下注释解释其含义。
# ------------------------------------------------------------

def format_number(x):
    """
    把整数显示成 -5、0、5，
    半整数显示成 -4.5、0.5 等。
    """

    if float(x).is_integer():
        return f"{int(x)}"

    return f"{x:.1f}"


# 实际分箱的内部名称
bin_internal_labels = [
    "below_-5"
]

for left in np.arange(
    -5,
    5,
    0.5
):
    bin_internal_labels.append(
        f"{left:.1f}"
    )

bin_internal_labels.append(
    "above_5"
)


# 横轴展示名称
x_display_labels = ["≤−5"]

# 对 20 个中间区间，
# 用其左边界数字作为横轴标签
for left in np.arange(
    -5,
    5,
    0.5
):

    # 第一个 [-5, -4.5) 已经可以直接表示为 −5
    display = format_number(left)

    # 使用真正的 Unicode minus，更适合出版图
    display = display.replace(
        "-",
        "−"
    )

    x_display_labels.append(
        display
    )

x_display_labels.append(
    "≥5"
)


# 检查数量
assert (
    len(bin_internal_labels)
    ==
    len(threshold_edges) - 1
)

assert (
    len(x_display_labels)
    ==
    len(bin_internal_labels)
)


# ============================================================
# 5. Create bins
# ============================================================

df["degree_bin"] = pd.cut(
    df["direct_degree"],

    bins=threshold_edges,

    labels=bin_internal_labels,

    # 左闭右开：
    # [-5, -4.5)
    # [-4.5, -4.0)
    # ...
    right=False,

    include_lowest=True,
    ordered=True
)


# ============================================================
# 6. Calculate category proportions
# ============================================================

def calculate_label_distribution(
    data,
    label_col,
    bin_col="degree_bin"
):
    """
    对每个 direct_degree 分箱计算：

    1. -2, -1, +1, +2 数量
    2. 四类在该 bin 内的比例
    3. 四类百分比

    每一个有样本的 bin：
        四类百分比之和 = 100
    """

    temp = data[
        [bin_col, label_col]
    ].dropna().copy()


    # --------------------------------------------------------
    # Count table
    # --------------------------------------------------------

    counts = pd.crosstab(
        temp[bin_col],
        temp[label_col]
    )


    # 保留所有 bin，即使某个 bin 没有样本
    counts = counts.reindex(
        index=bin_internal_labels,
        fill_value=0
    )


    # 保证四种类别完整且顺序固定
    counts = counts.reindex(
        columns=LABEL_ORDER,
        fill_value=0
    )


    # --------------------------------------------------------
    # Bin sample size
    # --------------------------------------------------------

    n_per_bin = counts.sum(
        axis=1
    )


    # --------------------------------------------------------
    # Proportions
    # --------------------------------------------------------

    proportions = counts.div(
        n_per_bin.replace(
            0,
            np.nan
        ),
        axis=0
    )


    percentages = (
        proportions * 100
    )


    return (
        counts,
        percentages,
        n_per_bin
    )


# ============================================================
# 7. Agent 1
# ============================================================

(
    count_agent1,
    pct_agent1,
    n_agent1
) = calculate_label_distribution(
    df,
    "type_表1"
)


# ============================================================
# 8. Agent 2
# ============================================================

(
    count_agent2,
    pct_agent2,
    n_agent2
) = calculate_label_distribution(
    df,
    "type_表2"
)


# ============================================================
# 9. Consensus
# ============================================================

# ------------------------------------------------------------
# 注意：
#
# 此处 consensus 使用“完整四分类完全一致”：
#
# type_表1 == type_表2
#
# 因为现在研究的是 -2/-1/+1/+2，
# 而不是单纯正负号。
# ------------------------------------------------------------

consensus_df = df[
    df["type_表1"]
    ==
    df["type_表2"]
].copy()


consensus_df["consensus_type"] = (
    consensus_df["type_表1"]
)


(
    count_consensus,
    pct_consensus,
    n_consensus
) = calculate_label_distribution(
    consensus_df,
    "consensus_type"
)


# ============================================================
# 10. Print results
# ============================================================

print("\n" + "=" * 70)
print("Agent 1 counts")
print("=" * 70)
print(count_agent1)

print("\nAgent 1 percentages")
print(pct_agent1.round(2))


print("\n" + "=" * 70)
print("Agent 2 counts")
print("=" * 70)
print(count_agent2)

print("\nAgent 2 percentages")
print(pct_agent2.round(2))


print("\n" + "=" * 70)
print("Consensus counts")
print("=" * 70)
print(count_consensus)

print("\nConsensus percentages")
print(pct_consensus.round(2))


# ============================================================
# 11. Publication-oriented colors
# ============================================================

# ------------------------------------------------------------
# 颜色设计：
#
# 负向标签：
#   -2 = 深蓝
#   -1 = 浅蓝
#
# 正向标签：
#   +1 = 浅暖红
#   +2 = 深暖红
#
# 优点：
# 1. 同号颜色天然归为一组
# 2. 强度越高颜色越深
# 3. 蓝 / 暖红形成清楚的方向对照
# 4. 饱和度低于常见默认配色，更像期刊图
# ------------------------------------------------------------

COLORS = {
    -2: "#355F8A",   # strong negative
    -1: "#9BBBD4",   # weak negative

     1: "#DDAA91",   # weak positive
     2: "#A6534B"    # strong positive
}


DISPLAY_LABELS = {
    -2: "−2",
    -1: "−1",
     1: "+1",
     2: "+2"
}


# ============================================================
# 12. Stacked-bar plotting function
# ============================================================

def plot_stacked_panel(
    ax,
    percentage_df,
    n_per_bin,
    title,
    panel_label,
    show_ylabel=True
):
    """
    画单个 100% stacked bar panel。
    """

    x = np.arange(
        len(bin_internal_labels)
    )


    # 起始高度
    bottom = np.zeros(
        len(x)
    )


    # --------------------------------------------------------
    # 依次堆积：
    #
    # -2
    # -1
    # +1
    # +2
    #
    # 这样同号类别自然彼此相邻。
    # --------------------------------------------------------

    for label in LABEL_ORDER:

        values = (
            percentage_df[label]
            .fillna(0)
            .to_numpy()
        )

        ax.bar(
            x,
            values,

            bottom=bottom,

            width=0.82,

            color=COLORS[label],

            edgecolor="white",
            linewidth=0.45,

            zorder=3
        )

        bottom += values


    # ========================================================
    # Axis
    # ========================================================

    ax.set_ylim(
        0,
        100
    )

    ax.set_yticks(
        np.arange(
            0,
            101,
            20
        )
    )


    if show_ylabel:
        ax.set_ylabel(
            "Proportion within interval (%)",
            labelpad=7
        )
    else:
        ax.set_ylabel("")


    ax.set_xlabel(
        "Relative Attitude (lexicon-based) bins",
        labelpad=8
    )


    # ========================================================
    # X tick labels
    #
    # 22 个标签全部显示会很密。
    # 使用 90° 可以避免重叠，也比斜着挤在一起更规整。
    # ========================================================

    ax.set_xticks(x)

    ax.set_xticklabels(
        x_display_labels,
        rotation=90,
        ha="center",
        va="top"
    )


    # ========================================================
    # Grid
    # ========================================================

    ax.grid(
        axis="y",
        linestyle=(0, (2, 2)),
        linewidth=0.65,
        color="#D8D8D8",
        alpha=0.80,
        zorder=0
    )

    ax.set_axisbelow(True)


    # ========================================================
    # Title
    # ========================================================

    ax.set_title(
        title,
        fontsize=11,
        fontweight="semibold",
        pad=10
    )


    # ========================================================
    # Panel label
    # ========================================================

    ax.text(
        -0.075,
        1.045,
        panel_label,

        transform=ax.transAxes,

        fontsize=11.5,
        fontweight="bold",

        ha="left",
        va="bottom"
    )


    # ========================================================
    # Spines
    # ========================================================

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax.spines["left"].set_color(
        "#333333"
    )

    ax.spines["bottom"].set_color(
        "#333333"
    )


    # ========================================================
    # Tick style
    # ========================================================

    ax.tick_params(
        axis="x",
        length=0,
        pad=3
    )

    ax.tick_params(
        axis="y",
        pad=3
    )


    # ========================================================
    # Empty-bin indication
    #
    # 如果某个 bin n=0，
    # 整根柱子为空。
    #
    # 在底部加一个小 ×，避免读者误以为它代表 0%。
    # ========================================================

    n_array = n_per_bin.to_numpy()

    for i, n in enumerate(
        n_array
    ):

        if n == 0:

            ax.text(
                i,
                2.2,
                "×",

                ha="center",
                va="bottom",

                fontsize=7.5,
                color="#888888"
            )


# ============================================================
# 13. Create 1 × 3 figure
# ============================================================

fig, axes = plt.subplots(
    1,
    3,

    figsize=(14.5, 5.1),

    sharey=True,

    facecolor="white"
)


# ------------------------------------------------------------
# 给：
# - 顶部 legend
# - 旋转后的 x 标签
# - 底部 explanatory note
#
# 留足空间
# ------------------------------------------------------------

fig.subplots_adjust(
    left=0.062,
    right=0.988,
    bottom=0.275,
    top=0.79,
    wspace=0.12
)


# ============================================================
# 14. Draw panels
# ============================================================

plot_stacked_panel(
    axes[0],

    pct_agent1,
    n_agent1,

    title="Agent 1",
    panel_label="(e)",

    show_ylabel=True
)


plot_stacked_panel(
    axes[1],

    pct_agent2,
    n_agent2,

    title="Agent 2",
    panel_label="(f)",

    show_ylabel=False
)


plot_stacked_panel(
    axes[2],

    pct_consensus,
    n_consensus,

    title="Consensus",
    panel_label="(g)",

    show_ylabel=False
)


# ============================================================
# 15. Shared legend
# ============================================================

legend_handles = [
    Patch(
        facecolor=COLORS[-2],
        edgecolor="none",
        label="−2"
    ),

    Patch(
        facecolor=COLORS[-1],
        edgecolor="none",
        label="−1"
    ),

    Patch(
        facecolor=COLORS[1],
        edgecolor="none",
        label="+1"
    ),

    Patch(
        facecolor=COLORS[2],
        edgecolor="none",
        label="+2"
    )
]


fig.legend(
    handles=legend_handles,

    loc="upper center",

    bbox_to_anchor=(
        0.5,
        0.945
    ),

    ncol=4,

    frameon=False,

    columnspacing=2.4,
    handlelength=1.7,
    handleheight=0.9,
    handletextpad=0.55
)


# ============================================================
# 16. Bottom explanatory note
# ============================================================

fig.text(
    0.5,
    0.072,

    (
        "Numeric x-axis labels denote the left boundaries of 0.5-wide Rel. Att. bins (e.g., −5 represents [−5.0, −4.5)), while ≤−5 and ≥5 denote the two open-ended endpoint bins."
    ),

    ha="center",
    va="center",

    fontsize=8,
    color="#555555",

    wrap=True
)


# ============================================================
# 17. Save
# ============================================================

output_dir = os.path.dirname(
    file_path
)


png_path = os.path.join(
    output_dir,
    "direct_degree_stacked_distribution.png"
)

pdf_path = os.path.join(
    output_dir,
    "direct_degree_stacked_distribution.pdf"
)

svg_path = os.path.join(
    output_dir,
    "direct_degree_stacked_distribution.svg"
)


fig.savefig(
    png_path,
    dpi=600,
    bbox_inches="tight",
    facecolor="white"
)


fig.savefig(
    pdf_path,
    bbox_inches="tight",
    facecolor="white"
)


fig.savefig(
    svg_path,
    bbox_inches="tight",
    facecolor="white"
)


plt.show()


print("\nSaved:")
print(png_path)
print(pdf_path)
print(svg_path)