"""
Phase 1 Data Integrity & Exact-Calendar Continuity Audit Engine
Produces all 9 required CSV outputs under backing/phase_01/outputs/
"""

import os
import glob
import hashlib
import pandas as pd
import numpy as np
from datetime import timedelta

ROOT_DIR = "/Users/theankit/Documents/AK/Projects/Mandi_Prediction"
RAW_DIR = os.path.join(ROOT_DIR, "data", "raw")
OUT_DIR = os.path.join(ROOT_DIR, "backing", "phase_01", "outputs")
os.makedirs(OUT_DIR, exist_ok=True)

print("=" * 80)
print("RUNNING PHASE 1 DATA INTEGRITY AUDIT ENGINE")
print("=" * 80)

# -----------------------------------------------------------------------------
# 1. Input Inventory (input_inventory.csv)
# -----------------------------------------------------------------------------
print("\n[1/9] Generating input_inventory.csv...")
raw_files = sorted(glob.glob(os.path.join(RAW_DIR, "*.csv")))
inventory_records = []
all_dfs = []

for f in raw_files:
    fname = os.path.basename(f)
    sz = os.path.getsize(f)
    with open(f, 'rb') as fp:
        h = hashlib.sha256(fp.read()).hexdigest()
    
    df_f = pd.read_csv(f)
    df_f['Source_File'] = fname
    df_f['Row_ID'] = [f"{fname}:{i}" for i in range(len(df_f))]
    all_dfs.append(df_f)
    
    dt = pd.to_datetime(df_f['Arrival_Date'], format='%d/%m/%Y', errors='coerce')
    
    inventory_records.append({
        'filename': fname,
        'file_path': os.path.relpath(f, ROOT_DIR),
        'file_size_bytes': sz,
        'sha256_hash': h,
        'row_count': len(df_f),
        'column_count': len(df_f.columns),
        'min_date': dt.min().strftime('%Y-%m-%d'),
        'max_date': dt.max().strftime('%Y-%m-%d'),
        'distinct_districts': df_f['District'].nunique(),
        'distinct_markets': df_f['Market'].nunique(),
        'distinct_commodities': df_f['Commodity'].nunique(),
        'distinct_varieties': df_f['Variety'].nunique()
    })

inv_df = pd.DataFrame(inventory_records)
inv_df.to_csv(os.path.join(OUT_DIR, "input_inventory.csv"), index=False)
print(f"Saved input_inventory.csv ({len(inv_df)} files, total {inv_df['row_count'].sum():,} rows)")

# Combine into master dataframe
raw_master = pd.concat(all_dfs, ignore_index=True)
raw_master['Arrival_Date_Parsed'] = pd.to_datetime(raw_master['Arrival_Date'], format='%d/%m/%Y', errors='coerce')
raw_master['Modal_Price_Num'] = pd.to_numeric(raw_master['Modal_Price'], errors='coerce')
raw_master['Min_Price_Num'] = pd.to_numeric(raw_master['Min_Price'], errors='coerce')
raw_master['Max_Price_Num'] = pd.to_numeric(raw_master['Max_Price'], errors='coerce')

series_cols = ['District', 'Market', 'Commodity', 'Variety']
raw_master['series_id'] = raw_master[series_cols].astype(str).agg('__'.join, axis=1)

# -----------------------------------------------------------------------------
# 2. Duplicate Groups & Price Ambiguity (duplicate_groups.csv)
# -----------------------------------------------------------------------------
print("\n[2/9] Generating duplicate_groups.csv...")
dupe_grouped = raw_master.groupby(series_cols + ['Arrival_Date_Parsed'])

dupe_records = []
for (dist, mkt, comm, var, dt), grp in dupe_grouped:
    if len(grp) > 1:
        modal_vals = grp['Modal_Price_Num'].dropna().unique()
        min_vals = grp['Min_Price_Num'].dropna().unique()
        max_vals = grp['Max_Price_Num'].dropna().unique()
        
        has_conflict = (len(modal_vals) > 1) or (len(min_vals) > 1) or (len(max_vals) > 1)
        series_str = f"{dist}__{mkt}__{comm}__{var}"
        
        dupe_records.append({
            'series_id': series_str,
            'district': dist,
            'market': mkt,
            'commodity': comm,
            'variety': var,
            'arrival_date': dt.strftime('%Y-%m-%d'),
            'duplicate_count': len(grp),
            'min_modal_price': grp['Modal_Price_Num'].min(),
            'max_modal_price': grp['Modal_Price_Num'].max(),
            'modal_price_spread': grp['Modal_Price_Num'].max() - grp['Modal_Price_Num'].min(),
            'price_conflict': has_conflict,
            'source_files': ";".join(grp['Source_File'].unique()),
            'sample_row_ids': ";".join(grp['Row_ID'].head(3))
        })

