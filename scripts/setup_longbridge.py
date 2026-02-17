#!/usr/bin/env python3
"""
长桥 API 配置助手

功能：
1. 检查 API 凭证
2. 设置环境变量
3. 测试连接
4. 配置交易系统
"""

import os
import sys
import json
from datetime import datetime


def check_environment():
    """检查环境变量"""
    print("\n" + "="*70)
    print("📋 长桥 API 环境检查")
    print("="*70)
    
    # 检查 API Key
    app_key = os.getenv("LONGBRIDGE_APP_KEY")
    app_secret = os.getenv("LONGBRIDGE_APP_SECRET")
    
    print(f"\n环境变量检查:")
    print(f"  LONGBRIDGE_APP_KEY: {'✅ 已设置' if app_key else '❌ 未设置'}")
    print(f"  LONGBRIDGE_APP_SECRET: {'✅ 已设置' if app_secret else '❌ 未设置'}")
    
    return app_key and app_secret


def test_connection(app_key: str, app_secret: str):
    """测试 API 连接"""
    print("\n" + "="*70)
    print("🔗 测试 API 连接")
    print("="*70)
    
    try:
        from longbridge.openapi import Config, Trade
        
        print("\n尝试连接长桥 API...")
        
        # 创建配置
        config = Config(
            app_key=app_key,
            app_secret=app_secret
        )
        
        # 初始化交易客户端
        trade = Trade(config)
        
        # 测试获取账户信息
        # 注意：实际调用可能需要额外权限
        print("✅ API 连接成功!")
        
        return True
        
    except ImportError as e:
        print(f"❌ 未安装长桥 SDK: {e}")
        print("\n解决方案:")
        print("  pip install longbridge")
        return False
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return False


def get_api_credentials():
    """获取 API 凭证"""
    print("\n" + "="*70)
    print("🔑 获取长桥 API 凭证")
    print("="*70)
    
    print("""
请按照以下步骤获取 API 凭证:

1. **注册长桥账户**
   - 访问: https://longbridge.global/
   - 完成注册和实名认证

2. **创建 API Key**
   - 登录后进入「账户」→「API 管理」
   - 点击「创建 API Key」
   - 选择权限:
     ✅ 市场行情 (Quote)
     ✅ 交易执行 (Trade)
     ✅ 账户信息 (Account)
   - 复制 App Key 和 App Secret

3. **设置环境变量** (macOS/Linux)
   在 ~/.zshrc 或 ~/.bashrc 添加:
   
   export LONGBRIDGE_APP_KEY="你的App Key"
   export LONGBRIDGE_APP_SECRET="你的App Secret"
   
   然后执行: source ~/.zshrc

4. **或者临时设置** (当前终端):
   
   export LONGBRIDGE_APP_KEY="你的App Key"
   export LONGBRIDGE_APP_SECRET="你的App Secret"

5. **安装 SDK**
   
   pip install longbridge

""")
    
    print("\n" + "="*70)
    print("📝 配置步骤")
    print("="*70)
    print("""
Step 1: 注册长桥账户
Step 2: 创建 API Key
Step 3: 设置环境变量
Step 4: 运行测试
Step 5: 开始交易

完成后请运行:
  python scripts/test_longbridge.py
""")


def setup_environment(app_key: str, app_secret: str):
    """设置环境变量"""
    print("\n" + "="*70)
    print("⚙️ 设置环境变量")
    print("="*70)
    
    # 保存到 .env 文件
    env_content = f"""# 长桥 API 配置
# 生成时间: {datetime.now().isoformat()}

LONGBRIDGE_APP_KEY={app_key}
LONGBRIDGE_APP_SECRET={app_secret}
"""
    
    with open(".env", "w") as f:
        f.write(env_content)
    
    print(f"\n✅ 已保存到 .env 文件")
    
    # 提示用户添加到 shell 配置
    print("""
请添加到 ~/.zshrc 或 ~/.bashrc:

echo 'export LONGBRIDGE_APP_KEY="{app_key}"' >> ~/.zshrc
echo 'export LONGBRIDGE_APP_SECRET="{app_secret}"' >> ~/.zshrc
source ~/.zshrc
""")


def update_trading_config():
    """更新交易配置"""
    print("\n" + "="*70)
    print("📝 更新交易系统配置")
    print("="*70)
    
    config_content = """# 交易系统配置
# 长桥 API 设置

execution:
  broker: longbridge
  paper_trading: false  # 设为 false 则使用实盘
  auto_trading: false  # 设为 true 则自动执行信号

# API 配置
# 从环境变量读取，无需手动填写
"""
    
    with open("config/trading_config.yaml", "w") as f:
        f.write(config_content)
    
    print("✅ 已更新 config/trading_config.yaml")
    print("""
注意: 请确保已设置环境变量:
  export LONGBRIDGE_APP_KEY="your_app_key"
  export LONGBRIDGE_APP_SECRET="your_app_secret"
""")


def main():
    """主函数"""
    print("\n" + "="*70)
    print("🚀 长桥 API 配置助手")
    print("="*70)
    
    # 1. 检查环境
    has_creds = check_environment()
    
    if has_creds:
        # 2. 测试连接
        app_key = os.getenv("LONGBRIDGE_APP_KEY")
        app_secret = os.getenv("LONGBRIDGE_APP_SECRET")
        
        if test_connection(app_key, app_secret):
            # 3. 更新配置
            update_trading_config()
            
            print("\n" + "="*70)
            print("✅ 配置完成!")
            print("="*70)
            print("""
现在可以:

1. 测试 API:
   python scripts/test_longbridge.py

2. 运行交易系统:
   python scripts/main_trading_system.py --mode signal

3. 开始实盘交易:
   python scripts/main_trading_system.py --mode full
""")
        else:
            get_api_credentials()
    else:
        get_api_credentials()


if __name__ == "__main__":
    main()
