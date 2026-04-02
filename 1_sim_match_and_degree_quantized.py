import os
import json
import pandas as pd
from tqdm import tqdm  
from config import DIC_PATH, OUTPUT_PATH, DOMAIN, STRUCTURED_QUERY_PATH, STRUCTURED_MATCH_PATH
from utils import selective_execution_analysis

def main():
    for domain in DOMAIN:

        output_path = r"results\sentences"

        output_sentences = output_path + f'\{domain}_senteces.xlsx' 

        if os.path.exists(output_sentences):
            print(f"Files for domain {domain} already exist, skipping...")
            continue
        
        with open(STRUCTURED_QUERY_PATH + f'\{domain}.json', 'r', encoding='utf-8') as file:
            query_items = json.load(file)
        with open(STRUCTURED_MATCH_PATH + f'\{domain}.json', 'r', encoding='utf-8') as file:
            match_items = json.load(file)
        
        
        query_dic = list(query_items.values())[0]  
        sentences_lists = []
        articles = []

        print("\nstart...")
       
        std_senteces = selective_execution_analysis(file, query_dic, query_dic, DIC_PATH,topk=10,threshold=0.5)

        for file, match_dic in tqdm(match_items.items(), desc="progress", unit="documents"):

            sentences = selective_execution_analysis(file, match_dic, query_dic, DIC_PATH,topk=10,threshold=0.5)
            for i,sentence in enumerate(sentences):
                sentence['hidden_sim'] = sentence['hidden_sim']/((std_senteces[i])['hidden_sim'])
                sentence['hidden_degree'] = sentence['hidden_degree'] - ((std_senteces[i])['hidden_degree'])
            sentences_lists.extend(sentences)

        print("\nsaving...")
        df = pd.DataFrame(sentences_lists)
        df.to_excel(output_sentences, index=False, engine='openpyxl')    

        print(f"\nFinish, results are saved in {output_sentences} ")

if __name__ == "__main__":
    main()