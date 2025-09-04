# Libraries to install:
# pip install "fastapi[all]" uvicorn
# pip install "strawberry-graphql[fastapi]"

import uvicorn
from fastapi import FastAPI, Request
from strawberry.fastapi import GraphQLRouter
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

# Import the GraphQL schema
from mutationss import schema

# ----------------- AUTHENTICATION CODE (COMMENTED FOR DEVELOPMENT) -----------------
from authenticate import AuthenticatedUser, get_current_user

async def get_context(request: Request) -> dict:
    current_user: Optional[AuthenticatedUser] = None
    try:
        current_user = get_current_user(request)
    except Exception as e:
        print(f"Authentication failed: {e}")
    return {
        "current_user": current_user,
    }
# -----------------------------------------------------------------------------------

# Create the FastAPI app
app = FastAPI()

# Allow only local React development server
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000"
]

app.add_middleware(
    CORSMiddleware,
    # allow_origins=origins,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------- PRODUCTION ROUTER (COMMENTED FOR DEVELOPMENT) -----------------
# For production, use this router to enable authentication
graphql_app = GraphQLRouter(
    schema,
    context_getter=get_context,
    multipart_uploads_enabled=True,
)
# ---------------------------------------------------------------------------------

# ----------------- DEVELOPMENT ROUTER (UNCOMMENTED) ------------------------------
# For development, use this router without authentication
# graphql_app = GraphQLRouter(
#     schema,
#     multipart_uploads_enabled=True,
# )
# ---------------------------------------------------------------------------------

# Include the GraphQL router in the main app
app.include_router(graphql_app, prefix="/graphql")

# A basic root endpoint to confirm the app is running
@app.get("/")
async def root():
    return {"message": "Welcome to the FastAPI GraphQL Server!"}

if __name__ == "__main__":
    # Run the server using Uvicorn
    # uvicorn.run(app, host="0.0.0.0", port=8000)
    uvicorn.run(app, host="0.0.0.0", port=9091)