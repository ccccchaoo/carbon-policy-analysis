
# ============================================================
# utils_embedding_matching.py
#
# 基于已经生成的 embedding 进行文件级别匹配
#
# 核心层级：
#
#     domain
#         ↓
#     query_file
#         ↓
#     match_file
#         ↓
#     query_sentence
#         ↓
#     match_sentence
#
# 非常重要：
#
# 每一次匹配严格限定在：
#
#     一个 query_file
#             VS
#     一个 match_file
#
# 不会把整个 domain 的 match sentences
# 混合成一个 corpus。
#
# 本文件：
#     不加载 SentenceTransformer
#     不调用 model.encode()
#     只读取 .npy + .csv
# ============================================================

import os
import csv
from collections import defaultdict, deque

import numpy as np
import pandas as pd
import jieba


# ============================================================
# 1. Embedding 模型
# ============================================================

# 当前匹配使用哪个已经生成的 embedding。
#
# 例如：
#
#     multilingual-e5-large
#     bge-m3
#     paraphrase-multilingual-MiniLM-L12-v2
#     Qwen3-Embedding-0.6B


MODEL_NAME = "Qwen3-Embedding-0.6B"


# ============================================================
# 2. Embedding 根目录
# ============================================================

EMBEDDING_ROOT = r"data\embeddings"


# ============================================================
# 3. Query / Match embedding directory
# ============================================================

QUERY_EMBEDDING_DIR = os.path.join(
    EMBEDDING_ROOT,
    MODEL_NAME,
    "structured_query"
)


MATCH_EMBEDDING_DIR = os.path.join(
    EMBEDDING_ROOT,
    MODEL_NAME,
    "structured_match"
)


# ============================================================
# 4. Cache
# ============================================================

# ------------------------------------------------------------
# npy cache
#
# 一个 domain 一个 npy
# ------------------------------------------------------------

_EMBEDDING_CACHE = {}


# ------------------------------------------------------------
# CSV cache
#
# key:
#     csv_path
#
# value:
#     完整记录
# ------------------------------------------------------------

_CSV_CACHE = {}


# ------------------------------------------------------------
# degree dictionary cache
# ------------------------------------------------------------

_DEGREE_CACHE = {}


# ============================================================
# 5. 文件名 stem
# ============================================================

def normalize_file_stem(file_name):
    """
    将文件名转换为 stem。

    例如：

        Building Materials Industry.csv
            ↓
        Building Materials Industry

    """

    return os.path.splitext(
        os.path.basename(
            file_name
        )
    )[0]


# ============================================================
# 6. 找到 domain 对应的 embedding 文件
# ============================================================

def get_domain_embedding_paths(
    domain,
    embedding_type
):
    """
    根据 domain 获取：

        domain.npy
        domain.csv

    embedding_type:

        "query"
        "match"
    """

    domain_stem = normalize_file_stem(
        domain
    )


    if embedding_type == "query":

        directory = QUERY_EMBEDDING_DIR

    elif embedding_type == "match":

        directory = MATCH_EMBEDDING_DIR

    else:

        raise ValueError(
            "embedding_type must be "
            "'query' or 'match'"
        )


    npy_path = os.path.join(
        directory,
        domain_stem + ".npy"
    )


    csv_path = os.path.join(
        directory,
        domain_stem + ".csv"
    )


    if not os.path.exists(
        npy_path
    ):

        raise FileNotFoundError(
            "\nEmbedding NPY not found:\n"
            f"{npy_path}\n"
        )


    if not os.path.exists(
        csv_path
    ):

        raise FileNotFoundError(
            "\nEmbedding CSV not found:\n"
            f"{csv_path}\n"
        )


    return (
        npy_path,
        csv_path
    )


# ============================================================
# 7. 加载 NPY
# ============================================================

