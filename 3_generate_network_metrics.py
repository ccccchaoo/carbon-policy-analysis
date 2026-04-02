import os
import json
import pandas as pd
from tqdm import tqdm  
from config import DIC_PATH, OUTPUT_PATH, DOMAIN, STRUCTURED_QUERY_PATH, STRUCTURED_MATCH_PATH
from utils import selective_execution_analysis
import statistics

TIME_ORDER_PATH = "data/time_order.xlsx"

time_order_cache = {}

def load_time_order_for_domain(domain):
    if domain not in time_order_cache:
        try:
            df_time = pd.read_excel(TIME_ORDER_PATH, sheet_name=domain)
            time_order_cache[domain] = df_time
        except Exception as e:
            print(f"警告: 无法加载时序信息表 {domain}, 错误: {e}")
            time_order_cache[domain] = pd.DataFrame(columns=['local', 'timeorder'])
    return time_order_cache[domain]

def get_time_order(region_name, time_df):
    if len(region_name) >= 2:
        prefix = region_name[:2]
        

        for _, row in time_df.iterrows():
            if isinstance(row['local'], str) and len(row['local']) >= 2:
                if row['local'][:2] == prefix:
                    return row['timeorder']
    

    central_match = time_df[time_df['local'] == '中央']
    if not central_match.empty:
        return central_match.iloc[0]['timeorder']
    

    return float('inf')

for domain in DOMAIN:

    print(f"start genrating {domain}")

    time_df = load_time_order_for_domain(domain)

    filenames = []
    locscores = []
    stdscores = []

    with open(STRUCTURED_MATCH_PATH + f'\{domain}.json', 'r', encoding='utf-8') as file:
        query_items = json.load(file)
    with open(STRUCTURED_MATCH_PATH + f'\{domain}.json', 'r', encoding='utf-8') as file:
        match_items = json.load(file)

    filenames = list(match_items.keys())
    df_direct_sim = pd.DataFrame(index=filenames, columns=list(query_items.keys()))
    df_hidden_sim = pd.DataFrame(index=filenames, columns=list(query_items.keys()))
    df_direct_deg = pd.DataFrame(index=filenames, columns=list(query_items.keys()))
    df_hidden_deg = pd.DataFrame(index=filenames, columns=list(query_items.keys()))

    time_orders = {}
    for filename in filenames:
        time_orders[filename] = get_time_order(filename, time_df)


    for referenced, query_dic in tqdm(query_items.items(), desc="query进度",unit="文件",position=0):
        direct_sims=[]
        hidden_sims=[]
        direct_degrees=[]
        hidden_degrees=[]

        referenced_time = time_orders.get(referenced, float('inf'))
        #std_senteces = selective_execution_analysis(file, query_dic, query_dic, DIC_PATH,topk=10,threshold=0.5)

        for referencing, match_dic in tqdm(match_items.items(),desc="match进度",unit="文件",position=1):

            referencing_time = time_orders.get(referencing, float('inf'))
            if referenced_time < referencing_time:
                sentences = selective_execution_analysis(referencing, match_dic, query_dic, DIC_PATH,topk=10,threshold=0.5)
                #for i,sentence in enumerate(sentences):
                    #sentence['hidden_sim'] = sentence['hidden_sim']/((std_senteces[i])['hidden_sim'])
                    #sentence['hidden_degree'] = sentence['hidden_degree'] - ((std_senteces[i])['hidden_degree'])

                avg_direct_sim = statistics.mean(s['direct_sim'] for s in sentences)
                #avg_hidden_sim = statistics.mean(s['hidden_sim'] for s in sentences)
                avg_direct_degree = statistics.mean(s['direct_degree'] for s in sentences)
                #avg_hidden_degree = statistics.mean(s['hidden_degree'] for s in sentences)

                direct_sims.append(avg_direct_sim)
                #hidden_sims.append(avg_hidden_sim)
                direct_degrees.append(avg_direct_degree)
                #hidden_degrees.append(avg_hidden_degree)
                #"""
            else:
                direct_sims.append(0.0)
                direct_degrees.append(0.0)

        df_direct_sim[referenced]= direct_sims
        #df_hidden_sim[referenced]= hidden_sims
        df_direct_deg[referenced]= direct_degrees
        #df_hidden_deg[referenced]= hidden_degrees

    output = os.path.join("results/metrics",f"{domain}_metric.xlsx")

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_direct_sim.to_excel(writer, sheet_name='direct_sim', index=True)
        #df_hidden_sim.to_excel(writer, sheet_name='hidden_sim', index=True)
        df_direct_deg.to_excel(writer, sheet_name='direct_deg', index=True)
        #df_hidden_deg.to_excel(writer, sheet_name='hidden_deg', index=True)