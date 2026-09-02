import sys
import urllib.error
import urllib.request

# Gateway's catch-all proxy has no route for "/" itself (nothing in the
# routing table matches), so it correctly answers with a 404 — still a
# real HTTP response, proving the server is up. urlopen() raises
# HTTPError on any non-2xx status; that still counts as healthy here.
# Only a connection failure (server not listening at all) is unhealthy.
try:
    urllib.request.urlopen("http://localhost:8000/", timeout=2)
except urllib.error.HTTPError:
    pass
except Exception:
    sys.exit(1)