dupe_df = pd.DataFrame(dupe_records)
dupe_df.to_csv(os.path.join(OUT_DIR, "duplicate_groups.csv"), index=False)
print(f"Saved duplicate_groups.csv ({len(dupe_df):,} groups, {dupe_df['price_conflict'].sum():,} conflicting)")

# -----------------------------------------------------------------------------
# 3. Data Quality Flags (data_quality_flags.csv)
# -----------------------------------------------------------------------------
print("\n[3/9] Generating data_quality_flags.csv...")
flags = []

# Build set of duplicate conflicting row keys
conflicting_keys = set(dupe_df[dupe_df['price_conflict']][['district', 'market', 'commodity', 'variety', 'arrival_date']].itertuples(index=False, name=None))

for idx, r in raw_master.iterrows():
    row_flags = []
    
    # Check price ordering
    if pd.notnull(r['Min_Price_Num']) and pd.notnull(r['Modal_Price_Num']) and r['Min_Price_Num'] > r['Modal_Price_Num']:
        row_flags.append('MIN_GT_MODAL')
    if pd.notnull(r['Modal_Price_Num']) and pd.notnull(r['Max_Price_Num']) and r['Modal_Price_Num'] > r['Max_Price_Num']:
        row_flags.append('MODAL_GT_MAX')
    if pd.notnull(r['Min_Price_Num']) and pd.notnull(r['Max_Price_Num']) and r['Min_Price_Num'] > r['Max_Price_Num']:
        row_flags.append('MIN_GT_MAX')
    
    # Check zero or negative
    if pd.notnull(r['Modal_Price_Num']) and r['Modal_Price_Num'] <= 0:
        row_flags.append('MODAL_PRICE_NON_POSITIVE')
    if pd.notnull(r['Min_Price_Num']) and r['Min_Price_Num'] <= 0:
        row_flags.append('MIN_PRICE_NON_POSITIVE')
    if pd.notnull(r['Max_Price_Num']) and r['Max_Price_Num'] <= 0:
        row_flags.append('MAX_PRICE_NON_POSITIVE')
    
    # Check duplicate conflict ambiguity
    dt_str = r['Arrival_Date_Parsed'].strftime('%Y-%m-%d')
    key_tuple = (r['District'], r['Market'], r['Commodity'], r['Variety'], dt_str)
    if key_tuple in conflicting_keys:
        row_flags.append('AMBIGUOUS_DUPLICATE_DATE')
        
    # Check extreme intraday spread ratio
    if pd.notnull(r['Modal_Price_Num']) and r['Modal_Price_Num'] > 0:
        spread = r['Max_Price_Num'] - r['Min_Price_Num']
        if spread / r['Modal_Price_Num'] > 2.0:
            row_flags.append('EXTREME_INTRADAY_SPREAD_RATIO')
    
    if row_flags:
        flags.append({
            'row_id': r['Row_ID'],
            'source_file': r['Source_File'],
            'district': r['District'],
            'market': r['Market'],
            'commodity': r['Commodity'],
            'variety': r['Variety'],
            'arrival_date': dt_str,
            'min_price': r['Min_Price_Num'],
            'modal_price': r['Modal_Price_Num'],
            'max_price': r['Max_Price_Num'],
            'flags': ";".join(row_flags)
        })

flags_df = pd.DataFrame(flags)
flags_df.to_csv(os.path.join(OUT_DIR, "data_quality_flags.csv"), index=False)
print(f"Saved data_quality_flags.csv ({len(flags_df):,} flagged rows)")

# -----------------------------------------------------------------------------
# 4. Price Quality Summary (price_quality_summary.csv)
# -----------------------------------------------------------------------------
print("\n[4/9] Generating price_quality_summary.csv...")
pq_records = []

