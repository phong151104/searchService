import logging
from wiki_search import WikiSearchService

# Cấu hình logging
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

# Khởi tạo service
service = WikiSearchService()

# Test với từ khóa "Hà Nội"
query = "Hà Nội"
result = service.process({"query": query}, log)

# In kết quả
print("\nKết quả tìm kiếm cho:", query)
print("Status:", result["status"])
print("Message:", result["message"])

if result["status"] == 200:
    print("\nKết quả đầu tiên:")
    first_result = result["results"][0]
    print("Tiêu đề:", first_result["title"])
    print("Đoạn trích:", first_result["snippet"])
    print("\nĐoạn văn đầu tiên:", first_result["first_paragraph"])
    print("\nURL:", first_result["fullurl"]) 