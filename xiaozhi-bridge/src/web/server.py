"""
Web UI server for device activation.
Provides simple HTML interface for activation process.
"""

import logging
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

logger = logging.getLogger(__name__)


def setup_web_ui(app: FastAPI, bridge):
    """Setup web UI routes."""
    
    templates_dir = Path(__file__).parent / "templates"
    static_dir = Path(__file__).parent / "static"
    
    # Create directories if they don't exist
    templates_dir.mkdir(exist_ok=True)
    static_dir.mkdir(exist_ok=True)
    
    # Mount static files
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    
    templates = Jinja2Templates(directory=str(templates_dir))
    
    @app.get("/", response_class=HTMLResponse)
    async def home(request: Request):
        """Home page with activation status."""
        status = bridge.get_status()
        
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "status": status,
                "bridge": bridge
            }
        )
    
    @app.get("/activate", response_class=HTMLResponse)
    async def activate_page(request: Request):
        """Activation page with code display."""
        if bridge.identity.is_activated():
            return templates.TemplateResponse(
                "activated.html",
                {"request": request, "status": bridge.get_status()}
            )
        
        # Start activation if not started
        success, user_code = await bridge.activate()
        
        return templates.TemplateResponse(
            "activate.html",
            {
                "request": request,
                "user_code": user_code if success else None,
                "success": success
            }
        )
    
    logger.info("Web UI setup complete")
