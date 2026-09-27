from pathlib import Path
import pandas as pd

# ============================================================
# Configuration
# ============================================================

INPUT_FILE = Path(
    r"results\Qwen3-Embedding-0.6B\matching_results\Carbon Peak (Overall).xlsx"
)

OUTPUT_DIR = Path(
    r"results\Qwen3-Embedding-0.6B\validity_experiment"
)

N_SAMPLE = 4000
RANDOM_SEED = 20260916

FULL_OUTPUT = OUTPUT_DIR / "validity_sample_4000_full.xlsx"
MASKED_OUTPUT = OUTPUT_DIR / "validity_sample_4000_masked.xlsx"

# Optional: convenient format for feeding the 4000 pairs to an LLM/API
AGENT_INPUT_JSONL = OUTPUT_DIR / "validity_sample_4000_agent_input.jsonl"


# ============================================================
# Load data
# ============================================================

required_columns = [
    "query",
    "direct_match",
    "direct_sim",
    "direct_degree",
]

df = pd.read_excel(
    INPUT_FILE,
    usecols=required_columns,
)

# Make sure direct_degree is numeric.
# Non-numeric values, if any, are converted to NaN and excluded.
df["direct_degree"] = pd.to_numeric(
    df["direct_degree"],
    errors="coerce"
)


# ============================================================
# Eligibility restriction: direct_degree != 0
# ============================================================

eligible = df.loc[
    df["direct_degree"].notna()
    & df["direct_degree"].ne(0)
].copy()

if len(eligible) < N_SAMPLE:
    raise ValueError(
        f"Only {len(eligible)} observations have direct_degree != 0, "
        f"which is fewer than the requested {N_SAMPLE} observations."
    )

# Optional integrity check
if eligible[["query", "direct_match"]].isna().any().any():
    raise ValueError(
        "Missing values detected in query or direct_match. "
        "Please inspect them before constructing the validation sample."
    )


# ============================================================
# Random sampling
# ============================================================

sample = (
    eligible
    .sample(
        n=N_SAMPLE,
        replace=False,
        random_state=RANDOM_SEED,
    )
    .reset_index(drop=True)
)

# Stable ID used throughout the entire validity experiment.
# Both the full and masked datasets use exactly the same sample_id.
sample.insert(
    0,
    "sample_id",
    range(1, N_SAMPLE + 1)
)

# Final column order
sample = sample[
    [
        "sample_id",
        "query",
        "direct_match",
        "direct_sim",
        "direct_degree",
    ]
]


# ============================================================
# Full sample
# ============================================================

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

sample.to_excel(
    FULL_OUTPUT,
    index=False
)


# ============================================================
# Masked sample
# ============================================================

masked_sample = sample.copy()

# Keep the columns but remove their values.
# This makes the schemas of the two files identical while preventing
# direct_sim and direct_degree from influencing the AI annotation.
masked_sample["direct_sim"] = pd.NA
masked_sample["direct_degree"] = pd.NA

masked_sample.to_excel(
    MASKED_OUTPUT,
    index=False
)


# ============================================================
# Optional agent-input file
# ============================================================

# For actual API/LLM annotation, only these three fields are needed.
agent_input = masked_sample[
    [
        "sample_id",
        "query",
        "direct_match",
    ]
].copy()

agent_input.to_json(
    AGENT_INPUT_JSONL,
    orient="records",
    lines=True,
    force_ascii=False,
)


# ============================================================
# Consistency checks
# ============================================================

assert len(sample) == N_SAMPLE
assert len(masked_sample) == N_SAMPLE

assert sample["sample_id"].equals(
    masked_sample["sample_id"]
)

assert sample["query"].equals(
    masked_sample["query"]
)

assert sample["direct_match"].equals(
    masked_sample["direct_match"]
)

assert masked_sample["direct_sim"].isna().all()
assert masked_sample["direct_degree"].isna().all()

print(f"Eligible observations: {len(eligible)}")
print(f"Sampled observations:  {len(sample)}")
print(f"Full sample saved to:   {FULL_OUTPUT}")
print(f"Masked sample saved to: {MASKED_OUTPUT}")
print(f"Agent input saved to:   {AGENT_INPUT_JSONL}")