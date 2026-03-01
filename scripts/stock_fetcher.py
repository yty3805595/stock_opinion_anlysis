#!/usr/bin/env python3
"""
东方财富 A股数据爬取和分析系统

功能：
1. 获取 A股实时数据
2. 按条件筛选股票
3. 执行三维选股策略
4. 生成选股报告
"""

import requests
import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Optional

# 配置
DB_PATH = "/Users/yintaoye/.openclaw/workspace/data/stocks.db"
REPORTS_PATH = "/Users/yintaoye/.openclaw/workspace/github_reports"

class EastMoneyFetcher:
    """东方财富数据爬取器"""
    
    def __init__(self):
        self.api_url = "https://push2.eastmoney.com/api/qt/clist/get"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
    def get_stocks(self, market: str = "sh", sort_by: str = "f3", limit: int = 100) -> List[Dict]:
        """
        获取股票列表
        
        market: sh=上海, sz=深圳, bj=北京, cy=创业板, kcb=科创板
        sort_by: f3=涨跌幅, f2=价格, f8=换手率
        """
        market_map = {
            "sh": "m:1+t:2,m:1+t:23",  # 上海
            "sz": "m:0+t:6,m:0+t:80",   # 深圳
            "cy": "m:0+t:80",            # 创业板
            "kcb": "m:1+t:23"           # 科创板
        }
        
        params = {
            'pn': 1,
            'pz': limit,
            'po': 1,
            'np': 1,
            'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
            'fid': sort_by,
            'fs': market_map.get(market, market_map["sz"]),
            'fields': 'f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f22,f11,f62,f128,f136,f115,f152'
        }
        
        try:
            resp = requests.get(self.api_url, params=params, timeout=10)
            data = resp.json()
            return data.get('data', {}).get('diff', [])
        except Exception as e:
            print(f"❌ 获取数据失败: {e}")
            return []
    
    def get_all_markets(self) -> List[Dict]:
        """获取所有市场股票"""
        all_stocks = []
        markets = ["sh", "sz", "cy", "kcb"]
        
        for market in markets:
            stocks = self.get_stocks(market, limit=200)
            all_stocks.extend(stocks)
            print(f"✅ {market}: 获取 {len(stocks)} 只")
        
        return all_stocks


