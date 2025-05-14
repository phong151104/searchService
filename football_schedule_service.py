import re
import uuid
import traceback
import requests
from datetime import datetime
from bs4 import BeautifulSoup

from common_service import CommonService


class FootballScheduleService(CommonService):
    service_name = "football_schedule_service"

    FIXTURE_URLS = {
        "Premier League":    "https://bongda24h.vn/bong-da-anh/lich-thi-dau-1.html",
        "Serie A":           "https://bongda24h.vn/bong-da-italia/lich-thi-dau-3.html",
        "Ligue 1":           "https://bongda24h.vn/bong-da-phap/lich-thi-dau-6.html",
        "La Liga":           "https://bongda24h.vn/bong-da-tay-ban-nha/lich-thi-dau-5.html",
        "Champions League":  "https://bongda24h.vn/bong-da-chau-au/lich-thi-dau-7.html",
        "Bundesliga":        "https://bongda24h.vn/bong-da-duc/lich-thi-dau-4.html"
    }

    def __init__(self):
        super(FootballScheduleService, self).__init__()

    def process(self, json_data, log):
        response = {
            "message": "Success!",
            "status": 200,
            "data": [],
            "url": "https://bongda24h.vn/bong-da/lich-thi-dau.html",
            "top_results": None
        }
        try:
            tournament = (json_data.get("tournament") or "").strip()
            club_filter = (json_data.get("club") or "").strip().lower()
            if not tournament:
                response.update({"message": "Bạn chưa cung cấp tên giải đấu.", "status": 400})
                return response
            if tournament not in self.FIXTURE_URLS:
                response.update({"message": f"Giải đấu '{tournament}' không được hỗ trợ.", "status": 400})
                return response

            log.debug("Input: %s", json_data)
            fixtures = self._get_fixtures(tournament)

            # filter theo club nếu có
            if club_filter:
                fixtures = [m for m in fixtures if club_filter in m["firstClub"].lower() or club_filter in m["secondsClub"].lower()]
                if not fixtures:
                    response.update({
                        "message": f"Không tìm thấy trận đấu của đội '{club_filter.title()}' trong giải {tournament}.",
                        "status": 404
                    })
                    return response

            response["data"].append({
                "tournament": tournament,
                "url": self.FIXTURE_URLS[tournament],
                "info": fixtures
            })
            log.debug("Response: %s", response)

        except Exception as e:
            log.error(traceback.format_exc())
            response.update({"message": str(e), "status": 500})

        return response

    def _get_fixtures(self, tournament):
        url = self.FIXTURE_URLS[tournament]
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, "html.parser")

        container = soup.select_one("div.match-football")
        if not container:
            raise ValueError("Không tìm thấy vùng lịch thi đấu trên trang.")

        fixtures = []
        for row in container.select("div.f-row.matchdetail"):
            td = row.select_one("div.columns-time")
            if not td:
                continue
            time_date = td.get_text(" ", strip=True)
            m = re.match(r"(\d{2}:\d{2})\s*-\s*(\d{2}/\d{2})", time_date)
            if not m:
                continue
            tm, date_part = m.groups()
            year = datetime.now().year
            dateTime = f"{tm} {date_part}/{year}"
            try:
                ts = int(datetime.strptime(dateTime, "%H:%M %d/%m/%Y").timestamp() * 1000)
            except:
                ts = None

            round_span = td.select_one("span.vongbang")
            rnd = round_span.get_text(strip=True) if round_span else None

            clubs = row.select("div.columns-club")
            if len(clubs) < 2:
                continue
            home_a = clubs[0].select_one("a.name-club")
            firstClub = home_a.get_text(strip=True) if home_a else ""
            img_tag = clubs[0].select_one("img")
            imgFirstClub = (img_tag.get("data-src") or img_tag.get("src")) if img_tag else None

            away_a = clubs[1].select_one("a.name-club")
            secondsClub = away_a.get_text(strip=True) if away_a else ""
            img_tag2 = clubs[1].select_one("img")
            imgSecondsClub = (img_tag2.get("data-src") or img_tag2.get("src")) if img_tag2 else None

            score_span = row.select_one("div.columns-match span")
            score = score_span.get_text(strip=True) if score_span else "vs"

            fixtures.append({
                "id": uuid.uuid4().hex,
                "tournament": tournament,
                "dateTime": dateTime,
                "time": ts,
                "round": rnd,
                "firstClub": firstClub,
                "imgFirstClub": imgFirstClub,
                "secondsClub": secondsClub,
                "imgSecondsClub": imgSecondsClub,
                "score": score,
                "url": url
            })

        return fixtures
