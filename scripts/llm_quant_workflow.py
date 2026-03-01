#!/usr/bin/env python3
"""
LLM + Quant 完整工作流

流程：
1. LLM 分析市场
2. LLM 生成信号
3. Quant 验证信号
4. Quant 执行订单
5. Quant 监控持仓
"""

import json
from datetime import datetime
import sys

# 添加脚本路径
sys.path.append('/Users/yintaoye/.openclaw/workspace/scripts')

from llm_strategy import LLMStrategyEngine
from quant_executor import QuantExecutor


def run_workflow():
    """运行完整工作流"""
    print("\n" + "=" * 70)
    print("🔄 LLM + Quant 完整工作流")
    print("=" * 70)
    
    # 初始化
    llm = LLMStrategyEngine()
    quant = QuantExecutor()
    
    # ============ 第一步：LLM 分析市场 ============
    print("\n📊 第一步：LLM 市场分析")
    print("-" * 50)
    market = llm.analyze_market()
    print(f"   宏观判断: {market['macro']['overall']}")
    print(f"   Fed政策: {market['macro']['fed_policy']}")
    print(f"   市场情绪: {market['sentiment']['label']}")
    print(f"   技术趋势: {market['technical']['trend']}")
    
    # ============ 第二步：LLM 生成信号 ============
    print("\n📈 第二步：LLM 生成交易信号")
    print("-" * 50)
    signal = llm.generate_signal(market, "EOF")
    print(f"   ✅ 信号ID: {signal.signal_id}")
    print(f"   🎯 动作: {signal.action} {signal.symbol}")
    print(f"   📊 数量: {signal.quantity}")
    print(f"   💰 价格: ${signal.price}")
    print(f"   🛡️ 止损: ${signal.stop_loss}")
    print(f"   🎯 止盈: ${signal.take_profit}")
    print(f"   📈 置信度: {signal.confidence:.0%}")
    print(f"   📝 原因: {signal.reason}")
    
    # LLM 分析
    print(f"\n   🧠 LLM 分析:")
    print(f"      市场: {signal.llm_analysis['market']}")
    print(f"      技术: {signal.llm_analysis['technical']}")
    print(f"      基本面: {signal.llm_analysis['fundamental']}")
    
    # ============ 第三步：Quant 验证信号 ============
    print("\n⚡ 第三步：Quant 验证信号")
    print("-" * 50)
    
    signal_dict = {
        "action": signal.action,
        "symbol": signal.symbol,
        "quantity": signal.quantity,
        "price": signal.price,
        "stop_loss": signal.stop_loss,
        "take_profit": signal.take_profit
    }
    
    validation = quant.validate_signal(signal_dict)
    print(f"   ✅ 验证结果: {'通过' if validation['valid'] else '失败'}")
    
    if validation['errors']:
        print(f"   ❌ 错误: {validation['errors']}")
    
    if validation['warnings']:
        print(f"   ⚠️ 警告: {validation['warnings']}")
    
    # ============ 第四步：Quant 执行订单 ============
    print("\n💼 第四步：Quant 执行订单")
    print("-" * 50)
    
    if validation['valid']:
        order = quant.submit_order(signal_dict)
        print(f"   📝 订单ID: {order.order_id}")
        print(f"   📊 状态: {order.status}")
        print(f"   💰 成交价: ${order.filled_price:.2f}")
        print(f"   ⏰ 成交时间: {order.filled_time}")
    else:
        print(f"   ❌ 订单被拒绝")
        return
    
    # ============ 第五步：Quant 监控持仓 ============
    print("\n👁️ 第五步：Quant 监控持仓")
    print("-" * 50)
    
    # 检查止盈止损
    alerts = quant.monitor_positions()
    
    if alerts:
        print("   🚨 警报:")
        for alert in alerts:
            print(f"      {alert['type']}: {alert['symbol']} {alert['pct']:.2%} - {alert['action']}")
    else:
        print("   ✅ 无警报")
    
    # 持仓状态
    status = quant.get_status()
    print(f"\n   📊 账户状态:")
    print(f"      总资金: ${status['total_capital']:,.2f}")
    print(f"      总仓位: {status['position_weight']:.1%}")
    print(f"      未实现盈亏: ${status['unrealized_pnl']:,.2f}")
    
    print("\n" + "=" * 70)
    print("✅ 工作流完成")
    print("=" * 70)
    
    # 保存结果
    result = {
        "timestamp": datetime.now().isoformat(),
        "llm": {
            "market": market,
            "signal": {
                "signal_id": signal.signal_id,
                "action": signal.action,
                "symbol": signal.symbol,
                "quantity": signal.quantity,
                "price": signal.price,
                "stop_loss": signal.stop_loss,
                "take_profit": signal.take_profit,
                "confidence": signal.confidence,
                "reason": signal.reason,
                "analysis": signal.llm_analysis
            }
        },
        "quant": {
            "validation": validation,
            "order": order.__dict__,
            "status": status,
            "alerts": alerts
        }
    }
    
    with open('/tmp/llm_quant_workflow.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 结果已保存: /tmp/llm_quant_workflow.json")
    
    return result


def show_system_status():
    """显示系统状态"""
    print("\n" + "=" * 70)
    print("📊 LLM + Quant 系统状态")
    print("=" * 70)
    
    print("\n🤖 LLM 策略引擎")
    print("-" * 50)
    print("   ✅ 市场分析")
    print("   ✅ 策略开发")
    print("   ✅ 信号生成")
    print("   ✅ 风险评估")
    
    print("\n⚡ 量化执行引擎")
    print("-" * 50)
    print("   ✅ 信号验证")
    print("   ✅ 订单执行")
    print("   ✅ 仓位管理")
    print("   ✅ 止盈止损监控")
    
    print("\n📋 分工")
    print("-" * 50)
    print("   🤖 LLM: 思考 + 创造")
    print("   ⚡ Quant: 执行 + 纪律")
    print("   📊 目标: 跑赢市场")
    
    print("\n" + "=" * 70)


def main():
    """主函数"""
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == 'status':
            show_system_status()
        else:
            print("用法: python3 llm_quant_workflow.py [status]")
    else:
        result = run_workflow()
        
        # 显示分工
        print("\n" + "=" * 70)
        print("💡 分工说明")
        print("=" * 70)
        print("\n🤖 LLM 负责:")
        print("   - 分析宏观经济")
        print("   - 研究行业趋势")
        print("   - 设计交易策略")
        print("   - 生成交易信号")
        print("   - 评估风险")
        
        print("\n⚡ Quant 负责:")
        print("   - 验证信号有效性")
        print("   - 执行交易订单")
        print("   - 管理仓位")
        print("   - 监控止盈止损")
        print("   - 控制风险")
        
        print("\n🎯 核心理念:")
        print("   'LLM 负责思考，Quant 负责执行'")
        print("=" * 70)


if __name__ == "__main__":
    main()
