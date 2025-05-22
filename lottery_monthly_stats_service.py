import traceback
import requests
from bs4 import BeautifulSoup
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time

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
            print("Row tds:", [td.get_text(strip=True) for td in tds])
            if len(tds) < 2:
                continue

            so = tds[0].get_text(strip=True)
            # Lấy số lần
            count = 0
            count_text = tds[1].find("span", class_="count-digits")
            if count_text:
                m = re.search(r"(\d+)", count_text.get_text(strip=True))
                if m:
                    count = int(m.group(1))

            # Lấy danh sách ngày xuất hiện
            dates = []
            for idx, td in enumerate(tds[2:]):
                if td.get("class") and "have-value" in td.get("class"):
                    if idx < len(date_headers):
                        dates.append(date_headers[idx])

            result[so] = {"count": count, "dates": dates}

        return result

    def format_monthly_stats_context(self, stats):
        """
        Định dạng kết quả thống kê tháng thành chuỗi dễ hiểu.
        """
        if not stats:
            return "Không có dữ liệu thống kê tháng."
        lines = []
        for so in sorted(stats, key=lambda x: int(x)):
            info = stats[so]
            lines.append(f"Số {so}: xuất hiện {info['count']} lần.")
            if info["dates"]:
                lines.append(f"  Ngày xuất hiện: {', '.join(info['dates'])}")
        return "\n".join(lines)

    def parse_special_loto_stats(self, table):
        """
        Parse bảng Thống kê tần suất loto đặc biệt (sau giải ĐB xuất hiện)
        Trả về dict: {so: count}
        """
        result = {}
        tbody = table.find("tbody")
        if not tbody:
            return result

        for row in tbody.find_all("tr"):
            tds = row.find_all("td")
            print("Row tds:", [td.get_text(strip=True) for td in tds])
            i = 0
            while i < len(tds) - 1:
                # Lấy số
                so = None
                so_span = tds[i].find("span", class_="text-red text-bold")
                if so_span:
                    so = so_span.get_text(strip=True)
                else:
                    so = tds[i].get_text(strip=True)
                # Lấy số lần
                cnt_text = tds[i+1].get_text(strip=True)
                if so and cnt_text:
                    try:
                        count = int(cnt_text)
                    except ValueError:
                        count = 0
                    result[so] = count
                i += 2
        return result

    def format_special_loto_context(self, special_stats):
        """
        Định dạng kết quả thống kê loto đặc biệt thành chuỗi.
        """
        if not special_stats:
            return "Không có dữ liệu loto đặc biệt."
        lines = ["Thống kê tần suất loto ĐB sau khi giải đặc biệt xuất hiện:"]
        for so in sorted(special_stats, key=lambda x: int(x)):
            lines.append(f"Bộ số {so}: xuất hiện {special_stats[so]} lần.")
        return "\n".join(lines)

    def process(self, json_data, log):
        """
        Thực thi dịch vụ: lấy dữ liệu thống kê tháng và loto đặc biệt,
        trả về cả raw result và formatted_context.
        """
        response = {"message": "Success", "status": 200}
        try:
            headers = {"User-Agent": "Mozilla/5.0"}

            # --- Thống kê tháng ---
            url_month = "https://www.kqxs.vn/thong-ke-tu-0-den-99"
            res_month = requests.get(url_month, headers=headers, verify=False)
            soup_month = BeautifulSoup(res_month.text, "html.parser")
            table_month = soup_month.find(
                "table",
                class_="table-fixed tbldata table-result-lottery"
            )
            stats_month = {}
            if table_month:
                stats_month = self.parse_lottery_monthly_stats(table_month)

            # --- Thống kê loto đặc biệt sau khi giải ĐB ---
            url_db = "https://www.kqxs.vn/giai-db-ngay-mai"
            # Sử dụng Selenium để lấy HTML đã render
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            driver = webdriver.Chrome(options=chrome_options)
            driver.get(url_db)
            time.sleep(3)  # Đợi JS render bảng, có thể tăng nếu mạng chậm
            html = driver.page_source
            driver.quit()
            soup_db = BeautifulSoup(html, "html.parser")
            # Lấy đúng bảng trong div id="table-statistic-next"
            table_db = None
            block_next = soup_db.find("div", id="table-statistic-next")
            if block_next:
                table_db = block_next.find("table")
            stats_special = {}
            if table_db:
                stats_special = self.parse_special_loto_stats(table_db)

            # Gộp kết quả vào response
            response["result"] = {
                "monthly": stats_month,
                "special_after_db": stats_special
            }

            # Định dạng context dễ đọc
            monthly_ctx = self.format_monthly_stats_context(stats_month)
            special_ctx = self.format_special_loto_context(stats_special)
            response["formatted_context"] = f"{monthly_ctx}\n\n{special_ctx}"

        except Exception as e:
            traceback.print_exc()
            response["message"] = str(e)
            response["status"] = 500

        return response