# Vertical Reinforcement, Horizontal Mimicry

Code and data for the manuscript **“Vertical Reinforcement, Horizontal Mimicry: The Anatomy of China’s Carbon Policy Diffusion.”**

This repository implements a sentence-level text-mining framework for studying how China’s carbon policies diffuse vertically from the central government to provinces and horizontally across provinces. It combines bidirectional semantic matching with a degree lexicon to measure how strongly an adopter expresses a policy statement relative to its source.

## Research overview

China’s “1+N” dual-carbon framework links central policy design to sectoral implementation and provincial action. The analysis asks two related questions:

1. **Vertical diffusion:** How are central policy statements reflected and reformulated in provincial policies?
2. **Horizontal diffusion:** After accounting for a shared central policy and policy timing, which earlier provincial policies are plausible sources for later provincial policies?

For a source policy \(S\) and an adopter policy \(A\), the code performs matching in both directions:

- **Source-to-adopter (S-to-A):** for every source statement, find the most similar adopter statement.
- **Adopter-to-source (A-to-S):** for every adopter statement, find the most similar source statement.

Semantic correspondence is measured with cosine similarity between sentence embeddings. Relative attitudinal stance is defined as

\[
\operatorname{Rel.Att}(s,a)=I(a)-I(s),
\]

where \(I(\cdot)\) is sentence-level attitudinal stance intensity calculated from the expert-built Degree Lexicon. Positive values indicate that the adopter expresses a stronger stance than the source; negative values indicate a weaker stance.

The manuscript reports three principal findings:

- Provincial governments tend to strengthen selected central-policy statements, producing higher S-to-A than A-to-S attitudinal stance.
- The same directional asymmetry appears in inferred horizontal diffusion networks, while central policies remain structurally dominant and the networks show limited community differentiation.
- Stronger text-based attitudinal stance is associated with lower post-issuance carbon emissions most consistently in the power sector, especially in provinces with higher pre-policy carbon intensity, power-emission shares, or secondary-industry shares. These estimates are interpreted as conditional associations, not causal treatment effects.

## Policy corpus

The manuscript’s analytical sample covers 12 central-policy-centered themes and 211 policies.

| Code | Theme | Central document | Level | Policies |
|---|---|---|---|---:|
| a | Carbon Peaking | *Action Plan for Carbon Dioxide Peaking Before 2030* | Top-level design | 25 |
| b | New Development Philosophy | *Opinions on Fully, Accurately, and Comprehensively Implementing the New Development Philosophy and Doing a Good Job in Carbon Peaking and Carbon Neutrality* | Top-level design | 21 |
| c | Industrial Sector | *Implementation Plan for Carbon Peaking in the Industrial Sector* | Key areas | 25 |
| d | Urban-Rural Development | *Implementation Plan for Carbon Peaking in Urban and Rural Development* | Key areas | 25 |
| e | Pollution and Carbon Reduction | *Implementation Plan for Synergizing Pollution Reduction and Carbon Reduction* | Key areas | 26 |
| f | Green Consumption | *Implementation Plan for Promoting Green Consumption* | Key areas | 10 |
| g | Green, Low-Carbon, and Circular Development | *State Council Guiding Opinions on Accelerating the Establishment of a Green, Low-Carbon, and Circular Development Economic System* | Key areas | 25 |
| h | Green and Low-Carbon Transition | *Implementation Opinions on Green and Low-Carbon Transition* | Key areas | 7 |
| i | Non-ferrous Metals | *Implementation Plan for Carbon Peaking in the Non-ferrous Metals Industry* | Key industries | 8 |
| j | Building Materials | *Implementation Plan for Carbon Peaking in the Building Materials Industry* | Key industries | 12 |
| k | Standards and Metrology | *Implementation Plan for Establishing a Sound Carbon Peaking and Carbon Neutrality Standards and Metrology System* | Support measures | 9 |
| l | Fiscal Support | *Opinions on Fiscal Support for Carbon Peaking and Carbon Neutrality* | Support measures | 18 |

