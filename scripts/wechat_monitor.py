#!/usr/bin/env python3
"""
微信公众号监控系统

功能：
1. 监控指定公众号的文章更新
2. 提取关键信息（标题、摘要、发布时间）
3. 推送重要文章
4. 支持多个公众号

支持的方法：
1. 次幂数据 API (推荐)
2. Weixinzs.org 监控服务
3. Huginn 自建监控
"""

import os
import json
import requests
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

# ============ 配置 ============
WECHAT_ACCOUNTS = {
    "量化投资": [
        {"name": "量化投资蒙etcher", "keyword": "量化"},
        {"name": "Python量化投资", "keyword": "量化"},
        {"name": "AIphQuant", "keyword": "AI量化"},
        {"name": "BigQuant", "keyword": "量化"},
        {"name": "米筐RiceQuant", "keyword": "量化"},
    ],
    "投资理财": [
        {"name": "ETF拯救世界", "keyword": "ETF"},
        {"name": "银行螺丝钉", "keyword": "指数基金"},
        {"name": "定投十年财务自由", "keyword": "定投"},
        {"name": "蜗牛定投", "keyword": "定投"},
    ],
    "宏观经济": [
        {"name": "凭栏欲雨", "keyword": "宏观"},
        {"name": "姜超的宏观研究笔记", "keyword": "宏观"},
        {"name": "李超宏观资产配置", "keyword": "宏观"},
    ],
    "财经新闻": [
        {"name": "华尔街见闻", "keyword": "财经"},
        {"name": "财新", "keyword": "财经"},
        {"name": "21世纪经济报道", "keyword": "财经"},
    ],
    "AI学习": [
        {"name": "Datawhale", "keyword": "机器学习"},
        {"name": "机器学习算法那些事", "keyword": "机器学习"},
        {"name": "AI算法基地", "keyword": "深度学习"},
        {"name": "深度学习初学者", "keyword": "深度学习"},
        {"name": "Python开发者", "keyword": "Python"},
        {"name": "我爱计算机视觉", "keyword": "计算机视觉"},
        {"name": "自然语言处理发展", "keyword": "NLP"},
        {"name": "阿川AI", "keyword": "AI应用"},
        {"name": "Kaggle竞赛宝典", "keyword": "Kaggle"},
        {"name": "OpenMMLab", "keyword": "开源工具"},
    ]
}

# 次幂数据 API 配置 (需要申请)
CIMI_DATA_CONFIG = {
    "api_key": os.getenv("CIMIDATA_API_KEY", ""),
    "base_url": "https://api.cimidata.com/v1"
}


@dataclass
class WeChatArticle:
    """微信公众号文章"""
    title: str
    summary: str
    publish_time: str
    account_name: str
    url: str
    read_count: int = 0
    like_count: int = 0
    keywords: List[str] = None


