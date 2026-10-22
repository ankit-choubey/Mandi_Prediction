"""
Audit and compute exact baseline metrics from Phase 5 outputs for the 4 approved crops:
Potato, Onion, Tomato, Wheat.
"""

import os
import gzip
import pandas as pd
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report,
    log_loss
)

PRED_DIR = "/Users/kumarsuryansh/Desktop/Temporary/Mandi_Prediction/backing/phase_05/outputs"
CROPS = ["Potato", "Onion", "Tomato", "Wheat"]
CLASS_NAMES = ['Unfavorable', 'Normal', 'Favorable']

def audit_baseline_predictions():
    test_path = os.path.join(PRED_DIR, "test_predictions.csv.gz")
    val_path = os.path.join(PRED_DIR, "val_predictions.csv.gz")
    
    test_df = pd.read_csv(test_path)
    val_df = pd.read_csv(val_path)
    
    print(f"Loaded test predictions: {len(test_df):,} rows")
    print(f"Loaded val predictions : {len(val_df):,} rows")
    print(f"Test date range: {test_df['Arrival_Date'].min()} to {test_df['Arrival_Date'].max()}")
    print(f"Val date range : {val_df['Arrival_Date'].min()} to {val_df['Arrival_Date'].max()}")

    # Evaluate Overall and Per-Crop
    records = []
    
    for split_name, df in [("Validation", val_df), ("Exploratory_Test", test_df)]:
        # Overall
        subgroups = [("ALL_CROPS", df)] + [(crop, df[df['Commodity'] == crop]) for crop in CROPS]
        
        for name, sub_df in subgroups:
            if len(sub_df) == 0:
                continue
            y_true = sub_df['Target_Class'].astype(int)
            y_pred = sub_df['Predicted_Class'].astype(int)
            
            # Majority baseline
            maj_class = y_true.mode()[0]
            y_maj = np.full_like(y_true, maj_class)
            maj_acc = accuracy_score(y_true, y_maj)
            
            acc = accuracy_score(y_true, y_pred)
            bal_acc = balanced_accuracy_score(y_true, y_pred)
            p_macro = precision_score(y_true, y_pred, average='macro', zero_division=0)
            r_macro = recall_score(y_true, y_pred, average='macro', zero_division=0)
            f1_macro = f1_score(y_true, y_pred, average='macro', zero_division=0)
            f1_weighted = f1_score(y_true, y_pred, average='weighted', zero_division=0)
            
            # Log loss
            prob_cols = ['Prob_Unfavorable', 'Prob_Normal', 'Prob_Favorable']
            y_prob = sub_df[prob_cols].values
            # Clip for numerical stability
            eps = 1e-15
            y_prob = np.clip(y_prob, eps, 1 - eps)
            y_prob = y_prob / y_prob.sum(axis=1, keepdims=True)
            
            # Unique classes in subset
            unique_classes = np.unique(y_true)
            if len(unique_classes) == 3:
                loss = log_loss(y_true, y_prob, labels=[0, 1, 2])
            else:
                loss = np.nan
            
            cm = confusion_matrix(y_true, y_pred, labels=[0, 1, 2])
            
            # Per class metrics
            p_class = precision_score(y_true, y_pred, average=None, labels=[0, 1, 2], zero_division=0)
            r_class = recall_score(y_true, y_pred, average=None, labels=[0, 1, 2], zero_division=0)
            f1_class = f1_score(y_true, y_pred, average=None, labels=[0, 1, 2], zero_division=0)
            support_class = np.bincount(y_true, minlength=3)
            
            records.append({
                'Split': split_name,
                'Subgroup': name,
                'N_Obs': len(sub_df),
                'Majority_Class': maj_class,
                'Majority_Baseline_Acc': round(maj_acc * 100, 2),
                'Accuracy': round(acc * 100, 2),
                'Accuracy_Lift_vs_Baseline': round((acc - maj_acc) * 100, 2),
                'Balanced_Accuracy': round(bal_acc * 100, 2),
                'Macro_Precision': round(p_macro, 4),
                'Macro_Recall': round(r_macro, 4),
                'Macro_F1': round(f1_macro, 4),
                'Weighted_F1': round(f1_weighted, 4),
                'Log_Loss': round(loss, 4) if pd.notnull(loss) else np.nan,
                'Supp_Unfav': support_class[0],
                'Supp_Norm': support_class[1],
                'Supp_Fav': support_class[2],
                'Pct_Norm': round(support_class[1] / len(sub_df) * 100, 2),
                'Prec_Unfav': round(p_class[0], 4),
                'Prec_Norm': round(p_class[1], 4),
                'Prec_Fav': round(p_class[2], 4),
                'Rec_Unfav': round(r_class[0], 4),
                'Rec_Norm': round(r_class[1], 4),
                'Rec_Fav': round(r_class[2], 4),
                'F1_Unfav': round(f1_class[0], 4),
                'F1_Norm': round(f1_class[1], 4),
                'F1_Fav': round(f1_class[2], 4),
                'CM_00': cm[0, 0], 'CM_01': cm[0, 1], 'CM_02': cm[0, 2],
                'CM_10': cm[1, 0], 'CM_11': cm[1, 1], 'CM_12': cm[1, 2],
                'CM_20': cm[2, 0], 'CM_21': cm[2, 1], 'CM_22': cm[2, 2],
            })
            
    res_df = pd.DataFrame(records)
    out_csv = "/Users/kumarsuryansh/Desktop/Temporary/suryansh - work/reports/phase_03_classification_protocol/baseline_metrics_summary.csv"
    res_df.to_csv(out_csv, index=False)
    print(f"Saved baseline metrics to {out_csv}")
    return res_df

if __name__ == "__main__":
    df = audit_baseline_predictions()
    print("\nTest Partition Performance Comparison:")
    test_res = df[df['Split'] == 'Exploratory_Test'][['Subgroup', 'N_Obs', 'Majority_Baseline_Acc', 'Accuracy', 'Accuracy_Lift_vs_Baseline', 'Balanced_Accuracy', 'Macro_F1', 'Pct_Norm']]
    print(test_res.to_string(index=False))
