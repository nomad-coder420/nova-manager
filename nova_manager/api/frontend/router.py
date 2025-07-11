from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates


router = APIRouter()


templates = Jinja2Templates(directory="nova_manager/templates")


@router.get("/")
async def serve_frontend(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
