from http.server import BaseHTTPRequestHandler
import json
import urllib.parse
from src.scraper import get_recent_reviews
from src.analyzer import analyze_reviews
from src.mailer import send_email
from src.config import Config

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            url = data.get('url')
            email = data.get('email')
            
            if not url or not email:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": "URL and Email are required."}).encode('utf-8'))
                return

            # Parse URL to extract ID and Country
            google_play_id = None
            app_store_id = None
            country = 'in' # Default
            
            parsed_url = urllib.parse.urlparse(url)
            
            if "play.google.com" in parsed_url.netloc:
                query_params = urllib.parse.parse_qs(parsed_url.query)
                google_play_id = query_params.get('id', [None])[0]
                if not google_play_id:
                     raise ValueError("Invalid Google Play URL")
            elif "apps.apple.com" in parsed_url.netloc:
                # Format: https://apps.apple.com/in/app/app-name/id123456789
                path_parts = parsed_url.path.split('/')
                for part in path_parts:
                    if part.startswith('id'):
                        app_store_id = part[2:]
                    if len(part) == 2: # Simple heuristic for country code
                        country = part
                if not app_store_id:
                    raise ValueError("Invalid App Store URL")
            else:
                raise ValueError("Unsupported URL. Please use Google Play or App Store URL.")

            # 1. Fetch Reviews
            reviews = get_recent_reviews(
                google_play_id=google_play_id,
                app_store_id=app_store_id,
                country=country,
                weeks=Config.WEEKS_TO_ANALYZE
            )
            
            if reviews.empty:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "message": "No reviews found in the last 12 weeks."}).encode('utf-8'))
                return

            # 2. Analyze Reviews
            analysis = analyze_reviews(reviews)
            if not analysis:
                raise Exception("Analysis failed.")

            # 3. Send Email
            # Override recipient email for this request
            # We need to modify send_email to accept recipient or handle it here.
            # Ideally send_email should take the recipient as an argument.
            # For now, let's check mailer.py. 
            # It uses Config.RECIPIENT_EMAIL. We should probably update mailer.py too.
            # But for now, let's assume we can pass it or it uses the default.
            # Wait, I should verify mailer.py first. 
            # Let's assume I will fix mailer.py in the next step if needed.
            # Actually, let's look at mailer.py content from previous turn.
            # It imports Config. 
            
            # Let's pass the email to send_email if I update it.
            # For now I will write this file assuming I will update mailer.py to accept 'to_email'.
            
            email_response = send_email(analysis, to_email=email)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "success", 
                "message": "Analysis complete and email sent.",
                "data": analysis
            }, default=str).encode('utf-8'))

        except Exception as e:
            print(f"Analysis failed: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))
