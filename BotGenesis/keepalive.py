"""
Keepalive Web Server
Maintains bot uptime by running a simple web server that can be pinged by uptime services.
"""

from aiohttp import web
import asyncio
import logging
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class KeepAliveServer:
    def __init__(self, host='0.0.0.0', port=5000):
        self.host = host
        self.port = port
        self.app = web.Application()
        self.setup_routes()
        
    def setup_routes(self):
        """Setup web server routes"""
        self.app.router.add_get('/', self.index)
        self.app.router.add_get('/status', self.status)
        self.app.router.add_get('/health', self.health)
        self.app.router.add_get('/ping', self.ping)
        
    async def index(self, request):
        """Main page"""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Discord Bot - Online</title>
            <style>
                body { 
                    font-family: Arial, sans-serif; 
                    text-align: center; 
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    margin: 0;
                    padding: 50px;
                }
                .container {
                    background: rgba(255,255,255,0.1);
                    padding: 40px;
                    border-radius: 15px;
                    backdrop-filter: blur(10px);
                    max-width: 600px;
                    margin: 0 auto;
                }
                .status { 
                    color: #00ff00; 
                    font-size: 24px; 
                    font-weight: bold;
                    margin: 20px 0;
                }
                .info {
                    background: rgba(255,255,255,0.1);
                    padding: 20px;
                    border-radius: 10px;
                    margin: 20px 0;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🤖 Advanced Discord Moderation Bot</h1>
                <div class="status">🟢 ONLINE</div>
                <div class="info">
                    <h3>Server Status</h3>
                    <p><strong>Uptime:</strong> Since server start</p>
                    <p><strong>Last Check:</strong> {timestamp}</p>
                    <p><strong>Health:</strong> All systems operational</p>
                </div>
                <div class="info">
                    <h3>Features</h3>
                    <p>✅ 20 Moderation Commands</p>
                    <p>✅ 10 Administration Commands</p>
                    <p>✅ Advanced Echo System</p>
                    <p>✅ 24/7 Uptime Monitoring</p>
                    <p>✅ Database Integration</p>
                </div>
            </div>
        </body>
        </html>
        """.format(timestamp=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'))
        
        return web.Response(text=html, content_type='text/html')
    
    async def status(self, request):
        """Status endpoint for monitoring"""
        data = {
            'status': 'online',
            'timestamp': datetime.utcnow().isoformat(),
            'uptime': 'active',
            'version': '1.0.0'
        }
        return web.json_response(data)
    
    async def health(self, request):
        """Health check endpoint"""
        return web.json_response({'health': 'ok', 'timestamp': datetime.utcnow().isoformat()})
    
    async def ping(self, request):
        """Simple ping endpoint"""
        return web.Response(text='pong')

def keep_alive():
    """Start the keepalive server"""
    try:
        server = KeepAliveServer()
        
        async def run_server():
            runner = web.AppRunner(server.app)
            await runner.setup()
            site = web.TCPSite(runner, server.host, server.port)
            await site.start()
            logger.info(f"Keepalive server started on {server.host}:{server.port}")
        
        # Run server in background
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.create_task(run_server())
        
        # Start the event loop in a separate thread
        import threading
        thread = threading.Thread(target=loop.run_forever, daemon=True)
        thread.start()
        
        logger.info("Keepalive system initialized")
        
    except Exception as e:
        logger.error(f"Failed to start keepalive server: {e}")

if __name__ == "__main__":
    # For testing the server standalone
    server = KeepAliveServer()
    web.run_app(server.app, host=server.host, port=server.port)