Central and provincial policy documents were assembled with reference to the official “1+N” framework and the Peking University Law database. The empirical validation additionally uses provincial statistics from the China Statistical Yearbook, China Energy Statistical Yearbook, local statistical yearbooks, and daily sectoral carbon-emission records from CEADs.

## Repository structure

```text
carbon-policy-analysis/
├── data/
│   ├── query/                  # central/source policy documents
│   ├── match/                  # provincial/adopter policy documents
│   ├── structured_query/       # sentence-structured central policies
│   ├── structured_match/       # sentence-structured provincial policies
│   ├── dictionary/             # degree lexicon and related resources
│   └── time_order.xlsx         # policy issuance order used for networks
├── results/
│   └── DID/                    # econometric-validation data/scripts/results
├── 0_structuring_text.py       # parse raw policy files into structured JSON
├── 0_embedding_qwen.py         # main Qwen3 embedding pipeline
├── 0_embedding.py              # BGE-M3 and MiniLM robustness embeddings
├── 0_embedding_e5.py           # multilingual-E5 robustness embeddings
├── 1_sim_match_and_degree_quantized.py
│                                # bidirectional matching and stance scoring
├── 2_summary.py                # document-level aggregation for one theme
├── 2_summary_section.py        # section- and document-level aggregation
├── 3_generate_network.py       # horizontal-network edge construction
├── 4_draw_network.py           # network visualization and node statistics
├── 4_draw_edge_analysis.py     # edge distributions and modularity
├── 4_draw_heatmap.py           # vertical-diffusion section heatmaps
├── 4_draw_nodes.py             # node-level comparisons
├── 4_draw_swimlane.py          # threshold sensitivity plots
├── 5_draw_att_robust1.py       # embedding robustness figures
├── 5_draw_att_robust2.py       # additional robustness figures
├── config.py
├── utils.py
└── utils_embedding.py
```

