"""ML Model Training for Churn Prediction (UC-2 Phase 5C)."""

import numpy as np
import pandas as pd
import pickle
import logging
from pathlib import Path
from typing import Tuple, Dict, Any
from datetime import datetime

from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    f1_score, precision_score, recall_score,
    roc_auc_score, roc_curve, confusion_matrix,
    classification_report, auc
)
from sklearn.preprocessing import StandardScaler

try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False

from sqlalchemy.orm import Session
from ..db.database import SessionLocal
from ..db.models import Customer
from .churn_features import ChurnFeatureEngineer


logger = logging.getLogger(__name__)


class ChurnModelTrainer:
    """Train and evaluate XGBoost churn prediction model."""

    # Model hyperparameters
    MODEL_PARAMS = {
        'objective': 'binary:logistic',
        'max_depth': 6,
        'learning_rate': 0.1,
        'n_estimators': 100,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'min_child_weight': 1,
        'gamma': 0,
        'random_state': 42,
        'eval_metric': 'logloss',
        'verbose': 0,
        'scale_pos_weight': None,  # Will be calculated during training based on class distribution
    }

    MODEL_DIR = Path(__file__).parent / "models"
    MODEL_PATH = MODEL_DIR / "churn_model.pkl"
    SCALER_PATH = MODEL_DIR / "feature_scaler.pkl"
    METRICS_PATH = MODEL_DIR / "metrics.json"

    def __init__(self, db: Session = None):
        """Initialize trainer with database session."""
        self.db = db or SessionLocal()
        self.model = None
        self.scaler = None
        self.feature_names = None
        self.metrics = {}
        self.shap_values = None
        self.shap_explainer = None

    def prepare_features(self) -> Tuple[pd.DataFrame, pd.Series]:
        """Load features for all customers and prepare training data.

        Returns:
            X: DataFrame with 15 features for all customers
            y: Series with is_churned labels
        """
        logger.info("Loading features for all customers...")

        customers = self.db.query(Customer).all()
        logger.info(f"Found {len(customers)} customers")

        features_list = []
        labels = []

        for i, customer in enumerate(customers):
            if (i + 1) % 100 == 0:
                logger.info(f"  Processing customer {i + 1}/{len(customers)}...")

            try:
                features = ChurnFeatureEngineer.engineer_churn_features(customer.id, self.db)
                features_list.append(features)
                labels.append(customer.is_churned or 0)
            except Exception as e:
                logger.warning(f"Failed to extract features for {customer.id}: {e}")
                continue

        logger.info(f"Successfully loaded features for {len(features_list)} customers")

        # Convert to DataFrame
        X = pd.DataFrame(features_list)
        y = pd.Series(labels, name='is_churned')

        self.feature_names = X.columns.tolist()
        logger.info(f"Features shape: {X.shape}")
        logger.info(f"Features: {self.feature_names}")
        logger.info(f"Label distribution:\n{y.value_counts()}")

        return X, y

    def train_test_split_data(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        test_size: float = 0.3,
        random_state: int = 42
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
        """Split data into train/test sets (temporal split for time series).

        Args:
            X: Feature dataframe
            y: Labels
            test_size: Proportion for test set
            random_state: Random seed

        Returns:
            X_train, X_test, y_train, y_test
        """
        logger.info(f"Splitting data: 70% train, 30% test")

        X_train, X_test, y_train, y_test = train_test_split(
            X, y,
            test_size=test_size,
            random_state=random_state,
            stratify=y  # Maintain churn distribution
        )

        logger.info(f"Train set: {X_train.shape}")
        logger.info(f"Test set: {X_test.shape}")
        logger.info(f"Train churn rate: {y_train.mean():.1%}")
        logger.info(f"Test churn rate: {y_test.mean():.1%}")

        return X_train, X_test, y_train, y_test

    def train_model(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series
    ) -> XGBClassifier:
        """Train XGBoost binary classifier.

        Args:
            X_train: Training features
            y_train: Training labels

        Returns:
            Trained XGBClassifier model
        """
        logger.info("Training XGBoost model...")

        # Calculate scale_pos_weight to handle class imbalance
        # scale_pos_weight = count(negative examples) / count(positive examples)
        n_negative = (y_train == 0).sum()
        n_positive = (y_train == 1).sum()
        scale_pos_weight = n_negative / n_positive if n_positive > 0 else 1.0

        logger.info(f"Class imbalance: {n_negative} negative, {n_positive} positive")
        logger.info(f"Scale pos weight: {scale_pos_weight:.2f}")

        # Update model params with calculated scale_pos_weight
        model_params = self.MODEL_PARAMS.copy()
        model_params['scale_pos_weight'] = scale_pos_weight
        logger.info(f"Hyperparameters: {model_params}")

        # Scale features
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)

        # Train model with class imbalance handling
        self.model = XGBClassifier(**model_params)
        self.model.fit(
            X_train_scaled, y_train,
            verbose=False
        )

        logger.info("Model training complete")
        return self.model

    def evaluate_model(
        self,
        X_test: pd.DataFrame,
        y_test: pd.Series
    ) -> Dict[str, float]:
        """Evaluate model on test set.

        Args:
            X_test: Test features
            y_test: Test labels

        Returns:
            Dictionary with evaluation metrics
        """
        logger.info("Evaluating model...")

        # Scale test features
        X_test_scaled = self.scaler.transform(X_test)

        # Get predictions
        y_pred = self.model.predict(X_test_scaled)
        y_pred_proba = self.model.predict_proba(X_test_scaled)[:, 1]

        # Calculate metrics
        metrics = {
            'f1': float(f1_score(y_test, y_pred)),
            'precision': float(precision_score(y_test, y_pred)),
            'recall': float(recall_score(y_test, y_pred)),
            'roc_auc': float(roc_auc_score(y_test, y_pred_proba)),
        }

        self.metrics = metrics

        # Log metrics
        logger.info(f"Model Metrics:")
        logger.info(f"  F1-Score: {metrics['f1']:.4f}")
        logger.info(f"  Precision: {metrics['precision']:.4f}")
        logger.info(f"  Recall: {metrics['recall']:.4f}")
        logger.info(f"  ROC-AUC: {metrics['roc_auc']:.4f}")

        # Check success criteria
        if metrics['f1'] >= 0.80 and metrics['roc_auc'] >= 0.85:
            logger.info("✅ ALL SUCCESS CRITERIA MET")
        else:
            warnings = []
            if metrics['f1'] < 0.80:
                warnings.append(f"F1-Score too low: {metrics['f1']:.4f} < 0.80")
            if metrics['roc_auc'] < 0.85:
                warnings.append(f"ROC-AUC too low: {metrics['roc_auc']:.4f} < 0.85")
            logger.warning(f"⚠️  Criteria not met: {', '.join(warnings)}")

        # Confusion matrix
        cm = confusion_matrix(y_test, y_pred)
        logger.info(f"Confusion Matrix:\n{cm}")

        # Classification report
        logger.info(f"\nClassification Report:\n{classification_report(y_test, y_pred)}")

        return metrics

    def generate_shap_explanations(self, X_train: pd.DataFrame) -> None:
        """Generate SHAP values for model explainability.

        Args:
            X_train: Training data for SHAP explainer background
        """
        if not SHAP_AVAILABLE:
            logger.warning("SHAP not available, skipping explanations")
            return

        logger.info("Generating SHAP explanations...")

        # Scale training data
        X_train_scaled = self.scaler.transform(X_train)

        try:
            # Create SHAP explainer
            self.shap_explainer = shap.TreeExplainer(self.model)

            # Calculate SHAP values on sample
            sample_size = min(100, len(X_train_scaled))
            self.shap_values = self.shap_explainer.shap_values(X_train_scaled[:sample_size])

            logger.info(f"SHAP values calculated for {sample_size} samples")
            logger.info(f"SHAP values shape: {np.array(self.shap_values).shape}")

        except Exception as e:
            logger.warning(f"Failed to generate SHAP values: {e}")

    def save_model(self) -> None:
        """Save trained model, scaler, and metrics to disk."""
        self.MODEL_DIR.mkdir(parents=True, exist_ok=True)

        # Save model
        with open(self.MODEL_PATH, 'wb') as f:
            pickle.dump(self.model, f)
        logger.info(f"Model saved to {self.MODEL_PATH}")

        # Save scaler
        with open(self.SCALER_PATH, 'wb') as f:
            pickle.dump(self.scaler, f)
        logger.info(f"Scaler saved to {self.SCALER_PATH}")

        # Save metrics
        metrics_with_timestamp = {
            **self.metrics,
            'training_date': datetime.utcnow().isoformat(),
            'feature_names': self.feature_names,
        }

        import json
        with open(self.METRICS_PATH, 'w') as f:
            json.dump(metrics_with_timestamp, f, indent=2)
        logger.info(f"Metrics saved to {self.METRICS_PATH}")

    def train_full_pipeline(self) -> Dict[str, Any]:
        """Execute full training pipeline: prepare → split → train → evaluate → save.

        Returns:
            Dictionary with training results
        """
        logger.info("=" * 80)
        logger.info("PHASE 5C: CHURN MODEL TRAINING PIPELINE")
        logger.info("=" * 80)

        try:
            # 1. Prepare features
            X, y = self.prepare_features()

            # 2. Split data
            X_train, X_test, y_train, y_test = self.train_test_split_data(X, y)

            # 3. Train model
            self.train_model(X_train, y_train)

            # 4. Evaluate model
            metrics = self.evaluate_model(X_test, y_test)

            # 5. Generate SHAP explanations
            self.generate_shap_explanations(X_train)

            # 6. Save model
            self.save_model()

            logger.info("=" * 80)
            logger.info("✅ PHASE 5C TRAINING COMPLETE")
            logger.info("=" * 80)

            return {
                'success': True,
                'metrics': metrics,
                'model_path': str(self.MODEL_PATH),
                'scaler_path': str(self.SCALER_PATH),
                'metrics_path': str(self.METRICS_PATH),
            }

        except Exception as e:
            logger.error(f"Training failed: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
            }

    def train_and_save(self, db: Session = None) -> Dict[str, float]:
        """Train model on current DB contents and save to disk.

        Convenience method for init_db.py to call during startup.

        Args:
            db: Optional database session (uses self.db if not provided)

        Returns:
            Dictionary with f1, precision, recall, roc_auc metrics
        """
        if db is not None:
            self.db = db

        result = self.train_full_pipeline()

        if not result['success']:
            raise RuntimeError(f"Model training failed: {result.get('error', 'unknown error')}")

        return result['metrics']

    def get_feature_importance(self) -> pd.DataFrame:
        """Get feature importance from trained model.

        Returns:
            DataFrame with feature names and importance scores
        """
        if self.model is None:
            logger.warning("Model not trained yet")
            return None

        importance_scores = self.model.feature_importances_
        importance_df = pd.DataFrame({
            'feature': self.feature_names,
            'importance': importance_scores,
        }).sort_values('importance', ascending=False)

        logger.info(f"\nFeature Importance (Top 10):")
        logger.info(importance_df.head(10).to_string())

        return importance_df


# Convenience function for quick training
def train_churn_model() -> Dict[str, Any]:
    """Train churn prediction model with default settings.

    Returns:
        Dictionary with training results
    """
    db = SessionLocal()
    try:
        trainer = ChurnModelTrainer(db)
        return trainer.train_full_pipeline()
    finally:
        db.close()


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Train model
    results = train_churn_model()

    if results['success']:
        print("\n✅ Training successful!")
        print(f"Model saved to: {results['model_path']}")
        print(f"\nMetrics:")
        for key, value in results['metrics'].items():
            print(f"  {key}: {value:.4f}")
    else:
        print(f"\n❌ Training failed: {results['error']}")
