from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {
        "app": "Product Sync Center",
        "status": "running",
        "message": "Shopify 商品同步系統已啟動"
    }

@app.post("/sync")
def sync():
    return {
        "success": True,
        "message": "商品同步成功",
        "source_store": "master-demo",
        "target_store": "target-demo-1",
        "products_synced": 25
    }