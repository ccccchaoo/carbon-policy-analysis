import re
import os
from sentence_transformers import SentenceTransformer

QUERY_PATH = r'data\query'
MATCH_PATH = r'data\match'
STRUCTURED_QUERY_PATH = r'data\structured_query'
STRUCTURED_MATCH_PATH = r'data\structured_match'
DIC_PATH = r'data\dictionary\dictionary.xlsx'
OUTPUT_PATH = r'results'

QUERY_MATCH = {}
DOMAIN = os.listdir(QUERY_PATH)
for domain in DOMAIN:
    query = QUERY_PATH + '\\' + domain
    match = MATCH_PATH + '\\' + domain
    QUERY_MATCH[domain] = (query,match)

space_pattern = r'[\n\t\r\u3000\u200b\u2003\u2002\u2009\u200a\u200c\u200d\u200e\u200f\u2028\u2029\u202f\u205f]+'
sentence_pattern = re.compile(r'[。！？………\n]', re.S)
model = SentenceTransformer("models\paraphrase-multilingual-MiniLM-L12-v2")

