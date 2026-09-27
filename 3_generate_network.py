import pandas as pd
import numpy as np
from pathlib import Path

# ============================================================
# 1. 参数与路径
# ============================================================
MATCHING_DIR = Path(r"results\Qwen3-Embedding-0.6B\matching_results")
TIME_ORDER_FILE = Path(r"data\time_order.xlsx")
OUTPUT_DIR = Path(r"results\Qwen3-Embedding-0.6B\network_metrics")
K = 1.0  # 比值阈值

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

# ============================================================
# 2. 中国省级行政区
# ============================================================
PROVINCES = [
    "北京", "天津", "河北", "山西", "内蒙古", "辽宁", "吉林", "黑龙江",
    "上海", "江苏", "浙江", "安徽", "福建", "江西", "山东", "河南",
    "湖北", "湖南", "广东", "广西", "海南", "重庆", "四川", "贵州",
    "云南", "西藏", "陕西", "甘肃", "青海", "宁夏", "新疆",
    "台湾", "香港", "澳门"
]
PROVINCE_PREFIXES = {p[:2] for p in PROVINCES}

def get_prefix(filename):
    if pd.isna(filename):
        return None
    return str(filename).strip()[:2]

def is_local_file(filename):
    return get_prefix(filename) in PROVINCE_PREFIXES

# ============================================================
# 3. 读取时间顺序表
# ============================================================
def load_time_order(time_order_file):
    time_order_dict = {}
    excel = pd.ExcelFile(time_order_file)
    for sheet in excel.sheet_names:
        df_time = pd.read_excel(time_order_file, sheet_name=sheet)
        required = ["文件名", "时序"]
        if not all(c in df_time.columns for c in required):
            raise ValueError(f"Sheet [{sheet}] 缺少 {required}")
        df_time = df_time[required].copy()
        df_time["prefix"] = df_time["文件名"].apply(get_prefix)
        df_time["时序"] = pd.to_numeric(df_time["时序"], errors="coerce")
        if df_time["时序"].isna().any():
            raise ValueError(f"Sheet [{sheet}] 存在无效时序")
        dup = df_time.groupby("prefix")["时序"].nunique()
        if (dup > 1).any():
            raise ValueError(f"Sheet [{sheet}] 中前缀对应多个时序")
        time_order_dict[sheet] = df_time.drop_duplicates("prefix").set_index("prefix")["时序"].to_dict()
    return time_order_dict

