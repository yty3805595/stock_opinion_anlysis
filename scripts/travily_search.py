#!/usr/bin/env python3
"""
Travily Search - Web Search Tool

API Key: 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
"""

import requests
import json
import os
from typing import List, Dict

class TravilySearch:
    """Travily Search API"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("TRAVILY_API_KEY", "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")
        self.base_url = "https://api.travily.com"
    
    def search(self, query: str, num_results: int = 10) -> List[Dict]:
        """
        Search the web
        
        Args:
            query: Search query
            num_results: Number of results to return
            
        Returns:
            List of search results
        """
        url = f"{self.base_url}/search"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "query": query,
            "num_results": num_results
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error: {response.status_code}")
                print(response.text)
                return []
                
        except Exception as e:
            print(f"Request failed: {e}")
            return []
    
    def get_news(self, query: str, num_results: int = 5) -> List[Dict]:
        """Get news results"""
        return self.search(query, num_results)


def main():
    """Test the search"""
    search = TravilySearch()
    
    print("=" * 60)
    print("🔍 Travily Search Test")
    print("=" * 60)
    
    results = search.search("Polymarket 教程", num_results=5)
    
    if results:
        print(f"\n✅ Found {len(results)} results:")
        for i, r in enumerate(results, 1):
            print(f"\n{i}. {r.get('title', 'No title')}")
            print(f"   {r.get('url', 'No URL')}")
    else:
        print("\n❌ No results or connection failed")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
