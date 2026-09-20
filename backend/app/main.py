from fastapi import FastAPI

app = FastAPI(title="Portfolio API")


@app.get("/")
async def root() -> dict[str, str]:
    return {"status": "ok"}
