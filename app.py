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
    margin: 0;
}

.container {
    max-width: 1000px;
    margin: 0 auto;
}

.card {
    background: white;
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 20px;
    border: 1px solid #ddd;
}

h1 {
    font-size: 32px;
    margin-bottom: 8px;
}

h2 {
    margin-top: 0;
}

select, textarea {
    width: 100%;
    padding: 12px;
    font-size: 16px;
    border: 1px solid #ccc;
    border-radius: 6px;
}

.checkbox-group {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 12px;
}

.checkbox-item {
    background: #f9fafb;
    padding: 12px;
    border: 1px solid #ddd;
    border-radius: 8px;
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

.note {
    color: #666;
    font-size: 14px;
}
</style>
</head>

<body>
<div class="container">

<h1>📦 Product Sync Center</h1>
<p>Shopify 多商店商品同步管理系統</p>

<div class="card">
    <h2>① 主來源商店</h2>
    <select id="sourceStore">
        <option value="master-demo-lflzyu3e.myshopify.com" selected>
            MASTER DEMO（測試主商店）
        </option>
    </select>
    <p class="note">目前為開發測試階段，正式版會改成 ASH。</p>
</div>

<div class="card">
    <h2>② 目標商店</h2>
    <div class="checkbox-group">
        <div class="checkbox-item">
            <input type="checkbox" checked data-brand="DESCENTE" value="target-demo-1-74h5qyuh.myshopify.com">
            DESCENTE（測試）
        </div>
        <div class="checkbox-item">
            <input type="checkbox" checked data-brand="GFORE" value="target-demo-1-74h5qyuh.myshopify.com">
            G/FORE（測試）
        </div>
        <div class="checkbox-item">
            <input type="checkbox" checked data-brand="2XU" value="target-demo-1-74h5qyuh.myshopify.com">
            2XU（測試）
        </div>
        <div class="checkbox-item">
            <input type="checkbox" checked data-brand="CALLAWAY" value="target-demo-1-74h5qyuh.myshopify.com">
            CALLAWAY（測試）
        </div>
    </div>
</div>

<div class="card">
    <h2>③ 品牌同步規則</h2>
    <textarea id="brandRules" rows="6" readonly></textarea>
</div>

<div class="card">
    <button onclick="runSync()">🚀 開始同步商品</button>
</div>

<div class="card">
    <h2>④ 同步結果</h2>
    <pre id="result">尚未執行同步</pre>
</div>

</div>

<script>
function generateRules() {
    const checked = document.querySelectorAll('.checkbox-group input[type="checkbox"]:checked');
    let rules = [];

    checked.forEach(item => {
        rules.push(item.dataset.brand + " -> " + item.value);
    });

    document.getElementById("brandRules").value =
        rules.length > 0 ? rules.join("\\n") : "尚未選擇目標商店";
}

document.querySelectorAll('.checkbox-group input[type="checkbox"]').forEach(item => {
    item.addEventListener("change", generateRules);
});

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

generateRules();
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
        "status": "running",
        "message": "Shopify 商品同步系統已啟動"
    }
