import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import gridspec
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.ticker import MultipleLocator
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    accuracy_score,
    confusion_matrix
)

# ============================================================
# 0. Global publication-style settings
# ============================================================

# 英文论文建议 Arial；如果系统没有 Arial，会自动回退到 DejaVu Sans
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],

    "font.size": 9.5,
    "axes.titlesize": 10.5,
    "axes.labelsize": 9.5,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,

    "axes.linewidth": 0.8,
    "xtick.major.width": 0.8,
    "ytick.major.width": 0.8,
    "xtick.major.size": 3.5,
    "ytick.major.size": 3.5,

    "figure.dpi": 150,
    "savefig.dpi": 600,

    # 矢量文件中文字保持为可编辑字体
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
# 2. Convert values to signs
# ============================================================

df["agent1_sign"] = np.sign(df["type_表1"])
df["agent2_sign"] = np.sign(df["type_表2"])
df["dict_sign"] = np.sign(df["direct_degree"])


# ============================================================
# 3. Prepare valid binary data
# ============================================================

def prepare_valid_data(y_true, y_pred):
    """
    保留有效二分类样本：
    - 删除缺失值
    - 删除词典预测为 0 的样本
    - 删除人工标签为 0 的样本
    """
    valid = pd.DataFrame({
        "y_true": y_true,
        "y_pred": y_pred
    }).dropna()

    # valid = valid[
    #     (valid["y_pred"] != 0) &
    #     (valid["y_true"] != 0)
    # ].copy()

    return valid


# ============================================================
# 4. Evaluation function
# ============================================================

def evaluate(y_true, y_pred, name=""):
    valid = prepare_valid_data(y_true, y_pred)

    y_true_bin = (valid["y_true"] == 1).astype(int)
    y_pred_bin = (valid["y_pred"] == 1).astype(int)

    accuracy = accuracy_score(
        valid["y_true"],
        valid["y_pred"]
    )

    precision = precision_score(
        y_true_bin,
        y_pred_bin,
        zero_division=0
    )

    recall = recall_score(
        y_true_bin,
        y_pred_bin,
        zero_division=0
    )

    f1 = f1_score(
        y_true_bin,
        y_pred_bin,
        zero_division=0
    )

    return {
        "validation_set": name,
        "n": len(valid),
        "sign_accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1
    }


# ============================================================
# 5. Evaluation sets
# ============================================================

result_agent1 = evaluate(
    df["agent1_sign"],
    df["dict_sign"],
    name="Agent 1"
)

result_agent2 = evaluate(
    df["agent2_sign"],
    df["dict_sign"],
    name="Agent 2"
)


# ------------------------------------------------------------
# Consensus
# ------------------------------------------------------------
# 保留你原始定义：
# 两位 Agent 的原始标注数值完全相同
# ------------------------------------------------------------

consensus_df = df[
    df["type_表1"] == df["type_表2"]
].copy()

# 如果你的理论含义其实是“方向一致”，建议改成：
#
# consensus_df = df[
#     df["agent1_sign"] == df["agent2_sign"]
# ].copy()


result_consensus = evaluate(
    consensus_df["agent1_sign"],
    consensus_df["dict_sign"],
    name="Consensus"
)

results = pd.DataFrame([
    result_agent1,
    result_agent2,
    result_consensus
])


# 百分数版本
results_percent = results.copy()

metric_cols = [
    "sign_accuracy",
    "precision",
    "recall",
    "f1"
]

for col in metric_cols:
    results_percent[col] = (
        results_percent[col] * 100
    )


print("\nEvaluation results:")
print(results)

print("\nPercentage results:")
print(results_percent.round(2))


# ============================================================
# 6. Confusion matrices
# ============================================================

def get_confusion_data(y_true, y_pred):
    valid = prepare_valid_data(y_true, y_pred)

    cm = confusion_matrix(
        valid["y_true"],
        valid["y_pred"],
        labels=[-1, 1]
    )

    return valid, cm


valid_agent1, cm_agent1 = get_confusion_data(
    df["agent1_sign"],
    df["dict_sign"]
)

valid_agent2, cm_agent2 = get_confusion_data(
    df["agent2_sign"],
    df["dict_sign"]
)

valid_consensus, cm_consensus = get_confusion_data(
    consensus_df["agent1_sign"],
    consensus_df["dict_sign"]
)


cms = [
    cm_agent1,
    cm_agent2,
    cm_consensus
]


# ============================================================
# 7. Publication-style color palette
# ============================================================

# ------------------------------------------------------------
# 柱状图：
# 低饱和、色盲相对友好、适合论文
#
# 蓝灰 / 暖棕 / 青绿 / 紫灰
# ------------------------------------------------------------

BAR_COLORS = [
    "#4477AA",   # muted blue
    "#CC6677",   # muted rose
    "#228833",   # muted green
    "#AA4499"    # muted purple
]


# ------------------------------------------------------------
# 混淆矩阵：
# 从极浅灰蓝到深靛蓝
# 不使用过亮的纯蓝
# ------------------------------------------------------------

