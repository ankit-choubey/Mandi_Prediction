"""
District-Level APMC Mandi Market Intelligence System Engine
Provides actionable market intelligence outputs combining:
- Selected District, Commodity, Variety, Mandi
- Expected Market Condition: Favorable / Normal / Unfavorable
- Supporting Recent Price Trends (Current price, 1d/3d/7d change, volatility, spread)
- Neighbouring-Mandi Summary & Spatial Price Arbitrage Indications
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
from src.feature_engineering import FEATURE_COLUMNS
from src.evaluate import CLASS_NAMES

class MandiMarketIntelligenceEngine:
    def __init__(self, model_pipeline, feature_dataset):
        self.model = model_pipeline
        self.dataset = feature_dataset
        
    def generate_intelligence(self, district=None, commodity=None, variety=None, market=None, record_index=None):
        """
        Generates comprehensive market intelligence for a specific observation or filtered criteria.
        """
        sub = self.dataset
        if district:
            sub = sub[sub['District'].str.lower() == district.lower()]
        if commodity:
            sub = sub[sub['Commodity'].str.lower() == commodity.lower()]
        if variety:
            sub = sub[sub['Variety'].str.lower() == variety.lower()]
        if market:
            sub = sub[sub['Market'].str.lower() == market.lower()]
            
        if sub.empty:
            return {"error": f"No records found matching criteria (District={district}, Commodity={commodity}, Variety={variety}, Market={market})"}
        
        # Pick the most recent record or specific index
        if record_index is not None and record_index in sub.index:
            row = sub.loc[record_index]
        else:
            row = sub.sort_values('Arrival_Date').iloc[-1]
            
        # Extract features for model inference
        x_input = pd.DataFrame([row[FEATURE_COLUMNS]])
        pred_class_idx = self.model.predict(x_input)[0]
        pred_condition = CLASS_NAMES[pred_class_idx]
        
        # Prediction probabilities if available
        probs = {}
        if hasattr(self.model, 'predict_proba'):
            proba_vals = self.model.predict_proba(x_input)[0]
            for idx, cname in enumerate(CLASS_NAMES):
                probs[cname] = round(float(proba_vals[idx]) * 100, 2)
                
        # Format intelligence payload
        intelligence = {
            "date": row['Arrival_Date'].strftime('%Y-%m-%d'),
            "district": row['District'],
            "market": row['Market'],
            "commodity": row['Commodity'],
            "variety": row['Variety'],
            "current_price": float(row['Modal_Price']),
            "min_price": float(row['Min_Price']),
            "max_price": float(row['Max_Price']),
            "intraday_spread": float(row['Price_Intraday_Spread']),
            "expected_condition_T7": pred_condition,
            "condition_confidence": probs.get(pred_condition, None),
            "all_probabilities": probs,
            "recent_trends": {
                "change_1d_pct": round(float(row.get('Price_Change_1d', 0)), 2),
                "change_3d_pct": round(float(row.get('Price_Change_3d', 0)), 2),
                "change_7d_pct": round(float(row.get('Price_Change_7d', 0)), 2),
                "rolling_avg_7d": round(float(row.get('Roll_Mean_Price_7', row['Modal_Price'])), 2),
                "volatility_7d_std": round(float(row.get('Roll_Std_Price_7', 0)), 2)
            },
            "district_summary": {
                "district_avg_price": round(float(row.get('District_Commodity_MeanPrice', row['Modal_Price'])), 2),
                "reporting_mandis": int(row.get('District_Commodity_MandiCount', 1)),
                "mandi_vs_district_pct": round((float(row['Modal_Price']) / float(row.get('District_Commodity_MeanPrice', row['Modal_Price'])) - 1) * 100, 2)
            },
            "neighbouring_summary": {
                "neighbor_avg_price": round(float(row.get('Neighbor_Commodity_MeanPrice', row['Modal_Price'])), 2),
                "price_difference": round(float(row.get('Price_Diff_Target_vs_Neighbor', 0)), 2),
                "arbitrage_indicator": "Higher than neighbours (Inflow likely)" if row.get('Price_Diff_Target_vs_Neighbor', 0) > 0 else "Lower than neighbours (Outflow likely)"
            },
            "actual_outcome_T7": {
                "actual_price_T7": float(row.get('Modal_Price_T7', np.nan)),
                "actual_pct_change": round(float(row.get('Pct_Change_T7', 0)), 2),
                "actual_condition": row.get('Market_Condition', 'Unknown')
            }
        }
        return intelligence

    def format_terminal_card(self, intel):
        if "error" in intel:
            return intel["error"]
        
        card = f"""
╔══════════════════════════════════════════════════════════════════════╗
║               APMC MANDI MARKET INTELLIGENCE SYSTEM                  ║
║           District-Level Future Market Condition Advisory            ║
╚══════════════════════════════════════════════════════════════════════╝
  LOCATION & COMMODITY:
    • District           : {intel['district']}
    • Mandi / Market     : {intel['market']}
    • Commodity          : {intel['commodity']} ({intel['variety']})
    • Observation Date   : {intel['date']}

  CURRENT MARKET STATUS (T):
    • Modal Price        : Rs. {intel['current_price']:,.2f} / Quintal
    • Price Range        : Rs. {intel['min_price']:,.2f} - {intel['max_price']:,.2f} (Spread: Rs. {intel['intraday_spread']:,.2f})
    • 7-Day Rolling Avg  : Rs. {intel['recent_trends']['rolling_avg_7d']:,.2f}
    • 7-Day Price Change : {intel['recent_trends']['change_7d_pct']:+.2f}%
    • 7-Day Volatility   : Rs. {intel['recent_trends']['volatility_7d_std']:.2f}

  REGIONAL & NEIGHBOURING INTELLIGENCE:
    • District Mean Price: Rs. {intel['district_summary']['district_avg_price']:,.2f} across {intel['district_summary']['reporting_mandis']} mandi(s)
    • Mandi Premium/Disc : {intel['district_summary']['mandi_vs_district_pct']:+.2f}% vs District Average
    • Neighbour Mean Price: Rs. {intel['neighbouring_summary']['neighbor_avg_price']:,.2f}
    • Neighbour Diff     : Rs. {intel['neighbouring_summary']['price_difference']:+.2f} ({intel['neighbouring_summary']['arbitrage_indicator']})

  ----------------------------------------------------------------------
  EXPECTED T+7 MARKET CONDITION: >>> {intel['expected_condition_T7'].upper()} <<<
  Confidence Probability: {intel['condition_confidence']}%
  Class Probabilities  : {intel['all_probabilities']}
  Ground Truth Outcome : {intel['actual_outcome_T7']['actual_condition']} (Actual: Rs. {intel['actual_outcome_T7']['actual_price_T7']:,.2f} [{intel['actual_outcome_T7']['actual_pct_change']:+.2f}%])
  ----------------------------------------------------------------------
"""
        return card
