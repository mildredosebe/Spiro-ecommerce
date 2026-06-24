from django.http import HttpResponse

def scalar_docs(request):
    return HttpResponse("""
    <!doctype html>
    <html>
    <head>
      <title>API Documentation</title>
    </head>
    <body>
      <script
        id="api-reference"
        data-url="/api/schema/">
      </script>

      <script src="https://cdn.jsdelivr.net/npm/@scalar/api-reference"></script>
    </body>
    </html>
    """)