for fname, grp in raw_master.groupby('Source_File'):
    tot = len(grp)
    valid_order = (grp['Min_Price_Num'] <= grp['Modal_Price_Num']) & (grp['Modal_Price_Num'] <= grp['Max_Price_Num'])
    min_gt_modal = (grp['Min_Price_Num'] > grp['Modal_Price_Num']).sum()
    modal_gt_max = (grp['Modal_Price_Num'] > grp['Max_Price_Num']).sum()
    min_gt_max = (grp['Min_Price_Num'] > grp['Max_Price_Num']).sum()
    zero_modal = (grp['Modal_Price_Num'] <= 0).sum()
    zero_min = (grp['Min_Price_Num'] <= 0).sum()
    zero_max = (grp['Max_Price_Num'] <= 0).sum()
    spread_zero = ((grp['Max_Price_Num'] - grp['Min_Price_Num']) == 0).sum()
    
    pq_records.append({
        'scope': fname,
        'total_rows': tot,
        'compliant_price_order_rows': valid_order.sum(),
        'compliance_pct': round((valid_order.sum() / tot) * 100, 4),
        'min_gt_modal_count': min_gt_modal,
        'modal_gt_max_count': modal_gt_max,
        'min_gt_max_count': min_gt_max,
        'zero_modal_price_count': zero_modal,
        'zero_min_price_count': zero_min,
        'zero_max_price_count': zero_max,
        'zero_spread_count': spread_zero,
        'zero_spread_pct': round((spread_zero / tot) * 100, 2)
    })

# Total statewide row
tot_all = len(raw_master)
valid_all = (raw_master['Min_Price_Num'] <= raw_master['Modal_Price_Num']) & (raw_master['Modal_Price_Num'] <= raw_master['Max_Price_Num'])
spread_zero_all = ((raw_master['Max_Price_Num'] - raw_master['Min_Price_Num']) == 0).sum()
pq_records.append({
    'scope': 'ALL_FILES_TOTAL',
    'total_rows': tot_all,
    'compliant_price_order_rows': valid_all.sum(),
    'compliance_pct': round((valid_all.sum() / tot_all) * 100, 4),
    'min_gt_modal_count': (raw_master['Min_Price_Num'] > raw_master['Modal_Price_Num']).sum(),
    'modal_gt_max_count': (raw_master['Modal_Price_Num'] > raw_master['Max_Price_Num']).sum(),
    'min_gt_max_count': (raw_master['Min_Price_Num'] > raw_master['Max_Price_Num']).sum(),
    'zero_modal_price_count': (raw_master['Modal_Price_Num'] <= 0).sum(),
    'zero_min_price_count': (raw_master['Min_Price_Num'] <= 0).sum(),
    'zero_max_price_count': (raw_master['Max_Price_Num'] <= 0).sum(),
    'zero_spread_count': spread_zero_all,
    'zero_spread_pct': round((spread_zero_all / tot_all) * 100, 2)
})

pq_df = pd.DataFrame(pq_records)
pq_df.to_csv(os.path.join(OUT_DIR, "price_quality_summary.csv"), index=False)
print("Saved price_quality_summary.csv")

# -----------------------------------------------------------------------------
# 5. Market Mapping Review (market_mapping_review.csv)
# -----------------------------------------------------------------------------
print("\n[5/9] Generating market_mapping_review.csv...")
market_meta = raw_master.groupby(['District', 'Market']).agg(
    record_count=('Arrival_Date', 'count'),
    min_date=('Arrival_Date_Parsed', 'min'),
    max_date=('Arrival_Date_Parsed', 'max')
).reset_index()

