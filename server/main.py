from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title = "Clinical Protocol API",description = "api for ai clinical chatbot")

#CORS setup

app.add_middleware(
    CORSMiddleware,
    allow_origins = ["*"],
    allow_credentials = ["*"],
    allow_headers = ["*"],
    allow_methods = ["*"]
)

#Middleware exception handlers

#routers

# 1.upload pdf documents
# 2. asking query