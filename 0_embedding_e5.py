# `2_embedding_e5.py`

import os
import json
import csv
import gc

import numpy as np
import torch
from sentence_transformers import SentenceTransformer


# ============================================================
# 1. 路径配置
# ============================================================

# ------------------------------------------------------------
# multilingual-e5-large 本地模型
# ------------------------------------------------------------

E5_MODEL_PATH = r"models\multilingual-e5-large"


# ------------------------------------------------------------
# 结构化 JSON
# ------------------------------------------------------------

STRUCTURED_QUERY_PATH = r"data\structured_query"

STRUCTURED_MATCH_PATH = r"data\structured_match"


# ------------------------------------------------------------
# Embedding 输出
# ------------------------------------------------------------

EMBEDDING_ROOT = r"data\embeddings"

MODEL_NAME = "multilingual-e5-large"


# ============================================================
# 2. 参数
# ============================================================

BATCH_SIZE = 16

NORMALIZE_EMBEDDINGS = True


# ============================================================
# 3. Device
# ============================================================

if torch.cuda.is_available():
    DEVICE = "cuda"
else:
    DEVICE = "cpu"


print("=" * 70)
print("multilingual-e5-large Embedding Generation")
print("=" * 70)

print(f"Device: {DEVICE}")
print(f"Batch size: {BATCH_SIZE}")
print(f"Normalize embeddings: {NORMALIZE_EMBEDDINGS}")
print()


# ============================================================
# 4. 读取 JSON
# ============================================================

def load_json(json_path):

    with open(
        json_path,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


# ============================================================
# 5. 提取句子
# ============================================================

def extract_sentences(data):

    """
    原始结构：

    {
        "文件名": {
            "章节": {
                "句子": "主题"
            }
        }
    }

    返回：

    [
        {
            "file_name": "...",
            "section": "...",
            "sentence": "..."
        }
    ]
    """

    sentence_items = []

    for file_name, section_dict in data.items():

        if not isinstance(section_dict, dict):
            continue


        for section, sentence_dict in section_dict.items():

            if not isinstance(sentence_dict, dict):
                continue


            for sentence in sentence_dict.keys():

                if not isinstance(sentence, str):
                    continue


                sentence = sentence.strip()


                if not sentence:
                    continue


                sentence_items.append(
                    {
                        "file_name": file_name,
                        "section": section,
                        "sentence": sentence
                    }
                )


    return sentence_items


# ============================================================
# 6. 保存 npy
# ============================================================

def save_embeddings(
    embeddings,
    output_path
):

    embeddings = np.asarray(
        embeddings,
        dtype=np.float32
    )

    np.save(
        output_path,
        embeddings
    )


# ============================================================
# 7. 保存 mapping CSV
# ============================================================

def save_mapping_csv(
    sentence_items,
    output_path
):

    """
    vector_id 与 npy 行号严格对应。

    embeddings[0]
        ↕
    vector_id = 0
    """

    fieldnames = [
        "vector_id",
        "file_name",
        "section",
        "sentence"
    ]


    with open(
        output_path,
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames
        )

        writer.writeheader()


        for vector_id, item in enumerate(
            sentence_items
        ):

            writer.writerow(
                {
                    "vector_id": vector_id,
                    "file_name": item["file_name"],
                    "section": item["section"],
                    "sentence": item["sentence"]
                }
            )


# ============================================================
# 8. 保存 metadata
# ============================================================

def save_metadata(
    source_json,
    embedding_path,
    mapping_path,
    sentence_count,
    embedding_dimension,
    split_type,
    output_path
):

    metadata = {

        "model": MODEL_NAME,

        "source_json": source_json,

        "embedding_file": embedding_path,

        "mapping_file": mapping_path,

        "sentence_count": sentence_count,

        "embedding_dimension": embedding_dimension,

        "dtype": "float32",

        "normalized": NORMALIZE_EMBEDDINGS,

        "task_type": "query_passage",

        "input_prefix": split_type

    }


    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            metadata,
            f,
            ensure_ascii=False,
            indent=4
        )


# ============================================================
# 9. 编码单个 JSON
# ============================================================