mapping_records = []
for idx, r in market_meta.iterrows():
    m = r['Market']
    d = r['District']
    
    # Determine canonical proposal
    clean_m = m.replace(' APMC', '').strip()
    if clean_m in ['Baripaal', 'Varipaal']:
        clean_m = 'Varipaal'
    elif clean_m == 'Jhansi Grain':
        clean_m = 'Jhansi (Grain)'
        
    is_apmc_variant = (' APMC' in m) or (m in ['Baripaal APMC', 'Jhansi Grain APMC'])
    
    # Find matching base market if APMC, or matching APMC market if base
    if is_apmc_variant:
        partner_m = clean_m
        if partner_m not in market_meta[market_meta['District'] == d]['Market'].values:
            partner_m = None
    else:
        partner_candidates = [other for other in market_meta[market_meta['District'] == d]['Market'].values if clean_m in other and other != m]
        partner_m = partner_candidates[0] if partner_candidates else None
    
    # Check date overlap
    date_overlap = 0
    conflict_risk = "LOW"
    if partner_m:
        p_dates = set(raw_master[(raw_master['District'] == d) & (raw_master['Market'] == partner_m)]['Arrival_Date_Parsed'])
        m_dates = set(raw_master[(raw_master['District'] == d) & (raw_master['Market'] == m)]['Arrival_Date_Parsed'])
        common_d = p_dates.intersection(m_dates)
        date_overlap = len(common_d)
        if date_overlap > 0:
            conflict_risk = "MEDIUM_COLLISION_POTENTIAL" if date_overlap <= 5 else "HIGH_PARALLEL_SERIES"
            
    mapping_records.append({
        'district': d,
        'market_raw': m,
        'record_count': r['record_count'],
        'min_date': r['min_date'].strftime('%Y-%m-%d'),
        'max_date': r['max_date'].strftime('%Y-%m-%d'),
        'has_apmc_suffix': ' APMC' in m,
        'proposed_canonical_market': clean_m,
        'partner_market_string': partner_m,
        'date_overlap_count': date_overlap,
        'proposal_status': 'PROPOSED_CANONICAL_MERGE' if is_apmc_variant else 'PROPOSED_BASE_CANONICAL',
        'merge_risk_assessment': conflict_risk
    })

map_df = pd.DataFrame(mapping_records)
map_df.to_csv(os.path.join(OUT_DIR, "market_mapping_review.csv"), index=False)
print(f"Saved market_mapping_review.csv ({len(map_df)} market strings)")

# -----------------------------------------------------------------------------
# 6. Observation Gap Summary by Series (observation_gap_summary.csv)
# -----------------------------------------------------------------------------
print("\n[6/9] Generating observation_gap_summary.csv...")
# Build deduplicated dataset for series gap analysis (using first entry to prevent duplicate 0-day gaps)
clean_series_df = raw_master.drop_duplicates(subset=series_cols + ['Arrival_Date_Parsed'], keep='first').copy()
clean_series_df.sort_values(by=['series_id', 'Arrival_Date_Parsed'], inplace=True)

gap_records = []
for sid, grp in clean_series_df.groupby('series_id'):
    dates = grp['Arrival_Date_Parsed'].sort_values()
    n_obs = len(dates)
    min_d = dates.min()
    max_d = dates.max()
    span = (max_d - min_d).days + 1
    
    diffs = (dates.diff().dt.days).dropna()
    
    g_1d = (diffs == 1).sum() if len(diffs) > 0 else 0
    g_2d = (diffs == 2).sum() if len(diffs) > 0 else 0
    g_3d = (diffs == 3).sum() if len(diffs) > 0 else 0
    g_4_6d = ((diffs >= 4) & (diffs <= 6)).sum() if len(diffs) > 0 else 0
    g_7d_plus = (diffs >= 7).sum() if len(diffs) > 0 else 0
    
    d, m, c, v = sid.split('__')
    
    gap_records.append({
        'series_id': sid,
        'district': d,
        'market': m,
        'commodity': c,
        'variety': v,
        'total_observations': n_obs,
        'min_date': min_d.strftime('%Y-%m-%d'),
        'max_date': max_d.strftime('%Y-%m-%d'),
        'span_calendar_days': span,
        'gap_1d_count': g_1d,
        'gap_2d_count': g_2d,
        'gap_3d_count': g_3d,
        'gap_4_to_6d_count': g_4_6d,
        'gap_7d_plus_count': g_7d_plus,
        'max_gap_days': int(diffs.max()) if len(diffs) > 0 else 0,
        'median_gap_days': float(diffs.median()) if len(diffs) > 0 else 0.0,
        'mean_gap_days': round(float(diffs.mean()), 2) if len(diffs) > 0 else 0.0
    })

