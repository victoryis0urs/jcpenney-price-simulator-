import pandas as pd
import numpy as np
import zipfile
import re

zip_path = "data/sample_data (2).zip"

# -----------------------------
# USER INPUTS
# -----------------------------

NUM_PRODUCTS = 100

SCENARIO_A_PRICE_CHANGE = -0.20  # 20% discount
SCENARIO_B_PRICE_CHANGE = 0.10   # 10% price increase

SCENARIO_A_NAME = "Scenario A: 20% Flash Sale Discount"
SCENARIO_B_NAME = "Scenario B: 10% Seasonal Price Increase"
all_dfs = []

with zipfile.ZipFile(zip_path, "r") as z:
    csv_files = [f for f in z.namelist() if f.endswith(".csv")]

    for file in csv_files:
        with z.open(file) as f:
            temp = pd.read_csv(f)

            # Extract scrape date from folder path
            date_match = re.search(r"data/(\d{4}-\d{2}-\d{2})/", file)
            temp["scrape_date"] = date_match.group(1) if date_match else None

            # Keep source file for traceability
            temp["source_file"] = file

            all_dfs.append(temp)

df = pd.concat(all_dfs, ignore_index=True)
print("Raw combined dataset shape:", df.shape)
print(df.head())
print(df.columns.tolist())

useful_cols = [
    "ppId",
    "name",
    "brand",
    "search_term",
    "currentMin",
    "originalMin",
    "averageRating",
    "reviewCount",
    "availabilityStatus",
    "priceType",
    "product_url",
    "scrape_date"
]

df = df[useful_cols].copy()


print("After selecting useful columns:", df.shape)
print(df.head())

# -----------------------------
# STEP 3: Clean price columns
# -----------------------------

df["currentMin"] = pd.to_numeric(df["currentMin"], errors="coerce")
df["originalMin"] = pd.to_numeric(df["originalMin"], errors="coerce")

print("\nBefore price cleaning:", df.shape)

df = df[
    (df["currentMin"].notna()) &
    (df["originalMin"].notna()) &
    (df["currentMin"] > 0) &
    (df["originalMin"] > 0)
].copy()

print("After price cleaning:", df.shape)
print(df[["name", "currentMin", "originalMin"]].head())

# -----------------------------
# STEP 4: Create discount percentage
# -----------------------------

df["discount_pct"] = (df["originalMin"] - df["currentMin"]) / df["originalMin"]

# Prevent negative discounts from confusing the simulator
df["discount_pct"] = df["discount_pct"].clip(lower=0)

print("\nDiscount percentage created:")
print(df[["name", "currentMin", "originalMin", "discount_pct"]].head())

# -----------------------------
# STEP 5: Keep latest record per product
# -----------------------------

df["scrape_date"] = pd.to_datetime(df["scrape_date"], errors="coerce")

products = (
    df.sort_values("scrape_date")
      .groupby("ppId", as_index=False)
      .tail(1)
      .copy()
)

print("\nUnique latest product records:", products.shape)
print(products[["ppId", "name", "search_term", "currentMin", "scrape_date"]].head())

# -----------------------------
# STEP 6: Clean review/rating data
# -----------------------------

products["reviewCount"] = pd.to_numeric(products["reviewCount"], errors="coerce")
products["averageRating"] = pd.to_numeric(products["averageRating"], errors="coerce")

# Fill missing review counts with the median review count in that category
products["reviewCount"] = products.groupby("search_term")["reviewCount"].transform(
    lambda x: x.fillna(x.median())
)

# If a whole category has missing review counts, fill remaining with 0
products["reviewCount"] = products["reviewCount"].fillna(0)

print("\nReview count cleaned:")
print(products[["name", "search_term", "reviewCount", "averageRating"]].head())

# -----------------------------
# STEP 7: Estimate baseline units sold
# -----------------------------

products["baseline_units"] = 50 + np.log1p(products["reviewCount"]) * 40
products["baseline_units"] = products["baseline_units"].round()

print("\nBaseline estimated units created:")
print(products[["name", "reviewCount", "baseline_units"]].head())

# -----------------------------
# STEP 8: Define category elasticity assumptions
# -----------------------------

category_elasticities = {
    "women's tops": -1.8,
    "women's dresses": -1.7,
    "women's activewear": -1.6,
    "handbags": -1.5,
    "comforter sets": -1.4,
    "men's outerwear": -1.4,
    "men's shoes": -1.3,
    "cookware": -1.2,
    "men's dress shirts": -1.2,
    "patio and outdoor furniture": -1.1,
    "diamond earrings": -1.0,
    "fragrances": -0.8
}

products["search_term"] = products["search_term"].str.lower().str.strip()
products["elasticity"] = products["search_term"].map(category_elasticities).fillna(-1.2)

print("\nElasticity assigned:")
print(products[["name", "search_term", "elasticity"]].head())

