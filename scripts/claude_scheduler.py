#!/usr/bin/env python3
"""
Claude Code 任务调度器

功能：
1. 管理 Claude Code 任务
2. 零轮询调用
3. Hooks 回调集成
4. 结果处理
"""

import os
import json
import subprocess
import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

# ============ 配置 ============
WORKSPACE = "/Users/yintaoye/.openclaw/workspace"
CLAUDE_CONFIG = {
    "timeout": 3600,  # 1小时超时
    "output_file": "/tmp/claude_code_output.log",
    "result_file": "/tmp/claude_code_result.json"
}

TASKS = {
    "quant_factors": {
        "description": "生成量化因子库",
        "prompt": """
Create a comprehensive Python quantitative factor library in scripts/quant_factors.py with:

1. **Momentum Factors**:
   - RSI (14-day)
   - MACD (12, 26, 9)
   - ADX (14-day)
   - Stochastic %K
   - CCI (20-day)

2. **Trend Factors**:
   - SMA (5, 20, 60-day)
   - EMA (12, 26-day)
   - MA Crossover Signal

3. **Volatility Factors**:
   - ATR (14-day)
   - Bollinger Bands (20-day, 2 std)
   - Historical Volatility (20-day)

4. **Volume Factors**:
   - OBV
   - VWAP
   - Volume Ratio (5-day)

5. **Quality**:
   - Clean structure with dataclasses
   - Comprehensive docstrings
   - Unit tests using pytest
   - Type hints

Save to: scripts/quant_factors.py

Include:
- FactorEngine class to calculate all factors
- FactorResult dataclass
- Usage examples in __main__
- Factor evaluation metrics (IC, Rank IC)
""",
        "output_file": "scripts/quant_factors.py",
        "timeout": 1800
    },
    
    "backtest": {
        "description": "构建回测框架",
        "prompt": """
Build a backtesting framework in scripts/backtest.py with:

1. **Strategy Base Class**:
   - Abstract methods (generate_signals, calculate_position)
   - Risk management integration

2. **Strategies**:
   - MA Crossover (MA5/MA20)
   - RSI Strategy (overbought/oversold)
   - Breakout Strategy

3. **Performance Metrics**:
   - Total Return
   - Annual Return
   - Sharpe Ratio
   - Sortino Ratio
   - Maximum Drawdown
   - Win Rate

4. **Visualization**:
   - Equity Curve
   - Drawdown Chart
   - Signal Markers on Price

5. **Features**:
   - Walk-forward analysis
   - Monte Carlo simulation
   - Transaction costs

Save to: scripts/backtest.py
""",
        "output_file": "scripts/backtest.py",
        "timeout": 1800
    },
    
    "ml_model": {
        "description": "创建ML交易模型",
        "prompt": """
Create a machine learning trading model in scripts/ml_trading_model.py:

1. **Feature Engineering**:
   - Alpha factors from quant_factors.py
   - Technical indicators
   - Fundamental features (PE, ROE, etc.)

2. **Model**:
   - XGBoost classifier for direction prediction
   - Feature importance analysis
   - Cross-validation with time-series split

3. **Pipeline**:
   - Data preprocessing
   - Feature scaling
   - Model training
   - Inference

4. **Evaluation**:
   - Accuracy
   - Precision/Recall
   - Confusion Matrix
   - Out-of-sample testing

Save to: scripts/ml_trading_model.py
""",
        "output_file": "scripts/ml_trading_model.py",
        "timeout": 2400
    },
    
    "strategy_eof": {
        "description": "EOF策略实现",
        "prompt": """
Implement the EOF (Economic Output Factor) strategy in scripts/eof_strategy.py:

1. **Strategy Logic**:
   - Buy when economic indicators improve
   - Sell when indicators deteriorate
   - Economic data sources (GDP, CPI, Fed Rate)

2. **Indicators**:
   - GDP Growth Rate
   - CPI Inflation
   - Fed Funds Rate
   - Yield Curve (10Y-2Y)

3. **Signal Generation**:
   - EOF Score calculation
   - Threshold-based signals
   - Position sizing

4. **Market Selection**:
   - US Stocks (QQQ, NVDA, TSLA, GOOGL, MSFT)
   - Sector rotation based on economic cycle

5. **Risk Management**:
   - Stop loss (-5%)
   - Take profit (+10%)
   - Maximum position (20%)
   - Maximum portfolio allocation (80%)

Save to: scripts/eof_strategy.py

Include comprehensive documentation and examples.
""",
        "output_file": "scripts/eof_strategy.py",
        "timeout": 1800
    }
}


@dataclass
class TaskResult:
    """任务结果"""
    task_name: str
    status: str  # success, failed, timeout
    output: str
    file_path: str
    timestamp: str
    duration: float
    error: Optional[str] = None


