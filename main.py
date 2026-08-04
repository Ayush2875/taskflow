from fastapi import FastAPI

app=FastAPI()

@app.get("/")
def get_req():
    return "Hello"
