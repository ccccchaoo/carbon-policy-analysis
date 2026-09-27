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
# 本地模型
# ------------------------------------------------------------

BGE_MODEL_PATH = r"models\bge-m3"
MINILM_MODEL_PATH = r"models\paraphrase-multilingual-MiniLM-L12-v2"


# ------------------------------------------------------------
# 结构化 JSON
# ------------------------------------------------------------

STRUCTURED_QUERY_PATH = r"data\structured_query"
STRUCTURED_MATCH_PATH = r"data\structured_match"


# ------------------------------------------------------------
# Embedding 输出根目录
# ------------------------------------------------------------

EMBEDDING_ROOT = r"data\embeddings"


# ============================================================
# 2. Embedding 参数
# ============================================================

# 每批处理多少句话
BATCH_SIZE = 32


# 是否进行 L2 normalization
#
# True:
#       后续可以直接用向量点积计算 cosine similarity
#
# False:
#       保存模型原始 embedding
#
NORMALIZE_EMBEDDINGS = True


# 是否保存句子文本
#
# CSV 中保存：
#
# vector_id
# file_name
# section
# sentence
#
SAVE_SENTENCE_TEXT = True


# ============================================================
# 3. 自动选择设备
# ============================================================

if torch.cuda.is_available():

    DEVICE = "cuda"

else:

    DEVICE = "cpu"


print("=" * 70)
print("Embedding Generation")
print("=" * 70)

print(f"Device: {DEVICE}")
print(f"Batch size: {BATCH_SIZE}")
print(
    f"Normalize embeddings: "
    f"{NORMALIZE_EMBEDDINGS}"
)

print()


# ============================================================
# 4. 读取 JSON
# ============================================================

def load_json(json_path):

    """
    读取结构化 JSON。
    """

    with open(
        json_path,
        "r",
        encoding="utf-8"
    ) as f:

        data = json.load(f)

    return data


# ============================================================
# 5. 提取句子
# ============================================================

def extract_sentences(data):

    """
    从你的结构化 JSON 中提取句子。

    原始 JSON 结构：

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
        },
        ...
    ]

    注意：

    不使用 sentence 本身作为唯一 key。

    因为不同文件/章节可能存在相同句子。

    """

    sentence_items = []

    for file_name, section_dict in data.items():

        if not isinstance(
            section_dict,
            dict
        ):
            continue


        for section, sentence_dict in section_dict.items():

            if not isinstance(
                sentence_dict,
                dict
            ):
                continue


            for sentence in sentence_dict.keys():

                if not isinstance(
                    sentence,
                    str
                ):
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
# 6. 保存 embedding matrix
# ============================================================

def save_embeddings(
    embeddings,
    output_path
):

    """
    保存 embedding matrix 到 .npy。

    shape:

        (sentence_count, embedding_dimension)

    """

    embeddings = np.asarray(
        embeddings,
        dtype=np.float32
    )


    np.save(
        output_path,
        embeddings
    )


# ============================================================
# 7. 保存 vector_id 映射表
# ============================================================

