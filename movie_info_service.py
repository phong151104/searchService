import traceback
import requests
from datetime import datetime
from bs4 import BeautifulSoup

from common_service import CommonService

class MovieInfoService(CommonService):
    service_name = "movie_info_service"

    def __init__(self):
        super(MovieInfoService, self).__init__()

    def process(self, json_data, log):
        response = {
            "message": "Success",
            "status": 200
        }

        try:
            # 1. Get movie name from payload
            movie_name = json_data.get("movie_name")
            if not movie_name or not isinstance(movie_name, str) or not movie_name.strip():
                response.update({
                    "message": "Movie name is required",
                    "status": 400
                })
                return response

            movie_name = movie_name.strip()
            log.debug(f"Searching for movie: {movie_name}")

            # 2. Determine URL (using IMDB as an example)
            base_url = "https://www.imdb.com/find"
            params = {
                "q": movie_name,
                "s": "tt",  # Search in titles
                "ttype": "ft"  # Feature films
            }
            
            # 3. Request and parse movie information
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            
            res = requests.get(base_url, params=params, headers=headers)
            if res.status_code != 200:
                response.update({
                    "message": f"Failed to fetch movie information, status_code: {res.status_code}",
                    "status": 500,
                    "source": res.url
                })
                return response

            soup = BeautifulSoup(res.text, "html.parser")
            movie_results = soup.select("div.findResult")

            movies = []
            for result in movie_results[:5]:  # Get top 5 results
                title_element = result.select_one("a")
                if title_element:
                    title = title_element.get_text(strip=True)
                    link = "https://www.imdb.com" + title_element.get("href", "")
                    
                    # Get year if available
                    year_element = result.select_one("span.lister-item-year")
                    year = year_element.get_text(strip=True) if year_element else "N/A"
                    
                    movies.append({
                        "title": title,
                        "year": year,
                        "link": link
                    })

            # 4. Generate formatted context
            parts = [f"Kết quả tìm kiếm phim '{movie_name}':"]
            for movie in movies:
                parts.append(f"- {movie['title']} ({movie['year']})")
            context_formated = "\n".join(parts)

            # 5. Return results
            response.update({
                "movie_name": movie_name,
                "movies": movies,
                "context_formated": context_formated,
                "source": res.url
            })

        except Exception as e:
            traceback.print_exc()
            response["message"] = str(e)
            response["status"] = 500

        return response 