HEAT_COLORS = [
    "#F7F8FA",
    "#E4EAF1",
    "#C5D2E1",
    "#91AAC5",
    "#587EA5",
    "#315A83",
    "#173B63"
]

heat_cmap = LinearSegmentedColormap.from_list(
    "journal_blue",
    HEAT_COLORS
)


# 三张图必须统一色阶，否则肉眼无法正确比较
global_vmax = max(cm.max() for cm in cms)
global_norm = Normalize(
    vmin=0,
    vmax=global_vmax
)


# ============================================================
# 8. Confusion-matrix plotting function
# ============================================================

def plot_confusion_matrix(
    ax,
    cm,
    title,
    panel_label,
    show_ylabel=False
):
    """
    每格显示：
    count
    row percentage

    百分比为按真实类别（行）归一化。
    """

    im = ax.imshow(
        cm,
        cmap=heat_cmap,
        norm=global_norm,
        interpolation="nearest",
        aspect="equal"
    )

    labels = [
        "Negative (−1)",
        "Positive (+1)"
    ]

    ax.set_xticks([0, 1])
    ax.set_yticks([0, 1])

    ax.set_xticklabels(labels)
    ax.set_yticklabels(labels)

    ax.set_xlabel(
        "Predicted label",
        labelpad=6
    )

    if show_ylabel:
        ax.set_ylabel(
            "True label",
            labelpad=6
        )
    else:
        ax.set_ylabel("")

    # 标题
    ax.set_title(
        title,
        fontsize=10.5,
        fontweight="semibold",
        pad=10
    )

    # panel label
    ax.text(
        -0.14,
        1.10,
        panel_label,
        transform=ax.transAxes,
        fontsize=11,
        fontweight="bold",
        ha="left",
        va="bottom"
    )

    # 按行计算百分比
    row_sum = cm.sum(axis=1, keepdims=True)

    cm_percent = np.divide(
        cm,
        row_sum,
        out=np.zeros_like(
            cm,
            dtype=float
        ),
        where=row_sum != 0
    ) * 100

    # 阈值决定白字 / 深色字
    threshold = global_vmax * 0.52

    for i in range(2):
        for j in range(2):

            value = cm[i, j]
            pct = cm_percent[i, j]

            text_color = (
                "white"
                if value > threshold
                else "#202020"
            )

            # 第一行：count
            ax.text(
                j,
                i - 0.055,
                f"{value}",
                ha="center",
                va="center",
                fontsize=10.5,
                fontweight="bold",
                color=text_color
            )

            # 第二行：row %
            ax.text(
                j,
                i + 0.105,
                f"{pct:.1f}%",
                ha="center",
                va="center",
                fontsize=7.8,
                color=text_color,
                alpha=0.92
            )

    # 热力图格线
    ax.set_xticks(
        np.arange(-0.5, 2, 1),
        minor=True
    )

    ax.set_yticks(
        np.arange(-0.5, 2, 1),
        minor=True
    )

    ax.grid(
        which="minor",
        color="white",
        linewidth=1.4
    )

    ax.tick_params(
        which="minor",
        bottom=False,
        left=False
    )

    ax.tick_params(
        axis="both",
        length=0,
        pad=5
    )

    # 去掉边框
    for spine in ax.spines.values():
        spine.set_visible(False)

    return im


# ============================================================
# 9. Create publication-style multi-panel figure
# ============================================================

# 论文双栏图常见宽度约 7–7.5 inch
# 这里稍宽一些，以保证三个 confusion matrix 标签不拥挤
fig = plt.figure(
    figsize=(11.6, 7.6),
    facecolor="white"
)


# ------------------------------------------------------------
# GridSpec
#
# 顶部：
#   legend 区域留白由 top 参数保证
#
# 第一行：
#   分组柱状图
#
# 第二行：
#   三个 confusion matrix
# ------------------------------------------------------------

gs = gridspec.GridSpec(
    nrows=2,
    ncols=3,
    figure=fig,
    height_ratios=[1.16, 1.0],
    left=0.075,
    right=0.925,
    bottom=0.085,
    top=0.875,
    hspace=0.47,
    wspace=0.30
)


# ============================================================
# 10. Panel (a): grouped bar chart
# ============================================================

ax_bar = fig.add_subplot(
    gs[0, :]
)


metric_labels = [
    "Sign accuracy",
    "Precision",
    "Recall",
    "F1-score"
]


x = np.arange(
    len(results_percent)
)

width = 0.18


for i, (
    metric,
    label,
    color
) in enumerate(
    zip(
        metric_cols,
        metric_labels,
        BAR_COLORS
    )
):

    offset = (
        i - (len(metric_cols) - 1) / 2
    ) * width

    values = results_percent[
        metric
    ].to_numpy()

    bars = ax_bar.bar(
        x + offset,
        values,
        width=width * 0.94,
        label=label,
        color=color,
        edgecolor="white",
        linewidth=0.6,
        alpha=0.96,
        zorder=3
    )

    # 数值标签
    for bar, value in zip(
        bars,
        values
    ):

        ax_bar.text(
            bar.get_x()
            + bar.get_width() / 2,
            value + 1.15,
            f"{value:.1f}",
            ha="center",
            va="bottom",
            fontsize=7.8,
            color="#282828"
        )


