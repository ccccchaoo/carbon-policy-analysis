import json
import pandas as pd
from config import DIC_PATH, OUTPUT_PATH, DOMAIN, STRUCTURED_QUERY_PATH, STRUCTURED_MATCH_PATH
import os
from openai import OpenAI


# API（deepseek, zhipu, qwen）
API_CHOICE = "qwen"  
MODEL = "Moonshot-Kimi-K2-Instruct" #deepseek-v3.2, deepseek-r1, qwen3-max, qwen-plus, kimi-k2-thinking, glm-4.7, Moonshot-Kimi-K2-Instruct


DEEPSEEK_CONFIG = {
    "api_key": "your_deepseek_api_key_here",# 替换为你的DeepSeekAPI密钥
    "base_url": "https://api.deepseek.com",
    "model": "deepseek-reasoner"
}


ZHIPU_CONFIG = {
    "api_key": "your_zhipu_api_key_here",  # 替换为你的智谱API密钥
    "base_url": "https://open.bigmodel.cn/api/paas/v4/",
    "model": "glm-4-plus"  # 或 "glm-4-flash", "glm-4-long"
}


QWEN_CONFIG = {
    "api_key": "your_qwen_api_key_here",  # 替换为你的通义千问API密钥
    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "model": MODEL  # 或 "qwen-plus", "qwen-turbo"
}


if API_CHOICE == "deepseek":
    client = OpenAI(
        api_key=DEEPSEEK_CONFIG["api_key"],
        base_url=DEEPSEEK_CONFIG["base_url"]
    )
elif API_CHOICE == "zhipu":
    client = OpenAI(
        api_key=ZHIPU_CONFIG["api_key"],
        base_url=ZHIPU_CONFIG["base_url"]
    )
elif API_CHOICE == "qwen":
    client = OpenAI(
        api_key=QWEN_CONFIG["api_key"],
        base_url=QWEN_CONFIG["base_url"]
    )
else:
    raise ValueError(f"不支持的API选择: {API_CHOICE}")

def get_model_name():
    """获取对应API的模型名称"""
    if API_CHOICE == "deepseek":
        return DEEPSEEK_CONFIG["model"]
    elif API_CHOICE == "zhipu":
        return ZHIPU_CONFIG["model"]
    elif API_CHOICE == "qwen":
        return QWEN_CONFIG["model"]
    else:
        return "unknown"

def construct_prompt(referenced_sentence, referencing_sentence):
    """构造prompt（保持不变）"""
    prompt = f"""你是一个专业的中国政策文本分析专家，精通政策语言的特征、强度层级和语义分析。现在，你需要根据给定的输入，严格按步骤完成两项核心任务。

【核心任务】
1.  **相似度评估任务**：评估每个 `referenced` 和 `referencing` 政策文本句子对的相似程度。
2.  **态度比较任务**：对每一对句子，精准分析 `referencing` 句子相对于 `referenced` 句子的态度强弱。

【输入文本】
referenced，referencing句子对:
referenced:{referenced_sentence}
referencing:{referencing_sentence}

【任务执行规则（必须严格遵守）】

**步骤1：相似度分析**
- **遍历与必选**：必须按顺序遍历每一个句子对，并给出两个句子相似度的打分。 
- **原则**：
  - **语义核心优先**：应基于句子表达的**核心政策意图、主体、对象和行动**，而非表面的词汇重叠。
- **相似程度**：
  使用以下三级分类标准进行分析：
  0：完全不同
  1：略有关联
  2：高度相似


**步骤2：科学态度强度分析**
使用以下三级分类标准进行分析，判断必须基于具体的政策措辞：

- **态度强化（返回 `1`）**：`referencing` 句子在 `referenced` 句子的态度基础上，出现以下一种或多种情况：
  - **强度词汇升级**：如"鼓励" → "大力支持"，"完善" → "建立健全"。
  - **目标要求提高**：如"降低能耗" → "显著降低能耗"，"推进" → "全面推进"。
  - **执行力度加大**：如"探索" → "加快实施"，"研究" → "制定并落实"。
  - **时限或范围收紧**：增加"限期"、"全域"等限定词。

- **态度弱化（返回 `-1`）**：`referencing` 句子在 `referenced` 句子的态度基础上，出现以下一种或多种情况：
  - **强度词汇降级**：如"确保" → "力争"，"严格执行" → "提倡"。
  - **目标要求放宽**：如"消除" → "减少"，"全面完成" → "有序推进"。
  - **表述转为柔性**：增加"条件成熟时"、"积极探索"等不确定性表述。

- **态度相同（返回 `0`）**：核心态度与执行要求完全一致。

-**不相关（返回`2`）**：两句话的**语义核心发生实质性改变**，不具备可比性。



**中国政策语言强度层级参考（从强到弱）**
1.  **强制命令层**：必须、确保、严禁、一律、杜绝、坚决。
2.  **强力推进层**：大力推进、深化、全面落实、加快实施、强化。
3.  **鼓励引导层**：支持、鼓励、促进、完善、引导、加强。
4.  **探索尝试层**：探索、试点、稳步推进、研究、适时。

**提供两个具体样例**
referenced_sentence：优化资源配置结构，充分发挥节约资源和降碳的协同作用，通过资源高效循环利用降低工业领域碳排放 matched_referencing_sentence：促进资源节约高效利用坚持"减量化、再利用、资源化"，充分发挥节约资源和降碳的协同作用，以资源高效综合利用为主要手段，推动工业领域碳排放大幅下降
similarity：2
attitude：1
analysis：政策工具具体化，新增"减量化、再利用、资源化"操作原则；目标强度提升，将"降低碳排放"强化为"大幅下降"；体现地方在落实中央精神时的"加码"倾向。 


referenced_sentence：加快推广多晶硅闭环制造工艺、先进拉晶技术、节能光纤预制及拉丝技术、印制电路板清洁生产技术等研发和产业化应用 &matched_referencing_sentence：支持多晶硅闭环制造工艺、先进拉晶技术、节能光纤预制及拉丝技术、印制电路板清洁生产技术等研发和产业化  
similarity：2
attitude：-1
保留核心技术表述；弱化执行要求，删除"加快推广"时限性表述；反映地方对产业基础差异的适应性调整。 


【输出格式（必须严格遵循此结构）】

similarity(0/1/2), attitude_change(-1/0/1/2)
例如：1,0
...
（遍历完所有句子对序号,**仅返回数字**）


【强制要求与质量控制】
0.  **输出格式**：仅返回以逗号相隔的两个数字，且无任何多余文字说明。
1.  **顺序保证与完整性**：结果列表的顺序必须与输入顺序完全一致，必须覆盖输入句子对中的每一个句子，不得遗漏（最重要）。
2.  **敏感性**：对政策态度敏感，除非完全一致或完全不相关的内容，否则应该积极基于知识对attitude_change进行打分。"""
     
    return prompt

