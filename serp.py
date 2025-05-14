# serp.py

import os
from serpapi import GoogleSearch

class Serp:
    """
    Wrapper nhỏ gọn cho GoogleSearch (SerpAPI).
    Phương thức .search(message, num_results) sẽ trả về list các dict (giống như môi trường thật).
    """
    def __init__(self, api_key: str = None):
        if api_key is None:
            api_key = os.getenv("SERPAPI_API_KEY")
        if not api_key:
            raise RuntimeError("Thiếu biến môi trường SERPAPI_API_KEY")
        self.api_key = api_key

    def search(self, message: str = None, num_results: int = 5, query: str = None, num: int = None, **kwargs) -> list:
        # Ưu tiên message/num_results, fallback sang query/num
        q = message or query
        n = num_results if num_results is not None else (num if num is not None else 5)
        params = {
            "engine":  "google",
            "q":       q,
            "num":     n,
            "api_key": self.api_key
        }
        client = GoogleSearch(params)
        data = client.get_dict()
        results = data.get("organic_results", [])
        return results[:n]