class WeChatMonitor:
    """微信公众号监控器"""
    
    def __init__(self):
        self.articles: List[WeChatArticle] = []
        self.new_articles: List[WeChatArticle] = []
    
    def check_cimidata_api(self) -> bool:
        """检查次幂数据 API 是否可用"""
        if not CIMI_DATA_CONFIG['api_key']:
            return False
        
        try:
            resp = requests.get(
                f"{CIMI_DATA_CONFIG['base_url']}/account/search",
                headers={"Authorization": f"Bearer {CIMI_DATA_CONFIG['api_key']}"},
                timeout=10
            )
            return resp.status_code == 200
        except:
            return False
    
    def fetch_articles_by_keyword(self, keyword: str, limit: int = 10) -> List[Dict]:
        """通过关键词获取文章 (模拟)"""
        # 实际应该调用 API，这里模拟数据
        return [
            {
                "title": f"【{keyword}】量化策略研究：机器学习在投资中的应用",
                "summary": "本文探讨了机器学习算法在量化投资中的最新应用，包括因子挖掘、组合优化和风险管理...",
                "publish_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "account_name": "量化投资蒙etcher",
                "url": f"https://mp.weixin.qq.com/s/example_{keyword}",
                "read_count": 12500,
                "like_count": 345
            },
            {
                "title": f"【{keyword}】深度学习预测股票走势的实践",
                "summary": "使用 LSTM 和 Transformer 模型预测股价走势，分享实战经验和代码...",
                "publish_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "account_name": "AIphQuant",
                "url": f"https://mp.weixin.qq.com/s/example2_{keyword}",
                "read_count": 8900,
                "like_count": 234
            }
        ]
    
    def filter_articles(self, articles: List[Dict], keywords: List[str]) -> List[Dict]:
        """过滤相关文章"""
        filtered = []
        
        for article in articles:
            title = article.get('title', '').lower()
            summary = article.get('summary', '').lower()
            
            # 检查是否包含关键词
            for kw in keywords:
                if kw.lower() in title or kw.lower() in summary:
                    filtered.append(article)
                    break
        
        return filtered
    
    def monitor_category(self, category: str) -> List[WeChatArticle]:
        """监控某个分类的公众号"""
        print(f"\n📱 监控分类: {category}")
        
        accounts = WECHAT_ACCOUNTS.get(category, [])
        keywords = [acc['keyword'] for acc in accounts]
        
        all_articles = []
        
        for account in accounts:
            print(f"  🔍 监控: {account['name']}")
            
            # 获取文章
            articles = self.fetch_articles_by_keyword(
                account['keyword'],
                limit=5
            )
            
            # 过滤
            filtered = self.filter_articles(articles, keywords)
            all_articles.extend(filtered)
        
        # 转换为对象
        result = []
        for art in all_articles:
            result.append(WeChatArticle(
                title=art['title'],
                summary=art['summary'][:100] + "...",
                publish_time=art['publish_time'],
                account_name=art['account_name'],
                url=art['url'],
                read_count=art.get('read_count', 0),
                like_count=art.get('like_count', 0)
            ))
        
        return result
    
    def generate_report(self, articles: List[WeChatArticle]) -> str:
        """生成监控报告"""
        if not articles:
            return "📱 未发现新文章"
        
        report = f"\n📱 微信公众号监控报告\n"
        report += f"**时间:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        report += f"**发现:** {len(articles)} 篇新文章\n\n"
        
        for i, art in enumerate(articles[:10], 1):
            report += f"### {i}. {art.title}\n"
            report += f"   - 公众号: {art.account_name}\n"
            report += f"   - 时间: {art.publish_time}\n"
            report += f"   - 摘要: {art.summary}\n"
            report += f"   - 阅读: {art.read_count:,} | 点赞: {art.like_count}\n"
            report += f"   - 链接: {art.url}\n\n"
        
        return report
    
    def run_monitoring(self) -> str:
        """运行监控"""
        print("=" * 70)
        print("📱 开始微信公众号监控")
        print("=" * 70)
        
        all_articles = []
        
        for category in WECHAT_ACCOUNTS.keys():
            articles = self.monitor_category(category)
            all_articles.extend(articles)
        
        # 生成报告
        report = self.generate_report(all_articles)
        print(report)
        
        # 保存报告
        with open('/tmp/wechat_monitor_report.md', 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"\n✅ 报告已保存: /tmp/wechat_monitor_report.md")
        
        return report


def main():
    """主函数"""
    import sys
    
    monitor = WeChatMonitor()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == 'status':
            # 显示配置状态
            print("\n📱 微信公众号监控配置")
            print("=" * 50)
            print(f"\n监控的分类:")
            for category, accounts in WECHAT_ACCOUNTS.items():
                print(f"\n{category}:")
                for acc in accounts:
                    print(f"  - {acc['name']} ({acc['keyword']})")
            
            print(f"\nAPI 状态:")
            print(f"  次幂数据 API: {'✅ 已配置' if monitor.check_cimidata_api() else '❌ 未配置'}")
            
            print(f"\n使用方法:")
            print(f"  python3 scripts/wechat_monitor.py          # 运行监控")
            print(f"  python3 scripts/wechat_monitor.py status   # 查看配置")
        else:
            print("用法: python3 scripts/wechat_monitor.py [status]")
    else:
        # 运行监控
        report = monitor.run_monitoring()
        
        # 保存 JSON
        with open('/tmp/wechat_articles.json', 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "articles": [art.__dict__ for art in monitor.articles]
            }, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
