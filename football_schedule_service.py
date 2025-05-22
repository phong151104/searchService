# football_schedule_service.py

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
        "Premier League": "https://bongda24h.vn/bong-da-anh/lich-thi-dau-1.html",
        "Serie A": "https://bongda24h.vn/bong-da-italia/lich-thi-dau-3.html",
        "Ligue 1": "https://bongda24h.vn/bong-da-phap/lich-thi-dau-6.html",
        "La Liga": "https://bongda24h.vn/bong-da-tay-ban-nha/lich-thi-dau-5.html",
        "Champions League": "https://bongda24h.vn/bong-da-chau-au/lich-thi-dau-7.html",
        "Bundesliga": "https://bongda24h.vn/bong-da-duc/lich-thi-dau-4.html",
        "V League": "https://bongda24h.vn/vleague/lich-thi-dau-25.html"
    }
    GLOBAL_FIXTURE_URL = "https://bongda24h.vn/bong-da/lich-thi-dau.html"

    def __init__(self):
        super(FootballScheduleService, self).__init__()

    def process(self, json_data, log):
        try:
            tournament = (json_data.get("tournament") or "").strip()
            club_filter = (json_data.get("club") or "").strip().lower()

            # 1) Lấy danh sách fixture phù hợp
            if not tournament and not club_filter:
                return {
                    "message": "Bạn phải cung cấp tên giải đấu hoặc tên đội.",
                    "status": 400
                }

            # global + chỉ club
            if not tournament and club_filter:
                fixtures = self._get_fixtures_from_url(self.GLOBAL_FIXTURE_URL)
                fixtures = [
                    m for m in fixtures
                    if club_filter in m["firstClub"].lower()
                       or club_filter in m["secondsClub"].lower()
                ]
                if not fixtures:
                    return {
                        "message": f"Không tìm thấy trận đấu của đội '{club_filter.title()}'.",
                        "status": 404
                    }
                context_header = f"Lịch thi đấu toàn bộ giải cho đội {club_filter.title()}:\n"
            else:
                # tournament (+ option club)
                if tournament not in self.FIXTURE_URLS:
                    return {
                        "message": f"Giải đấu '{tournament}' không được hỗ trợ.",
                        "status": 400
                    }
                url = self.FIXTURE_URLS[tournament]
                fixtures = self._get_fixtures_from_url(url)
                if club_filter:
                    fixtures = [
                        m for m in fixtures
                        if club_filter in m["firstClub"].lower()
                           or club_filter in m["secondsClub"].lower()
                    ]
                    if not fixtures:
                        return {
                            "message": (
                                f"Không tìm thấy trận đấu của đội "
                                f"'{club_filter.title()}' trong giải {tournament}."
                            ),
                            "status": 404
                        }
                context_header = (
                        f"Lịch thi đấu {tournament}"
                        + (f" cho đội {club_filter.title()}" if club_filter else "")
                        + ":\n"
                )

            # 2) Tạo các dòng mô tả từng trận
            lines = []
            for m in fixtures:
                # format ngày giờ
                dt = m["dateTime"]
                home = m["firstClub"]
                away = m["secondsClub"]
                score = m["score"]
                lines.append(f"- {dt}: {home} {score} {away}")

            # 3) Tổng hợp thành 1 chuỗi context_formated
            context = context_header + "\n".join(lines)

            # Trả về đầy đủ các trường (fixtures) và context_formated
            return {
                "context_formated": context,
                "fixtures": fixtures
            }

        except Exception as e:
            log.error(traceback.format_exc())
            return {
                "message": str(e),
                "status": 500
            }

    @staticmethod
    def _get_fixtures_from_url(url):
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, "html.parser")

        fixtures = []
        for match in soup.select("div.match-football div.f-row.matchdetail"):
            time_div = match.select_one("div.football-match div.columns-time")
            clubs = match.select("div.football-match div.columns-match div.row-teams div.columns-club")
            score_div = match.select_one("div.football-match div.columns-number span.soccer-scores")

            if not time_div or not clubs or not score_div:
                continue

            text = time_div.get_text(" ", strip=True)
            m = re.match(r"(\d{2}:\d{2})\s*-\s*(\d{2}/\d{2})", text)
            if not m:
                continue
            tm, date_part = m.groups()
            year = datetime.now().year
            dateTime = f"{tm} {date_part}/{year}"

            home_a = clubs[0].select_one("a.name-club")
            firstClub = home_a.get("title", "").strip() if home_a else ""
            img_home = clubs[0].select_one("img")
            imgFirstClub = (img_home.get("data-src") or img_home.get("src")) if img_home else None

            away_a = clubs[1].select_one("a.name-club")
            secondsClub = away_a.get("title", "").strip() if away_a else ""
            img_away = clubs[1].select_one("img")
            imgSecondsClub = (img_away.get("data-src") or img_away.get("src")) if img_away else None

            score = score_div.get_text(strip=True) if score_div else "vs"

            fixtures.append({
                "id": uuid.uuid4().hex,
                "dateTime": dateTime,
                "time": int(datetime.strptime(dateTime, "%H:%M %d/%m/%Y").timestamp() * 1000),
                "round": None,
                "firstClub": firstClub,
                "imgFirstClub": imgFirstClub,
                "secondsClub": secondsClub,
                "imgSecondsClub": imgSecondsClub,
                "score": score,
                "url": url
            })

        return fixtures