def load_embedding_matrix(
    npy_path
):
    """
    返回：

        numpy.ndarray

    shape：

        [N, D]
    """

    if npy_path not in _EMBEDDING_CACHE:

        print(
            f"[LOAD NPY] {npy_path}"
        )


        embeddings = np.load(
            npy_path
        )


        if embeddings.ndim != 2:

            raise ValueError(
                f"Invalid embedding shape: "
                f"{embeddings.shape}\n"
                f"Expected [N, D]."
            )


        _EMBEDDING_CACHE[
            npy_path
        ] = embeddings


        print(
            f"           shape = "
            f"{embeddings.shape}"
        )


    return _EMBEDDING_CACHE[
        npy_path
    ]


# ============================================================
# 8. 加载 CSV
# ============================================================

def load_embedding_csv(
    csv_path
):
    """
    CSV 格式：

        vector_id,file_name,section,sentence

    返回 list[dict]
    """

    if csv_path in _CSV_CACHE:

        return _CSV_CACHE[
            csv_path
        ]


    records = []


    with open(
        csv_path,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        reader = csv.DictReader(
            f
        )


        required_columns = {

            "vector_id",
            "file_name",
            "section",
            "sentence"

        }


        actual_columns = set(
            reader.fieldnames or []
        )


        missing = (
            required_columns
            -
            actual_columns
        )


        if missing:

            raise ValueError(
                "\nInvalid embedding CSV:\n"
                f"{csv_path}\n\n"
                f"Missing columns:\n"
                f"{missing}\n\n"
                f"Actual columns:\n"
                f"{actual_columns}"
            )


        for row in reader:

            records.append({

                "vector_id": int(
                    row[
                        "vector_id"
                    ]
                ),

                "file_name": row[
                    "file_name"
                ],

                "section": row[
                    "section"
                ],

                "sentence": row[
                    "sentence"
                ]

            })


    _CSV_CACHE[
        csv_path
    ] = records


    return records


# ============================================================
# 9. 按 file_name 对 embedding 进行分组
# ============================================================

def group_records_by_file(
    records
):
    """
    将：

        [
            {
                file_name: A,
                vector_id: 0,
                ...
            },
            {
                file_name: A,
                vector_id: 1,
                ...
            },
            {
                file_name: B,
                vector_id: 2,
                ...
            }
        ]

    转换成：

        {
            A: [...],
            B: [...]
        }
    """

    grouped = defaultdict(
        list
    )


    for record in records:

        grouped[
            record[
                "file_name"
            ]
        ].append(
            record
        )


    return dict(
        grouped
    )


# ============================================================
# 10. 建立 sentence -> records
# ============================================================

def build_sentence_index(
    records
):
    """
    建立：

        sentence
            ↓
        [
            record1,
            record2,
            ...
        ]

    处理重复句子。
    """

    index = defaultdict(
        deque
    )


    for record in records:

        index[
            record[
                "sentence"
            ]
        ].append(
            record
        )


    return index


# ============================================================
# 11. Cosine similarity
# ============================================================

def cosine_similarity(
    query_embedding,
    corpus_embeddings
):
    """
    query:
        [D]

    corpus:
        [N, D]

    return:
        [N]
    """

    query_embedding = np.asarray(
        query_embedding,
        dtype=np.float32
    )


    corpus_embeddings = np.asarray(
        corpus_embeddings,
        dtype=np.float32
    )


    query_norm = np.linalg.norm(
        query_embedding
    )


    if query_norm == 0:

        return np.zeros(
            len(corpus_embeddings),
            dtype=np.float32
        )


    corpus_norms = np.linalg.norm(
        corpus_embeddings,
        axis=1
    )


    query_normalized = (

        query_embedding
        /
        query_norm

    )


    corpus_normalized = np.divide(

        corpus_embeddings,

        corpus_norms[:, None],

        out=np.zeros_like(
            corpus_embeddings
        ),

        where=(
            corpus_norms[:, None] != 0
        )

    )


    return np.dot(

        corpus_normalized,

        query_normalized

    ).astype(
        np.float32
    )


# ============================================================
# 12. semantic search
# ============================================================

def semantic_search(
    query_embedding,
    corpus_embeddings,
    top_k=1
):
    """
    返回：

        [
            {
                "corpus_id": 0,
                "score": 0.91
            },
            ...
        ]

    corpus_id 是当前 match_file 内部的局部 index。
    """

    corpus_size = len(
        corpus_embeddings
    )


    if corpus_size == 0:

        return []


    top_k = min(
        int(top_k),
        corpus_size
    )


    scores = cosine_similarity(

        query_embedding,

        corpus_embeddings

    )


    if top_k == corpus_size:

        ids = np.arange(
            corpus_size
        )

    else:

        ids = np.argpartition(

            -scores,

            top_k - 1

        )[:top_k]


    ids = ids[
        np.argsort(
            -scores[ids],
            kind="stable"
        )
    ]


    return [

        {
            "corpus_id": int(
                idx
            ),

            "score": float(
                scores[idx]
            )

        }

        for idx in ids

    ]


# ============================================================
# 13. Degree score
# ============================================================

def degree_score(
    sentence,
    degree_dict
):
    """
    与原始逻辑保持一致：

        jieba.lcut(sentence)

        word -> dictionary score

        最后累加。
    """

    if degree_dict not in _DEGREE_CACHE:

        df = pd.read_excel(
            degree_dict
        )


        score_dict = dict(

            zip(
                df.iloc[:, 0],
                df.iloc[:, 1]
            )

        )


        _DEGREE_CACHE[
            degree_dict
        ] = score_dict


    score_dict = _DEGREE_CACHE[
        degree_dict
    ]


    score = 0


    for word in jieba.lcut(
        sentence
    ):

        if word in score_dict:

            score += score_dict[
                word
            ]


    return score


# ============================================================
# 14. 构造一个文件的 embedding corpus
# ============================================================

def build_file_corpus(
    file_records,
    embeddings
):
    """
    给定一个 file_name 的 records：

        file_records

    根据 vector_id 从 domain npy 中取出：

        sentences
        embeddings
        metadata

    """

    records = list(
        file_records
    )


    vector_ids = np.asarray(

        [
            record[
                "vector_id"
            ]

            for record in records
        ],

        dtype=np.int64

    )


    corpus_embeddings = embeddings[
        vector_ids
    ]


    sentences = [

        record[
            "sentence"
        ]

        for record in records

    ]


    return (
        records,
        sentences,
        corpus_embeddings
    )


# ============================================================
# 15. selective_execution_analysis
# ============================================================

def selective_execution_analysis(
    domain,
    query_file,
    match_file,
    query_records,
    match_records,
    query_embeddings,
    match_embeddings,
    degree_dict,
    topk=1,
    threshold=0
):
    """
    ============================================================
    最核心的匹配函数
    ============================================================

    输入：

        domain
            例如：
            Building Materials Industry

        query_file
            例如：
            云南省建材行业碳达峰实施方案.docx

        match_file
            例如：
            四川省建材行业碳达峰实施方案.docx

        query_records
            仅属于 query_file 的 CSV records

        match_records
            仅属于 match_file 的 CSV records

        query_embeddings
            当前 domain 的 query npy

        match_embeddings
            当前 domain 的 match npy


    ============================================================
    最关键的约束
    ============================================================

    match corpus：

        只来自当前 match_file。

    即：

        query_file
             VS
        match_file

    而不是：

        query_file
             VS
        整个 domain 的所有 match sentences。


    ============================================================
    返回
    ============================================================

    每个 query sentence 一条结果。
    """

    # ========================================================
    # 1. 构造当前 match_file corpus
    # ========================================================

    (
        match_records,
        match_sentences,
        match_corpus_embeddings
    ) = build_file_corpus(

        match_records,

        match_embeddings

    )


    # ========================================================
    # 2. query sentence
    # ========================================================

    (
        query_records,
        query_sentences,
        _
    ) = build_file_corpus(

        query_records,

        query_embeddings

    )


    # ========================================================
    # 3. 空 match_file
    # ========================================================

    if len(
        match_sentences
    ) == 0:

        return [

            {

                "domain": domain,

                "query_file": query_file,

                "match_file": match_file,

                "query": query_sentence,

                "direct_match": None,

                "query_section": (
                    query_record[
                        "section"
                    ]
                ),

                "match_section": None,

                "direct_sim": 0,

                "hidden_sim": 0,

                "direct_degree": 0,

                "hidden_degree": 0

            }

            for query_record,
            query_sentence

            in zip(
                query_records,
                query_sentences
            )

        ]


    # ========================================================
    # 4. 开始逐 query sentence 匹配
    # ========================================================

    results = []


    for query_record, query_sentence, query_vector_id in zip(

        query_records,

        query_sentences,

        [
            record[
                "vector_id"
            ]

            for record in query_records
        ]

    ):

        # ----------------------------------------------------
        # query embedding
        # ----------------------------------------------------

        query_embedding = (
            query_embeddings[
                query_vector_id
            ]
        )


        # ----------------------------------------------------
        # IMPORTANT
        #
        # 这里只传入当前 match_file 的：
        #
        #     match_corpus_embeddings
        #
        # 所以搜索范围严格限定于：
        #
        #     query_file × match_file
        #
        # ----------------------------------------------------

        hits = semantic_search(

            query_embedding=query_embedding,

            corpus_embeddings=(
                match_corpus_embeddings
            ),

            top_k=topk

        )


        # ----------------------------------------------------
        # 没有 match
        # ----------------------------------------------------

        if not hits:

            results.append({

                "domain": domain,

                "query_file": query_file,

                "match_file": match_file,

                "query": query_sentence,

                "direct_match": None,

                "query_section": (
                    query_record[
                        "section"
                    ]
                ),

                "match_section": None,

                "direct_sim": 0,

                "hidden_sim": 0,

                "direct_degree": 0,

                "hidden_degree": 0

            })

            continue


        # ====================================================
        # 5. Direct match
        # ====================================================

        direct_hit = hits[0]


        local_corpus_id = (
            direct_hit[
                "corpus_id"
            ]
        )


        direct_record = (
            match_records[
                local_corpus_id
            ]
        )


        direct_match = (
            direct_record[
                "sentence"
            ]
        )


        direct_sim = (
            direct_hit[
                "score"
            ]
        )


        # ====================================================
        # 6. Degree
        # ====================================================

        query_degree = degree_score(

            query_sentence,

            degree_dict

        )


        direct_match_degree = degree_score(

            direct_match,

            degree_dict

        )


        direct_degree = (

            direct_match_degree
            -
            query_degree

        )


        # ====================================================
        # 7. Hidden similarity / degree
        # ====================================================

        hidden_sim = 0

        hidden_degree = 0

        n = 0


        for hit in hits:

            local_id = (
                hit[
                    "corpus_id"
                ]
            )


            hidden_record = (
                match_records[
                    local_id
                ]
            )


            hidden_sentence = (
                hidden_record[
                    "sentence"
                ]
            )


            sim = hit[
                "score"
            ]


            relative_degree = (

                degree_score(

                    hidden_sentence,

                    degree_dict

                )

                -

                query_degree

            )


            if sim > threshold:

                hidden_sim += sim

                hidden_degree += (
                    relative_degree
                )

                n += 1


        if n > 0:

            hidden_sim /= n

            hidden_degree /= n


        # ====================================================
        # 8. 保存
        # ====================================================

        results.append({

            "domain": domain,

            "query_file": query_file,

            "match_file": match_file,

            "query": query_sentence,

            "direct_match": direct_match,

            "query_section": (
                query_record[
                    "section"
                ]
            ),

            "match_section": (
                direct_record[
                    "section"
                ]
            ),

            "direct_sim": direct_sim,

            "hidden_sim": hidden_sim,

            "direct_degree": direct_degree,

            "hidden_degree": hidden_degree

        })


    return results


# ============================================================
# 16. Cache 清理
# ============================================================

def clear_embedding_cache():

    _EMBEDDING_CACHE.clear()

    _CSV_CACHE.clear()

    _DEGREE_CACHE.clear()