# ============================================================
# 4. 核心处理函数
# ============================================================
def process_domain(df, time_order_dict, domain, K=1.0):
    # ---- 4.1 央地标记 ----
    df["query_is_local"] = df["query_file"].apply(is_local_file)
    df["match_is_local"] = df["match_file"].apply(is_local_file)

    # ---- 4.2 时序 ----
    def get_time(domain, filename):
        if domain not in time_order_dict:
            return np.nan
        prefix = get_prefix(filename)
        return time_order_dict[domain].get(prefix, np.nan)

    df["query_time"] = df.apply(lambda r: get_time(domain, r["query_file"]), axis=1)
    df["match_time"] = df.apply(lambda r: get_time(domain, r["match_file"]), axis=1)

    # ---- 4.3 中央基准：每个地方句子 vs 中央的最佳匹配 ----
    central_df = df[~df["match_is_local"]].copy()
    central_key = ["domain", "query_file", "query"]
    central_df = central_df[central_key + ["match_file", "direct_sim", "direct_degree"]].copy()
    for col in ["direct_sim", "direct_degree"]:
        central_df[col] = pd.to_numeric(central_df[col], errors="coerce")
    central_df = central_df.sort_values(central_key + ["direct_sim"], ascending=[True, True, True, False])
    central_benchmark = central_df.drop_duplicates(subset=central_key, keep="first").rename(
        columns={"match_file": "central_match_file",
                 "direct_sim": "central_sim",
                 "direct_degree": "central_degree"}
    )
    # central_degree = 中央 - 地方(adopter)  (原 direct_degree = match - query)

    # ============================================================
    #  (a) 生成 Source 结果表（同时计算 p_a_s）
    #      adopter = query (地方), source = match (地方或中央)
    # ============================================================
    source_mask = df["query_is_local"]
    source_data = df[source_mask].copy()

    # 地方源需满足时序：query_time > match_time；中央源无时序限制
    local_src_cond = (
        source_data["match_is_local"] &
        source_data["query_time"].notna() & source_data["match_time"].notna() &
        (source_data["query_time"] > source_data["match_time"])
    )
    central_src_cond = ~source_data["match_is_local"]
    source_data = source_data[local_src_cond | central_src_cond].copy()

    # 合并中央基准
    source_data = source_data.merge(central_benchmark, on=["domain", "query_file", "query"], how="left")

    # 逐句指标
    source_data["source_att_per"] = -source_data["direct_degree"]          # adopter - source
    source_data["source_diff_per"] = 0.0
    is_local_src = source_data["match_is_local"]
    source_data.loc[is_local_src, "source_diff_per"] = (
        source_data.loc[is_local_src, "central_degree"] -
        source_data.loc[is_local_src, "direct_degree"]
    )
    # 比值（仅地方源有意义）
    source_data["ratio"] = np.where(
        source_data["central_sim"] != 0,
        source_data["direct_sim"] / source_data["central_sim"],
        np.nan
    )

    # 聚合 source 表
    source_agg = source_data.groupby(["domain", "query_file", "match_file"], as_index=False).agg(
        source_sim=("direct_sim", "mean"),
        source_att=("source_att_per", "mean"),
        source_diff=("source_diff_per", "mean")
    )

    # 计算 p_a_s（统一共享）
    # 地方源按实际比值
    local_src_agg = source_data[source_data["match_is_local"]]
    central_src_agg = source_data[~source_data["match_is_local"]]

    pas_local = local_src_agg.groupby(["domain", "query_file", "match_file"]).apply(
        lambda g: (g["ratio"] >= K).mean() if g["ratio"].notna().any() else np.nan
    ).reset_index(name="p_a_s")

    pas_central = central_src_agg[["domain", "query_file", "match_file"]].drop_duplicates()
    pas_central["p_a_s"] = 1.0

    pas_all = pd.concat([pas_local, pas_central], ignore_index=True)

    # 合并 p_a_s 到 source_agg
    source_agg = source_agg.merge(pas_all, on=["domain", "query_file", "match_file"], how="left")
    source_agg["source_type"] = source_agg["match_file"].apply(lambda x: "地方" if is_local_file(x) else "中央")
    source_result = source_agg.rename(columns={"query_file": "adopter_file", "match_file": "source_file"})
    source_result["k"] = K
    source_result = source_result[["domain", "adopter_file", "source_file", "source_type",
                                   "source_sim", "source_att", "source_diff", "p_a_s", "k"]]

    # ============================================================
    #  (b) 生成 Adoption 结果表（使用共享的 p_a_s）
    #      source = query (地方或中央), adopter = match (地方)
    # ============================================================
    adoption_mask = df["match_is_local"]
    adoption_data = df[adoption_mask].copy()

    # 地方源需满足时序：query_time < match_time；中央源无时序限制
    local_adopt_cond = (
        adoption_data["query_is_local"] &
        adoption_data["query_time"].notna() & adoption_data["match_time"].notna() &
        (adoption_data["query_time"] < adoption_data["match_time"])
    )
    central_adopt_cond = ~adoption_data["query_is_local"]
    adoption_data = adoption_data[local_adopt_cond | central_adopt_cond].copy()

    # 修正：合并中央基准时应按 adopter 的句子匹配，即 match_file 和 match
    adoption_data = adoption_data.merge(
        central_benchmark,
        left_on=["domain", "match_file", "direct_match"],
        right_on=["domain", "query_file", "query"],
        how="left",
        suffixes=("", "_central")
    )
    adoption_data.rename(columns={"central_sim": "adopter_central_sim",
                                  "central_degree": "adopter_central_degree"}, inplace=True)

    # 逐句指标
    adoption_data["adoption_att_per"] = adoption_data["direct_degree"]      # adopter - source
    adoption_data["adoption_diff_per"] = 0.0
    is_local_adopt = adoption_data["query_is_local"]
    # diff = (adopter - source) - (adopter - central) = direct_degree + adopter_central_degree
    adoption_data.loc[is_local_adopt, "adoption_diff_per"] = (
        adoption_data.loc[is_local_adopt, "direct_degree"] +
        adoption_data.loc[is_local_adopt, "adopter_central_degree"]
    )

    # 聚合 adoption 表
    adoption_agg = adoption_data.groupby(["domain", "query_file", "match_file"], as_index=False).agg(
        adoption_sim=("direct_sim", "mean"),
        adoption_att=("adoption_att_per", "mean"),
        adoption_diff=("adoption_diff_per", "mean")
    )

    # 关键修正：直接合并 source_result 中的 p_a_s（确保一致）
    # source_result 有 (adopter_file, source_file) = (query_file, match_file)
    # adoption_agg 有 (query_file, match_file) 分别对应 (source_file, adopter_file)
    # 因此将 adoption_agg 的 (query_file, match_file) 映射到 source 的 (adopter_file, source_file)
    pas_for_adoption = source_result[["domain", "adopter_file", "source_file", "p_a_s"]].copy()
    pas_for_adoption = pas_for_adoption.rename(columns={"adopter_file": "match_file", "source_file": "query_file"})
    adoption_agg = adoption_agg.merge(pas_for_adoption, on=["domain", "query_file", "match_file"], how="left")

    adoption_agg["source_type"] = adoption_agg["query_file"].apply(lambda x: "地方" if is_local_file(x) else "中央")
    adoption_result = adoption_agg.rename(columns={"query_file": "source_file", "match_file": "adopter_file"})
    adoption_result["k"] = K
    adoption_result = adoption_result[["domain", "source_file", "adopter_file", "source_type",
                                       "adoption_sim", "adoption_att", "adoption_diff", "p_a_s", "k"]]

    # ============================================================
    #  (c) 生成 p_a_s 汇总表（直接从 source_result 提取）
    # ============================================================
    pas_final = source_result[["domain", "adopter_file", "source_file", "source_type", "p_a_s", "k"]].copy()

    return pas_final, source_result, adoption_result

