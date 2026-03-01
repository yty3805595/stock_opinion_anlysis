#!/usr/bin/env python3
"""
智能搜索系统

功能：
1. 优先使用 Tavily Search
2. Tavily 用完后自动切换到备用搜索
3. 自动统计使用量
4. 监控 API 配额
"""

import os
import json
import subprocess
import requests
from datetime import datetime
from typing import Dict, List

# 配置
TAVILY_LIMIT = 1000  # 每月限制
BING_LIMIT = 10000  # Bing 限制

class SmartSearch:
    """智能搜索系统"""
    
    def __init__(self):
        self.tavily_usage = 0
        self.bing_usage = 0
        self.ddg_usage = 0  # DuckDuckGo as backup
        self.load_usage()
        
    def load_usage(self):
        """加载使用统计"""
        try:
            with open('/tmp/search_usage.json', 'r') as f:
                data = json.load(f)
                self.tavily_usage = data.get('tavily', 0)
                self.bing_usage = data.get('bing', 0)
                self.ddg_usage = data.get('duckduckgo', 0)
        except:
            self.tavily_usage = 0
            self.bing_usage = 0
            self.ddg_usage = 0
    
    def save_usage(self):
        """保存使用统计"""
        with open('/tmp/search_usage.json', 'w') as f:
            json.dump({
                'tavily': self.tavily_usage,
                'bing': self.bing_usage,
                'duckduckgo': self.ddg_usage,
                'updated': datetime.now().isoformat()
            }, f, indent=2)
    
    def check_status(self) -> Dict:
        """检查使用状态"""
        tavily_left = max(0, TAVILY_LIMIT - self.tavily_usage)
        
        return {
            'tavily': {
                'used': self.tavily_usage,
                'limit': TAVILY_LIMIT,
                'remaining': tavily_left,
                'percentage': (self.tavily_usage / TAVILY_LIMIT) * 100
            },
            'bing': {
                'used': self.bing_usage,
                'limit': 'unlimited'
            },
            'duckduckgo': {
                'used': self.ddg_usage,
                'limit': 'unlimited'
            }
        }
    
    def search(self, query: str, num_results: int = 5) -> Dict:
        """
        智能搜索
        
        Args:
            query: 搜索关键词
            num_results: 返回结果数量
        """
        # 1. 优先使用 Tavily（如果还有配额）
        if self.tavily_usage < TAVILY_LIMIT:
            result = self._search_tavily(query, num_results)
            if result['status'] == 'success':
                self.tavily_usage += 1
                self.save_usage()
                return result
        
        # 2. Tavily 失败或用完，使用 DuckDuckGo
        result = self._search_duckduckgo(query, num_results)
        if result['status'] == 'success':
            self.ddg_usage += 1
            self.save_usage()
            return result
        
        # 3. 都失败
        return {
            'status': 'error',
            'message': '所有搜索方法都失败了',
            'sources_tried': ['tavily', 'duckduckgo']
        }
    
    def _search_tavily(self, query: str, num_results: int = 5) -> Dict:
        """Tavily 搜索"""
        try:
            os.environ['TAVILY_API_KEY'] = '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'
            
            result = subprocess.run([
                'node',
                '/Users/yintaoye/.openclaw/workspace/skills/tavily-search/scripts/search.mjs',
                query,
                '-n', str(num_results)
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                return {
                    'source': 'tavily',
                    'status': 'success',
                    'data': result.stdout,
                    'usage': self.tavily_usage
                }
            else:
                return {
                    'source': 'tavily',
                    'status': 'error',
                    'message': result.stderr
                }
                
        except Exception as e:
            return {
                'source': 'tavily',
                'status': 'error',
                'message': str(e)
            }
    
    def _search_duckduckgo(self, query: str, num_results: int = 5) -> Dict:
        """DuckDuckGo 搜索（备用方案）"""
        try:
            url = 'https://api.duckduckgo.com/'
            params = {
                'q': query,
                'format': 'json',
                'no_html': 1,
                'skip_disambig': 1
            }
            
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                results = []
                
                if 'RelatedTopics' in data:
                    for topic in data['RelatedTopics'][:num_results]:
                        if 'Text' in topic and 'FirstURL' in topic:
                            results.append({
                                'title': topic['Text'][:100],
                                'url': topic['FirstURL']
                            })
                
                return {
                    'source': 'duckduckgo',
                    'status': 'success',
                    'data': results,
                    'usage': self.ddg_usage
                }
            else:
                return {
                    'source': 'duckduckgo',
                    'status': 'error',
                    'message': f'HTTP {response.status_code}'
                }
                
        except Exception as e:
            return {
                'source': 'duckduckgo',
                'status': 'error',
                'message': str(e)
            }
    
    def print_status(self):
        """打印使用状态"""
        status = self.check_status()
        
        print("\n📊 搜索配额使用情况")
        print("=" * 50)
        
        # Tavily
        t = status['tavily']
        bar_len = int(t['percentage'] / 5)
        bar = '█' * bar_len + '░' * (20 - bar_len)
        print(f"\n🔍 Tavily Search")
        print(f"   已用: {t['used']}/{t['limit']} ({t['percentage']:.1f}%)")
        print(f"   {bar}")
        print(f"   剩余: {t['remaining']} 次")
        
        # DuckDuckGo
        d = status['duckduckgo']
        print(f"\n🦆 DuckDuckGo (备用)")
        print(f"   已用: {d['used']} (无限制)")
        
        print("\n" + "=" * 50)


def search(query: str, num_results: int = 5) -> Dict:
    """便捷搜索函数"""
    engine = SmartSearch()
    return engine.search(query, num_results)


def main():
    """主函数"""
    import sys
    
    search_engine = SmartSearch()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == 'status':
            # 显示状态
            search_engine.print_status()
        else:
            query = ' '.join(sys.argv[1:])
            num = 5
            if '--num' in sys.argv:
                idx = sys.argv.index('--num')
                if idx + 1 < len(sys.argv):
                    try:
                        num = int(sys.argv[idx + 1])
                    except:
                        pass
            
            print(f"🔍 搜索: {query}")
            print("-" * 50)
            
            result = search_engine.search(query, num)
            
            print(f"\n✅ 来源: {result['source']}")
            
            if result['status'] == 'success':
                if isinstance(result['data'], str):
                    print(f"\n结果:\n{result['data'][:500]}")
                else:
                    print(f"\n找到 {len(result['data'])} 个结果:")
                    for i, item in enumerate(result['data'][:5], 1):
                        if isinstance(item, dict):
                            print(f"\n{i}. {item.get('title', 'No title')}")
                            print(f"   {item.get('url', 'No URL')}")
                        else:
                            print(f"{i}. {item}")
            else:
                print(f"\n❌ 错误: {result.get('message', 'Unknown error')}")
    else:
        # 显示状态
        search_engine.print_status()
        
        print("\n💡 使用方式:")
        print("  python3 scripts/smart_search.py \"查询内容\"")
        print("  python3 scripts/smart_search.py status")
        print("  python3 scripts/smart_search.py \"A股选股\" --num 10")


if __name__ == "__main__":
    main()
