# Copilot / AI Agent 指南（项目特定）

目的：帮助自动化编码代理快速理解本仓库的“结构、约定与常用操作”，以便安全、可重复地修改与扩展代码。

1) 大局观（Why & high-level flow）
- 本仓库为以文本相似度/分级/网络分析为主的数据处理流水线。关键阶段按文件名前缀数字排列（流水线顺序）：
  - `0_structuring_text.py` -> 文本预处理
  - `1_sim_match_and_degree_quantized.py` -> 相似度匹配与分级量化
  - `2_summary_by_threshold.py`, `2_summary_of_paragraph_and_article.py` -> 汇总/摘要
  - `3_generate_network_metrics.py`, `4_generate_network.py*` -> 网络生成与指标
 变更时尊重此序号约定；上游输出通常写入 `results/` 子目录供下游使用。

2) 关键入口与运行方式（可复制命令）
- 单脚本运行（Windows 任意 PowerShell / CMD）：
  - `python 1_sim_match_and_degree_quantized.py`
  - `python analysis.py` （高阶分析脚本）
- 配置由 `config.py` 控制（模型路径、阈值等），请修改前确认默认值与 `models/` 下可用模型。

3) 重要目录与示例文件
- `data/`：原始与中间数据（包括 `structured_match/` 与 `structured_query/`），脚本会从中读取或写回。
- `models/`：保存本地 sentence-transformers 模型（示例：`paraphrase-multilingual-MiniLM-L12-v2`），`config.py` 中引用该路径。
- `dictionary_expanding/`：词典扩展相关工具与数据（见 `dic_expanding.py`）。
- `results/`：所有输出（summary、network、metrics、threshold 分析等）最终落在这里，CI/后处理通常读取此目录。

4) 项目特定约定与模式
- 文件按数字前缀表示流水线阶段，添加新阶段时遵循同样命名方式以保持可重现性。
- 数据传递以 CSV/JSON 文件为主（见 `results/` 与 `data/structured_*`），避免直接在内存中传递临时文件到不同脚本。
- 嵌入/相似度使用 `sentence_transformers`（在 `config.py` 或 `utils.py` 中被导入）。

5) 依赖（从源码可发现）
- 常见依赖：`pandas`, `numpy`, `matplotlib`, `networkx`, `sentence-transformers`。
  在打开或运行脚本前，确保在虚拟环境中安装这些包。

6) 调试/开发提示
- 若要理解某个阶段的输入输出，先打开对应脚本（例如 `1_sim_match_and_degree_quantized.py`），并查看 `results/` 与 `data/structured_*` 中的示例输出。
- 对于模型路径问题，检查 `models/` 下的子目录，并在 `config.py` 中同步路径。

7) 变更与合并策略（AI 代理须遵守）
- 不要在未明确测试的情况下重命名或删除以数字开头的脚本；若重构，保持兼容的输入/输出文件格式，并更新 `results/` 的读写路径。
- 修改行为性逻辑前先本地运行对应脚本，捕获输出差异并加入简短说明到提交消息。

8) 可能需要人工确认的地方（edge cases）
- 外部模型文件较大（`models/`），AI 代理不可自动替换模型路径或下载大文件，需提示开发者确认。
- 如果新增第三方依赖，务必将 `requirements.txt` 或等效说明更新，并在提交中说明原因。

---
如果有需要我可以把这份文件合并/替换仓库中的已有内容（若存在），或根据你的偏好缩短/扩展其中某些段落。请告诉我哪些部分需要补充或修改。
