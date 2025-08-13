
#mongodb
# main.py

# main.py

# Libraries to install:
# pip install "fastapi[all]" uvicorn
# pip install "strawberry-graphql[fastapi]"

# main.py

import uvicorn
from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter
from fastapi.middleware.cors import CORSMiddleware


# Import the GraphQL schema from the mutations.py file
from mutationss import schema

# Create the FastAPI app
app = FastAPI()

# Allow only local React development server
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create the GraphQL router with the schema
graphql_app = GraphQLRouter(schema,multipart_uploads_enabled=True)

# Include the GraphQL router in the main app
# The 'prefix' argument defines the URL path for your GraphQL endpoint.
app.include_router(graphql_app, prefix="/graphql")

# A basic root endpoint to confirm the app is running
@app.get("/")
async def root():
    return {"message": "Welcome to the FastAPI GraphQL Server!"}

if __name__ == "__main__":
    # Run the server using Uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)



