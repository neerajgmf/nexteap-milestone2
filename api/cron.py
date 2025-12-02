from http.server import BaseHTTPRequestHandler
import json
from src.scraper import get_recent_reviews
from src.analyzer import analyze_reviews
from src.mailer import send_email

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            print("Starting cron job...")
            
            # 1. Fetch Reviews
            from src.config import Config
            reviews = get_recent_reviews(
                google_play_id=Config.GOOGLE_PLAY_ID,
                app_store_id=Config.APP_STORE_ID,
                country=Config.APP_STORE_COUNTRY,
                weeks=Config.WEEKS_TO_ANALYZE
            )
            print(f"Fetched {len(reviews)} reviews.")
            
            if reviews.empty:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "message": "No reviews found."}).encode('utf-8'))
                return

            # 2. Analyze Reviews
            analysis = analyze_reviews(reviews)
            if not analysis:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": "Analysis failed."}).encode('utf-8'))
                return

            # 3. Send Email
            email_response = send_email(analysis)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "success", 
                "message": "Report generated and sent.",
                "email_id": email_response.get('id') if email_response else None
            }).encode('utf-8'))

        except Exception as e:
            print(f"Cron job failed: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))
