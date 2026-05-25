from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import sys

app = FastAPI(title="Product Sync Center")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
def home():
    return """
<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8">
<title>Product Sync Center</title>
<style>
body {
    font-family: Arial, sans-serif;
    background: #f6f6f7;
    padding: 32px;
}
.card {
    background: white;
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 20px;
    border: 1px solid #ddd;
}
button {
    background: #008060;
    color: white;
    border: none;
    padding: 14px 28px;
    border-radius: 8px;
    font-size: 18px;
    cursor: pointer;
}
pre {
    background: #111827;
    color: #10b981;
    padding: 20px;
    border-radius: 8px;
    white-space: pre-wrap;
    font-size: 15px;
}
</style>
</head>
<body>

<h1>📦 Product Sync Center</h1>
<p>Shopify 多商店商品同步管理系統</p>

<div class="card">
    <button onclick="runSync()">🚀 開始同步商品</button>
</div>

<div class="card">
    <h2>同步結果</h2>
    <pre id="result">尚未執行同步</pre>
</div>

<script>
async function runSync() {
    const resultBox = document.getElementById("result");
    resultBox.textContent = "同步中，請稍候...";

    try {
        const response = await fetch("/sync", {
            method: "POST"
        });

        const data = await response.json();

        resultBox.textContent =
            "執行狀態：" + (data.success ? "成功" : "失敗") + "\\n\\n" +
            "Return Code：" + data.returncode + "\\n\\n" +
            "同步輸出：\\n" + data.stdout + "\\n\\n" +
            "錯誤訊息：\\n" + data.stderr;

    } catch (error) {
        resultBox.textContent = "同步失敗：\\n" + error;
    }
}
</script>

</body>
</html>
"""


@app.post("/sync")
def sync_products():
    result = subprocess.run(
        [sys.executable, "sync_products.py"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore"
    )

    return JSONResponse({
        "success": result.returncode == 0,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode
    })


@app.get("/health")
def health():
    return {
        "app": "Product Sync Center",
        "status": "running"
    }
