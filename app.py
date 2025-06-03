# app.py
import os
os.environ['SERPAPI_API_KEY'] = '689b4f607f68eed5cae1293ec43715f7e55d40be6e87e3140160b8c88dc6047a'

from flask import Flask, request, jsonify
from service_factory import ServiceFactory

app = Flask(__name__)

def handle_request(service, request):
    """Handle request for services"""
    app.logger.debug("\n\nInput: %s", request.json)
    response = service.process(json_data=request.json, log=app.logger)
    app.logger.debug("Response: %s", response)
    return jsonify(response), response.get("status", 200)

@app.route("/search/movie", methods=["POST"])
def movie():
    app.logger.debug("\n\nInput: %s", request.json)
    response = ServiceFactory().get_movie_service().process(
        json_data=request.json,
        log=app.logger
    )
    app.logger.debug("Response: %s", response)
    return jsonify(response)

@app.route("/search/weatherPhong", methods=["POST"])
def ask_weather():
    app.logger.debug("\n\nInput: %s", request.json)
    response = ServiceFactory().get_weather_service_phong().process(
        json_data=request.json,
        log=app.logger
    )
    app.logger.debug("Response: %s", response)
    return jsonify(response)

@app.route("/search/weather/format", methods=["POST"])
def ask_weather_format():
    app.logger.debug("\n\nInput: %s", request.json)
    response = ServiceFactory().get_weather_format_service().process(json_data=request.json, log=app.logger)
    app.logger.debug("Response: %s", response)
    return jsonify(response)

@app.route("/search/footballSchedule", methods=["POST"])
def football_schedule():
    app.logger.debug("Input: %s", request.json)
    response = ServiceFactory() \
        .get_football_schedule_service() \
        .process(json_data=request.json, log=app.logger)
    app.logger.debug("Response: %s", response)
    return jsonify(response), response.get("status", 200)

@app.route("/search/searchAll", methods=["POST"])
def search_all():
    factory = ServiceFactory()
    service = factory.get_search_all_service()
    response = service.process(json_data=request.json, log=app.logger)
    return jsonify(response), response.get("status", 200)

@app.route("/search/stockQuote", methods=["POST"])
def stock_quote():
    app.logger.debug("Input: %s", request.json)
    response = ServiceFactory().get_stock_quote_service().process(json_data=request.json, log=app.logger)
    app.logger.debug("Response: %s", response)
    return jsonify(response), response.get("status", 200)

@app.route("/search/stockInfo", methods=["POST"])
def stock_info():
    app.logger.debug("\n\nInput: %s", request.json)
    service = ServiceFactory().get_stock_info_service()
    response = service.process(json_data=request.json, log=app.logger)
    app.logger.debug("Response: %s", response)
    return jsonify(response), response.get("status", 200)

@app.route("/search/gold/format", methods=["POST"])
def ask_gold_format():
    app.logger.debug("\n\nInput: %s", request.json)
    service = ServiceFactory().get_gold_format_service()
    response = service.process(json_data=request.json,log=app.logger)
    app.logger.debug("Response: %s", response)
    return jsonify(response)

@app.route("/search/movieInfo", methods=["POST"])
def movie_info():
    app.logger.debug("\n\nInput: %s", request.json)
    service = ServiceFactory().get_movie_info_service()
    response = service.process(json_data=request.json, log=app.logger)
    app.logger.debug("Response: %s", response)
    return jsonify(response), response.get("status", 200)

@app.route("/search/wiki", methods=["POST"])
def wiki_search():
    app.logger.debug("\n\nInput: %s", request.json)
    service = ServiceFactory().get_wiki_search_service()
    response = service.process(json_data=request.json, log=app.logger)
    app.logger.debug("Response: %s", response)
    return jsonify(response), response.get("status", 200)

@app.route("/search/process-data", methods=["POST"])
def process_data():
    app.logger.debug("\n\nInput: %s", request.json)
    service = ServiceFactory().get_data_process_service()
    response = service.process(json_data=request.json, log=app.logger)
    app.logger.debug("Response: %s", response)
    return jsonify(response), response.get("status", 200)