def call_deepseek_api(prompt):
    """调用DeepSeek API"""
    try:
        response = client.chat.completions.create(
            model="deepseek-reasoner",
            messages=[
                {"role": "system", "content": "你是一个专业的中国政策文本分析专家，精通政策语言的特征、强度层级和语义分析。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=64000,
            response_format={"type": "text"}
        )
        
        result = response.choices[0].message.content
        return result
        
    except Exception as e:
        print(f"DeepSeek API调用出错: {e}")
        return None

def call_zhipu_api(prompt):
    """调用智谱清言API"""
    try:
        response = client.chat.completions.create(
            model="glm-4-plus",  # 可根据需要改为其他模型
            messages=[
                {"role": "system", "content": "你是一个专业的中国政策文本分析专家，精通政策语言的特征、强度层级和语义分析。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=64000,
            # 智谱API可能需要其他参数
        )
        
        result = response.choices[0].message.content
        return result
        
    except Exception as e:
        print(f"智谱清言API调用出错: {e}")
        return None

def call_qwen_api(prompt):
    """调用通义千问API"""
    try:
        # 注意：通义千问的API可能需要不同的参数设置
        response = client.chat.completions.create(
            model=MODEL,  # 可根据需要改为其他模型
            messages=[
                {"role": "system", "content": "你是一个专业的中国政策文本分析专家，精通政策语言的特征、强度层级和语义分析。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
        )
        
        result = response.choices[0].message.content
        return result
        
    except Exception as e:
        print(f"通义千问API调用出错: {e}")
        return None

def call_api(prompt):
    """统一的API调用接口"""
    if API_CHOICE == "deepseek":
        return call_deepseek_api(prompt)
    elif API_CHOICE == "zhipu":
        return call_zhipu_api(prompt)
    elif API_CHOICE == "qwen":
        return call_qwen_api(prompt)
    else:
        raise ValueError(f"不支持的API选择: {API_CHOICE}")

def save_result(i, result, output_path):
    """保存结果到Excel"""
    try:
        # 解析结果
        similarity, attitude_change = result.replace(' ', '').split(',')
        similarity = int(similarity)
        attitude_change = int(attitude_change)

        parsed_result = {
            'id': i + 1,  # id从1开始
            'similarity': similarity,
            'attitude': attitude_change
        }

        # 检查文件是否存在
        if os.path.exists(output_path):
            existing_df = pd.read_excel(output_path)
        else:
            existing_df = pd.DataFrame(columns=['id', 'similarity', 'attitude'])
        
        # 使用 concat 添加新行
        new_row_df = pd.DataFrame([parsed_result])
        df = pd.concat([existing_df, new_row_df], ignore_index=True)
        
        # 保存到Excel
        df.to_excel(output_path, index=False)
        
        print(f"结果已保存到: {output_path}")
        return parsed_result
        
    except Exception as e:
        print(f"解析第{i+1}行数据时出错, 错误: {e}")
        return None

def main():
    """主函数"""
    print(f"使用API: {API_CHOICE}")
    print(f"使用模型: {get_model_name()}")

    # 修改为你的数据文件路径
    df = pd.read_excel(r'')
    referenced = df['referenced'].tolist()
    referencing = df['referencing'].tolist()

    # 根据选择的API创建输出文件名
    output_filename = f"results_{MODEL}.xlsx"
    output_path = os.path.join(OUTPUT_PATH, output_filename) if OUTPUT_PATH else output_filename

    for i in range(1690):  
        print(f"处理第{i+1}行数据...")
        prompt = construct_prompt(referenced[i], referencing[i])

        # 调用API
        print("正在调用API...")
        result = call_api(prompt)

        if result:
            # 保存结果
            save_result(i, result, output_path)
        else:
            print("API调用失败")

if __name__ == "__main__":
    main()