from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import sys
import json
import os
import hmac
import hashlib
import base64

app = FastAPI(title="Product Sync Center")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SYNC_FILE = os.path.join(BASE_DIR, "sync_products.py")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# Webhook 自動同步開關
# Render Environment 設定：
# WEBHOOK_AUTO_SYNC_ENABLED=true  開啟
# WEBHOOK_AUTO_SYNC_ENABLED=false 關閉
# =========================

def is_webhook_auto_sync_enabled():
    value = os.getenv(
        "WEBHOOK_AUTO_SYNC_ENABLED",
        "true"
    )

    return value.lower() == "true"


def verify_shopify_webhook(raw_body: bytes, hmac_header: str) -> bool:
    secret = os.getenv("SHOPIFY_WEBHOOK_SECRET")

    if not secret:
        print("❌ SHOPIFY_WEBHOOK_SECRET 未設定")
        return False

    if not hmac_header:
        print("❌ Webhook 沒有 HMAC Header")
        return False

    digest = hmac.new(
        secret.encode("utf-8"),
        raw_body,
        hashlib.sha256
    ).digest()

    calculated_hmac = base64.b64encode(digest).decode("utf-8")

    return hmac.compare_digest(calculated_hmac, hmac_header)


def run_sync_script():
    print("🚀 開始執行 sync_products.py")
    print(f"📄 Sync file path: {SYNC_FILE}")

    result = subprocess.run(
        [sys.executable, SYNC_FILE],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore"
    )

    print("========== SYNC STDOUT ==========")
    print(result.stdout)
    print("========== SYNC STDERR ==========")
    print(result.stderr)
    print("========== SYNC RETURN CODE ==========")
    print(result.returncode)

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

    except Exception as error:
        print("❌ 解析同步 JSON 失敗")
        print(str(error))
        summary["failed"] = 1

    return {
        "success": result.returncode == 0,
        "summary": summary,
        "results": results,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode
    }


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
    <button onclick="runSync()">🚀 手動同步商品</button>
    <p>Webhook 自動同步可用 Render 環境變數 WEBHOOK_AUTO_SYNC_ENABLED 開啟或關閉。</p>
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
def manual_sync():
    print("🖱️ 手動同步被觸發")
    return JSONResponse(run_sync_script())


@app.post("/webhooks/products/create")
async def product_create_webhook(request: Request):
    print("🔥 Product Create Webhook Received")

    raw_body = await request.body()
    hmac_header = request.headers.get("X-Shopify-Hmac-Sha256")

    if not verify_shopify_webhook(raw_body, hmac_header):
        print("❌ Product Create Webhook HMAC 驗證失敗")
        return JSONResponse(
            {
                "success": False,
                "message": "Invalid webhook HMAC"
            },
            status_code=401
        )

    print("✅ Product Create Webhook HMAC 驗證成功")

    if not is_webhook_auto_sync_enabled():
        print("⏸️ Webhook 自動同步已關閉")
        return JSONResponse({
            "success": True,
            "event": "products/create",
            "message": "Webhook received, auto sync disabled"
        })

    data = run_sync_script()

    return JSONResponse({
        "success": True,
        "event": "products/create",
        "message": "Webhook received and sync executed",
        "sync": data
    })


@app.post("/webhooks/products/update")
async def product_update_webhook(request: Request):
    print("🔥 Product Update Webhook Received")

    raw_body = await request.body()
    hmac_header = request.headers.get("X-Shopify-Hmac-Sha256")

    if not verify_shopify_webhook(raw_body, hmac_header):
        print("❌ Product Update Webhook HMAC 驗證失敗")
        return JSONResponse(
            {
                "success": False,
                "message": "Invalid webhook HMAC"
            },
            status_code=401
        )

    print("✅ Product Update Webhook HMAC 驗證成功")

    if not is_webhook_auto_sync_enabled():
        print("⏸️ Webhook 自動同步已關閉")
        return JSONResponse({
            "success": True,
            "event": "products/update",
            "message": "Webhook received, auto sync disabled"
        })

    data = run_sync_script()

    return JSONResponse({
        "success": True,
        "event": "products/update",
        "message": "Webhook received and sync executed",
        "sync": data
    })


@app.get("/health")
def health():
    return {
        "app": "Product Sync Center",
        "status": "running",
        "webhook": "enabled",
        "webhook_auto_sync_enabled": is_webhook_auto_sync_enabled(),
        "sync_file": SYNC_FILE
    }
