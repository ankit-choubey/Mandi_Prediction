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

def chronological_split(dataset, train_ratio=0.70, val_ratio=0.15):
    """
    Splits dataset chronologically based on Arrival_Date.
    Train: earliest 70% dates
    Val: next 15% dates
    Test: final 15% dates
    """
    sorted_df = dataset.sort_values('Arrival_Date').reset_index(drop=True)
    dates = sorted_df['Arrival_Date'].drop_duplicates().sort_values().reset_index(drop=True)
    
    n_dates = len(dates)
    train_end_idx = int(n_dates * train_ratio)
    val_end_idx = int(n_dates * (train_ratio + val_ratio))
    
    train_cutoff = dates.iloc[train_end_idx]
    val_cutoff = dates.iloc[val_end_idx]
    
    train_df = sorted_df[sorted_df['Arrival_Date'] < train_cutoff].copy()
    val_df = sorted_df[(sorted_df['Arrival_Date'] >= train_cutoff) & (sorted_df['Arrival_Date'] < val_cutoff)].copy()
    test_df = sorted_df[sorted_df['Arrival_Date'] >= val_cutoff].copy()
    
    print(f"[ChronologicalSplit] Total Records: {len(sorted_df):,}")
    print(f"  - Train Split: {len(train_df):,} records ({train_df['Arrival_Date'].min().strftime('%Y-%m-%d')} to {train_df['Arrival_Date'].max().strftime('%Y-%m-%d')})")
    print(f"  - Val Split  : {len(val_df):,} records ({val_df['Arrival_Date'].min().strftime('%Y-%m-%d')} to {val_df['Arrival_Date'].max().strftime('%Y-%m-%d')})")
    print(f"  - Test Split : {len(test_df):,} records ({test_df['Arrival_Date'].min().strftime('%Y-%m-%d')} to {test_df['Arrival_Date'].max().strftime('%Y-%m-%d')})")
    
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
    
    for name, pipeline in models.items():
        print(f"\n[Training] Fitting {name}...")
        pipeline.fit(X_train, y_train)
        trained_pipelines[name] = pipeline
        
        # Predict on Test set
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
        
        print(f"[{name}] Test Accuracy: {acc:.4f} | F1 Macro: {f1_macro:.4f} | F1 Weighted: {f1_weighted:.4f}")
        
        # Save Confusion Matrix Plot
        plt.figure(figsize=(6, 5))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                    xticklabels=CLASS_NAMES, yticklabels=CLASS_NAMES)
        plt.title(f'Confusion Matrix: {name}')
        plt.xlabel('Predicted Condition')
        plt.ylabel('True Condition')
        plt.tight_layout()
        cm_filename = f"confusion_matrix_{name.lower().replace(' ', '_')}.png"
        plt.savefig(os.path.join(output_dir, cm_filename), dpi=200)
        plt.close()
    
    # Generate Feature Importance Plot for Random Forest
    rf_importances = results['Random Forest']['feature_importances']
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
    acc_vals = [results[m]['accuracy'] * 100 for m in model_names]
    f1_vals = [results[m]['f1_macro'] * 100 for m in model_names]
    
    fig, ax = plt.subplots(figsize=(10, 5), dpi=200)
    x = np.arange(len(model_names))
    width = 0.35
    
    rects1 = ax.bar(x - width/2, acc_vals, width, label='Test Accuracy (%)', color='#2B6CB0')
    rects2 = ax.bar(x + width/2, f1_vals, width, label='Macro F1-Score (%)', color='#319795')
    
    ax.set_ylabel('Percentage (%)', fontsize=11)
    ax.set_title('Test Set Performance Across Pure Classification Models', fontsize=13, weight='bold', pad=12, color='#1A365D')
    ax.set_xticks(x)
    ax.set_xticklabels(model_names, fontsize=10, weight='bold')
    ax.legend(frameon=True, facecolor='#F7FAFC')
    ax.set_ylim(35, 70)
    
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
        
    return results, trained_pipelines

def generate_comparison_markdown(results):
    md = "| Model | Test Accuracy | Precision (Macro) | Recall (Macro) | F1-Score (Macro) | F1-Score (Weighted) |\n"
    md += "|---|---|---|---|---|---|\n"
    for name, m in results.items():
        md += f"| **{name}** | {m['accuracy']:.4f} | {m['precision_macro']:.4f} | {m['recall_macro']:.4f} | {m['f1_macro']:.4f} | {m['f1_weighted']:.4f} |\n"
    return md
