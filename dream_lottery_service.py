import requests
from bs4 import BeautifulSoup

class DreamLotteryService:
    service_name = 'dream_lottery_service'
    url = "https://ngaydep.com/giai-ma-giac-mo-trung-so.html"

    def fetch_dream_lottery(self):
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(self.url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        table = soup.find("table", class_="week_tbl")
        result = []
        formatted_context = []
        if table:
            rows = table.find_all("tr", class_="body")
            for row in rows:
                cols = row.find_all("td")
                if len(cols) >= 3:
                    dream = cols[1].get_text(strip=True)
                    numbers = cols[2].get_text(strip=True)
                    result.append({"dream": dream, "numbers": numbers})
                    formatted_context.append(f"{dream}: {numbers}")
        return {
            "message": "Success",
            "status": 200,
            "result": result,
            "formatted_context": "; ".join(formatted_context)
        }

    def process(self, json_data, log):
        try:
            return self.fetch_dream_lottery()
        except Exception as e:
            log.error(str(e))
            return {"message": "Error", "status": 500, "error": str(e)}