@app.route("/search/lottery", methods=["POST"])
def lottery():
    app.logger.debug("\n\nInput: %s", request.json)
    service = ServiceFactory().get_lottery_service()
    response = service.process(json_data=request.json, log=app.logger)
    app.logger.debug("Response: %s", response)
    return jsonify(response), response.get("status", 200)

@app.route("/search/lottery-monthly-stats", methods=["POST"])
def lottery_monthly_stats():
    app.logger.debug("\n\nInput: %s", request.json)
    service = ServiceFactory().get_lottery_monthly_stats_service()
    response = service.process(json_data=request.json, log=app.logger)
    app.logger.debug("Response: %s", response)
    return jsonify(response), response.get("status", 200)

@app.route("/search/dream-lottery", methods=["POST"])
def dream_lottery():
    app.logger.debug("\n\nInput: %s", request.json)
    service = ServiceFactory().get_dream_lottery_service()
    response = service.process(json_data=request.json, log=app.logger)
    app.logger.debug("Response: %s", response)
    return jsonify(response), response.get("status", 200)

@app.route("/search/cgv_now_showing", methods=["POST"])
def cgv_now_showing():
    app.logger.debug("\n\nInput: %s", request.json)
    service = ServiceFactory().get_cgv_now_showing_service()
    response = service.process(json_data=request.json, log=app.logger)
    app.logger.debug("Response: %s", response)
    return jsonify(response), response.get("status", 200)

@app.route("/search/tuvi", methods=["POST"])
def tuvi():
    app.logger.debug("\n\nInput: %s", request.json)
    service = ServiceFactory().get_tuvi_service()
    response = service.process(json_data=request.json, log=app.logger)
    app.logger.debug("Response: %s", response)
    return jsonify(response), response.get("status", 200)

@app.route('/api/translate', methods=['POST'])
def translate_text():
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({
                "status": "error",
                "message": "Missing text parameter"
            }), 400

        translation_service = TranslationService()
        result = translation_service.translate_text(data['text'])
        
        if result["status"] == "error":
            return jsonify(result), 500
            
        return jsonify(result)
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route("/api/gold", methods=["POST"])
def gold_price():
    return handle_request(GoldPriceService(), request)

@app.route("/search/calendar", methods=["POST"])
def calendar():
    app.logger.debug("\n\nInput: %s", request.json)
    service = ServiceFactory().get_calendar_service()
    response = service.process(json_data=request.json, log=app.logger)
    app.logger.debug("Response: %s", response)
    return jsonify(response), response.get("status", 200)

@app.route("/search/google_image", methods=["POST"])
def google_image():
    app.logger.debug("\n\nInput: %s", request.json)
    service = ServiceFactory().get_google_image_service()
    response = service.process(json_data=request.json, log=app.logger)
    app.logger.debug("Response: %s", response)
    return jsonify(response), response.get("status", 200)

@app.route("/search/google_maps", methods=["POST"])
def google_maps():
    app.logger.debug("\n\nInput: %s", request.json)
    service = ServiceFactory().get_google_maps_service()
    response = service.process(json_data=request.json, log=app.logger)
    app.logger.debug("Response: %s", response)
    return jsonify(response), response.get("status", 200)

@app.route("/search/investing-world-gold", methods=["POST"])
def investing_world_gold():
    app.logger.debug("\n\nInput: %s", request.json)
    service = ServiceFactory().get_investing_world_gold_service()
    response = service.process(json_data=request.json, log=app.logger)
    app.logger.debug("Response: %s", response)
    return jsonify(response), response.get("status", 200)

@app.route("/search/weekday", methods=["POST"])
def weekday():
    app.logger.debug("\n\nInput: %s", request.json)
    service = ServiceFactory().get_weekday_service()
    response = service.process(json_data=request.json, log=app.logger)
    app.logger.debug("Response: %s", response)
    return jsonify(response), response.get("status", 200)

@app.route("/search/vietstock-top-stock", methods=["POST"])
def vietstock_top_stock():
    app.logger.debug("\n\nInput: %s", request.json)
    service = ServiceFactory().get_vietstock_top_stock_service()
    response = service.process(json_data=request.json, log=app.logger)
    app.logger.debug("Response: %s", response)
    return jsonify(response), response.get("status", 200)

if __name__ == "__main__":
    # Chạy app ở chế độ debug để dễ theo dõi log
    app.run(host="0.0.0.0", port=5000, debug=True)