def save_mapping_csv(
    sentence_items,
    output_path
):

    """
    保存：

        vector_id
        file_name
        section
        sentence

    的对应关系。

    vector_id 对应 .npy 中的行号。

    例如：

        vector_id = 0

    就表示：

        embeddings[0]

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
# 8. 保存 metadata JSON
# ============================================================

def save_metadata(
    model_name,
    source_json,
    embedding_path,
    mapping_path,
    sentence_count,
    embedding_dimension,
    output_path
):

    """
    保存 embedding 的元数据。

    这个文件非常小，不存实际向量。
    """

    metadata = {

        "model": model_name,

        "source_json": source_json,

        "embedding_file": embedding_path,

        "mapping_file": mapping_path,

        "sentence_count": sentence_count,

        "embedding_dimension": embedding_dimension,

        "dtype": "float32",

        "normalized": NORMALIZE_EMBEDDINGS

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
# 9. 编码一个 JSON
# ============================================================

def encode_single_json(
    model,
    model_name,
    input_path,
    output_directory,
    batch_size=BATCH_SIZE
):

    """
    对一个 JSON 文件进行 embedding。

    最终产生三个文件：

        xxx.npy
        xxx.csv
        xxx_metadata.json
    """

    print()
    print("-" * 70)

    print(
        f"Processing: "
        f"{os.path.basename(input_path)}"
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
            "No sentences found. "
            "Skip."
        )

        return


    print(
        f"Sentence count: "
        f"{sentence_count}"
    )


    # --------------------------------------------------------
    # 获得 sentence list
    # --------------------------------------------------------

    sentences = [

        item["sentence"]

        for item in sentence_items

    ]


    # --------------------------------------------------------
    # SentenceTransformer encoding
    # --------------------------------------------------------

    print("Encoding...")


    embeddings = model.encode(

        sentences,

        batch_size=batch_size,

        show_progress_bar=True,

        convert_to_numpy=True,

        normalize_embeddings=(
            NORMALIZE_EMBEDDINGS
        )

    )


    # --------------------------------------------------------
    # 转换为 float32
    # --------------------------------------------------------

    embeddings = np.asarray(

        embeddings,

        dtype=np.float32

    )


    # --------------------------------------------------------
    # 检查 embedding shape
    # --------------------------------------------------------

    embedding_dimension = (
        embeddings.shape[1]
    )


    print(
        f"Embedding shape: "
        f"{embeddings.shape}"
    )


    # --------------------------------------------------------
    # 创建输出目录
    # --------------------------------------------------------

    os.makedirs(

        output_directory,

        exist_ok=True

    )


    # --------------------------------------------------------
    # 文件名
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

        model_name=model_name,

        source_json=input_path,

        embedding_path=embedding_path,

        mapping_path=mapping_path,

        sentence_count=sentence_count,

        embedding_dimension=embedding_dimension,

        output_path=metadata_path

    )


    # --------------------------------------------------------
    # 输出信息
    # --------------------------------------------------------

    print(
        f"Embedding saved : "
        f"{embedding_path}"
    )

    print(
        f"Mapping saved   : "
        f"{mapping_path}"
    )

    print(
        f"Metadata saved  : "
        f"{metadata_path}"
    )


    # --------------------------------------------------------
    # 检查文件大小
    # --------------------------------------------------------

    embedding_size_mb = (

        os.path.getsize(
            embedding_path
        )

        / 1024
        / 1024

    )


    print(
        f"Embedding size  : "
        f"{embedding_size_mb:.2f} MB"
    )


# ============================================================
# 10. 批量处理一个目录
# ============================================================

def process_directory(
    model,
    model_name,
    input_directory,
    output_directory,
    batch_size=BATCH_SIZE
):

    """
    处理目录下所有 JSON。
    """

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

            model_name=model_name,

            input_path=input_path,

            output_directory=(
                output_directory
            ),

            batch_size=batch_size

        )


# ============================================================
# 11. 加载模型
# ============================================================

def load_model(
    model_path
):

    """
    使用 SentenceTransformer
    加载本地模型。
    """

    print()
    print("=" * 70)

    print(
        f"Loading model: "
        f"{model_path}"
    )

    print("=" * 70)


    model = SentenceTransformer(

        model_path,

        device=DEVICE

    )


    dimension = (

        model.get_sentence_embedding_dimension()

    )


    print(
        "Model loaded successfully."
    )

    print(
        f"Embedding dimension: "
        f"{dimension}"
    )

    return model


# ============================================================
# 12. BGE-M3
# ============================================================

def run_bge_m3():

    model_name = "bge-m3"


    model = load_model(

        BGE_MODEL_PATH

    )


    output_root = os.path.join(

        EMBEDDING_ROOT,

        model_name

    )


    # --------------------------------------------------------
    # Query
    # --------------------------------------------------------

    process_directory(

        model=model,

        model_name=model_name,

        input_directory=(
            STRUCTURED_QUERY_PATH
        ),

        output_directory=os.path.join(

            output_root,

            "structured_query"

        )

    )


    # --------------------------------------------------------
    # Match
    # --------------------------------------------------------

    process_directory(

        model=model,

        model_name=model_name,

        input_directory=(
            STRUCTURED_MATCH_PATH
        ),

        output_directory=os.path.join(

            output_root,

            "structured_match"

        )

    )


    # --------------------------------------------------------
    # 释放模型
    # --------------------------------------------------------

    del model

    gc.collect()


    if torch.cuda.is_available():

        torch.cuda.empty_cache()


# ============================================================
# 13. paraphrase-multilingual-MiniLM-L12-v2
# ============================================================

def run_minilm():

    model_name = (
        "paraphrase-multilingual-MiniLM-L12-v2"
    )


    model = load_model(

        MINILM_MODEL_PATH

    )


    output_root = os.path.join(

        EMBEDDING_ROOT,

        model_name

    )


    # --------------------------------------------------------
    # Query
    # --------------------------------------------------------

    process_directory(

        model=model,

        model_name=model_name,

        input_directory=(
            STRUCTURED_QUERY_PATH
        ),

        output_directory=os.path.join(

            output_root,

            "structured_query"

        )

    )


    # --------------------------------------------------------
    # Match
    # --------------------------------------------------------

    process_directory(

        model=model,

        model_name=model_name,

        input_directory=(
            STRUCTURED_MATCH_PATH
        ),

        output_directory=os.path.join(

            output_root,

            "structured_match"

        )

    )


    # --------------------------------------------------------
    # 释放模型
    # --------------------------------------------------------

    del model

    gc.collect()


    if torch.cuda.is_available():

        torch.cuda.empty_cache()


# ============================================================
# 14. Main
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 70)
    print("START")
    print("=" * 70)


    # ========================================================
    # BGE-M3
    # ========================================================

    print()
    print("#" * 70)
    print("# BGE-M3")
    print("#" * 70)


    run_bge_m3()


    # ========================================================
    # MiniLM
    # ========================================================

    print()
    print("#" * 70)
    print(
        "# paraphrase-multilingual-MiniLM-L12-v2"
    )
    print("#" * 70)


    run_minilm()


    # ========================================================
    # Finish
    # ========================================================

    print()
    print("=" * 70)
    print("ALL EMBEDDINGS GENERATED")
    print("=" * 70)