from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import sys
import json

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
    max-width: 1100px;
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

.summary {
    display: flex;
    gap: 16px;
    margin-bottom: 16px;
}

.summary-box {
    flex: 1;
    background: #f9fafb;
    border: 1px solid #ddd;
    border-radius: 10px;
    padding: 16px;
    font-size: 18px;
    font-weight: bold;
}

.products-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 18px;
}

.product-card {
    background: #ffffff;
    border: 1px solid #ddd;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}

.product-card img {
    width: 100%;
    height: 220px;
    object-fit: cover;
    background: #f3f4f6;
}

.product-content {
    padding: 16px;
}

.product-title {
    font-weight: bold;
    font-size: 16px;
    margin-bottom: 8px;
}

.status-success {
    color: green;
    font-weight: bold;
}

.status-skipped {
    color: orange;
    font-weight: bold;
}

.status-failed {
    color: red;
    font-weight: bold;
}

.link-btn {
    display: inline-block;
    margin-top: 10px;
    background: #2563eb;
    color: white;
    text-decoration: none;
    padding: 8px 12px;
    border-radius: 6px;
}

pre {
    background: #111827;
    color: #10b981;
    padding: 20px;
    border-radius: 8px;
    white-space: pre-wrap;
    font-size: 14px;
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
        <option value="ash-golf-taiwan.myshopify.com">
            ASH（正式主商店）
        </option>
    </select>
    <p class="note">目前為開發測試階段，正式版會改成 ASH。</p>
</div>

<div class="card">
    <h2>② 目標商店（可多選）</h2>
    <div class="checkbox-group">
        <label class="checkbox-item">
            <input type="checkbox" checked data-brand="DESCENTE" value="target-demo-1-74h5qyuh.myshopify.com">
            DESCENTE（測試）
        </label>

        <label class="checkbox-item">
            <input type="checkbox" checked data-brand="GFORE" value="target-demo-1-74h5qyuh.myshopify.com">
            G/FORE（測試）
        </label>

        <label class="checkbox-item">
            <input type="checkbox" checked data-brand="2XU" value="target-demo-1-74h5qyuh.myshopify.com">
            2XU（測試）
        </label>

        <label class="checkbox-item">
            <input type="checkbox" checked data-brand="CALLAWAY" value="target-demo-1-74h5qyuh.myshopify.com">
            CALLAWAY（測試）
        </label>
    </div>
</div>

<div class="card">
    <h2>③ 品牌同步規則（自動產生）</h2>
    <textarea id="brandRules" rows="6" readonly></textarea>
</div>

<div class="card">
    <button onclick="runSync()">🚀 開始同步商品</button>
</div>

<div class="card">
    <h2>④ 同步結果</h2>

    <div class="summary">
        <div class="summary-box">✅ 成功：<span id="successCount">0</span></div>
        <div class="summary-box">⏭️ 略過：<span id="skippedCount">0</span></div>
        <div class="summary-box">❌ 失敗：<span id="failedCount">0</span></div>
    </div>

    <div id="productCards" class="products-grid">
        <p>尚未執行同步</p>
    </div>
</div>

<div class="card">
    <h2>⑤ 原始同步輸出</h2>
    <pre id="rawOutput">尚未執行同步</pre>
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

function statusText(status) {
    if (status === "success") return "✅ 成功";
    if (status === "skipped") return "⏭️ 已存在 / 略過";
    if (status === "failed") return "❌ 失敗";
    return status;
}

function statusClass(status) {
    if (status === "success") return "status-success";
    if (status === "skipped") return "status-skipped";
    if (status === "failed") return "status-failed";
    return "";
}

async function runSync() {
    const productCards = document.getElementById("productCards");
    const rawOutput = document.getElementById("rawOutput");

    productCards.innerHTML = "<p>同步中，請稍候...</p>";
    rawOutput.textContent = "同步中，請稍候...";

    try {
        const response = await fetch("/sync", { method: "POST" });
        const data = await response.json();

        document.getElementById("successCount").textContent = data.summary.success || 0;
        document.getElementById("skippedCount").textContent = data.summary.skipped || 0;
        document.getElementById("failedCount").textContent = data.summary.failed || 0;

        rawOutput.textContent =
            "執行狀態：" + (data.success ? "成功" : "失敗") + "\\n\\n" +
            "Return Code：" + data.returncode + "\\n\\n" +
            "同步輸出：\\n" + data.stdout + "\\n\\n" +
            "錯誤訊息：\\n" + data.stderr;

        productCards.innerHTML = "";

        if (!data.results || data.results.length === 0) {
            productCards.innerHTML = "<p>沒有同步商品資料。</p>";
            return;
        }

        data.results.forEach(item => {
            const image = item.image || "https://cdn.shopify.com/s/files/1/0533/2089/files/placeholder-images-image_large.png";
            const productUrl = item.product_url || "#";

            productCards.innerHTML += `
                <div class="product-card">
                    <img src="${image}" alt="${item.title}">
                    <div class="product-content">
                        <div class="product-title">${item.title}</div>
                        <div>品牌：${item.vendor || "-"}</div>
                        <div>目標商店：${item.target_shop || "-"}</div>
                        <div class="${statusClass(item.status)}">狀態：${statusText(item.status)}</div>
                        <div>訊息：${item.message || ""}</div>
                        ${productUrl !== "#" ? `<a class="link-btn" href="${productUrl}" target="_blank">查看商品</a>` : ""}
                    </div>
                </div>
            `;
        });

    } catch (error) {
        productCards.innerHTML = "<p>同步失敗。</p>";
        rawOutput.textContent = "同步失敗：\\n" + error;
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

    summary = {
        "success": 0,
        "skipped": 0,
        "failed": 0
    }

    results = []

    stdout = result.stdout or ""

    try:
        start_key = "SYNC_RESULT_JSON_START"
        end_key = "SYNC_RESULT_JSON_END"

        if start_key in stdout and end_key in stdout:
            json_text = stdout.split(start_key)[-1].split(end_key)[0].strip()
            parsed = json.loads(json_text)
            summary = parsed.get("summary", summary)
            results = parsed.get("results", [])

    except Exception:
        summary["failed"] = 1

    return JSONResponse({
        "success": result.returncode == 0,
        "summary": summary,
        "results": results,
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
