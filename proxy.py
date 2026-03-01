#!/usr/bin/env python3
"""
Local proxy server for the Economic Dashboard.
Serves static files AND proxies /api/fred/* → api.stlouisfed.org with CORS headers.
"""
import http.server
import urllib.request
import ssl
import os

# macOS Python ships without system certs; create a context that skips
# verification for this local-only dev proxy (traffic goes to FRED's HTTPS).
_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE

PORT = 8080
FRED_BASE = 'https://api.stlouisfed.org/fred/series/observations'


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/api/fred'):
            self._proxy_fred()
        else:
            super().do_GET()

    def _proxy_fred(self):
        qs = self.path[len('/api/fred'):]      # keep the ?series_id=...&... part
        fred_url = FRED_BASE + qs
        try:
            req = urllib.request.Request(fred_url, headers={'User-Agent': 'EconDashboard/1.0'})
            with urllib.request.urlopen(req, timeout=30, context=_ssl_ctx) as resp:
                data = resp.read()
            self.send_response(200)
            self._cors_headers()
            self.end_headers()
            self.wfile.write(data)
        except urllib.error.HTTPError as e:
            data = e.fp.read()
            self.send_response(e.code)
            self._cors_headers()
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            self.send_response(502)
            self._cors_headers()
            self.end_headers()
            self.wfile.write(f'{{"error_message":"{e}"}}'.encode())

    def _cors_headers(self):
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')

    def log_message(self, fmt, *args):
        pass  # quiet


if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    with http.server.HTTPServer(('', PORT), Handler) as httpd:
        print(f'Dashboard → http://localhost:{PORT}/economic-dashboard.html')
        httpd.serve_forever()