gap_df = pd.DataFrame(gap_records)
gap_df.to_csv(os.path.join(OUT_DIR, "observation_gap_summary.csv"), index=False)
print(f"Saved observation_gap_summary.csv ({len(gap_df):,} unique series)")

# -----------------------------------------------------------------------------
# 7. Exact Target Coverage (exact_target_coverage.csv)
# -----------------------------------------------------------------------------
print("\n[7/9] Generating exact_target_coverage.csv...")
max_calendar_date = clean_series_df['Arrival_Date_Parsed'].max()

coverage_rows = []

for horizon in [3, 7]:
    clean_series_df[f'Target_Date_T{horizon}'] = clean_series_df['Arrival_Date_Parsed'] + timedelta(days=horizon)
    clean_series_df[f'Is_Truncated_T{horizon}'] = clean_series_df[f'Target_Date_T{horizon}'] > max_calendar_date
    
    # Exact lookup
    lookup = clean_series_df[['series_id', 'Arrival_Date_Parsed', 'Modal_Price_Num']].copy()
    matched = pd.merge(
        clean_series_df,
        lookup,
        left_on=['series_id', f'Target_Date_T{horizon}'],
        right_on=['series_id', 'Arrival_Date_Parsed'],
        suffixes=('', f'_T{horizon}'),
        how='left'
    )
    
    matched[f'Has_Match_T{horizon}'] = matched[f'Modal_Price_Num_T{horizon}'].notnull()
    
    # A. Global Level
    tot = len(matched)
    trunc = matched[f'Is_Truncated_T{horizon}'].sum()
    elig = tot - trunc
    m_cnt = matched[f'Has_Match_T{horizon}'].sum()
    interior_miss = elig - m_cnt
    
    coverage_rows.append({
        'aggregation_level': 'GLOBAL',
        'entity_name': 'STATEWIDE_TOTAL',
        'horizon': f'T+{horizon}',
        'total_origin_records': tot,
        'boundary_truncated_origins': trunc,
        'eligible_origins': elig,
        'matched_targets': m_cnt,
        'interior_missing_targets': interior_miss,
        'match_rate_all_origins_pct': round((m_cnt / tot) * 100, 2),
        'match_rate_eligible_pct': round((m_cnt / elig) * 100, 2)
    })
    
    # B. District Level
    for d, grp in matched.groupby('District'):
        d_tot = len(grp)
        d_trunc = grp[f'Is_Truncated_T{horizon}'].sum()
        d_elig = d_tot - d_trunc
        d_m = grp[f'Has_Match_T{horizon}'].sum()
        d_miss = d_elig - d_m
        coverage_rows.append({
            'aggregation_level': 'DISTRICT',
            'entity_name': d,
            'horizon': f'T+{horizon}',
            'total_origin_records': d_tot,
            'boundary_truncated_origins': d_trunc,
            'eligible_origins': d_elig,
            'matched_targets': d_m,
            'interior_missing_targets': d_miss,
            'match_rate_all_origins_pct': round((d_m / d_tot) * 100, 2),
            'match_rate_eligible_pct': round((d_m / d_elig) * 100, 2)
        })
        
    # C. Commodity Level (Top 25)
    comm_counts = matched['Commodity'].value_counts()
    for c in comm_counts.head(25).index:
        grp = matched[matched['Commodity'] == c]
        c_tot = len(grp)
        c_trunc = grp[f'Is_Truncated_T{horizon}'].sum()
        c_elig = c_tot - c_trunc
        c_m = grp[f'Has_Match_T{horizon}'].sum()
        c_miss = c_elig - c_m
        coverage_rows.append({
            'aggregation_level': 'COMMODITY',
            'entity_name': c,
            'horizon': f'T+{horizon}',
            'total_origin_records': c_tot,
            'boundary_truncated_origins': c_trunc,
            'eligible_origins': c_elig,
            'matched_targets': c_m,
            'interior_missing_targets': c_miss,
            'match_rate_all_origins_pct': round((c_m / c_tot) * 100, 2),
            'match_rate_eligible_pct': round((c_m / c_elig) * 100, 2)
        })

cov_df = pd.DataFrame(coverage_rows)
cov_df.to_csv(os.path.join(OUT_DIR, "exact_target_coverage.csv"), index=False)
print(f"Saved exact_target_coverage.csv ({len(cov_df)} breakdown rows)")

