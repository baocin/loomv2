import caldav
from datetime import datetime, timedelta
import os
import logging
import requests
from typing import List, Dict, Any

class CalendarFetcher:
    def __init__(self):
        """Initialize calendar fetcher with account configurations"""
        self.accounts = self._load_accounts()
        self.processed_events = set()  # Keep track of processed events in memory
        self.nominatim_base_url = os.getenv("NOMINATIM_BASE_URL", "http://localhost:8080")
        
    def _load_accounts(self) -> List[Dict[str, Any]]:
        """Load calendar accounts from environment variables"""
        all_accounts = []
        
        # Support up to 10 calendar accounts
        for i in range(1, 11):
            url_env = f"CALDAV_URL_{i}"
            username_env = f"CALDAV_USERNAME_{i}"
            password_env = f"CALDAV_PASSWORD_{i}"
            disabled_env = f"CALDAV_DISABLED_{i}"
            
            url = os.getenv(url_env)
            if not url:
                break
                
            account = {
                "url": url,
                "username": os.getenv(username_env),
                "password": os.getenv(password_env),
                "disabled": os.getenv(disabled_env, "false").lower() == "true"
            }
            
            if not account["disabled"] and account["username"] and account["password"]:
                all_accounts.append(account)
        
        logging.info(f"Loaded {len(all_accounts)} calendar accounts")
        return all_accounts

    def fetch_all_calendar_events(self) -> List[Dict[str, Any]]:
        """Fetch calendar events from all configured accounts"""
        all_events = []
        
        for account in self.accounts:
            try:
                events = self._fetch_account_events(account)
                all_events.extend(events)
            except Exception as e:
                logging.error(f"Error fetching calendar events for {account['username']}: {e}")
        
        return all_events

    def _fetch_account_events(self, account: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fetch events from a single calendar account"""
        events = []
        
        try:
            client = caldav.DAVClient(
                url=account["url"],
                username=account["username"],
                password=account["password"]
            )
            principal = client.principal()
            calendars = principal.calendars()
            
            logging.info(f"Fetching events for {account['username']} from {len(calendars)} calendars")
            
            for calendar in calendars:
                try:
                    calendar_events = calendar.search(
                        start=datetime.now() - timedelta(days=30),  # Last 30 days
                        end=datetime.now() + timedelta(days=365),   # Next year
                        event=True
                    )
                    
                    for event in calendar_events:
                        try:
                            event_data = self._parse_event(event, account, calendar)
                            if event_data:
                                unique_id = f"{account['username']}:{event_data['event_id']}"
                                if unique_id not in self.processed_events:
                                    events.append(event_data)
                                    self.processed_events.add(unique_id)
                        except Exception as e:
                            logging.error(f"Error parsing event: {e}")
                            
                except Exception as e:
                    logging.error(f"Error searching calendar {calendar.name}: {e}")
                    
        except Exception as e:
            logging.error(f"CalDAV connection error for {account['username']}: {e}")
            
        return events

    def _parse_event(self, event, account: Dict[str, Any], calendar) -> Dict[str, Any]:
        """Parse individual calendar event"""
        try:
            vevent = event.vobject_instance.vevent
            
            # Generate unique event ID
            event_id = f"{calendar.url}_{vevent.uid.value}"
            
            # Extract basic information
            summary = getattr(vevent, 'summary', None)
            summary = summary.value if summary else "No Title"
            
            description = getattr(vevent, 'description', None)
            description = description.value if description else ""
            
            location = getattr(vevent, 'location', None)
            location = location.value if location else ""
            
            # Extract dates
            start_time = getattr(vevent, 'dtstart', None)
            start_time = start_time.value if start_time else None
            
            end_time = getattr(vevent, 'dtend', None)
            end_time = end_time.value if end_time else None
            
            # Convert datetime objects to timestamps
            if start_time and hasattr(start_time, 'isoformat'):
                start_time = start_time
            elif start_time:
                start_time = datetime.combine(start_time, datetime.min.time())
                
            if end_time and hasattr(end_time, 'isoformat'):
                end_time = end_time
            elif end_time:
                end_time = datetime.combine(end_time, datetime.min.time())
            
            # Get GPS coordinates for location if available
            gps_point = None
            if location:
                gps_point = self._get_location_coordinates(location)
            
            return {
                "event_id": event_id,
                "source_calendar": f"{account['username']} - {calendar.name}",
                "summary": summary,
                "description": description,
                "location": location,
                "start_time": start_time,
                "end_time": end_time,
                "gps_point": gps_point,
                "source_account": account['username']
            }
            
        except Exception as e:
            logging.error(f"Error parsing event details: {e}")
            return None

    def _get_location_coordinates(self, location: str) -> str:
        """Get GPS coordinates for a location using Nominatim"""
        try:
            if not self.nominatim_base_url or not location:
                return None
                
            endpoint = "/search"
            params = {
                'q': location,
                'format': 'json',
                'limit': 1
            }
            
            response = requests.get(
                self.nominatim_base_url + endpoint,
                params=params,
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                if data:
                    lat = data[0]['lat']
                    lon = data[0]['lon']
                    gps_point = f'POINT({lon} {lat})'
                    logging.debug(f"GPS point for location '{location}': {gps_point}")
                    return gps_point
            else:
                logging.warning(f"Nominatim request failed with status {response.status_code}")
                
        except Exception as e:
            logging.error(f"Error fetching GPS coordinates for '{location}': {e}")
            
        return None