# -----------------------------
# STEP 9: Select 100 products
# -----------------------------

eligible_products = products[
    (products["currentMin"] > 0) &
    (products["baseline_units"] > 0)
].copy()

sample_products = eligible_products.sample(NUM_PRODUCTS, random_state=42).copy()

print("\nSample of 100 products selected:", sample_products.shape)
print(sample_products[["name", "search_term", "currentMin", "baseline_units"]].head())

# -----------------------------
# STEP 10: Price simulator function
# -----------------------------

def simulate_price_change(df, price_change_pct, scenario_name):
    result = df.copy()

    result["scenario"] = scenario_name
    result["price_change_pct"] = price_change_pct

    # New price after proposed change
    result["new_price"] = result["currentMin"] * (1 + price_change_pct)

    # Estimated unit change based on elasticity
    result["unit_change_pct"] = result["elasticity"] * price_change_pct

    # Cap extreme behavior for realism
    result["unit_change_pct"] = result["unit_change_pct"].clip(lower=-0.80, upper=1.50)

    # Estimate new units
    result["estimated_new_units"] = result["baseline_units"] * (1 + result["unit_change_pct"])
    result["estimated_new_units"] = result["estimated_new_units"].clip(lower=0).round()

    # Revenue calculations
    result["baseline_revenue"] = result["currentMin"] * result["baseline_units"]
    result["new_revenue"] = result["new_price"] * result["estimated_new_units"]

    result["revenue_change_pct"] = (
        (result["new_revenue"] - result["baseline_revenue"]) /
        result["baseline_revenue"]
    )

    return result

# -----------------------------
# STEP 11: Run scenarios
# -----------------------------

scenario_a = simulate_price_change(
    sample_products,
    price_change_pct=SCENARIO_A_PRICE_CHANGE,
    scenario_name=SCENARIO_A_NAME
)

scenario_b = simulate_price_change(
    sample_products,
    price_change_pct=SCENARIO_B_PRICE_CHANGE,
    scenario_name=SCENARIO_B_NAME
)

simulation_results = pd.concat([scenario_a, scenario_b], ignore_index=True)

print("\nSimulation complete:", simulation_results.shape)
print(simulation_results[[
    "scenario",
    "name",
    "currentMin",
    "new_price",
    "baseline_units",
    "estimated_new_units",
    "unit_change_pct"
]].head())

# -----------------------------
# STEP 12: Save output files
# -----------------------------

output_cols = [
    "scenario",
    "ppId",
    "name",
    "brand",
    "search_term",
    "currentMin",
    "new_price",
    "baseline_units",
    "estimated_new_units",
    "unit_change_pct",
    "baseline_revenue",
    "new_revenue",
    "revenue_change_pct",
    "elasticity",
    "product_url"
]

final_output = simulation_results[output_cols].copy()

final_output["unit_change_pct"] = final_output["unit_change_pct"] * 100
final_output["revenue_change_pct"] = final_output["revenue_change_pct"] * 100

final_output.to_csv("outputs/simulation_results.csv", index=False)

print("\nSaved simulation_results.csv")
print(final_output.head())

# -----------------------------
# STEP 12B: Side-by-side scenario comparison
# -----------------------------

side_by_side = final_output.pivot_table(
    index=["ppId", "name", "brand", "search_term", "currentMin", "baseline_units"],
    columns="scenario",
    values=[
        "new_price",
        "estimated_new_units",
        "unit_change_pct",
        "new_revenue",
        "revenue_change_pct"
    ],
    aggfunc="first"
)

side_by_side.to_csv("outputs/side_by_side_simulation.csv")

print("\nSaved side_by_side_simulation.csv")

# -----------------------------
# STEP 13: Scenario summary
# -----------------------------

scenario_summary = final_output.groupby("scenario").agg(
    total_baseline_units=("baseline_units", "sum"),
    total_estimated_units=("estimated_new_units", "sum"),
    total_baseline_revenue=("baseline_revenue", "sum"),
    total_new_revenue=("new_revenue", "sum"),
    average_unit_change_pct=("unit_change_pct", "mean"),
    average_revenue_change_pct=("revenue_change_pct", "mean")
).reset_index()

scenario_summary.to_csv("outputs/scenario_summary.csv", index=False)

print("\nScenario summary:")
print(scenario_summary)
print("\nSaved scenario_summary.csv")

# STEP 14: Human-readable example
# -----------------------------

example = simulation_results.iloc[0]

direction = "increases" if example["estimated_new_units"] > example["baseline_units"] else "decreases"

print("\nExample result:")
print(
    f"For {example['name']}, with a {example['price_change_pct']:.0%} price change, "
    f"estimated units sold {direction} from "
    f"{int(example['baseline_units'])} to {int(example['estimated_new_units'])} "
    f"({example['unit_change_pct']:.1%})."
)

