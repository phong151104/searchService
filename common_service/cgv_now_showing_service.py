import traceback
import requests
from bs4 import BeautifulSoup
from common_service import CommonService

class CGVNowShowingService(CommonService):
    service_name = "cgv_now_showing_service"

    def __init__(self):
        super(CGVNowShowingService, self).__init__()

    def process(self, json_data, log):
        response = {
            "message": "Success",
            "status": 200
        }
        try:
            url = "https://www.cgv.vn/default/movies/now-showing.html"
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            movies = []
            for li in soup.select("ul.products-grid li.film-lists"):
                movie = {}
                # Rating
                rating = li.find("span", class_="nmovie-rating")
                movie["rating"] = rating.text.strip() if rating else ""
                # Poster
                img = li.find("div", class_="product-images").find("img")
                movie["poster"] = img["src"] if img else ""
                # Link + Title
                a = li.find("h2", class_="product-name").find("a")
                movie["title"] = a["title"].strip() if a else ""
                movie["detail_url"] = a["href"] if a else ""
                # Thể loại
                genre = ""
                for info in li.find_all("div", class_="cgv-movie-info"):
                    label = info.find("span", class_="cgv-info-bold")
                    if label and "Thể loại" in label.text:
                        genre = info.find("span", class_="cgv-info-normal").text.strip()
                movie["genre"] = genre
                # Thời lượng
                duration = ""
                for info in li.find_all("div", class_="cgv-movie-info"):
                    label = info.find("span", class_="cgv-info-bold")
                    if label and "Thời lượng" in label.text:
                        duration = info.find("span", class_="cgv-info-normal").text.strip()
                movie["duration"] = duration
                # Khởi chiếu
                release = ""
                for info in li.find_all("div", class_="cgv-movie-info"):
                    label = info.find("span", class_="cgv-info-bold")
                    if label and "Khởi chiếu" in label.text:
                        release = info.find("span", class_="cgv-info-normal").text.strip()
                movie["release_date"] = release
                # Công nghệ chiếu
                techs = []
                for tech in li.select("div.movie-technology span"):
                    techs.append(tech.text.strip())
                movie["technologies"] = techs
                movies.append(movie)
            response["results"] = movies
        except Exception as e:
            log.error(traceback.format_exc())
            response.update({
                "message": str(e),
                "status": 500
            })
        return response 