Downloaded models, generated sentence embeddings, and large generated outputs are deliberately excluded from Git. See [Storage policy](#storage-policy).

## Environment

Python 3.10 or later is recommended. Install the packages used by the text and network pipeline:

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
# source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install numpy pandas torch sentence-transformers scikit-learn networkx matplotlib seaborn openpyxl jieba pdfplumber python-docx huggingface-hub
```

The econometric scripts under `results/DID/` require Stata and are not executed by the Python pipeline.

## Model setup

The main analysis uses **Qwen3-Embedding-0.6B**, which maps statements to 1,024-dimensional vectors and uses asymmetric query/document encoding. Three alternative multilingual models are used for robustness checks.

| Role | Hugging Face model | Expected local directory |
|---|---|---|
| Main analysis | `Qwen/Qwen3-Embedding-0.6B` | `models/Qwen3-Embedding-0.6B/` |
| Robustness | `BAAI/bge-m3` | `models/bge-m3/` |
| Robustness | `intfloat/multilingual-e5-large` | `models/multilingual-e5-large/` |
| Robustness | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | `models/paraphrase-multilingual-MiniLM-L12-v2/` |

Download only the models required for the analysis you intend to run. For example:

```bash
python -c "from huggingface_hub import snapshot_download; snapshot_download('Qwen/Qwen3-Embedding-0.6B', local_dir='models/Qwen3-Embedding-0.6B')"
```

To reproduce all robustness checks, repeat the command with the other three model identifiers and their corresponding local directories. Model weights are not redistributed in this repository.

## Reproduction workflow

Run commands from the repository root. Review the path and parameter constants near the top of each script before launching long jobs.

### 1. Prepare structured policy text

The repository already contains structured JSON inputs under `data/structured_query/` and `data/structured_match/`, so most users can skip this step. To rebuild them from the raw files:

```bash
python 0_structuring_text.py
```

`data/query/` contains central/source policies and `data/match/` contains provincial/adopter policies. The current import chain also initializes the local MiniLM model, so download that model before rerunning the structuring script.

### 2. Generate sentence embeddings

For the manuscript’s primary specification:

```bash
python 0_embedding_qwen.py
```

For robustness checks:

```bash
python 0_embedding.py
python 0_embedding_e5.py
```

The scripts write reproducible `.npy`, index, and metadata files under `data/embeddings/<model>/`. GPU acceleration is strongly recommended. Runtime and memory use depend on hardware and corpus size.

### 3. Match statements and calculate relative stance

```bash
python 1_sim_match_and_degree_quantized.py
```

This script loads the precomputed embeddings, restricts each search to a single source-adopter document pair, finds nearest semantic matches in both directions, and combines similarity with degree-lexicon scores. The default model is configured in `utils_embedding.py`; matching outputs are written beneath `results/<model>/matching_results/`.

### 4. Aggregate vertical-diffusion results

```bash
python 2_summary_section.py
```

`2_summary.py` performs a document-level aggregation for a single input workbook. Its input and output paths are currently set near the top of the script and should be changed when processing another theme.

### 5. Construct horizontal-diffusion networks

```bash
python 3_generate_network.py
```

For a temporally ordered local-policy pair, the algorithm compares each adopter statement’s best match in the earlier local policy with its best match in the common central policy. The share for which the earlier local policy is more similar is denoted \(p_{a,s}\) and used as the confidence threshold for a potential horizontal edge. These links are inferential and should not be interpreted as directly observed diffusion.

### 6. Generate network statistics and figures

```bash
python 4_draw_network.py
python 4_draw_edge_analysis.py
python 4_draw_nodes.py
python 4_draw_swimlane.py
python 4_draw_heatmap.py
```

The manuscript’s principal horizontal-network presentation uses \(p_{a,s}\geq0.50\); the code also evaluates alternative thresholds. Generated workbooks and figures are written under `results/` and are not tracked by Git by default.

### 7. Run econometric validation

The Stata files under `results/DID/` estimate two-way fixed-effects specifications using daily total and sectoral emissions. The focal regressors interact the post-issuance indicator with four text-derived measures:

- S-to-A relative attitudinal stance;
- A-to-S relative attitudinal stance;
- S-to-A average network out-edge weight; and
- A-to-S average network out-edge weight.

Specifications include province fixed effects, day fixed effects, the post-issuance indicator, and controls for regional GDP, industrial structure, urbanization, population density, technological progress, and fiscal self-sufficiency. Standard errors are clustered at the province level. These models provide external validation of the text measures and are not presented as a causal difference-in-differences design.

## Storage policy

Large or reproducible artifacts are excluded through `.gitignore`:

- `models/` - downloaded model weights (previously more than 15 GB locally);
- `data/embeddings/` - regenerated by the `0_embedding*.py` scripts;
- model-specific directories under `results/` - generated matches, networks, workbooks, and figures;
- common checkpoint formats such as `.safetensors`, `.bin`, `.onnx`, `.pt`, and `.pth`.

The raw/structured policy corpus, degree lexicon, policy timing table, source code, and compact empirical-validation materials remain eligible for version control. Do not commit generated models or embeddings with Git LFS: several model files approach or exceed common hosted-LFS per-file and storage limits, and all can be downloaded from their original model repositories.

## Interpretation and limitations

- Similarity identifies textual correspondence consistent with potential diffusion; it does not distinguish learning, imitation, competition, or coercion.
- Relative attitudinal stance measures strengthening or weakening but does not separately identify strictness, urgency, or procedural rigor.
- Local-to-local network links are inferred from timing, semantic similarity, and a common-source benchmark; they are not directly observed citations.
- The empirical analysis establishes systematic associations with emissions, not causal policy effects.

## Citation

If you use this repository, please cite the manuscript:

```bibtex
@unpublished{zhang2026vertical,
  title  = {Vertical Reinforcement, Horizontal Mimicry: The Anatomy of China's Carbon Policy Diffusion},
  author = {Zhang, Chaohan and Cui, Yaofeng and Zheng, Xinman and Huang, Shixu and Zheng, Haitao and Zhu, Lei and Dong, Yu and Liu, Pengfei},
  year   = {2026},
  note   = {Manuscript}
}
```

## License

No open-source license has yet been specified for this repository. Unless a license file is added, please contact the authors before reusing or redistributing the code or data beyond scholarly replication.
