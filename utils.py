import os
import pandas as pd
import pdfplumber
import docx
import re
import jieba
from config import space_pattern, sentence_pattern, model
from sentence_transformers import util
from collections import defaultdict


def get_dirs(parent_dir: str):
    child_dirs = os.listdir(parent_dir)
    # 删除word、excel、txt格式的文件
    child_dirs = [child_dir for child_dir in child_dirs if '.' not in child_dir]
    if child_dirs == []:
        print(f'Error: No folder in {dir}')
    return child_dirs

# 读取.pdf .docx .txt文件
def read_file(path: str):
    # 读取pdf文件
    content = ''
    if path.split('.')[-1] == 'pdf':
        with pdfplumber.open(path) as pdf:
            content = ''
            for page in pdf.pages:
                content += page.extract_text()
    # 读取word文件，docx格式
    elif path.split('.')[-1] == 'docx':
        doc = docx.Document(path)
        content = ''
        for para in doc.paragraphs:
            content += para.text +'\n'  #仅在这句代码上进行修改
    # 读取txt文件
    elif path.split('.')[-1] == 'txt':
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
    return content

# 获取文件夹下的所有文本文件(.pdf, .docx, .txt)，返回字典{文件名: 内容}
def get_files(parent_dir: str):
    dirs = [parent_dir]
    file_path_dic = {}
    while dirs != []:
        parent_dir = dirs.pop()
        new_dirs_and_files = os.listdir(parent_dir)
        new_files = [new_file for new_file in new_dirs_and_files if '.' in new_file and new_file.split('.')[-1] in
             ['pdf', 'docx']]
        file_path_dic.update({file: parent_dir + '/' + file for file in new_files})
        new_dirs = [parent_dir + '/' + new_child_dirs for new_child_dirs in new_dirs_and_files if '.' not in new_child_dirs]
        dirs += new_dirs
    # 删除文件夹，只保留word、pdf、txt文件
    files_dic = {}
    if file_path_dic.keys() == []:
        print(f'Warning: No file in {parent_dir}')
    else:
        for file, path in file_path_dic.items():
            files_dic[file] = read_file(path)
    return files_dic

# 实现按上级标题分段，用于sbert
def divide_by_subheadings(text: str):
    """
    text：str，进行分段的文本
    输出：元组列表，[(段落文本，对应的上级标题),...]，按最低级标题进行分段，每个分段记录了其上级标题
    """
    pattern1 = re.compile(r'^[一二三四五六七八九十百千万]+\、')  # "一、标题内容"
    pattern2 = re.compile(r'^\（[一二三四五六七八九十百千万]+\）')  # "（三）标题内容"

    segments = []
    current_segment = []
    headings = '空、无上级标题'   #记录上级标题

    lines = re.split(space_pattern, text)

    for line in lines:
        if pattern1.match(line) and not current_segment:#上级标题，且当前无current存储
            headings = line
        elif pattern1.match(line) and current_segment:#上级标题，有current，写入current
            segments.append(('\n'.join(current_segment),headings))
            current_segment = []
            headings = line
        elif pattern2.match(line):
            if current_segment:#下级标题，有current，写入
                segments.append(('\n'.join(current_segment),headings))
                current_segment = []
            current_segment.append(line)#下级标题，无current，添加current
        else:#正文，添加current
            current_segment.append(line)
    if current_segment: #处理最后一段
        segments.append(('\n'.join(current_segment),headings))

    return segments

def packaging_for_search(files_dic: dict):
    """
    Args: files_dic: {文件名: 文本内容}    
    Returns:{文件: {段落号: {句子: 段落标题}}}  # 同seg下的多个segment已合并
    """
    result = {}
    for file, context in files_dic.items():
        file_dict = defaultdict(dict)  
        
        for segment in divide_by_subheadings(context):

            parts = segment[1].split("、", 1)
            seg = parts[0].strip() if parts else ""
            theme = parts[1] if len(parts) > 1 else "无标题"
            
            #sentences = [s.strip() for s in re.split(sentence_pattern, segment[0].replace("\n", "")) if s.strip()]
            # 先对段落文本做子标题断句增强
            text = segment[0]
            # 在常见的子标题模式前插入换行（确保它们成为独立行）
            # 支持：（一）、（1）、1.、1）、(1) 等
            text = re.sub(r'(?<!\n)([（(]\s*[一二三四五六七八九十\d]+\s*[\）\)\.]\s*[^\s])', r'\n\1',text)
            cleaned_text = text.replace('"', '').replace('“', '').replace('”', '')
            # 再按句子切分
            sentences = [s.strip() for s in re.split(sentence_pattern, cleaned_text) if s.strip()]

            file_dict[seg].update({sentence: theme for sentence in sentences})
        
        result[file] = dict(file_dict)
    
    return result

def degree_score(sentence, degree_dict):
    """
    计算句子的语义程度得分。
    :param sentence: 输入的句子
    :param degree_dict: 语义程度字典文件路径
    :return: 语义程度得分
    """
    df = pd.read_excel(degree_dict)
    score_dict = dict(zip(df.iloc[:, 0], df.iloc[:, 1]))
    score = 0
    words = jieba.lcut(sentence)
    for word in words:
        if word in score_dict:
            score += score_dict[word]
    return score


