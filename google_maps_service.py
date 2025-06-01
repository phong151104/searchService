import os
import requests
from typing import Dict, List, Optional
from common_service import CommonService

class GoogleMapsService(CommonService):
    service_name = "google_maps_service"
    
    def __init__(self):
        super(GoogleMapsService, self).__init__()
        self.api_key = "AIzaSyDF8uhq0FlMcyarxFpsShnMqs7j_nCfAM4"
        self.base_url = "https://routes.googleapis.com/directions/v2"
        self.places_url = "https://places.googleapis.com/v1"
        
    def process(self, json_data: Dict, log) -> Dict:
        response = {"message": "Success", "status": 200}
        
        try:
            action = json_data.get("action", "").lower()
            
            if not self.api_key:
                response.update(message="Google Maps API key not configured", status=500)
                return response
                
            if action == "directions":
                response = self.get_directions(json_data)
            elif action == "place_search":
                response = self.search_places(json_data)
            elif action == "place_details":
                response = self.get_place_details(json_data)
            elif action == "geocode":
                response = self.geocode_address(json_data)
            elif action == "reverse_geocode":
                response = self.reverse_geocode(json_data)
            elif action == "distance_matrix":
                response = self.get_distance_matrix(json_data)
            elif action == "autocomplete":
                response = self.get_place_autocomplete(json_data)
            else:
                response.update(
                    message="Invalid action. Supported actions: directions, place_search, place_details, geocode, reverse_geocode, distance_matrix, autocomplete",
                    status=400
                )
                
        except Exception as e:
            log.error("GoogleMapsService error:", exc_info=True)
            response.update(
                message="Internal error",
                status=500,
                error=repr(e)
            )
            
        return response

    def get_directions(self, data: Dict) -> Dict:
        """Get directions between two points using Routes API"""
        origin = data.get("origin")
        destination = data.get("destination")
        mode = data.get("mode", "DRIVING")  # DRIVING, WALKING, BICYCLING, TRANSIT
        
        if not origin or not destination:
            return {"message": "Origin and destination are required", "status": 400}
            
        url = f"{self.base_url}:computeRoutes"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "routes.duration,routes.distanceMeters,routes.legs.duration,routes.legs.distanceMeters,routes.legs.steps"
        }
        
        payload = {
            "origin": {
                "address": origin
            },
            "destination": {
                "address": destination
            },
            "travelMode": mode,
            "routingPreference": "TRAFFIC_AWARE",
            "computeAlternativeRoutes": True,
            "languageCode": "vi-VN",
            "units": "METRIC"
        }
        
        response = requests.post(url, headers=headers, json=payload)
        return response.json()

    def search_places(self, data: Dict) -> Dict:
        """Search for places using Places API"""
        query = data.get("query")
        location = data.get("location")  # lat,lng
        radius = data.get("radius", 5000)  # meters
        type = data.get("type")  # restaurant, cafe, etc.
        
        if not query:
            return {"message": "Search query is required", "status": 400}
            
        url = f"{self.places_url}:searchText"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location,places.rating"
        }
        
        payload = {
            "textQuery": query,
            "languageCode": "vi"
        }
        
        if location:
            lat, lng = location.split(",")
            payload["locationBias"] = {
                "circle": {
                    "center": {
                        "latitude": float(lat),
                        "longitude": float(lng)
                    },
                    "radius": radius
                }
            }
            
        response = requests.post(url, headers=headers, json=payload)
        return response.json()

    def get_place_details(self, data: Dict) -> Dict:
        """Get detailed information about a place"""
        place_id = data.get("place_id")
        
        if not place_id:
            return {"message": "Place ID is required", "status": 400}
            
        url = f"{self.places_url}/places/{place_id}"
        headers = {
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "displayName,formattedAddress,location,rating,openingHours,photos"
        }
        
        response = requests.get(url, headers=headers)
        return response.json()

    def geocode_address(self, data: Dict) -> Dict:
        """Convert address to coordinates using Geocoding API"""
        address = data.get("address")
        
        if not address:
            return {"message": "Address is required", "status": 400}
            
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            "address": address,
            "key": self.api_key,
            "language": "vi"
        }
        
        response = requests.get(url, params=params)
        return response.json()

    def reverse_geocode(self, data: Dict) -> Dict:
        """Convert coordinates to address using Geocoding API"""
        latlng = data.get("latlng")
        
        if not latlng:
            return {"message": "Latitude and longitude are required", "status": 400}
            
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            "latlng": latlng,
            "key": self.api_key,
            "language": "vi"
        }
        
        response = requests.get(url, params=params)
        return response.json()

    def get_distance_matrix(self, data: Dict) -> Dict:
        """Get distance and duration between multiple origins and destinations"""
        origins = data.get("origins")
        destinations = data.get("destinations")
        mode = data.get("mode", "driving")
        
        if not origins or not destinations:
            return {"message": "Origins and destinations are required", "status": 400}
            
        url = "https://maps.googleapis.com/maps/api/distancematrix/json"
        params = {
            "origins": origins,
            "destinations": destinations,
            "mode": mode,
            "key": self.api_key,
            "language": "vi"
        }
        
        response = requests.get(url, params=params)
        return response.json()

    def get_place_autocomplete(self, data: Dict) -> Dict:
        """Get place suggestions based on partial input"""
        input_text = data.get("input")
        types = data.get("types", "geocode")
        location = data.get("location")
        radius = data.get("radius", 5000)
        
        if not input_text:
            return {"message": "Input text is required", "status": 400}
            
        url = f"{self.places_url}:autocomplete"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress"
        }
        
        payload = {
            "textQuery": input_text,
            "languageCode": "vi"
        }
        
        if location:
            lat, lng = location.split(",")
            payload["locationBias"] = {
                "circle": {
                    "center": {
                        "latitude": float(lat),
                        "longitude": float(lng)
                    },
                    "radius": radius
                }
            }
            
        response = requests.post(url, headers=headers, json=payload)
        return response.json() 