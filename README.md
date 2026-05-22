# JCPenney Price Simulator

## Project Overview

This project builds a simple price simulator using JCPenney product and pricing data. The simulator estimates how units sold may change when prices are discounted or increased.

The simulator compares two scenarios:

- Scenario A: 20% price cut for a flash sale
- Scenario B: 10% price increase going into a new season

## How to Run

Install dependencies:

```bash
pip install -r requirements.txt
```
Run the Simulator:

```bash
python price_simulator.py
```
The dataset should be stored in the following location:

```bash
data/sample_data.zip
```

## Outputs

The simulator creates three main output files:

- outputs/simulation_results.csv,
Product-level results for both pricing scenarios.

- outputs/side_by_side_simulation.csv,
A side-by-side comparison of Scenario A and Scenario B for the same 100 products.

- outputs/scenario_summary.csv,
A high-level summary of total estimated units, estimated revenue, and average percentage changes.

## Approach

The raw dataset was split across multiple CSV files inside a ZIP folder. Each file represented a product category and scrape date. I first loaded every CSV file, combined them into one dataset, and preserved the scrape date for each row.

After combining the data, I kept only the columns needed for a simple price simulator:

product ID
product name
brand
product category/search term
current price
original price
rating
review count
availability status
product URL
scrape date

The original data contained many additional fields, such as image metadata, swatches, badges, and video information. These were excluded because they were not necessary for estimating price impact.

## Data Cleaning

The dataset was real and messy, so I cleaned it in several steps:

### 1. Price cleaning
- I converted currentMin and originalMin into numeric values and removed rows with missing, zero, or invalid prices.
### 2. Discount calculation
- I calculated each product’s current discount percentage using:
   ``` bash
   discount_pct = (original price - current price) / original price
   ```
   Negative discounts were clipped to 0 so unusual pricing records would not distort the analysis.
### 3. Duplicate product handling
- Since products appeared across multiple scrape dates, I kept only the latest available record for each unique product ID. This avoids counting the same product multiple times.
### 4. Review count cleaning
- Missing review counts were filled using the median review count within each product category. Remaining missing values were filled with 0.

## Baseline Sales Assumption

The dataset does not include actual units sold. Because of this, I estimated baseline units using reviewCount as a proxy for product popularity.

The assumption is that products with more reviews likely had more historical customer activity and therefore stronger baseline demand.

The baseline formula used was:
```bash
baseline_units = 50 + log(1 + reviewCount) × 40
```
I used a logarithmic transformation so products with extremely high review counts would not dominate the results too heavily.

This value does not represent actual sales. It is only an estimated starting point for the simulation.

## Price Elasticity Assumptions

The simulator uses price elasticity to estimate how quantity sold changes when price changes.

The formula used is:
 ```bash
% change in units = elasticity × % change in price
```
For example, if a product has an elasticity of -1.8 and receives a 20% price cut:
```bash
-1.8 × -20% = +36%
```
So estimated units sold would increase by 36%.

Because actual sales data is unavailable, I could not calculate true price elasticity directly. Instead, I assigned category-level elasticity values based on:

- observed discount behavior,
- product category type,
- likely customer price sensitivity,
- product substitutability,
- whether the category is fashion-driven, seasonal, brand-driven, or luxury-oriented.

## Category-Level Elasticity Values

| Category                    | Elasticity | Reasoning                                                   |
| --------------------------- | ---------: | ----------------------------------------------------------- |
| women's tops                |       -1.8 | Highly substitutable, fashion-driven, frequent promotions   |
| women's dresses             |       -1.7 | Seasonal/fashion-driven with many alternatives              |
| women's activewear          |       -1.6 | Competitive category with many substitutes                  |
| handbags                    |       -1.5 | Promotion-sensitive but somewhat brand-influenced           |
| comforter sets              |       -1.4 | Home goods category with moderate price sensitivity         |
| men's outerwear             |       -1.4 | Seasonal category with moderate sensitivity                 |
| men's shoes                 |       -1.3 | Brand matters, but price still influences demand            |
| cookware                    |       -1.2 | Practical purchase category with moderate price sensitivity |
| men's dress shirts          |       -1.2 | Less volatile than women’s fashion categories               |
| patio and outdoor furniture |       -1.1 | Higher-ticket items, less impulse-driven                    |
| diamond earrings            |       -1.0 | Luxury/occasion-based, less purely price-driven             |
| fragrances                  |       -0.8 | Brand loyalty matters, lower price sensitivity              |

Categories with many substitutes and frequent markdowns were assigned stronger elasticity values. More brand-sensitive or luxury categories were assigned weaker elasticity values.

## Simulation Scenarios

The simulator samples 100 eligible products and compares two scenarios.

### Scenario A: 20% Flash Sale Discount

This scenario applies a 20% price cut to each sampled product.

The expected effect is that estimated units sold increase, especially in more price-sensitive categories such as apparel.

### Scenario B: 10% Seasonal Price Increase

This scenario applies a 10% price increase to each sampled product.

The expected effect is that estimated units sold decrease, with larger drops in categories that have stronger price sensitivity.

## Limitations 

This simulator is not a true sales forecasting model. It is a simple decision-support tool based on transparent assumptions.

The dataset does not include:

- actual units sold
- transaction history
- customer traffic
- inventory levels
- marketing spend
- seasonality
- competitor prices
- product-level conversion rates

Because of this, the estimated unit and revenue changes should be interpreted as directional estimates, not exact forecasts.

The use of review count as a demand proxy is also imperfect. Reviews accumulate over time and may not reflect current demand, recent promotions, or actual purchase volume during the scrape period.

## What I Would Improve With More Time

With more time and better data, I would improve the simulator by:

- Using actual transaction or units-sold data to estimate real price elasticity.
- Estimating elasticity by product category, brand, price range, and season.
- Adding inventory and availability data to avoid estimating demand for unavailable products.
- Incorporating seasonality, especially for categories like patio furniture, outerwear, dresses, and fragrances.
- Adding confidence intervals to show uncertainty around each estimate.
- Building an interactive dashboard where users can select products and test custom price changes.
- Validating the simulator against historical sales performance.




