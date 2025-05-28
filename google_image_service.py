# common_service/google_image_service.py
import os
import requests
from common_service import CommonService

class GoogleImageService(CommonService):
    service_name = "google_image_service"

    def __init__(self):
        super(GoogleImageService, self).__init__()
        self.api_key = os.environ.get("SERPAPI_API_KEY")

    def process(self, json_data, log):
        response = {
            "message": "Success",
            "status": 200
        }
        try:
            query = json_data.get("query", "").strip()
            if not query:
                response.update({
                    "message": "Bạn chưa cung cấp từ khóa tìm kiếm.",
                    "status": 400
                })
                return response

            log.debug(f"Searching Google Images for: {query}")

            url = "https://serpapi.com/search"
            params = {
                "q": query,
                "tbm": "isch",
                "api_key": self.api_key,
                "ijn": 0
            }
            r = requests.get(url, params=params)
            r.raise_for_status()
            data = r.json()
            images = []
            if "images_results" in data:
                for img in data["images_results"]:
                    images.append({
                        "title": img.get("title"),
                        "original": img.get("original"),
                        "thumbnail": img.get("thumbnail"),
                        "source": img.get("source"),
                        "link": img.get("link")
                    })
            if not images:
                response.update({
                    "message": f"Không tìm thấy ảnh cho '{query}'.",
                    "status": 404
                })
                return response

            response["results"] = images
            response["query"] = query
        except Exception as e:
            log.error(str(e))
            response.update({
                "message": str(e),
                "status": 500
            })
        return response