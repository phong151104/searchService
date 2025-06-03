import traceback
from datetime import datetime
from common_service import CommonService

class WeekdayService(CommonService):
    service_name = "weekday_service"

    def process(self, json_data, log):
        response = {"message": "Success", "status": 200}
        try:
            date_str = json_data.get("date")
            if not date_str:
                response.update({"message": "Missing 'date' parameter", "status": 400})
                return response
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
            except Exception:
                response.update({"message": "Invalid date format, must be yyyy-mm-dd", "status": 400})
                return response
            weekdays = [
                "Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"
            ]
            # Python: Monday=0, Sunday=6
            weekday = weekdays[dt.weekday()] if dt.weekday() < 6 else weekdays[6]
            response["weekday"] = weekday
            response["input_date"] = date_str
        except Exception as e:
            log.error(traceback.format_exc())
            response.update({"message": str(e), "status": 500})
        return response 