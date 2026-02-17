#!/usr/bin/env python3
"""
长桥 API 测试脚本
"""

import os
import sys
import json
from pathlib import Path

# 查找凭证文件
CREDENTIALS_PATHS = [
    "skills/longbridge-trading/config/credentials.json",
]

def load_credentials():
    """从配置文件加载凭证"""
    print("="*70)
    print("🔍 查找配置文件...")
    
    for path_str in CREDENTIALS_PATHS:
        path = Path(path_str)
        if path.exists():
            print(f"  找到: {path}")
            with open(path) as f:
                data = json.load(f)
                return data.get("credentials", {})
    
    return None

def main():
    print("\n" + "="*70)
    print("🚀 长桥 API 测试")
    print("="*70)
    
    # 加载凭证
    credentials = load_credentials()
    
    if not credentials:
        print("❌ 未找到配置文件")
        sys.exit(1)
    
    print(f"\n凭证信息:")
    print(f"  app_id: {credentials.get('app_id')}")
    print(f"  app_key: {credentials.get('app_key')[:20]}...")
    print(f"  app_secret: {credentials.get('app_secret')[:20]}...")
    print(f"  access_token: {credentials.get('access_token')[:50]}...")
    
    # 设置环境变量
    os.environ["LONGBRIDGE_APP_ID"] = credentials.get("app_id", "")
    os.environ["LONGBRIDGE_APP_KEY"] = credentials.get("app_key", "")
    os.environ["LONGBRIDGE_APP_SECRET"] = credentials.get("app_secret", "")
    os.environ["LONGBRIDGE_ACCESS_TOKEN"] = credentials.get("access_token", "")
    
    print("\n✅ 环境变量已设置")
    
    # 测试 SDK
    try:
        from longbridge.openapi import Config, QuoteContext
        
        config = Config(
            app_key=credentials.get("app_key"),
            app_secret=credentials.get("app_secret"),
            access_token=credentials.get("access_token", "")
        )
        
        quote = QuoteContext(config)
        print("✅ 行情客户端初始化成功!")
        
        print("\n" + "="*70)
        print("🎉 长桥 API 配置成功!")
        print("="*70)
        print("""
现在可以:
1. 运行交易系统:
   python scripts/main_trading_system.py --mode signal
""")
        
    except Exception as e:
        print(f"\n❌ SDK 测试失败: {e}")
        print("\n可能原因:")
        print("1. SDK 版本问题")
        print("2. 权限不足")
        print("请参考: https://longbridge.global/docs")

if __name__ == "__main__":
    main()
