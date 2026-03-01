#!/usr/bin/env python3
"""
A股数据获取替代方案
使用 akshare 或 baostock（免费，无需积分）
"""

import os
import sys

def use_akshare():
    """使用 akshare 获取 A股数据"""
    print("=" * 80)
    print("📊 使用 akshare 获取 A股数据（免费）")
    print("=" * 80)
    
    try:
        import akshare as ak
        
        # 获取上证指数
        print("\n📈 获取上证指数...")
        try:
            sh_index = ak.stock_zh_index_spot()
            print("✅ 上证指数数据:")
            print(sh_index.head().to_string())
        except Exception as e:
            print(f"❌ 获取上证指数失败: {e}")
        
        # 获取 A股实时行情
        print("\n💹 获取 A股实时行情...")
        try:
            df = ak.stock_zh_a_spot_em()
            print(f"✅ 获取 {len(df)} 只 A股行情")
            print(df.head().to_string())
        except Exception as e:
            print(f"❌ 获取行情失败: {e}")
        
        # 获取资金流向
        print("\n💰 获取资金流向...")
        try:
            df = ak.stock_fund_flow_summary()
            print("✅ 资金流向:")
            print(df.head().to_string())
        except Exception as e:
            print(f"❌ 获取资金流向失败: {e}")
            
    except ImportError:
        print("❌ akshare 未安装")
        print("   安装: pip3 install akshare --user")

def use_baostock():
    """使用 baostock 获取 A股数据"""
    print("\n" + "=" * 80)
    print("📊 使用 baostock 获取 A股数据（免费）")
    print("=" * 80)
    
    try:
        import baostock as bs
        
        # 登录
        lg = bs.login()
        print(f"✅ baostock 登录: {lg.error_msg}")
        
        # 获取上证指数
        print("\n📈 获取上证指数...")
        rs = bs.query_sh_k_line("sh.000001", 2026, 2, 10, 2026, 2, 13)
        print("✅ 上证指数数据获取成功")
        
        # 登出
        bs.logout()
        
    except ImportError:
        print("❌ baostock 未安装")
        print("   安装: pip3 install baostock --user")

def use_eastmoney():
    """使用东方财富 API"""
    print("\n" + "=" * 80)
    print("📊 使用东方财富 API（无需安装）")
    print("=" * 80)
    
    # 使用 requests 直接调用东方财富接口
    print("\n📈 上证指数实时行情:")
    print("   URL: http://push2.eastmoney.com/api/qt/stock/get")
    print("   参数: secid=1.000001")
    print("\n💹 A股列表:")
    print("   URL: http://push2.eastmoney.com/api/qt/clist/get")
    print("   参数: pn=1,ps=50,fq=0")

def main():
    print("=" * 80)
    print("🐂 A股数据获取方案")
    print("=" * 80)
    
    print("\n📝 问题说明:")
    print("   Tushare 需要积分才能访问大部分接口")
    print("\n✅ 免费替代方案:")
    print("   1. akshare - Python 库，A股数据全面")
    print("   2. baostock - 证券宝，免费开源")
    print("   3. 东方财富 API - 直接调用")
    
    print("\n🚀 选择方案:")
    print("   [1] 使用 akshare (推荐)")
    print("   [2] 使用 baostock")
    print("   [3] 查看东方财富 API")
    print("   [4] 全部测试")
    
    choice = input("\n请选择 (1-4): ").strip()
    
    if choice == "1" or choice == "4":
        use_akshare()
    if choice == "2" or choice == "4":
        use_baostock()
    if choice == "3":
        use_eastmoney()

if __name__ == "__main__":
    main()
