"""
Evaluation & Validation Module
APMC Mandi Market Intelligence System
Implements chronological train/val/test split and computes:
- Accuracy, Precision (Macro/Weighted), Recall (Macro/Weighted), F1 (Macro/Weighted)
- Confusion Matrices
- Feature Importance ranking
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix
)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

from src.feature_engineering import FEATURE_COLUMNS
from src.models import get_models, get_feature_importances

CLASS_NAMES = ['Unfavorable', 'Normal', 'Favorable']

def chronological_split(dataset, train_ratio=0.70, val_ratio=0.15, horizon_days=7):
    """
    Splits dataset chronologically based on Arrival_Date with horizon-aware embargo purging.
    - Prevents target realization leakage across split boundaries.
    - Train: earliest 70% dates minus h-day embargo buffer.
    - Val: next 15% dates minus h-day embargo buffer.
    - Test: final 15% dates (designated as historical exploratory test window).
    """
    sorted_df = dataset.sort_values('Arrival_Date').reset_index(drop=True)
    dates = sorted_df['Arrival_Date'].drop_duplicates().sort_values().reset_index(drop=True)
    
    n_dates = len(dates)
    train_end_idx = int(n_dates * train_ratio)
    val_end_idx = int(n_dates * (train_ratio + val_ratio))
    
    train_cutoff = dates.iloc[train_end_idx]
    val_cutoff = dates.iloc[val_end_idx]
    
    # Train partition: origins with target realization strictly before validation start date
    # With horizon=7, an origin at train_cutoff - 7 days realizes on train_cutoff (first day of val).
    # Thus, origin must be <= train_cutoff - (horizon_days + 1) days so realization is <= train_cutoff - 1 day.
    train_embargo_cutoff = train_cutoff - pd.Timedelta(days=horizon_days + 1)
    train_df = sorted_df[sorted_df['Arrival_Date'] <= train_embargo_cutoff].copy()
    
    # Train embargo: origins whose targets would realize on or after validation start date
    train_embargo = sorted_df[(sorted_df['Arrival_Date'] > train_embargo_cutoff) & (sorted_df['Arrival_Date'] < train_cutoff)]
    
    # Validation partition: origins starting at train_cutoff with realization strictly before test start date
    val_embargo_cutoff = val_cutoff - pd.Timedelta(days=horizon_days + 1)
    val_df = sorted_df[(sorted_df['Arrival_Date'] >= train_cutoff) & (sorted_df['Arrival_Date'] <= val_embargo_cutoff)].copy()
    
    # Val embargo: origins whose targets would realize on or after test start date
    val_embargo = sorted_df[(sorted_df['Arrival_Date'] > val_embargo_cutoff) & (sorted_df['Arrival_Date'] < val_cutoff)]
    
    # Test partition: exploratory historical test set
    test_df = sorted_df[sorted_df['Arrival_Date'] >= val_cutoff].copy()
    
    print(f"[ChronologicalSplit] Total Records: {len(sorted_df):,}")
    print(f"  - Train Partition : {len(train_df):,} records ({train_df['Arrival_Date'].min().strftime('%Y-%m-%d')} to {train_df['Arrival_Date'].max().strftime('%Y-%m-%d')})")
    print(f"    [Purged Embargo] : {len(train_embargo):,} records (Origins > {train_embargo_cutoff.strftime('%Y-%m-%d')} to < {train_cutoff.strftime('%Y-%m-%d')})")
    print(f"  - Val Partition   : {len(val_df):,} records ({val_df['Arrival_Date'].min().strftime('%Y-%m-%d')} to {val_df['Arrival_Date'].max().strftime('%Y-%m-%d')})")
    print(f"    [Purged Embargo] : {len(val_embargo):,} records (Origins > {val_embargo_cutoff.strftime('%Y-%m-%d')} to < {val_cutoff.strftime('%Y-%m-%d')})")
    print(f"  - Exploratory Test: {len(test_df):,} records ({test_df['Arrival_Date'].min().strftime('%Y-%m-%d')} to {test_df['Arrival_Date'].max().strftime('%Y-%m-%d')}) [Exploratory Window]")
    
    return train_df, val_df, test_df

def train_and_evaluate_all(train_df, val_df, test_df, output_dir="results"):
    os.makedirs(output_dir, exist_ok=True)
    
    X_train = train_df[FEATURE_COLUMNS]
    y_train = train_df['Target_Class']
    
    X_val = val_df[FEATURE_COLUMNS]
    y_val = val_df['Target_Class']
    
    X_test = test_df[FEATURE_COLUMNS]
    y_test = test_df['Target_Class']
    
    models = get_models()
    results = {}
    trained_pipelines = {}
    
    # Stage 1: Fit on train, evaluate strictly on Validation partition for candidate selection
    print("\n" + "=" * 70)
    print("STAGE 1: CANDIDATE MODEL EVALUATION & SELECTION ON VALIDATION SET")
    print("=" * 70)
    
    val_scores = {}
    for name, pipeline in models.items():
        print(f"\n[Training] Fitting {name} on training partition (n={len(X_train):,})...")
        pipeline.fit(X_train, y_train)
        trained_pipelines[name] = pipeline
        
        # Predict strictly on Validation set
        y_val_pred = pipeline.predict(X_val)
        val_acc = accuracy_score(y_val, y_val_pred)
        val_f1_macro = f1_score(y_val, y_val_pred, average='macro', zero_division=0)
        val_p_macro = precision_score(y_val, y_val_pred, average='macro', zero_division=0)
        val_r_macro = recall_score(y_val, y_val_pred, average='macro', zero_division=0)
        
        val_scores[name] = {
            'val_accuracy': val_acc,
            'val_f1_macro': val_f1_macro,
            'val_precision_macro': val_p_macro,
            'val_recall_macro': val_r_macro,
        }
        print(f"  [Validation: {name}] Acc: {val_acc:.4f} | Macro F1: {val_f1_macro:.4f} | Macro Prec: {val_p_macro:.4f} | Macro Recall: {val_r_macro:.4f}")
    
    # Select candidate model based strictly on validation Macro F1
    best_candidate_name = max(val_scores.keys(), key=lambda k: val_scores[k]['val_f1_macro'])
    print("\n" + "-" * 70)
    print(f"SELECTED PRIMARY CANDIDATE: '{best_candidate_name}' based on Validation Macro F1 ({val_scores[best_candidate_name]['val_f1_macro']:.4f})")
    print("Zero test data was used for model selection or hyperparameter decisions.")
    print("-" * 70)
    
    # Stage 2: Exploratory test evaluation of all models (for historical transparency)
    print("\n" + "=" * 70)
    print("STAGE 2: EVALUATION ON EXPLORATORY TEST SET (HISTORICAL EXPLORATION WINDOW)")
    print("=" * 70)
    
    for name, pipeline in trained_pipelines.items():
        y_pred = pipeline.predict(X_test)
        
        acc = accuracy_score(y_test, y_pred)
        p_macro = precision_score(y_test, y_pred, average='macro', zero_division=0)
        r_macro = recall_score(y_test, y_pred, average='macro', zero_division=0)
        f1_macro = f1_score(y_test, y_pred, average='macro', zero_division=0)
        
        p_weighted = precision_score(y_test, y_pred, average='weighted', zero_division=0)
        r_weighted = recall_score(y_test, y_pred, average='weighted', zero_division=0)
        f1_weighted = f1_score(y_test, y_pred, average='weighted', zero_division=0)
        
        cm = confusion_matrix(y_test, y_pred)
        report = classification_report(y_test, y_pred, target_names=CLASS_NAMES, zero_division=0)
        importances = get_feature_importances(pipeline, FEATURE_COLUMNS)
        
        results[name] = {
            'is_selected_candidate': (name == best_candidate_name),
            'val_accuracy': val_scores[name]['val_accuracy'],
            'val_f1_macro': val_scores[name]['val_f1_macro'],
            'val_precision_macro': val_scores[name]['val_precision_macro'],
            'val_recall_macro': val_scores[name]['val_recall_macro'],
            'accuracy': acc,
            'precision_macro': p_macro,
            'recall_macro': r_macro,
            'f1_macro': f1_macro,
            'precision_weighted': p_weighted,
            'recall_weighted': r_weighted,
            'f1_weighted': f1_weighted,
            'confusion_matrix': cm,
            'classification_report': report,
            'feature_importances': importances
        }
        
        print(f"[{name}] Val Macro F1: {val_scores[name]['val_f1_macro']:.4f} | Test Acc (Exploratory): {acc:.4f} | Test F1 Macro: {f1_macro:.4f}")
        
        # Save Confusion Matrix Plot
        plt.figure(figsize=(6, 5))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                    xticklabels=CLASS_NAMES, yticklabels=CLASS_NAMES)
        plt.title(f'Exploratory Test CM: {name}')
        plt.xlabel('Predicted Condition')
        plt.ylabel('True Condition')
        plt.tight_layout()
        cm_filename = f"confusion_matrix_{name.lower().replace(' ', '_')}.png"
        plt.savefig(os.path.join(output_dir, cm_filename), dpi=200)
        plt.close()
    
    # Generate Feature Importance Plot for Random Forest
    rf_importances = results.get('Random Forest', {}).get('feature_importances', {})
    if rf_importances:
        fi_series = pd.Series(rf_importances).sort_values(ascending=True)
        plt.figure(figsize=(10, 8), dpi=200)
        fi_series.plot(kind='barh', color='#2b5c8f')
        plt.title('Random Forest Feature Importance (MDI)', fontsize=13, weight='bold', pad=12)
        plt.xlabel('Relative Importance', fontsize=11)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'feature_importance_rf.png'), dpi=200)
        plt.close()
        
    # Generate Dynamic Model Performance Comparison Chart
    model_names = list(results.keys())
    val_f1_vals = [results[m]['val_f1_macro'] * 100 for m in model_names]
    test_f1_vals = [results[m]['f1_macro'] * 100 for m in model_names]
    
    fig, ax = plt.subplots(figsize=(10, 5), dpi=200)
    x = np.arange(len(model_names))
    width = 0.35
    
    rects1 = ax.bar(x - width/2, val_f1_vals, width, label='Validation Macro F1 (%) [Model Selection]', color='#2B6CB0')
    rects2 = ax.bar(x + width/2, test_f1_vals, width, label='Exploratory Test Macro F1 (%)', color='#319795')
    
    ax.set_ylabel('Macro F1 (%)', fontsize=11)
    ax.set_title('Model Performance: Validation Selection vs Exploratory Test Evaluation', fontsize=13, weight='bold', pad=12, color='#1A365D')
    ax.set_xticks(x)
    ax.set_xticklabels(model_names, fontsize=10, weight='bold')
    ax.legend(frameon=True, facecolor='#F7FAFC')
    ax.set_ylim(20, 70)
    
    for r in rects1:
        h = r.get_height()
        ax.annotate(f'{h:.1f}%', xy=(r.get_x() + r.get_width()/2, h), xytext=(0, 3),
                    textcoords='offset points', ha='center', va='bottom', fontsize=8.5, weight='bold')
    for r in rects2:
        h = r.get_height()
        ax.annotate(f'{h:.1f}%', xy=(r.get_x() + r.get_width()/2, h), xytext=(0, 3),
                    textcoords='offset points', ha='center', va='bottom', fontsize=8.5, weight='bold')
                    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'model_performance_chart.png'), dpi=200)
    plt.close()
        
    return results, trained_pipelines, best_candidate_name

def generate_comparison_markdown(results):
    md = "| Model | Candidate Selected | Val Accuracy | Val Macro F1 | Exploratory Test Acc | Exploratory Test Macro F1 | Exploratory Test Weighted F1 |\n"
    md += "|---|---|---|---|---|---|---|\n"
    for name, m in results.items():
        sel = "⭐ YES" if m.get('is_selected_candidate', False) else "No"
        md += f"| **{name}** | {sel} | {m['val_accuracy']:.4f} | {m['val_f1_macro']:.4f} | {m['accuracy']:.4f} | {m['f1_macro']:.4f} | {m['f1_weighted']:.4f} |\n"
    return md
