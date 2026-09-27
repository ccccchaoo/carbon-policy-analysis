
# ============================================================
# matching_main.py
#
# ============================================================
#
# 已生成 embedding 后的文件级匹配程序
#
# 核心流程：
#
# for domain:
#
#     for query_file:
#
#         for match_file:
#
#             for query_sentence:
#
#                 在当前 match_file 的 sentence embedding
#                 范围内进行匹配
#
#
# 即：
#
#     domain
#       │
#       ├── query_file_1
#       │      ├── match_file_1
#       │      ├── match_file_2
#       │      ├── match_file_3
#       │      └── ...
#       │
#       ├── query_file_2
#       │      ├── match_file_1
#       │      ├── match_file_2
#       │      ├── match_file_3
#       │      └── ...
#       │
#       └── ...
#
#
# 每个 domain：
#
#     Building Materials Industry.csv
#
# 对应生成：
#
#     Building Materials Industry.xlsx
#
#
# Excel 中：
#
#     query_file
#     match_file
#
# 均为具体的 docx 文件名。
#
#
# ============================================================


import os
import time

import pandas as pd


from utils_embedding import (

    get_domain_embedding_paths,

    load_embedding_matrix,

    load_embedding_csv,

    group_records_by_file,

    selective_execution_analysis,

    clear_embedding_cache,

    MODEL_NAME

)


# ============================================================
# 1. Embedding 根目录
# ============================================================

EMBEDDING_ROOT = r"data\embeddings"
RESULT_ROOT = r"results"


# ============================================================
# 2. Query embedding directory
# ============================================================

QUERY_EMBEDDING_DIR = os.path.join(

    EMBEDDING_ROOT,

    MODEL_NAME,

    "structured_query"

)


# ============================================================
# 3. Match embedding directory
# ============================================================

MATCH_EMBEDDING_DIR = os.path.join(

    EMBEDDING_ROOT,

    MODEL_NAME,

    "structured_match"

)


# ============================================================
# 4. Degree dictionary
# ============================================================

DEGREE_DICT = r"data\dictionary\dictionary.xlsx"


# ============================================================
# 5. Output directory
# ============================================================

OUTPUT_DIR = os.path.join(

    RESULT_ROOT,

    MODEL_NAME,

    "matching_results"

)


# ============================================================
# 6. Matching parameters
# ============================================================

TOPK = 1

THRESHOLD = 0


# ============================================================
# 7. 获取目录中的所有 domain CSV
# ============================================================

def get_domain_csv_files(directory):
    """
    获取目录中的所有 CSV。

    例如：

        structured_query/
            Building Materials Industry.csv
            Carbon Peak (Overall).csv
            Fiscal Support.csv
            ...

    返回：

        [
            "Building Materials Industry.csv",
            "Carbon Peak (Overall).csv",
            ...
        ]
    """

    if not os.path.isdir(directory):

        raise FileNotFoundError(

            f"\nDirectory not found:\n"
            f"{directory}\n"

        )


    files = [

        filename

        for filename in os.listdir(directory)

        if filename.lower().endswith(".csv")

    ]


    files.sort()


    return files


# ============================================================
# 8. 获取 domain 名称
# ============================================================

def get_domain_name(csv_filename):
    """
    例如：

        Building Materials Industry.csv

    返回：

        Building Materials Industry
    """

    return os.path.splitext(
        csv_filename
    )[0]


# ============================================================
# 9. 保存 domain Excel
# ============================================================

def save_domain_results(
    domain,
    results
):
    """
    一个 domain 对应一个 Excel。

    例如：

        Building Materials Industry

            ↓

        Building Materials Industry.xlsx
    """

    os.makedirs(

        OUTPUT_DIR,

        exist_ok=True

    )


    output_path = os.path.join(

        OUTPUT_DIR,

        domain + ".xlsx"

    )


    if not results:

        print()

        print(
            f"[WARNING] "
            f"No matching results for domain: "
            f"{domain}"
        )

        return


    df = pd.DataFrame(
        results
    )


    # --------------------------------------------------------
    # Excel 列顺序
    # --------------------------------------------------------

    preferred_columns = [

        "domain",

        "query_file",

        "match_file",

        "query",

        "direct_match",

        "query_section",

        "match_section",

        "direct_sim",

        "hidden_sim",

        "direct_degree",

        "hidden_degree"

    ]


    existing_columns = [

        column

        for column in preferred_columns

        if column in df.columns

    ]


    other_columns = [

        column

        for column in df.columns

        if column not in existing_columns

    ]


    df = df[
        existing_columns
        +
        other_columns
    ]


    # --------------------------------------------------------
    # 保存
    # --------------------------------------------------------

    df.to_excel(

        output_path,

        index=False

    )


    print()

    print(
        "=" * 80
    )

    print(
        f"[EXCEL SAVED]"
    )

    print(
        f"Domain : {domain}"
    )

    print(
        f"Rows   : {len(df)}"
    )

    print(
        f"Path   : {output_path}"
    )

    print(
        "=" * 80
    )