class ClaudeCodeScheduler:
    """Claude Code 任务调度器"""
    
    def __init__(self):
        self.tasks = TASKS
        self.results: List[TaskResult] = []
    
    def run_task(self, task_name: str) -> TaskResult:
        """运行单个任务"""
        if task_name not in self.tasks:
            return TaskResult(
                task_name=task_name,
                status="failed",
                output="",
                file_path="",
                timestamp=datetime.now().isoformat(),
                duration=0,
                error=f"Unknown task: {task_name}"
            )
        
        task = self.tasks[task_name]
        print(f"\n🚀 运行任务: {task['description']}")
        print(f"📝 Prompt 长度: {len(task['prompt'])} 字符")
        
        start_time = datetime.now()
        
        try:
            # 构建 Claude Code 命令
            cmd = [
                "claude-code",
                task['prompt'],
                "--no-interactive",
                "--output-format", "text"
            ]
            
            # 运行任务
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=task.get('timeout', 1800),
                cwd=WORKSPACE
            )
            
            duration = (datetime.now() - start_time).total_seconds()
            
            if result.returncode == 0:
                # 任务成功
                output_file = task['output_file']
                
                return TaskResult(
                    task_name=task_name,
                    status="success",
                    output=result.stdout,
                    file_path=output_file,
                    timestamp=datetime.now().isoformat(),
                    duration=duration
                )
            else:
                # 任务失败
                return TaskResult(
                    task_name=task_name,
                    status="failed",
                    output=result.stdout,
                    file_path=task['output_file'],
                    timestamp=datetime.now().isoformat(),
                    duration=duration,
                    error=result.stderr
                )
                
        except subprocess.TimeoutExpired:
            duration = (datetime.now() - start_time).total_seconds()
            return TaskResult(
                task_name=task_name,
                status="timeout",
                output="",
                file_path=task['output_file'],
                timestamp=datetime.now().isoformat(),
                duration=duration,
                error="Task timed out"
            )
        
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            return TaskResult(
                task_name=task_name,
                status="failed",
                output="",
                file_path=task['output_file'],
                timestamp=datetime.now().isoformat(),
                duration=duration,
                error=str(e)
            )
    
    def run_all(self) -> List[TaskResult]:
        """运行所有任务"""
        results = []
        
        for task_name in self.tasks.keys():
            result = self.run_task(task_name)
            results.append(result)
            self.results.append(result)
            
            print(f"\n{'='*70}")
            print(f"📊 任务结果: {task_name}")
            print(f"状态: {result.status}")
            if result.status == "success":
                print(f"输出文件: {result.file_path}")
            else:
                print(f"错误: {result.error}")
            print(f"耗时: {result.duration:.1f}秒")
        
        return results
    
    def get_status(self) -> Dict:
        """获取调度器状态"""
        success_count = sum(1 for r in self.results if r.status == "success")
        failed_count = sum(1 for r in self.results if r.status == "failed")
        
        return {
            "total_tasks": len(self.tasks),
            "completed": len(self.results),
            "success": success_count,
            "failed": failed_count,
            "pending": len(self.tasks) - len(self.results),
            "total_duration": sum(r.duration for r in self.results)
        }


def main():
    """主函数"""
    import sys
    
    scheduler = ClaudeCodeScheduler()
    
    if len(sys.argv) > 1:
        task_name = sys.argv[1]
        
        if task_name == "status":
            # 显示状态
            status = scheduler.get_status()
            print("\n📊 Claude Code 任务调度器状态")
            print("=" * 50)
            print(f"总任务数: {status['total_tasks']}")
            print(f"已完成: {status['completed']}")
            print(f"成功: {status['success']}")
            print(f"失败: {status['failed']}")
            print(f"待运行: {status['pending']}")
            print(f"总耗时: {status['total_duration']:.1f}秒")
            
            print("\n可用任务:")
            for name, task in TASKS.items():
                print(f"  • {name}: {task['description']}")
        
        elif task_name == "all":
            # 运行所有任务
            print("\n🚀 运行所有 Claude Code 任务")
            print("=" * 70)
            results = scheduler.run_all()
            
            print(f"\n📊 总结果: {len(results)} 个任务")
            success = sum(1 for r in results if r.status == "success")
            print(f"成功: {success}")
            print(f"失败: {len(results) - success}")
        
        elif task_name in TASKS:
            # 运行单个任务
            result = scheduler.run_task(task_name)
            
            print(f"\n{'='*70}")
            print(f"📊 任务结果: {task_name}")
            print(f"状态: {result.status}")
            
            if result.status == "success":
                print(f"输出文件: {result.file_path}")
            else:
                print(f"错误: {result.error}")
            
            print(f"耗时: {result.duration:.1f}秒")
        
        else:
            print(f"未知任务: {task_name}")
            print("\n可用任务:")
            for name, task in TASKS.items():
                print(f"  • {name}: {task['description']}")
    
    else:
        # 默认显示状态
        print("📊 Claude Code 任务调度器")
        print("=" * 50)
        print("用法:")
        print("  python3 scripts/claude_scheduler.py status   # 查看状态")
        print("  python3 scripts/claude_scheduler.py all      # 运行所有任务")
        print("  python3 scripts/claude_scheduler.py quant_factors  # 运行单个任务")
        print("\n可用任务:")
        for name, task in TASKS.items():
            print(f"  • {name}: {task['description']}")


if __name__ == "__main__":
    main()