class StockAnalyzer:
    """股票分析器 - 三维选股策略"""
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.init_db()
    
    def init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stocks (
                code TEXT PRIMARY KEY,
                name TEXT,
                price REAL,
                change_pct REAL,
                volume REAL,
                turnover REAL,
                amplitude REAL,
                high REAL,
                low REAL,
                open_price REAL,
                prev_close REAL,
                turnover_rate REAL,
                pe REAL,
                pb REAL,
                market_cap REAL,
                update_time TEXT,
                market TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_picks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT,
                name TEXT,
                score INTEGER,
                reason TEXT,
                pick_time TEXT,
                status TEXT DEFAULT 'pending'
            )
        """)
        
        conn.commit()
        conn.close()
        print(f"✅ 数据库初始化完成")
    
    def save_stocks(self, stocks: List[Dict], market: str = ""):
        """保存股票数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        for s in stocks:
            cursor.execute("""
                INSERT OR REPLACE INTO stocks 
                (code, name, price, change_pct, volume, turnover, amplitude, 
                 high, low, open_price, prev_close, turnover_rate, 
                 pe, pb, market_cap, update_time, market)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                s.get('f12'), s.get('f14'), s.get('f2'), s.get('f3'),
                s.get('f6'), s.get('f8'), s.get('f7'),
                s.get('f15'), s.get('f17'), s.get('f18'), s.get('f4'),
                s.get('f8'), s.get('f162'), s.get('f167'), s.get('f20'),
                now, market
            ))
        
        conn.commit()
        conn.close()
        print(f"✅ 已保存 {len(stocks)} 只股票")
    
    def screen_stocks(self, 
                      min_change: float = 3.0,
                      max_change: float = 10.0,
                      min_turnover: float = 3.0) -> List[Dict]:
        """
        三维选股策略筛选
        
        基本面: 涨幅 3-10%, 换手率 > 3%
        技术面: 待实现（需要K线数据）
        结构: 待实现（需要趋势数据）
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = """
            SELECT * FROM stocks 
            WHERE change_pct >= ? AND change_pct <= ?
            AND turnover_rate >= ?
            ORDER BY change_pct DESC
        """
        
        cursor.execute(query, (min_change, max_change, min_turnover))
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return results
    
    def calculate_score(self, stock: Dict) -> tuple:
        """
        计算选股分数（三维评分）
        
        返回: (分数, 评分理由)
        """
        score = 0
        reasons = []
        
        # 基本面 (0-50分)
        change = stock.get('change_pct', 0)
        turnover = stock.get('turnover_rate', 0)
        
        if 3 <= change <= 5:
            score += 20
            reasons.append("涨幅3-5%")
        elif 5 < change <= 10:
            score += 25
            reasons.append("涨幅5-10%")
        
        if turnover > 5:
            score += 15
            reasons.append("换手率>5%")
        elif turnover > 3:
            score += 10
            reasons.append("换手率>3%")
        
        # 技术面 (0-30分) - 待扩展
        score += 15  # 基础分
        
        # 结构 (0-20分) - 待扩展
        score += 10  # 基础分
        
        return score, ", ".join(reasons) if reasons else "基础评分"
    
    def run_screening(self) -> List[Dict]:
        """执行选股"""
        # 1. 获取数据
        print("📥 获取股票数据...")
        fetcher = EastMoneyFetcher()
        all_stocks = fetcher.get_all_markets()
        
        # 2. 保存到数据库
        print("💾 保存数据...")
        self.save_stocks(all_stocks)
        
        # 3. 筛选
        print("🔍 执行三维筛选...")
        stocks = self.screen_stocks(min_change=3.0, max_change=10.0, min_turnover=3.0)
        
        # 4. 计算分数
        picks = []
        for s in stocks:
            score, reason = self.calculate_score(s)
            if score >= 30:  # 至少30分
                picks.append({
                    **s,
                    'score': score,
                    'reason': reason
                })
        
        return picks


def generate_report(picks: List[Dict]):
    """生成选股报告"""
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    report = f"""# 📊 A股三维选股报告

**生成时间**: {now}  
**选股数量**: {len(picks)} 只

---

## 🎯 选股结果

| 代码 | 名称 | 涨幅 | 换手率 | 评分 | 理由 |
|------|------|------|---------|------|------|
"""
    
    for p in picks[:30]:
        report += f"| {p.get('code', '')} | {p.get('name', '')[:6]} | {p.get('change_pct', 0):.2f}% | {p.get('turnover_rate', 0):.1f}% | {p.get('score', 0)} | {p.get('reason', '-')} |\n"
    
    report += f"""
---

## 📊 统计

- **总数**: {len(picks)} 只
- **最高涨幅**: {max(p['change_pct'] for p in picks):.2f}% (如有)
- **平均换手率**: {sum(p.get('turnover_rate', 0) for p in picks)/len(picks):.1f}% (如有)

---

## 🎯 选股策略（三维一体）

1. **基本面**: 涨幅 3-10%, 换手率 > 3%
2. **技术面**: 待实现（需要K线数据）
3. **结构**: 待实现（需要趋势数据）

---

*由 Agent Team 自动生成*
"""
    
    # 保存报告
    filename = f"{REPORTS_PATH}/a_stock_screening_{datetime.now().strftime('%Y%m%d')}.md"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(report)
    
    return filename


def main():
    """主函数"""
    import sys
    
    analyzer = StockAnalyzer()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "--fetch":
            # 只获取数据
            fetcher = EastMoneyFetcher()
            stocks = fetcher.get_all_markets()
            analyzer.save_stocks(stocks)
            
        elif command == "--screen":
            # 只筛选
            picks = analyzer.screen_stocks()
            print(f"\n🎯 选出 {len(picks)} 只股票:")
            for p in picks[:20]:
                print(f"  {p['code']} {p['name']}: {p['change_pct']:.2f}%")
            
        elif command == "--full":
            # 完整选股流程
            picks = analyzer.run_screening()
            
            print(f"\n🎯 选出 {len(picks)} 只股票:")
            for p in picks[:20]:
                print(f"  {p.get('code')} {p.get('name')}: {p.get('change_pct'):.2f}%, 换手率{p.get('turnover_rate'):.1f}%, 评分{p.get('score')}")
            
            # 生成报告
            filename = generate_report(picks)
            print(f"\n✅ 报告已保存: {filename}")
        
        else:
            print("""
使用方式:
  python3 stock_fetcher.py --fetch   # 获取数据
  python3 stock_fetcher.py --screen  # 筛选股票
  python3 stock_fetcher.py --full    # 完整流程
            """)
    else:
        # 默认完整流程
        picks = analyzer.run_screening()
        
        print(f"\n🎯 选出 {len(picks)} 只股票:")
        for p in picks[:20]:
            print(f"  {p.get('code')} {p.get('name')}: {p.get('change_pct'):.2f}%")
        
        filename = generate_report(picks)
        print(f"\n✅ 报告已保存: filename")


if __name__ == "__main__":
    main()
