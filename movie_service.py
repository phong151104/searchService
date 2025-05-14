# movie_service.py

import traceback
import requests
import json
from common_service import CommonService  # hoặc from .common_service import CommonService nếu bạn đang để trong package

class MovieService(CommonService):
    service_name = "movie_service"

    def __init__(self):
        super().__init__()

    def process(self, json_data, log):
        response = {
            "message": "Success",
            "status": 200
        }
        try:
            system_message = json_data.get("system_message", "")
            if not system_message:
                response["message"] = "Input message is not valid!"
                response["status"] = 400
            else:
                log.debug(f"Search keyword [{system_message}] on tv360.vn")
                response = self.search_on_tv360(response, system_message)
        except Exception as e:
            response["message"] = getattr(e, "message", str(e))
            response["status"] = 500
            traceback.print_exc()
        return response

    @staticmethod
    def search_on_tv360(response, keyword):
        def extract_film_data(list_films):
            output = []
            for film in list_films:
                output.append({
                    "name": film.get("name", ""),
                    "link": f"http://tv360.vn/movie/{film.get('slug')}?m={film.get('id')}",
                    "coverImage": film.get("coverImage", ""),
                    "coverImageH": film.get("coverImage", ""),
                    "description": film.get("description", ""),
                    "durationStr": film.get("durationStr", ""),
                    "imdb": str(film.get("imdb", "")),
                    "yearOfProduct": str(film.get("yearOfProduct", ""))
                })
            return output

        num_results = 20
        url = (
            f"http://tv360.vn/public/v1/search/search"
            f"?keyword={keyword}&searchType=search&offset=0&limit={num_results}"
        )
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
            "Content-Type": "application/json"
        }

        res = requests.get(url, headers=headers)
        res_json = res.json()

        if res_json.get("errorCode") == 200:
            data = res_json.get("data", [])
            films_raw = data[1].get("content", []) if len(data) > 1 else []
            films = extract_film_data(films_raw)

            if not films:
                response["message"] = "Không tìm thấy kết quả"
                response["status"] = 404
            else:
                response["data"] = films
        else:
            response["message"] = res_json.get("message", "Xảy ra lỗi khi gọi API tv360.vn")
            response["status"] = res_json.get("errorCode", 500)

        return response