# -----------------------------------------------------------------------------
# 8. Target Match Examples (target_match_examples.csv)
# -----------------------------------------------------------------------------
print("\n[8/9] Generating target_match_examples.csv...")
# Find diverse concrete examples
example_records = []

# Exact T+7 match
t7_lookup = clean_series_df[['series_id', 'Arrival_Date_Parsed', 'Modal_Price_Num']].copy()
t7_merged = pd.merge(
    clean_series_df,
    t7_lookup,
    left_on=['series_id', 'Target_Date_T7'],
    right_on=['series_id', 'Arrival_Date_Parsed'],
    suffixes=('', '_T7'),
    how='left'
)

# A. Exact Match Example
m_sample = t7_merged[t7_merged['Modal_Price_Num_T7'].notnull()].iloc[0]
pct_chg = ((m_sample['Modal_Price_Num_T7'] - m_sample['Modal_Price_Num']) / m_sample['Modal_Price_Num']) * 100
example_records.append({
    'category': 'SUCCESSFUL_EXACT_MATCH_T7',
    'series_id': m_sample['series_id'],
    'origin_date': m_sample['Arrival_Date_Parsed'].strftime('%Y-%m-%d'),
    'target_date_required': m_sample['Target_Date_T7'].strftime('%Y-%m-%d'),
    'origin_price': m_sample['Modal_Price_Num'],
    'matched_price': m_sample['Modal_Price_Num_T7'],
    'pct_change': round(pct_chg, 4),
    'market_condition': 'Favorable' if pct_chg >= 2.5 else ('Unfavorable' if pct_chg <= -2.5 else 'Normal'),
    'notes': 'Matched exactly at T+7 calendar days.'
})

# B. Exact Match T+3 Example
t3_merged = pd.merge(
    clean_series_df,
    clean_series_df[['series_id', 'Arrival_Date_Parsed', 'Modal_Price_Num']],
    left_on=['series_id', 'Target_Date_T3'],
    right_on=['series_id', 'Arrival_Date_Parsed'],
    suffixes=('', '_T3'),
    how='left'
)
m3_sample = t3_merged[t3_merged['Modal_Price_Num_T3'].notnull()].iloc[10]
pct_chg3 = ((m3_sample['Modal_Price_Num_T3'] - m3_sample['Modal_Price_Num']) / m3_sample['Modal_Price_Num']) * 100
example_records.append({
    'category': 'SUCCESSFUL_EXACT_MATCH_T3',
    'series_id': m3_sample['series_id'],
    'origin_date': m3_sample['Arrival_Date_Parsed'].strftime('%Y-%m-%d'),
    'target_date_required': m3_sample['Target_Date_T3'].strftime('%Y-%m-%d'),
    'origin_price': m3_sample['Modal_Price_Num'],
    'matched_price': m3_sample['Modal_Price_Num_T3'],
    'pct_change': round(pct_chg3, 4),
    'market_condition': 'Favorable' if pct_chg3 >= 2.5 else ('Unfavorable' if pct_chg3 <= -2.5 else 'Normal'),
    'notes': 'Matched exactly at T+3 calendar days.'
})

# C. Interior Missing Example (Market closed on target date)
interior_sample = t7_merged[(~t7_merged['Is_Truncated_T7']) & (t7_merged['Modal_Price_Num_T7'].isnull())].iloc[0]
example_records.append({
    'category': 'INTERIOR_MISSING_GAP_T7',
    'series_id': interior_sample['series_id'],
    'origin_date': interior_sample['Arrival_Date_Parsed'].strftime('%Y-%m-%d'),
    'target_date_required': interior_sample['Target_Date_T7'].strftime('%Y-%m-%d'),
    'origin_price': interior_sample['Modal_Price_Num'],
    'matched_price': np.nan,
    'pct_change': np.nan,
    'market_condition': 'UNOBSERVED',
    'notes': 'Target date is within dataset span but no auction reported for this series on that day.'
})