# ============================================================
# 10. 打印当前 domain 的文件信息
# ============================================================

def print_domain_file_info(
    domain,
    query_files,
    match_files
):
    """
    打印当前 domain 实际发现了多少 query_file
    和多少 match_file。

    这个函数主要用于确认：

        query_file 是否全部被遍历。
    """

    print()

    print(
        "-" * 80
    )

    print(
        f"DOMAIN: {domain}"
    )

    print(
        f"Query files = {len(query_files)}"
    )

    print(
        f"Match files = {len(match_files)}"
    )

    print(
        f"Expected file pairs = "
        f"{len(query_files) * len(match_files)}"
    )

    print(
        "-" * 80
    )


    print()

    print(
        "Query files:"
    )


    for index, filename in enumerate(

        sorted(query_files),

        start=1

    ):

        print(

            f"    Q{index:03d}: "
            f"{filename}"

        )


    print()

    print(
        "Match files:"
    )


    for index, filename in enumerate(

        sorted(match_files),

        start=1

    ):

        print(

            f"    M{index:03d}: "
            f"{filename}"

        )


# ============================================================
# 11. 主程序
# ============================================================

def main():
    

    start_time = time.time()


    print()

    print(
        "=" * 80
    )

    print(
        "FILE-LEVEL EMBEDDING MATCHING"
    )

    print(
        "=" * 80
    )

    print(
        f"Model:"
    )

    print(
        f"    {MODEL_NAME}"
    )

    print()

    print(
        f"Query embedding directory:"
    )

    print(
        f"    {QUERY_EMBEDDING_DIR}"
    )

    print()

    print(
        f"Match embedding directory:"
    )

    print(
        f"    {MATCH_EMBEDDING_DIR}"
    )

    print()

    print(
        f"Output directory:"
    )

    print(
        f"    {OUTPUT_DIR}"
    )

    print()

    print(
        f"TOPK:"
    )

    print(
        f"    {TOPK}"
    )

    print()

    print(
        f"THRESHOLD:"
    )

    print(
        f"    {THRESHOLD}"
    )

    print(
        "=" * 80
    )


    # ========================================================
    # STEP 1
    #
    # 找到 query / match 中所有 domain CSV
    # ========================================================

    query_domain_csvs = get_domain_csv_files(

        QUERY_EMBEDDING_DIR

    )


    match_domain_csvs = get_domain_csv_files(

        MATCH_EMBEDDING_DIR

    )


    # ========================================================
    # STEP 2
    #
    # 建立：
    #
    #     domain -> csv filename
    #
    # ========================================================

    query_domain_map = {

        get_domain_name(filename):
            filename

        for filename in query_domain_csvs

    }


    match_domain_map = {

        get_domain_name(filename):
            filename

        for filename in match_domain_csvs

    }


    # ========================================================
    # STEP 3
    #
    # query / match 都存在的 domain
    #
    # ========================================================

    common_domains = sorted(

        set(
            query_domain_map.keys()
        )

        &

        set(
            match_domain_map.keys()
        )

    )


    print()

    print(
        f"Query domains : "
        f"{len(query_domain_map)}"
    )

    print(
        f"Match domains : "
        f"{len(match_domain_map)}"
    )

    print(
        f"Common domains: "
        f"{len(common_domains)}"
    )


    # ========================================================
    # STEP 4
    #
    # 检查 domain 不一致
    # ========================================================

    query_only_domains = sorted(

        set(
            query_domain_map.keys()
        )

        -

        set(
            match_domain_map.keys()
        )

    )


    match_only_domains = sorted(

        set(
            match_domain_map.keys()
        )

        -

        set(
            query_domain_map.keys()
        )

    )


    if query_only_domains:

        print()

        print(
            "[WARNING] "
            "Domains only found in query:"
        )


        for domain in query_only_domains:

            print(
                f"    {domain}"
            )


    if match_only_domains:

        print()

        print(
            "[WARNING] "
            "Domains only found in match:"
        )


        for domain in match_only_domains:

            print(
                f"    {domain}"
            )


    # ========================================================
    # STEP 5
    #
    # 遍历 domain
    # ========================================================

    total_domain_count = len(
        common_domains
    )


    for domain_index, domain in enumerate(

        common_domains,

        start=1

    ):

        print()

        print()

        print(
            "#" * 80
        )

        print(
            f"DOMAIN "
            f"{domain_index}/"
            f"{total_domain_count}"
        )

        print(
            f"{domain}"
        )

        print(
            "#" * 80
        )


        # ====================================================
        # STEP 5.1
        #
        # 获取对应的 CSV
        # ====================================================

        query_domain_csv = (

            query_domain_map[
                domain
            ]

        )


        match_domain_csv = (

            match_domain_map[
                domain
            ]

        )


        # ====================================================
        # STEP 5.2
        #
        # 找到 npy + csv
        # ====================================================

        (
            query_npy_path,
            query_csv_path
        ) = get_domain_embedding_paths(

            query_domain_csv,

            "query"

        )


        (
            match_npy_path,
            match_csv_path
        ) = get_domain_embedding_paths(

            match_domain_csv,

            "match"

        )


        # ====================================================
        # STEP 5.3
        #
        # 加载整个 domain 的 embedding
        #
        # 注意：
        #
        # 这里加载整个 domain 是为了根据 vector_id
        # 取出当前文件的向量。
        #
        # 并不是拿整个 domain 做 similarity search。
        # ====================================================

        print()

        print(
            "[LOAD] Query embeddings"
        )


        query_embeddings = (

            load_embedding_matrix(

                query_npy_path

            )

        )


        print()

        print(
            "[LOAD] Match embeddings"
        )


        match_embeddings = (

            load_embedding_matrix(

                match_npy_path

            )

        )


        # ====================================================
        # STEP 5.4
        #
        # 加载 CSV metadata
        # ====================================================

        print()

        print(
            "[LOAD] Query metadata"
        )


        query_records_all = (

            load_embedding_csv(

                query_csv_path

            )

        )


        print(

            f"        records = "
            f"{len(query_records_all)}"

        )


        print()

        print(
            "[LOAD] Match metadata"
        )


        match_records_all = (

            load_embedding_csv(

                match_csv_path

            )

        )


        print(

            f"        records = "
            f"{len(match_records_all)}"

        )


        # ====================================================
        # STEP 5.5
        #
        # 按 file_name 分组
        #
        # 这是最关键的一步。
        #
        # domain CSV：
        #
        #     vector_id
        #     file_name
        #     section
        #     sentence
        #
        # ↓
        #
        # {
        #
        #     query_file_1: [
        #         sentence...
        #     ],
        #
        #     query_file_2: [
        #         sentence...
        #     ],
        #
        #     ...
        #
        # }
        # ====================================================

        query_files = (

            group_records_by_file(

                query_records_all

            )

        )


        match_files = (

            group_records_by_file(

                match_records_all

            )

        )


        # ====================================================
        # 打印实际发现的文件
        # ====================================================

        print_domain_file_info(

            domain,

            query_files,

            match_files

        )


        # ====================================================
        # 如果任意一边没有文件
        # ====================================================

        if not query_files:

            print()

            print(
                "[WARNING] "
                f"No query files in domain: "
                f"{domain}"
            )

            continue


        if not match_files:

            print()

            print(
                "[WARNING] "
                f"No match files in domain: "
                f"{domain}"
            )

            continue


        # ====================================================
        # STEP 5.6
        #
        # 计算 file pair 数量
        #
        # 注意这里明确是：
        #
        #     len(query_files)
        #
        #         ×
        #
        #     len(match_files)
        #
        # ====================================================

        total_pairs = (

            len(query_files)

            *

            len(match_files)

        )


        pair_counter = 0


        # ====================================================
        # 当前 domain 的全部结果
        # ====================================================

        domain_results = []


        # ====================================================
        # STEP 6
        #
        # query_file × match_file
        #
        # ====================================================

        for query_file in sorted(

            query_files.keys()

        ):


            # =================================================
            # 当前 query_file 的所有 sentence
            # =================================================

            current_query_records = (

                query_files[
                    query_file
                ]

            )


            print()

            print(
                ">" * 80
            )

            print(
                "[QUERY FILE]"
            )

            print(
                f"{query_file}"
            )

            print(
                f"Sentences: "
                f"{len(current_query_records)}"
            )

            print(
                "<" * 80
            )


            # =================================================
            # 遍历所有 match_file
            #
            # 注意：
            #
            # 这里没有任何：
            #
            #     break
            #
            # 或：
            #
            #     match_file = ...
            #
            # 因此会完整遍历所有 match_file。
            # =================================================

            for match_file in sorted(

                match_files.keys()

            ):


                pair_counter += 1


                # =================================================
                # 当前 match_file 的所有 sentence
                #
                # 这里非常关键：
                #
                # current_match_records
                #
                # 只属于当前 match_file。
                # =================================================

                current_match_records = (

                    match_files[
                        match_file
                    ]

                )


                print()

                print(
                    "-" * 80
                )

                print(
                    f"[FILE PAIR "
                    f"{pair_counter}/"
                    f"{total_pairs}]"
                )

                print()

                print(
                    f"QUERY:"
                )

                print(
                    f"    {query_file}"
                )

                print()

                print(
                    f"MATCH:"
                )

                print(
                    f"    {match_file}"
                )

                print()

                print(
                    f"Query sentences:"
                    f" {len(current_query_records)}"
                )

                print(
                    f"Match sentences:"
                    f" {len(current_match_records)}"
                )

                print(
                    "-" * 80
                )


                # =================================================
                # 当前 query_file × 当前 match_file
                # =================================================

                pair_results = (

                    selective_execution_analysis(

                        domain=domain,

                        query_file=query_file,

                        match_file=match_file,

                        query_records=(
                            current_query_records
                        ),

                        match_records=(
                            current_match_records
                        ),

                        query_embeddings=(
                            query_embeddings
                        ),

                        match_embeddings=(
                            match_embeddings
                        ),

                        degree_dict=DEGREE_DICT,

                        topk=TOPK,

                        threshold=THRESHOLD

                    )

                )


                # =================================================
                # 将当前 pair 的结果加入当前 domain
                # =================================================

                domain_results.extend(

                    pair_results

                )


                print()

                print(
                    f"[PAIR FINISHED]"
                )

                print(
                    f"    Results: "
                    f"{len(pair_results)}"
                )


        # ========================================================
        # STEP 7
        #
        # 当前 domain 的所有 query_file × match_file
        # 全部结束后，保存一个 Excel。
        # ========================================================

        print()

        print(
            "=" * 80
        )

        print(
            f"[DOMAIN FINISHED]"
        )

        print(
            f"Domain:"
        )

        print(
            f"    {domain}"
        )

        print()

        print(
            f"Query files:"
            f" {len(query_files)}"
        )

        print(
            f"Match files:"
            f" {len(match_files)}"
        )

        print()

        print(
            f"File pairs:"
            f" {pair_counter}"
        )

        print(
            f"Expected pairs:"
            f" {total_pairs}"
        )

        print()

        print(
            f"Result rows:"
            f" {len(domain_results)}"
        )

        print(
            "=" * 80
        )


        # ========================================================
        # 安全检查
        #
        # 如果 pair_counter != total_pairs，
        # 说明程序没有完整遍历 query_file × match_file。
        # ========================================================

        if pair_counter != total_pairs:

            raise RuntimeError(

                "\nFILE PAIR COUNT ERROR\n"

                f"Expected: {total_pairs}\n"

                f"Actual:   {pair_counter}\n"

                f"Domain:   {domain}\n"

            )


        # ========================================================
        # 保存
        # ========================================================

        save_domain_results(

            domain=domain,

            results=domain_results

        )


    # ============================================================
    # STEP 8
    #
    # 清理 cache
    # ============================================================

    clear_embedding_cache()


    # ============================================================
    # STEP 9
    #
    # 完成
    # ============================================================

    elapsed = (

        time.time()

        -

        start_time

    )


    print()

    print()

    print(
        "=" * 80
    )

    print(
        "ALL MATCHING FINISHED"
    )

    print(
        "=" * 80
    )

    print()

    print(
        f"Domains processed:"
        f" {total_domain_count}"
    )

    print()

    print(
        f"Elapsed time:"
        f" {elapsed:.2f} seconds"
    )

    print()

    print(
        f"Output directory:"
    )

    print(
        f"    {OUTPUT_DIR}"
    )

    print()

    print(
        "=" * 80
    )


# ============================================================
# Entry
# ============================================================

if __name__ == "__main__":

    main()

