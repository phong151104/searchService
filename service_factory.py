# service_factory.py

from movie_service import MovieService
from weather_service import WeatherServicePhong 
from weather_format_service import WeatherFormatService
from football_schedule_service import FootballScheduleService
from stock_quote_service import StockQuoteService
from search_all_service import SearchAllService
from stock_info_service import StockInfoService
from gold_format_service import GoldPriceService
from movie_info_service import MovieInfoService
from wiki_search import WikiSearchService
from data_process_service import DataProcessService
from lottery_service import LotteryService
from lottery_monthly_stats_service import LotteryMonthlyStatsService
from dream_lottery_service import DreamLotteryService

class ServiceFactory:
    def __init__(self):
        # Lưu cache các instance của service
        self.dic = {}

    def get_movie_service(self) -> MovieService:
        key = MovieService.service_name
        if key in self.dic:
            return self.dic[key]
        # Khởi tạo mới và cache lại
        self.dic[key] = MovieService()
        return self.dic[key]
    
    def get_weather_service_phong(self) -> WeatherServicePhong:
        key = WeatherServicePhong.service_name
        if key in self.dic:
            return self.dic[key]
        # Phải khởi WeatherServicePhong, không phải WeatherService
        self.dic[key] = WeatherServicePhong()
        return self.dic[key]
    
    def get_weather_format_service(self) -> WeatherFormatService:
        key = WeatherFormatService.service_name
        if key in self.dic:
            return self.dic[key]
        self.dic[key] = WeatherFormatService()
        return self.dic[key]
    
    def get_football_schedule_service(self):
        key = FootballScheduleService.service_name
        if key in self.dic:
            return self.dic[key]
        self.dic[key] = FootballScheduleService()
        return self.dic[key]
    
    def get_search_all_service(self):
        key = SearchAllService.service_name
        if key in self.dic:
            return self.dic[key]
        self.dic[key] = SearchAllService()
        return self.dic[key]
    
    def get_stock_info_service(self):
        key = StockInfoService.service_name
        if key in self.dic:
            return self.dic[key]
        self.dic[key] = StockInfoService()
        return self.dic[key]
    
    def get_gold_format_service(self) -> GoldPriceService:
        key = GoldPriceService.service_name
        if key in self.dic:
            return self.dic[key]
        self.dic[key] = GoldPriceService()
        return self.dic[key]
    
    def get_movie_info_service(self) -> MovieInfoService:
        key = MovieInfoService.service_name
        if key in self.dic:
            return self.dic[key]
        self.dic[key] = MovieInfoService()
        return self.dic[key]
    
    def get_wiki_search_service(self) -> WikiSearchService:
        key = WikiSearchService.service_name
        if key in self.dic:
            return self.dic[key]
        self.dic[key] = WikiSearchService()
        return self.dic[key]
    
    def get_data_process_service(self) -> DataProcessService:
        key = DataProcessService.service_name
        if key in self.dic:
            return self.dic[key]
        self.dic[key] = DataProcessService()
        return self.dic[key]
    
    def get_lottery_service(self) -> LotteryService:
        key = LotteryService.service_name
        if key in self.dic:
            return self.dic[key]
        self.dic[key] = LotteryService()
        return self.dic[key]
    
    def get_lottery_monthly_stats_service(self) -> LotteryMonthlyStatsService:
        key = LotteryMonthlyStatsService.service_name
        if key in self.dic:
            return self.dic[key]
        self.dic[key] = LotteryMonthlyStatsService()
        return self.dic[key]
    
    def get_dream_lottery_service(self) -> DreamLotteryService:
        key = DreamLotteryService.service_name
        if key in self.dic:
            return self.dic[key]
        self.dic[key] = DreamLotteryService()
        return self.dic[key]
    
    