# D. Boundary Truncated Example (Origin near end of 2-year dataset)
trunc_sample = t7_merged[t7_merged['Is_Truncated_T7']].iloc[0]
example_records.append({
    'category': 'BOUNDARY_TRUNCATED_HORIZON_T7',
    'series_id': trunc_sample['series_id'],
    'origin_date': trunc_sample['Arrival_Date_Parsed'].strftime('%Y-%m-%d'),
    'target_date_required': trunc_sample['Target_Date_T7'].strftime('%Y-%m-%d'),
    'origin_price': trunc_sample['Modal_Price_Num'],
    'matched_price': np.nan,
    'pct_change': np.nan,
    'market_condition': 'TRUNCATED',
    'notes': 'Target date is beyond dataset maximum date (2026-09-01).'
})

# E. Sticky Price Zero Change Example
sticky_sample = t7_merged[t7_merged['Modal_Price_Num_T7'] == t7_merged['Modal_Price_Num']].iloc[5]
example_records.append({
    'category': 'STICKY_PRICE_ZERO_CHANGE_T7',
    'series_id': sticky_sample['series_id'],
    'origin_date': sticky_sample['Arrival_Date_Parsed'].strftime('%Y-%m-%d'),
    'target_date_required': sticky_sample['Target_Date_T7'].strftime('%Y-%m-%d'),
    'origin_price': sticky_sample['Modal_Price_Num'],
    'matched_price': sticky_sample['Modal_Price_Num_T7'],
    'pct_change': 0.0000,
    'market_condition': 'Normal',
    'notes': 'Price was completely unchanged after 7 calendar days.'
})

examples_df = pd.DataFrame(example_records)
examples_df.to_csv(os.path.join(OUT_DIR, "target_match_examples.csv"), index=False)
print("Saved target_match_examples.csv")

# -----------------------------------------------------------------------------
# 9. Class Distribution & Boundary Conditions (class_distribution.csv)
# -----------------------------------------------------------------------------
print("\n[9/9] Generating class_distribution.csv...")
dist_records = []

for horizon, m_df in [(3, t3_merged), (7, t7_merged)]:
    valid_m = m_df[m_df[f'Modal_Price_Num_T{horizon}'].notnull()].copy()
    valid_m['pct_change'] = ((valid_m[f'Modal_Price_Num_T{horizon}'] - valid_m['Modal_Price_Num']) / valid_m['Modal_Price_Num']) * 100
    
    tot = len(valid_m)
    p = valid_m['pct_change']
    
    # Exactly zero
    zeros = (p == 0.0).sum()
    
    # Boundary edge cases (exact matches on +2.5 and -2.5)
    exact_pos_25 = (p == 2.5).sum()
    exact_neg_25 = (p == -2.5).sum()
    
    # Fixed +/- 2.5% threshold
    fav = (p >= 2.5).sum()
    unfav = (p <= -2.5).sum()
    norm = ((p > -2.5) & (p < 2.5)).sum()
    
    dist_records.append({
        'horizon': f'T+{horizon}',
        'threshold_definition': 'Fixed +/-2.5% [<= -2.5: Unfav, >= +2.5: Fav, else: Normal]',
        'total_matched_records': tot,
        'favorable_count': fav,
        'favorable_pct': round((fav / tot) * 100, 2),
        'normal_count': norm,
        'normal_pct': round((norm / tot) * 100, 2),
        'unfavorable_count': unfav,
        'unfavorable_pct': round((unfav / tot) * 100, 2),
        'exact_zero_change_count': zeros,
        'exact_zero_change_pct': round((zeros / tot) * 100, 2),
        'exact_plus_2_5_edge_cases': exact_pos_25,
        'exact_minus_2_5_edge_cases': exact_neg_25,
        'pct_change_mean': round(float(p.mean()), 4),
        'pct_change_median': round(float(p.median()), 4),
        'pct_change_std': round(float(p.std()), 4),
        'pct_change_q25': round(float(p.quantile(0.25)), 4),
        'pct_change_q75': round(float(p.quantile(0.75)), 4),
        'pct_change_iqr': round(float(p.quantile(0.75) - p.quantile(0.25)), 4)
    })

class_df = pd.DataFrame(dist_records)
class_df.to_csv(os.path.join(OUT_DIR, "class_distribution.csv"), index=False)
print("Saved class_distribution.csv")

print("\n" + "=" * 80)
print("PHASE 1 OUTPUT ENGINE COMPLETED SUCCESSFULLY")
print("=" * 80)
