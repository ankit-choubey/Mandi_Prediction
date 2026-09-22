"""
Machine Learning Models Module - 100% Pure Classification Suite
APMC Mandi Market Intelligence System

Implements:
1. Decision Tree Classifier
2. Random Forest Classifier
3. Extra Trees Classifier (Extremely Randomized Trees)
4. Gradient Boosting Classifier
5. Soft-Voting Ensemble (Combining Gradient Boosting, Random Forest, and Extra Trees)

Strictly zero regression algorithms. All models predict discrete market condition classes:
- Unfavorable (0)
- Normal (1)
- Favorable (2)
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import (
    RandomForestClassifier,
    ExtraTreesClassifier,
    GradientBoostingClassifier,
    VotingClassifier
)

def get_models(random_state=42):
    """
    Returns a dictionary of 5 pure classification models with appropriate imputation and scaling.
    """
    # Base individual classifiers
    dt = DecisionTreeClassifier(
        max_depth=8,
        min_samples_leaf=20,
        class_weight='balanced',
        random_state=random_state
    )
    
    rf = RandomForestClassifier(
        n_estimators=100,
        max_depth=12,
        min_samples_leaf=15,
        class_weight='balanced',
        n_jobs=-1,
        random_state=random_state
    )
    
    et = ExtraTreesClassifier(
        n_estimators=100,
        max_depth=12,
        min_samples_leaf=15,
        class_weight='balanced',
        n_jobs=-1,
        random_state=random_state
    )
    
    gb = GradientBoostingClassifier(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.1,
        random_state=random_state
    )
    
    voting = VotingClassifier(
        estimators=[
            ('gb', GradientBoostingClassifier(n_estimators=80, max_depth=4, learning_rate=0.1, random_state=random_state)),
            ('rf', RandomForestClassifier(n_estimators=80, max_depth=10, min_samples_leaf=15, class_weight='balanced', n_jobs=-1, random_state=random_state)),
            ('et', ExtraTreesClassifier(n_estimators=80, max_depth=10, min_samples_leaf=15, class_weight='balanced', n_jobs=-1, random_state=random_state))
        ],
        voting='soft'
    )
    
    models = {
        'Decision Tree': Pipeline([
            ('imputer', SimpleImputer(strategy='median')),
            ('classifier', dt)
        ]),
        'Random Forest': Pipeline([
            ('imputer', SimpleImputer(strategy='median')),
            ('classifier', rf)
        ]),
        'Extra Trees': Pipeline([
            ('imputer', SimpleImputer(strategy='median')),
            ('classifier', et)
        ]),
        'Gradient Boosting': Pipeline([
            ('imputer', SimpleImputer(strategy='median')),
            ('classifier', gb)
        ]),
        'Voting Ensemble': Pipeline([
            ('imputer', SimpleImputer(strategy='median')),
            ('classifier', voting)
        ])
    }
    return models

def get_feature_importances(model_pipeline, feature_names):
    """
    Extracts feature importances from tree pipelines or voting ensembles.
    """
    classifier = model_pipeline.named_steps['classifier']
    if hasattr(classifier, 'feature_importances_'):
        return dict(zip(feature_names, classifier.feature_importances_))
    elif isinstance(classifier, VotingClassifier):
        # Average feature importances of fitted estimators in voting ensemble
        importances = []
        for est in classifier.estimators_:
            if hasattr(est, 'feature_importances_'):
                importances.append(est.feature_importances_)
        if importances:
            avg_imp = np.mean(importances, axis=0)
            return dict(zip(feature_names, avg_imp))
    return {}
