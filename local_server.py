from http.server import HTTPServer, SimpleHTTPRequestHandler
import os
import sys

# Add the current directory to sys.path so imports in api/analyze.py work
sys.path.append(os.getcwd())

try:
    from api.analyze import handler as AnalyzeHandler
except ImportError as e:
    print(f"Error importing api.analyze: {e}")
    sys.exit(1)

class LocalRequestHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        # Serve static files from public/ directory
        if self.path == '/' or self.path == '/index.html':
            self.path = '/public/index.html'
        elif self.path.startswith('/style.css'):
             self.path = '/public/style.css'
        elif self.path.startswith('/script.js'):
             self.path = '/public/script.js'
        
        return SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        if self.path == '/api/analyze':
            # Delegate to the Vercel handler
            # We instantiate the handler with the current request details.
            # This effectively hands over control of the request to AnalyzeHandler.
            AnalyzeHandler(self.request, self.client_address, self.server)
            return
        
        self.send_error(404, "Not Found")

if __name__ == '__main__':
    port = 8000
    print(f"Starting local server on http://localhost:{port}")
    httpd = HTTPServer(('localhost', port), LocalRequestHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        httpd.server_close()