# ------------------------------------------------------------
# X labels 中直接加入 n
# 避免右侧额外 textbox
# ------------------------------------------------------------

x_labels = [
    f"Agent 1\n$n$ = {int(results.iloc[0]['n'])}",
    f"Agent 2\n$n$ = {int(results.iloc[1]['n'])}",
    f"Consensus\n$n$ = {int(results.iloc[2]['n'])}"
]

ax_bar.set_xticks(x)
ax_bar.set_xticklabels(
    x_labels,
    linespacing=1.35
)


ax_bar.set_ylabel(
    "Performance (%)",
    labelpad=7
)

# 不需要 Validation set 这个 x 轴标题
# 因为三个类别本身已经非常明确
ax_bar.set_xlabel("")


# ------------------------------------------------------------
# 合理缩紧 Y 范围
#
# 不建议一律画 0–110：
# 因为所有值都约 80%，会浪费大量版面。
#
# 但截断 y 轴会放大视觉差异，所以这里保留从 0 开始，
# 最高值设为 100。
# ------------------------------------------------------------

ax_bar.set_ylim(
    0,
    100
)

ax_bar.yaxis.set_major_locator(
    MultipleLocator(20)
)


# 横向辅助线
ax_bar.grid(
    axis="y",
    color="#D9D9D9",
    linestyle=(0, (2, 2)),
    linewidth=0.65,
    alpha=0.75,
    zorder=0
)

ax_bar.set_axisbelow(True)


# 边框
ax_bar.spines["top"].set_visible(False)
ax_bar.spines["right"].set_visible(False)

ax_bar.spines["left"].set_color(
    "#333333"
)
ax_bar.spines["bottom"].set_color(
    "#333333"
)


# Panel 标记，而不是额外的大标题
ax_bar.text(
    -0.055,
    1.08,
    "(a)",
    transform=ax_bar.transAxes,
    fontsize=11,
    fontweight="bold",
    ha="left",
    va="bottom"
)

ax_bar.set_title(
    "Performance across validation sets",
    fontsize=11,
    fontweight="semibold",
    pad=19
)


# ============================================================
# 11. Legend: independently positioned
# ============================================================

# 用 figure-level legend，而不是 axes legend
# 这样它不会和柱状图标题抢位置
handles, labels = ax_bar.get_legend_handles_labels()

legend = fig.legend(
    handles,
    labels,
    loc="upper center",
    bbox_to_anchor=(0.5, 0.947),
    ncol=4,
    frameon=False,
    columnspacing=1.8,
    handlelength=2.0,
    handletextpad=0.55,
    borderaxespad=0
)


# ============================================================
# 12. Panels (b)–(d): confusion matrices
# ============================================================

ax_cm1 = fig.add_subplot(
    gs[1, 0]
)

ax_cm2 = fig.add_subplot(
    gs[1, 1]
)

ax_cm3 = fig.add_subplot(
    gs[1, 2]
)


im1 = plot_confusion_matrix(
    ax_cm1,
    cm_agent1,
    "Agent 1",
    "(b)",
    show_ylabel=True
)

im2 = plot_confusion_matrix(
    ax_cm2,
    cm_agent2,
    "Agent 2",
    "(c)",
    show_ylabel=False
)

im3 = plot_confusion_matrix(
    ax_cm3,
    cm_consensus,
    "Consensus",
    "(d)",
    show_ylabel=False
)


# ============================================================
# 13. Shared colorbar
# ============================================================

# 手动创建 cbar axis，可以完全控制位置
# 防止 matplotlib 自动挤压第 3 张热力图
cax = fig.add_axes([
    0.943,   # left
    0.105,   # bottom
    0.012,   # width
    0.275    # height
])

cbar = fig.colorbar(
    im3,
    cax=cax
)

cbar.set_label(
    "Count",
    rotation=90,
    labelpad=8
)

cbar.ax.tick_params(
    labelsize=8,
    width=0.7,
    length=3
)

cbar.outline.set_linewidth(
    0.7
)


# ============================================================
# 14. Optional figure note
# ============================================================

fig.text(
    0.5,
    0.025,
    "Values in confusion-matrix cells show counts; percentages are normalized within true-label rows.",
    ha="center",
    va="center",
    fontsize=8,
    color="#555555"
)


# ============================================================
# 15. Save
# ============================================================

output_dir = os.path.dirname(
    file_path
)

png_path = os.path.join(
    output_dir,
    "valid_results_publication.png"
)

pdf_path = os.path.join(
    output_dir,
    "valid_results_publication.pdf"
)

svg_path = os.path.join(
    output_dir,
    "valid_results_publication.svg"
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