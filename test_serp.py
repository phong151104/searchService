from serp import Serp
import json
import logging

def test_serp():
    serp = Serp()
    queries = [
        "finance.vietstock.vn VIC",
        "finance.vietstock.vn vic",
        "finance.vietstock.vn vingroup"
    ]
    
    for query in queries:
        print(f"\nTesting query: {query}")
        try:
            results = serp.search(message=query)
            if results:
                first = results[0]
                url = first["link"] if isinstance(first, dict) else first
                print(f"First URL: {url}")
                print(f"Title: {first.get('title', 'N/A')}")
            else:
                print("No results found")
        except Exception as e:
            print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_serp() 