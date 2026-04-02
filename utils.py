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

    child_dirs = [child_dir for child_dir in child_dirs if '.' not in child_dir]
    if child_dirs == []:
        print(f'Error: No folder in {dir}')
    return child_dirs


def read_file(path: str):

    content = ''
    if path.split('.')[-1] == 'pdf':
        with pdfplumber.open(path) as pdf:
            content = ''
            for page in pdf.pages:
                content += page.extract_text()

    elif path.split('.')[-1] == 'docx':
        doc = docx.Document(path)
        content = ''
        for para in doc.paragraphs:
            content += para.text +'\n'  

    elif path.split('.')[-1] == 'txt':
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
    return content


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

    files_dic = {}
    if file_path_dic.keys() == []:
        print(f'Warning: No file in {parent_dir}')
    else:
        for file, path in file_path_dic.items():
            files_dic[file] = read_file(path)
    return files_dic


def divide_by_subheadings(text: str):

    pattern1 = re.compile(r'^[一二三四五六七八九十百千万]+\、')  # "一、标题内容"
    pattern2 = re.compile(r'^\（[一二三四五六七八九十百千万]+\）')  # "（三）标题内容"

    segments = []
    current_segment = []
    headings = '空、无上级标题'   

    lines = re.split(space_pattern, text)

    for line in lines:
        if pattern1.match(line) and not current_segment:
            headings = line
        elif pattern1.match(line) and current_segment:
            segments.append(('\n'.join(current_segment),headings))
            current_segment = []
            headings = line
        elif pattern2.match(line):
            if current_segment:
                segments.append(('\n'.join(current_segment),headings))
                current_segment = []
            current_segment.append(line)
        else:
            current_segment.append(line)
    if current_segment: 
        segments.append(('\n'.join(current_segment),headings))

    return segments

def packaging_for_search(files_dic: dict):
    """
    Args: files_dic: {document name: text context}    
    Returns:{document: {section number: {sentence: section title}}}  
    """
    result = {}
    for file, context in files_dic.items():
        file_dict = defaultdict(dict)  
        
        for segment in divide_by_subheadings(context):

            parts = segment[1].split("、", 1)
            seg = parts[0].strip() if parts else ""
            theme = parts[1] if len(parts) > 1 else "无标题"
            
            #sentences = [s.strip() for s in re.split(sentence_pattern, segment[0].replace("\n", "")) if s.strip()]
           
            text = segment[0]

            text = re.sub(r'(?<!\n)([（(]\s*[一二三四五六七八九十\d]+\s*[\）\)\.]\s*[^\s])', r'\n\1',text)
            cleaned_text = text.replace('"', '').replace('“', '').replace('”', '')

            sentences = [s.strip() for s in re.split(sentence_pattern, cleaned_text) if s.strip()]

            file_dict[seg].update({sentence: theme for sentence in sentences})
        
        result[file] = dict(file_dict)
    
    return result

def degree_score(sentence, degree_dict):

    df = pd.read_excel(degree_dict)
    score_dict = dict(zip(df.iloc[:, 0], df.iloc[:, 1]))
    score = 0
    words = jieba.lcut(sentence)
    for word in words:
        if word in score_dict:
            score += score_dict[word]
    return score


def selective_execution_analysis_with_structure(file, match_dict, query_dict, degree_dict, topk = 1, threshold = 0.6):

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
                hits_for_current_query = hits[0]    

                direct_hit = hits_for_current_query[0]
                direct_match = match_sentences[direct_hit['corpus_id']]
                direct_sim = direct_hit['score']
                match_structure = (seg, match_dict[seg][direct_match])
                query_structure = (seg, query_dict[seg][query])
                direct_degree = degree_score(direct_match, degree_dict) - degree_score(query, degree_dict)

                n = 0
                hidden_sim = 0
                hidden_degree = 0
                for hit in hits_for_current_query:  #topk = 1
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

    sentences = []  
    

    all_match_sentences = [] 
    sentence_to_segment = {} 
    
    for seg in match_dict.keys():
        for sentence in match_dict[seg].keys():
            all_match_sentences.append(sentence)
            sentence_to_segment[sentence] = seg
    

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
            

            match_seg = sentence_to_segment[direct_match]
            match_structure = (match_seg, match_dict[match_seg][direct_match])
            query_structure = (seg, query_dict[seg][query])
            direct_degree = degree_score(direct_match, degree_dict) - degree_score(query, degree_dict)

            n = 0
            hidden_sim = 0
            hidden_degree = 0
            for hit in hits_for_current_query:  # topk = 1
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