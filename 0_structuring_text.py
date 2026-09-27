import json
import os
from utils import get_files, packaging_for_search
from config import QUERY_MATCH, DOMAIN, STRUCTURED_QUERY_PATH, STRUCTURED_MATCH_PATH

for domain in DOMAIN:
    domain_name = domain + ".json"
    query_path = os.path.join(STRUCTURED_QUERY_PATH, domain_name)
    match_path = os.path.join(STRUCTURED_MATCH_PATH, domain_name)
    
    # Check if both files already exist
    if os.path.exists(query_path) and os.path.exists(match_path):
        print(f"Files for domain {domain} already exist, skipping...")
        continue
    
    query_file_dic = get_files(QUERY_MATCH[domain][0])  # 获取中央的政策文件
    match_file_dic = get_files(QUERY_MATCH[domain][1])  # 获取地方的政策文件

    query_items = packaging_for_search(query_file_dic)
    match_items = packaging_for_search(match_file_dic)

    with open(query_path, 'w', encoding='utf-8') as f:
        json.dump(query_items, f, ensure_ascii=False, indent=4)
    with open(match_path, 'w', encoding='utf-8') as f:
        json.dump(match_items, f, ensure_ascii=False, indent=4)