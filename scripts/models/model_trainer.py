#!/usr/bin/env python3
"""
模型训练器 - 使用 QLib 框架训练选股模型
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ModelConfig:
    """模型配置"""
    name: str
    enabled: bool
    weight: float
    params: Dict


class ModelTrainer:
    """
    模型训练器
    
    整合 QLib 模型训练框架
    """
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.models = {}
        self.model_configs = {
            "lightgbm": ModelConfig(
                name="LightGBM",
                enabled=True,
                weight=0.6,
                params={
                    "n_estimators": 100,
                    "max_depth": 5,
                    "learning_rate": 0.05,
                    "num_leaves": 31
                }
            ),
            "xgboost": ModelConfig(
                name="XGBoost",
                enabled=True,
                weight=0.3,
                params={
                    "n_estimators": 100,
                    "max_depth": 5,
                    "learning_rate": 0.05
                }
            )
        }
    
    def prepare_data(self, df: pd.DataFrame, label_col: str = "return_5d") -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """
        准备训练数据
        
        Args:
            df: 特征 DataFrame
            label_col: 标签列名
            
        Returns:
            X: 特征矩阵
            y: 标签向量
            feature_names: 特征名列表
        """
        # 标签：未来5日收益率
        if label_col not in df.columns:
            df[label_col] = df["close"].pct_change(5).shift(-5)
        
        # 特征列
        exclude_cols = ["date", "open", "high", "low", "close", "volume", label_col]
        feature_cols = [col for col in df.columns if col not in exclude_cols]
        
        # 清理数据
        df_clean = df[feature_cols + [label_col]].dropna()
        
        X = df_clean[feature_cols].values
        y = df_clean[label_col].values
        
        return X, y, feature_cols
    
    def train_lightgbm(self, X: np.ndarray, y: np.ndarray) -> object:
        """
        训练 LightGBM 模型
        """
        try:
            import lightgbm as lgb
            
            # 准备数据
            train_size = int(len(X) * 0.8)
            X_train, X_test = X[:train_size], X[train_size:]
            y_train, y_test = y[:train_size], y[train_size:]
            
            # 创建数据集
            train_data = lgb.Dataset(X_train, label=y_train)
            test_data = lgb.Dataset(X_test, label=y_test)
            
            # 参数
            params = {
                "objective": "regression",
                "metric": "mae",
                "boosting_type": "gbdt",
                "num_leaves": 31,
                "learning_rate": 0.05,
                "feature_fraction": 0.9,
                "bagging_fraction": 0.8,
                "bagging_freq": 5,
                "verbose": -1
            }
            
            # 训练
            model = lgb.train(
                params,
                train_data,
                num_boost_round=500,
                valid_sets=[test_data],
                callbacks=[lgb.early_stopping(50), lgb.log_evaluation(100)]
            )
            
            # 评估
            y_pred = model.predict(X_test)
            mse = np.mean((y_pred - y_test) ** 2)
            
            print(f"  LightGBM MSE: {mse:.6f}")
            
            self.models["lightgbm"] = model
            
            return model
            
        except ImportError:
            print("  ⚠️ LightGBM 未安装，使用模拟模型")
            return self._create_mock_model("lightgbm")
    
    def train_xgboost(self, X: np.ndarray, y: np.ndarray) -> object:
        """
        训练 XGBoost 模型
        """
        try:
            import xgboost as xgb
            
            # 准备数据
            train_size = int(len(X) * 0.8)
            X_train, X_test = X[:train_size], X[train_size:]
            y_train, y_test = y[:train_size], y[train_size:]
            
            # 参数
            params = {
                "objective": "reg:squarederror",
                "max_depth": 5,
                "learning_rate": 0.05,
                "eval_metric": "rmse"
            }
            
            # 训练
            model = xgb.train(
                params,
                xgb.DMatrix(X_train, label=y_train),
                num_boost_round=500,
                evals=[(xgb.DMatrix(X_test, label=y_test), "test")],
                early_stopping_rounds=50,
                verbose_eval=100
            )
            
            # 评估
            y_pred = model.predict(xgb.DMatrix(X_test))
            mse = np.mean((y_pred - y_test) ** 2)
            
            print(f"  XGBoost MSE: {mse:.6f}")
            
            self.models["xgboost"] = model
            
            return model
            
        except ImportError:
            print("  ⚠️ XGBoost 未安装，使用模拟模型")
            return self._create_mock_model("xgboost")
    
    def train_all(self, df: pd.DataFrame) -> Dict[str, object]:
        """
        训练所有模型
        
        Args:
            df: 特征 DataFrame
            
        Returns:
            训练好的模型字典
        """
        print("\n🧠 开始训练模型...")
        
        # 准备数据
        X, y, feature_names = self.prepare_data(df)
        
        models = {}
        
        # LightGBM
        if self.model_configs.get("lightgbm", ModelConfig("", False, 0, {})).enabled:
            print("\n  📦 训练 LightGBM...")
            models["lightgbm"] = self.train_lightgbm(X, y)
        
        # XGBoost
        if self.model_configs.get("xgboost", ModelConfig("", False, 0, {})).enabled:
            print("\n  📦 训练 XGBoost...")
            models["xgboost"] = self.train_xgboost(X, y)
        
        self.models = models
        
        return models
    
    def ensemble_predict(self, X: np.ndarray) -> np.ndarray:
        """
        集成预测
        
        使用加权平均组合多个模型
        """
        predictions = []
        weights = []
        
        for name, model in self.models.items():
            if model is not None:
                pred = self._predict(model, X)
                predictions.append(pred)
                
                # 获取模型权重
                weight = self.model_configs.get(name, ModelConfig("", True, 0.5, {})).weight
                weights.append(weight)
        
        if not predictions:
            return np.zeros(X.shape[0])
        
        # 归一化权重
        weights = np.array(weights) / sum(weights)
        
        # 加权平均
        ensemble = np.zeros_like(predictions[0])
        for pred, weight in zip(predictions, weights):
            ensemble += pred * weight
        
        return ensemble
    
    def _predict(self, model: object, X: np.ndarray) -> np.ndarray:
        """模型预测"""
        if model is None:
            return np.zeros(X.shape[0])
        
        try:
            # LightGBM
            if hasattr(model, "predict"):
                return model.predict(X)
        except:
            pass
        
        return np.zeros(X.shape[0])
    
    def _create_mock_model(self, name: str) -> object:
        """创建模拟模型"""
        class MockModel:
            def __init__(self, name):
                self.name = name
                
            def predict(self, X):
                # 返回随机预测
                return np.random.randn(X.shape[0]) * 0.02
            
            def feature_importance(self):
                return {"random": 0.5}
        
        return MockModel(name)
    
    def get_feature_importance(self) -> Dict[str, float]:
        """获取特征重要性"""
        if "lightgbm" not in self.models:
            return {}
        
        model = self.models["lightgbm"]
        
        if hasattr(model, "feature_importance"):
            importance = model.feature_importance()
            return dict(zip(range(len(importance)), importance))
        
        return {}


# 测试代码
if __name__ == "__main__":
    from data_handler import DataManager
    
    # 准备数据
    manager = DataManager({"symbols": ["QQQ"]})
    df = manager.get_klines("QQQ", period="365d")
    df = manager.create_features(df)
    
    # 训练模型
    trainer = ModelTrainer()
    models = trainer.train_all(df)
    
    print("\n✅ 训练完成!")
    print(f"模型列表: {list(models.keys())}")
