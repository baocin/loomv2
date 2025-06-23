import asyncio
import logging
import random
import tempfile
from playwright.async_api import async_playwright
from typing import Dict, Any, Optional

class XTweetProcessor:
    def __init__(self):
        """Initialize X.com tweet processor"""
        self.playwright_instance = None
        self.browser = None
        self.context = None
        
        # User agents for rotation
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.101 Safari/537.36"
        ]

    async def setup(self):
        """Setup browser for screenshot capture"""
        self.playwright_instance = await async_playwright().start()
        
        user_agent = random.choice(self.user_agents)
        self.browser = await self.playwright_instance.chromium.launch(headless=True)
        
        self.context = await self.browser.new_context(
            viewport={"width": 700, "height": 3000}, 
            user_agent=user_agent
        )

    async def scrape_tweet(self, url: str) -> Optional[Dict[str, Any]]:
        """Scrape tweet content and take screenshot"""
        _xhr_calls = []

        async def intercept_response(response):
            if response.request.resource_type == "xhr":
                _xhr_calls.append(response)
            return response

        page = await self.context.new_page()
        page.on("response", intercept_response)
        
        try:
            await page.goto(url)

            try:
                await page.wait_for_load_state("networkidle", timeout=2000)
            except Exception:
                pass
            
            # Check if the page contains the text indicating the tweet doesn't exist
            if await page.locator("text=Hmm...this page doesn't exist. Try searching for something else.").count() > 0:
                logging.info(f"Tweet does not exist: {url}")
                return None

            tweet_id = url.split("/")[-1]
            
            # Take screenshot
            try:
                image_data = await page.locator('[data-testid="tweet"]').screenshot(timeout=5000)
            except Exception as e:
                logging.error(f"Screenshot failed: {e} - {url}")
                try:
                    image_data = await page.locator('[data-testid="primaryColumn"]').screenshot(timeout=5000)
                except Exception as e:
                    logging.error(f"Screenshot of primaryColumn also failed: {e} - {url}")
                    image_data = None

            # Collect background API calls for tweet data
            tweet_data = await self._collect_background_calls(_xhr_calls)
            
            if tweet_data:
                tweet_data['image_data'] = image_data
                tweet_data['url'] = url
                tweet_data['tweet_id'] = tweet_id
                
                return tweet_data
            
            return None
            
        except Exception as e:
            logging.error(f"Error scraping tweet {url}: {e}")
            return None
        finally:
            await page.close()

    async def _collect_background_calls(self, _xhr_calls) -> Optional[Dict[str, Any]]:
        """Extract tweet data from XHR calls"""
        try:
            tweet_calls = [f for f in _xhr_calls if "TweetResultByRestId" in f.url]
            for xhr in tweet_calls:
                data = await xhr.json()
                if 'data' in data and 'tweetResult' in data['data'] and 'result' in data['data']['tweetResult']:
                    result = data['data']['tweetResult']['result']
                    
                    # Extract relevant fields
                    core = result.get('core', {})
                    user_results = core.get('user_results', {})
                    user_result = user_results.get('result', {}) if user_results else {}
                    legacy_user = user_result.get('legacy', {}) if user_result else {}
                    
                    legacy_tweet = result.get('legacy', {})
                    
                    return {
                        'user': {
                            'id': user_result.get('rest_id'),
                            'name': legacy_user.get('name'),
                            'screen_name': legacy_user.get('screen_name'),
                        },
                        'text': legacy_tweet.get('full_text', ''),
                        'created_at': legacy_tweet.get('created_at'),
                        'favorite_count': legacy_tweet.get('favorite_count', 0),
                        'retweet_count': legacy_tweet.get('retweet_count', 0),
                        'reply_count': legacy_tweet.get('reply_count', 0),
                        'lang': legacy_tweet.get('lang'),
                        'source': legacy_tweet.get('source'),
                        'raw_data': result
                    }
                    
        except Exception as e:
            logging.error(f"Error collecting background calls: {e}")
            
        return None

    async def cleanup(self):
        """Cleanup browser resources"""
        if self.browser:
            await self.browser.close()
        if self.playwright_instance:
            await self.playwright_instance.stop()