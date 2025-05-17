import traceback
import requests
from bs4 import BeautifulSoup
import re

class LotteryMonthlyStatsService:
    service_name = 'lottery_monthly_stats_service'

    def parse_lottery_monthly_stats(self, table):
        """
        Parse bảng thống kê tháng từ HTML (table-fixed tbldata table-result-lottery)
        Trả về dict: {so: {"count": int, "dates": ["dd/mm/yyyy", ...]}}
        """
        result = {}
        # Lấy header ngày tháng
        thead = table.find("thead")
        date_headers = []
        if thead:
            ths = thead.find_all("th")
            # Bỏ 2 cột đầu (Cặp số, Tổng số lần ra)
            for th in ths[2:]:
                date_headers.append(th.get_text(strip=True))
        tbody = table.find("tbody")
        if not tbody:
            return result
        for row in tbody.find_all("tr"):
            tds = row.find_all("td")
            if len(tds) < 2:
                continue
            so = tds[0].get_text(strip=True)
            count_text = tds[1].find("span", class_="count-digits")
            count = 0
            if count_text:
                m = re.search(r"(\d+)", count_text.get_text(strip=True))
                if m:
                    count = int(m.group(1))
            # Lấy từng ngày xuất hiện
            dates = []
            for idx, td in enumerate(tds[2:]):
                if td.get("class") and "have-value" in td.get("class"):
                    # Lấy ngày từ header
                    if idx < len(date_headers):
                        dates.append(date_headers[idx])
            result[so] = {"count": count, "dates": dates}
        return result

    def format_monthly_stats_context(self, stats):
        """
        Định dạng kết quả thống kê tháng thành chuỗi dễ hiểu.
        """
        if not stats:
            return "Không có dữ liệu thống kê."
        lines = []
        for so in sorted(stats, key=lambda x: int(x)):
            info = stats[so]
            count = info["count"]
            dates = info["dates"]
            lines.append(f"Số {so}: xuất hiện {count} lần.")
            if dates:
                lines.append(f"  Ngày xuất hiện: {', '.join(dates)}")
        return "\n".join(lines)

    def process(self, json_data, log):
        response = {
            "message": "Success",
            "status": 200
        }
        try:
            url = "https://www.kqxs.vn/thong-ke-tu-0-den-99"
            headers = {"User-Agent": "Mozilla/5.0"}
            res = requests.get(url, headers=headers, verify=False)
            soup = BeautifulSoup(res.text, "html.parser")
            table = soup.find("table", class_="table-fixed tbldata table-result-lottery")
            if table is not None:
                stats = self.parse_lottery_monthly_stats(table)
                response["result"] = stats
                response["formatted_context"] = self.format_monthly_stats_context(stats)
            else:
                response["message"] = "Không tìm thấy bảng thống kê."
                response["status"] = 404
        except Exception as e:
            response["message"] = str(e)
            response["status"] = 500
            traceback.print_exc()
        return response 