from fastapi import FastAPI

app = FastAPI(title="Calculator Microservice")


@app.get("/health")
def health_check():
    return {"status": "ok"}