def encode_single_json(
    model,
    input_path,
    output_directory,
    split_type
):

    print()
    print("-" * 70)

    print(
        f"Processing: "
        f"{os.path.basename(input_path)}"
    )

    print(
        f"Embedding type: "
        f"{split_type}"
    )


    # --------------------------------------------------------
    # 读取 JSON
    # --------------------------------------------------------

    data = load_json(
        input_path
    )


    # --------------------------------------------------------
    # 提取句子
    # --------------------------------------------------------

    sentence_items = extract_sentences(
        data
    )


    sentence_count = len(
        sentence_items
    )


    if sentence_count == 0:

        print(
            "No sentences found. Skip."
        )

        return


    print(
        f"Sentence count: "
        f"{sentence_count}"
    )


    # --------------------------------------------------------
    # 原始句子
    # --------------------------------------------------------

    sentences = [

        item["sentence"]

        for item in sentence_items

    ]


    # --------------------------------------------------------
    # E5 prefix
    # --------------------------------------------------------

    if split_type == "query":

        encoded_sentences = [

            "query: " + sentence

            for sentence in sentences

        ]

    elif split_type == "passage":

        encoded_sentences = [

            "passage: " + sentence

            for sentence in sentences

        ]

    else:

        raise ValueError(
            "split_type must be "
            "'query' or 'passage'"
        )


    # --------------------------------------------------------
    # Encode
    # --------------------------------------------------------

    print("Encoding...")


    embeddings = model.encode(

        encoded_sentences,

        batch_size=BATCH_SIZE,

        show_progress_bar=True,

        convert_to_numpy=True,

        normalize_embeddings=(
            NORMALIZE_EMBEDDINGS
        )

    )


    embeddings = np.asarray(
        embeddings,
        dtype=np.float32
    )


    print(
        f"Embedding shape: "
        f"{embeddings.shape}"
    )


    embedding_dimension = (
        embeddings.shape[1]
    )


    # --------------------------------------------------------
    # 创建目录
    # --------------------------------------------------------

    os.makedirs(
        output_directory,
        exist_ok=True
    )


    # --------------------------------------------------------
    # 输出文件名
    # --------------------------------------------------------

    base_name = os.path.splitext(
        os.path.basename(input_path)
    )[0]


    embedding_path = os.path.join(
        output_directory,
        base_name + ".npy"
    )


    mapping_path = os.path.join(
        output_directory,
        base_name + ".csv"
    )


    metadata_path = os.path.join(
        output_directory,
        base_name + "_metadata.json"
    )


    # --------------------------------------------------------
    # 保存 embedding
    # --------------------------------------------------------

    save_embeddings(
        embeddings,
        embedding_path
    )


    # --------------------------------------------------------
    # 保存 mapping
    # --------------------------------------------------------

    save_mapping_csv(
        sentence_items,
        mapping_path
    )


    # --------------------------------------------------------
    # 保存 metadata
    # --------------------------------------------------------

    save_metadata(

        source_json=input_path,

        embedding_path=embedding_path,

        mapping_path=mapping_path,

        sentence_count=sentence_count,

        embedding_dimension=embedding_dimension,

        split_type=split_type,

        output_path=metadata_path

    )


    # --------------------------------------------------------
    # 输出
    # --------------------------------------------------------

    print(
        f"Embedding saved: "
        f"{embedding_path}"
    )

    print(
        f"Mapping saved: "
        f"{mapping_path}"
    )

    print(
        f"Metadata saved: "
        f"{metadata_path}"
    )


# ============================================================
# 10. 批量处理目录
# ============================================================

def process_directory(
    model,
    input_directory,
    output_directory,
    split_type
):

    if not os.path.exists(
        input_directory
    ):

        print(
            f"Directory does not exist: "
            f"{input_directory}"
        )

        return


    os.makedirs(
        output_directory,
        exist_ok=True
    )


    json_files = [

        file_name

        for file_name
        in os.listdir(input_directory)

        if file_name.lower().endswith(
            ".json"
        )

    ]


    print()
    print(
        f"Directory: "
        f"{input_directory}"
    )

    print(
        f"JSON files: "
        f"{len(json_files)}"
    )


    for file_name in json_files:

        input_path = os.path.join(
            input_directory,
            file_name
        )


        encode_single_json(

            model=model,

            input_path=input_path,

            output_directory=(
                output_directory
            ),

            split_type=split_type

        )


# ============================================================
# 11. Main
# ============================================================

def main():

    # --------------------------------------------------------
    # 加载 E5
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("Loading multilingual-e5-large")
    print("=" * 70)


    model = SentenceTransformer(

        E5_MODEL_PATH,

        device=DEVICE

    )


    dimension = (
        model.get_sentence_embedding_dimension()
    )


    print(
        f"Embedding dimension: "
        f"{dimension}"
    )


    # --------------------------------------------------------
    # 输出根目录
    # --------------------------------------------------------

    output_root = os.path.join(

        EMBEDDING_ROOT,

        MODEL_NAME

    )


    # ========================================================
    # Query
    # ========================================================

    print()
    print("#" * 70)
    print("# QUERY")
    print("#" * 70)


    process_directory(

        model=model,

        input_directory=(
            STRUCTURED_QUERY_PATH
        ),

        output_directory=os.path.join(

            output_root,

            "structured_query"

        ),

        split_type="query"

    )


    # ========================================================
    # Match / Passage
    # ========================================================

    print()
    print("#" * 70)
    print("# MATCH / PASSAGE")
    print("#" * 70)


    process_directory(

        model=model,

        input_directory=(
            STRUCTURED_MATCH_PATH
        ),

        output_directory=os.path.join(

            output_root,

            "structured_match"

        ),

        split_type="passage"

    )


    # --------------------------------------------------------
    # 释放模型
    # --------------------------------------------------------

    del model

    gc.collect()


    if torch.cuda.is_available():

        torch.cuda.empty_cache()


    print()
    print("=" * 70)
    print("multilingual-e5-large finished.")
    print("=" * 70)


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":

    main()

