import pandas as pd
import os

# =========================
# 1. 输入和输出文件路径
#results\Qwen3-Embedding-0.6B\matching_results\Carbon Peak (Overall).xlsx
#results\Qwen3-Embedding-0.6B\matching_results\New Development Philosophy.xlsx
#results\Qwen3-Embedding-0.6B\matching_results\Industrial Sector.xlsx
#results\Qwen3-Embedding-0.6B\matching_results\Urban and Rural Development Sec.xlsx
#results\Qwen3-Embedding-0.6B\matching_results\Pollution and Carbon Reduction.xlsx
#results\Qwen3-Embedding-0.6B\matching_results\Green Consumption.xlsx
#results\Qwen3-Embedding-0.6B\matching_results\Green, Low-Carbon, and Circular.xlsx
#results\Qwen3-Embedding-0.6B\matching_results\Green and Low-Carbon Transition.xlsx
#results\Qwen3-Embedding-0.6B\matching_results\Non-ferrous Metals.xlsx
#results\Qwen3-Embedding-0.6B\matching_results\Building Materials Industry.xlsx
#results\Qwen3-Embedding-0.6B\matching_results\Standards and Metrology.xlsx
#results\Qwen3-Embedding-0.6B\matching_results\Fiscal Support.xlsx

# =========================
input_file = r"results\Qwen3-Embedding-0.6B\matching_results\Fiscal Support.xlsx"

# 输出文件名
output_file = r"results\Qwen3-Embedding-0.6B\matching_results\Fiscal Support_averaged.xlsx"


# =========================
# 2. 读取 Excel
# =========================
df = pd.read_excel(input_file)

print("原始数据行数:", len(df))
print("原始表头:")
print(df.columns.tolist())


# =========================
# 3. 检查需要的列是否存在
# =========================
required_columns = [
    "query_file",
    "match_file",
    "direct_sim",
    "direct_degree"
]

missing_columns = [col for col in required_columns if col not in df.columns]

if missing_columns:
    raise ValueError(
        f"Excel 中缺少以下列: {missing_columns}"
    )


# =========================
# 4. 确保 direct_sim 和 direct_degree 是数值类型
# =========================
df["direct_sim"] = pd.to_numeric(
    df["direct_sim"],
    errors="coerce"
)

df["direct_degree"] = pd.to_numeric(
    df["direct_degree"],
    errors="coerce"
)


# =========================
# 5. 按 (query_file, match_file) 分组
#    分别计算 direct_sim 和 direct_degree 平均值
# =========================
result = (
    df.groupby(
        ["query_file", "match_file"],
        as_index=False
    )
    .agg(
        direct_sim=("direct_sim", "mean"),
        direct_degree=("direct_degree", "mean")
    )
)


# =========================
# 6. 输出结果
# =========================
# 如果输出目录不存在，则创建
output_dir = os.path.dirname(output_file)

if output_dir:
    os.makedirs(output_dir, exist_ok=True)

result.to_excel(
    output_file,
    index=False
)


# =========================
# 7. 打印结果信息
# =========================
print("\n处理完成！")
print("原始数据行数:", len(df))
print("不同 (query_file, match_file) 对数量:", len(result))
print("结果文件:", output_file)

print("\n结果示例:")
print(result.head(10))