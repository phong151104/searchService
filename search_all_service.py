# search_all_service.py

import traceback
from common_service import CommonService

class SearchAllService(CommonService):
    service_name = "search_all"

    def __init__(self):
        super(SearchAllService, self).__init__()

    def process(self, json_data, log):
        response = {
            "message":  "",
            "status":   200,
            "top_link": ""
        }

        try:
            # 1. Đọc query đầu vào (có thể gọi "query" hoặc "message")
            query = (json_data.get("query") or json_data.get("message") or "").strip()
            if not query:
                response.update({
                    "message": "Bạn chưa cung cấp chuỗi tìm kiếm.",
                    "status":  400
                })
                return response

            log.debug("Searching top-1 for query: %s", query)

            # 2. Lấy top-1 URL từ SerpAPI
            urls = self.serp.search(query=query, num=1)
            if not urls:
                response.update({
                    "message": f"Không tìm thấy kết quả cho '{query}'.",
                    "status":  404
                })
                return response

            # 3. Trả về link đầu tiên
            top_link = urls[0]
            response.update({
                "message":  "Success!",
                "top_link": top_link
            })

        except Exception as e:
            log.error(traceback.format_exc())
            response.update({
                "message": str(e),
                "status":  500
            })

        return response
