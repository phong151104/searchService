# -*- coding: utf-8 -*-
import httpx
from bs4 import BeautifulSoup
from common_service import CommonService
import urllib3
import logging
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
            
            # Configure Chrome options
            chrome_options = Options()
            chrome_options.add_argument('--headless')  # Run in headless mode
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            log.info(f"Initializing Chrome driver")
            driver = webdriver.Chrome(options=chrome_options)
            
            try:
                log.info(f"Fetching data from {url}")
                driver.get(url)
                
                # Wait for the movie list to load
                log.info("Waiting for movie list to load")
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "ul.products-grid li.film-lists"))
                )
                
                # Give extra time for dynamic content to load
                time.sleep(2)
                
                log.info("Parsing HTML content")
                soup = BeautifulSoup(driver.page_source, "html.parser")
                
                # Log HTML content for debugging
                log.debug(f"HTML content length: {len(driver.page_source)}")
                log.debug(f"First 500 characters: {driver.page_source[:500]}")
                
                movies = []
                
                # Try different selectors
                selectors = [
                    "ul.products-grid li.film-lists",
                    "div.category-products li.film-lists",
                    "li.film-lists",
                    "div.product-info"
                ]
                
                for selector in selectors:
                    movie_items = soup.select(selector)
                    log.info(f"Found {len(movie_items)} movie items with selector: {selector}")
                    if movie_items:
                        break
                
                if not movie_items:
                    log.error("No movie items found with any selector")
                    response.update({
                        "message": "No movies found",
                        "status": 404
                    })
                    return response
                
                for li in movie_items:
                    try:
                        movie = {}
                        
                        # Rating
                        rating = li.find("span", class_="nmovie-rating")
                        movie["rating"] = rating.text.strip() if rating else ""
                        log.debug(f"Rating: {movie['rating']}")
                        
                        # Poster
                        img = li.find("div", class_="product-images").find("img")
                        movie["poster"] = img["src"] if img else ""
                        log.debug(f"Poster: {movie['poster']}")
                        
                        # Title and URL
                        a = li.find("h2", class_="product-name").find("a")
                        movie["title"] = a["title"].strip() if a else ""
                        movie["detail_url"] = a["href"] if a else ""
                        log.debug(f"Title: {movie['title']}")
                        
                        # Genre
                        genre = li.find("span", class_="cgv-info-normal")
                        movie["genre"] = genre.text.strip() if genre else ""
                        log.debug(f"Genre: {movie['genre']}")
                        
                        # Duration
                        duration = ""
                        for info in li.find_all("div", class_="cgv-movie-info"):
                            label = info.find("span", class_="cgv-info-bold")
                            if label and "Thời lượng" in label.text:
                                duration = info.find("span", class_="cgv-info-normal").text.strip()
                        movie["duration"] = duration
                        log.debug(f"Duration: {movie['duration']}")
                        
                        # Release date
                        release = ""
                        for info in li.find_all("div", class_="cgv-movie-info"):
                            label = info.find("span", class_="cgv-info-bold")
                            if label and "Khởi chiếu" in label.text:
                                release = info.find("span", class_="cgv-info-normal").text.strip()
                        movie["release_date"] = release
                        log.debug(f"Release date: {movie['release_date']}")
                        
                        # Technologies
                        techs = []
                        for tech in li.select("div.movie-technology span"):
                            techs.append(tech.text.strip())
                        movie["technologies"] = techs
                        log.debug(f"Technologies: {movie['technologies']}")
                        
                        movies.append(movie)
                        log.info(f"Successfully parsed movie: {movie['title']}")
                        
                    except Exception as e:
                        log.error(f"Error parsing movie item: {str(e)}")
                        continue
                
                log.info(f"Successfully parsed {len(movies)} movies")
                response["results"] = movies
                
            finally:
                log.info("Closing Chrome driver")
                driver.quit()
            
        except Exception as e:
            log.error(f"Unexpected Error: {str(e)}")
            response.update({
                "message": f"Unexpected Error: {str(e)}",
                "status": 500
            })
        return response