#!/usr/bin/env python3
"""
Longbridge 连接测试脚本
"""

import sys
import os

# 添加路径
sys.path.insert(0, os.path.dirname(__file__))

from client import LongbridgeClient


def test_connection():
    """测试连接"""
    client = LongbridgeClient()
    return client.test_connection()


def test_quotes():
    """测试行情获取"""
    client = LongbridgeClient()
    client.connect()
    
    symbols = ["QQQ", "NVDA", "TSLA", "GOOGL", "MSFT"]
    
    print(f"\n📊 测试行情获取...")
    for symbol in symbols:
        quote = client.get_quote(symbol)
        print(f"   {symbol}: ${quote['price']} ({quote['change_pct']:+.2f}%)")
    
    return True


def test_order():
    """测试订单提交"""
    client = LongbridgeClient()
    
    print(f"\n💼 测试订单提交...")
    order = client.submit_order(
        symbol="QQQ",
        action="BUY",
        quantity=10,
        price=600.00,
        order_type="LIMIT"
    )
    
    print(f"   订单ID: {order['order_id']}")
    print(f"   状态: {order['status']}")
    
    return order['status'] == "FILLED"


def main():
    """主测试"""
    print("=" * 70)
    print("🧪 Longbridge Skill 测试")
    print("=" * 70)
    
    tests = [
        ("连接测试", test_connection),
        ("行情测试", test_quotes),
        ("订单测试", test_order)
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, "✅ 通过" if result else "❌ 失败"))
        except Exception as e:
            results.append((name, f"❌ 错误: {e}"))
    
    print("\n" + "=" * 70)
    print("📊 测试结果汇总")
    print("=" * 70)
    for name, result in results:
        print(f"   {name}: {result}")
    
    all_passed = all("✅" in r for _, r in results)
    
    print("\n" + "=" * 70)
    if all_passed:
        print("🎉 所有测试通过!")
    else:
        print("⚠️ 部分测试失败，请检查配置")
    print("=" * 70)
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