def selective_execution_analysis_with_structure(file, match_dict, query_dict, degree_dict, topk = 1, threshold = 0.6):
    """
    分析文本中的选择性执行现象。
    :param file: 文件名
    :param match_dict: 匹配句子字典，格式为 {段落号: {句子: 段落标题,...},...}
    :param query_dict: 查询句子字典，格式为 {段落号: {句子: 段落标题}}
    :param degree_dict: 语义程度字典文件路径
    :return: 文本逐句信息列表, 文章总体信息
    """

    sentences = []  # 文本逐句信息

    for seg in query_dict.keys():
        query_sentences = list((query_dict[seg]).keys())
        if seg in match_dict:
            match_sentences = list((match_dict[seg]).keys())
            if '零' in match_dict:
                match_sentences.extend(list((match_dict['零']).keys()))

            match_embeddings = model.encode(match_sentences)

            for i, query in enumerate(query_sentences):
                query_embedding = model.encode(query, convert_to_tensor=True)
                hits = util.semantic_search(query_embedding, match_embeddings, top_k=topk)
                hits_for_current_query = hits[0]    # 取消张量，[[]]

                direct_hit = hits_for_current_query[0]
                direct_match = match_sentences[direct_hit['corpus_id']]
                direct_sim = direct_hit['score']
                match_structure = (seg, match_dict[seg][direct_match])
                query_structure = (seg, query_dict[seg][query])
                direct_degree = degree_score(direct_match, degree_dict) - degree_score(query, degree_dict)

                n = 0
                hidden_sim = 0
                hidden_degree = 0
                for hit in hits_for_current_query:  #topk = 1, 一轮
                    match = match_sentences[hit['corpus_id']]

                    sim = hit["score"]
                    relative_degree = degree_score(match, degree_dict) - degree_score(query, degree_dict)

                    if sim > threshold:
                        hidden_sim += sim
                        hidden_degree += relative_degree
                        n += 1
                
                hidden_sim = hidden_sim / n if n != 0 else 0
                hidden_degree = hidden_degree / n if n != 0 else 0

                sentence = {
                    "file": file,
                    "query": query,
                    "direct_match": direct_match,
                    "query_structure": query_structure,
                    "match_structure": match_structure,
                    "direct_sim": direct_sim,
                    "hidden_sim": hidden_sim,
                    "direct_degree": direct_degree,
                    "hidden_degree": hidden_degree,
                }

                sentences.append(sentence)

        else:
            for i, query in enumerate(query_sentences):
                query_structure = (seg, query_dict[seg][query])
                sentence = {
                    "file": file,
                    "query": query,
                    "direct_match": None,
                    "query_structure": query_structure,
                    "match_structure": None,
                    "direct_sim": 0,
                    "hidden_sim": 0,
                    "direct_degree": 0,
                    "hidden_degree": 0,
                }

                sentences.append(sentence)
            
    return sentences


def selective_execution_analysis(file, match_dict, query_dict, degree_dict, topk=1, threshold=0.6):
    """
    分析文本中的选择性执行现象。
    :param file: 文件名
    :param match_dict: 匹配句子字典，格式为 {段落号: {句子: 段落标题,...},...}
    :param query_dict: 查询句子字典，格式为 {段落号: {句子: 段落标题}}
    :param degree_dict: 语义程度字典文件路径
    :return: 文本逐句信息列表
    """

    sentences = []  # 文本逐句信息
    
    # 预处理：构建全文本的匹配句子列表和映射关系
    all_match_sentences = []  # 所有匹配句子
    sentence_to_segment = {}  # 句子到段落的映射
    
    for seg in match_dict.keys():
        for sentence in match_dict[seg].keys():
            all_match_sentences.append(sentence)
            sentence_to_segment[sentence] = seg
    
    # 编码所有匹配句子
    match_embeddings = model.encode(all_match_sentences)

    for seg in query_dict.keys():
        query_sentences = list((query_dict[seg]).keys())

        for i, query in enumerate(query_sentences):
            query_embedding = model.encode(query, convert_to_tensor=True)
            hits = util.semantic_search(query_embedding, match_embeddings, top_k=topk)
            hits_for_current_query = hits[0]

            direct_hit = hits_for_current_query[0]
            direct_match = all_match_sentences[direct_hit['corpus_id']]
            direct_sim = direct_hit['score']
            
            # 通过映射找到匹配句子所在的段落
            match_seg = sentence_to_segment[direct_match]
            match_structure = (match_seg, match_dict[match_seg][direct_match])
            query_structure = (seg, query_dict[seg][query])
            direct_degree = degree_score(direct_match, degree_dict) - degree_score(query, degree_dict)

            n = 0
            hidden_sim = 0
            hidden_degree = 0
            for hit in hits_for_current_query:  # topk = 1, 一轮
                match = all_match_sentences[hit['corpus_id']]
                sim = hit["score"]
                relative_degree = degree_score(match, degree_dict) - degree_score(query, degree_dict)

                if sim > threshold:
                    hidden_sim += sim
                    hidden_degree += relative_degree
                    n += 1
            
            hidden_sim = hidden_sim / n if n != 0 else 0
            hidden_degree = hidden_degree / n if n != 0 else 0

            sentence = {
                "file": file,
                "query": query,
                "direct_match": direct_match,
                "query_structure": query_structure,
                "match_structure": match_structure,
                "direct_sim": direct_sim,
                "hidden_sim": hidden_sim,
                "direct_degree": direct_degree,
                "hidden_degree": hidden_degree,
            }

            sentences.append(sentence)
            
    return sentences