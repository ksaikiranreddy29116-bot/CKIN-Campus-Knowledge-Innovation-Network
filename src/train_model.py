
import os
import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score
from config import Config


def generate_synthetic_training_data(n_samples=500, random_seed=42):
    np.random.seed(random_seed)

    years = np.random.choice([1, 2, 3, 4], size=n_samples, p=[0.1, 0.25, 0.4, 0.25])
    cgpas = np.round(np.random.normal(7.8, 1.0, size=n_samples).clip(5.0, 10.0), 2)
    avail_hours = np.random.choice([5, 10, 15, 20, 25], size=n_samples)
    past_scores = np.round(np.random.normal(82, 10, size=n_samples).clip(50, 100), 1)

    difficulties = np.random.choice([1, 2, 3, 4], size=n_samples)
    commitments = np.random.choice([5, 10, 15, 20], size=n_samples)
    team_sizes = np.random.choice([2, 3, 4, 5, 6], size=n_samples)

    skill_match_ratios = np.round(np.random.uniform(0.1, 1.0, size=n_samples), 2)
    missing_skills_counts = np.round((1.0 - skill_match_ratios) * 5)

    domain_matches = np.random.choice([0.0, 1.0], size=n_samples, p=[0.4, 0.6])
    type_matches = np.random.choice([0.0, 1.0], size=n_samples, p=[0.3, 0.7])

    commitment_fits = np.where(avail_hours >= commitments, 1.0, avail_hours / commitments)
    cgpa_fits = cgpas / 10.0
    difficulty_fits = np.where((years >= 3) | (difficulties <= 2), 1.0, 0.6)
    text_sim_scores = np.round(np.random.uniform(0.0, 0.9, size=n_samples), 2)

    X = np.column_stack([
        years, cgpas, avail_hours, past_scores,
        difficulties, commitments, team_sizes,
        skill_match_ratios, missing_skills_counts, domain_matches,
        type_matches, commitment_fits, cgpa_fits, difficulty_fits,
        text_sim_scores
    ])

    # Rule-based synthetic ground truth label generation for training
    score_signal = (
        0.30 * skill_match_ratios +
        0.20 * domain_matches +
        0.15 * commitment_fits +
        0.15 * cgpa_fits +
        0.10 * text_sim_scores +
        0.10 * (past_scores / 100.0)
    )

    labels = np.where(score_signal > 0.55, 1, 0)

    return X, labels


def train_and_save_model(models_dir=None):
    target_dir = models_dir or Config.MODELS_DIR
    os.makedirs(target_dir, exist_ok=True)

    X, y = generate_synthetic_training_data(n_samples=600)

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y
    )

    models = {
        'LogisticRegression': LogisticRegression(
            random_state=42,
            max_iter=1000
        ),
        'RandomForest': RandomForestClassifier(
            n_estimators=100,
            random_state=42
        ),
        'GradientBoosting': GradientBoostingClassifier(
            n_estimators=100,
            random_state=42
        )
    }

    results = {}
    best_model = None
    best_f1 = -1.0
    best_name = None

    print("\n" + "=" * 65)
    print("       CKIN - ML RECOMMENDATION MODEL TRAINING")
    print("=" * 65)
    print(f"Training samples: {len(X_train)}")
    print(f"Testing samples : {len(X_test)}")

    # Train and evaluate every model
    for name, model in models.items():

        print(f"\nTraining {name}...")

        model.fit(X_train, y_train)

        y_pred = model.predict(X_test)

        y_proba = (
            model.predict_proba(X_test)[:, 1]
            if hasattr(model, 'predict_proba')
            else y_pred
        )

        prec = precision_score(
            y_test, y_pred, zero_division=0
        )

        rec = recall_score(
            y_test, y_pred, zero_division=0
        )

        f1 = f1_score(
            y_test, y_pred, zero_division=0
        )

        try:
            auc = roc_auc_score(y_test, y_proba)
        except Exception:
            auc = 0.5

        results[name] = {
            'precision': prec,
            'recall': rec,
            'f1': f1,
            'auc': auc
        }

        # Print individual model scores
        print("-" * 45)
        print(f"Model     : {name}")
        print(f"Precision : {prec:.4f}")
        print(f"Recall    : {rec:.4f}")
        print(f"F1 Score  : {f1:.4f}")
        print(f"AUC       : {auc:.4f}")
        print("-" * 45)

        # Select the model with the highest F1 score
        if f1 > best_f1:
            best_f1 = f1
            best_model = model
            best_name = name

    # Print comparison of all models
    print("\n" + "=" * 85)
    print("                    ALL MODELS COMPARISON")
    print("=" * 85)

    print(
        f"{'Model':<22}"
        f"{'Precision':>14}"
        f"{'Recall':>12}"
        f"{'F1 Score':>12}"
        f"{'AUC':>12}"
    )

    print("-" * 85)

    for name, metrics in results.items():
        print(
            f"{name:<22}"
            f"{metrics['precision']:>14.4f}"
            f"{metrics['recall']:>12.4f}"
            f"{metrics['f1']:>12.4f}"
            f"{metrics['auc']:>12.4f}"
        )

    # Save the best model using the existing artifact structure
    model_path = os.path.join(
        target_dir,
        'recommendation_model.joblib'
    )

    artifact = {
        'model': best_model,
        'model_name': best_name,
        'metrics': results[best_name],
        'all_metrics': results
    }

    joblib.dump(artifact, model_path)

    # Print the final best model
    print("\n" + "=" * 65)
    print("                 BEST MODEL SELECTED")
    print("=" * 65)

    print(f"Best Model  : {best_name}")
    print(f"Precision   : {results[best_name]['precision']:.4f}")
    print(f"Recall      : {results[best_name]['recall']:.4f}")
    print(f"F1 Score    : {results[best_name]['f1']:.4f}")
    print(f"AUC         : {results[best_name]['auc']:.4f}")

    print("-" * 65)
    print(f"Model saved : {model_path}")
    print("=" * 65)
    print("Model training completed successfully!")

    return artifact