# ============================================================
# 5. 主循环
# ============================================================
def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading time order...")
    time_order_dict = load_time_order(TIME_ORDER_FILE)
    print("Done.\n")

    for domain in DOMAINS:
        print(f"Processing {domain}...")
        input_file = MATCHING_DIR / f"{domain}.xlsx"
        if not input_file.exists():
            print(f"  File {input_file} not found, skipped.")
            continue

        df = pd.read_excel(input_file)
        required_cols = ["domain", "query_file", "match_file", "query", "direct_match",
                         "query_section", "match_section", "direct_sim", "hidden_sim",
                         "direct_degree", "hidden_degree"]
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            raise ValueError(f"Missing columns: {missing} in {input_file}")

        pas_df, source_df, adoption_df = process_domain(df, time_order_dict, domain, K)

        pas_df.to_excel(OUTPUT_DIR / f"{domain}_p_a_s.xlsx", index=False)
        source_df.to_excel(OUTPUT_DIR / f"{domain}_source.xlsx", index=False)
        adoption_df.to_excel(OUTPUT_DIR / f"{domain}_adoption.xlsx", index=False)

        print(f"  -> {domain}_p_a_s.xlsx, {domain}_source.xlsx, {domain}_adoption.xlsx")

    print("\nAll tasks completed.")

if __name__ == "__main__":
    main()