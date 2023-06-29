import uvicorn
from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.comment.api import router

app = FastAPI(
    title="Free Comments API",
    version="1.0.0b"
)

app.include_router(router)


@app.get("/", include_in_schema=False)
async def redirect_to_docs():
    return RedirectResponse("/docs")


if __name__ == "__main__":
    uvicorn.run("main:app", host="localhost", port=8000, reload=True)
