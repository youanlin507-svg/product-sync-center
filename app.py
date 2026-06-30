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
import requests

app = FastAPI(title="Product Sync Center")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SYNC_FILE = os.path.join(BASE_DIR, "sync_products.py")
WEBHOOK_SETTING_FILE = os.path.join(BASE_DIR, "webhook_setting.json")
BRAND_RULES_FILE = os.path.join(BASE_DIR, "brand_rules.json")
SELECTED_PRODUCTS_FILE = os.path.join(BASE_DIR, "selected_products.json")

API_VERSION = "2024-04"
MASTER_SHOP = os.getenv("MASTER_SHOP")
MASTER_TOKEN = os.getenv("MASTER_TOKEN")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DEFAULT_BRAND_RULES = {
    "DESCENTE": ["target-demo-1-74h5qyuh.myshopify.com"],
    "GFORE": ["target-demo-1-74h5qyuh.myshopify.com"],
    "2XU": ["target-demo-1-74h5qyuh.myshopify.com"],
    "CALLAWAY": ["target-demo-1-74h5qyuh.myshopify.com"],
}


def get_brand_rules():
    if not os.path.exists(BRAND_RULES_FILE):
        return DEFAULT_BRAND_RULES

    try:
        with open(BRAND_RULES_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return DEFAULT_BRAND_RULES


def set_brand_rules(rules):
    with open(BRAND_RULES_FILE, "w", encoding="utf-8") as file:
        json.dump(rules, file, ensure_ascii=False, indent=2)


def get_webhook_setting():
    if not os.path.exists(WEBHOOK_SETTING_FILE):
        return True

    try:
        with open(WEBHOOK_SETTING_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
            return data.get("enabled", True)
    except Exception:
        return True


def set_webhook_setting(enabled: bool):
    with open(WEBHOOK_SETTING_FILE, "w", encoding="utf-8") as file:
        json.dump({"enabled": enabled}, file, ensure_ascii=False)


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

input, select, textarea {
    width: 100%;
    padding: 12px;
    font-size: 16px;
    border: 1px solid #ccc;
    border-radius: 6px;
}

.rule-row {
    display: grid;
    grid-template-columns: 180px 1fr;
    gap: 12px;
    align-items: center;
    margin-bottom: 14px;
}

.rule-brand {
    font-weight: bold;
}

button {
    background: #008060;
    color: white;
    border: none;
    padding: 14px 28px;
    border-radius: 8px;
    font-size: 18px;
    cursor: pointer;
    margin-right: 10px;
    margin-top: 8px;
}

button.off {
    background: #d72c0d;
}

button.gray {
    background: #4b5563;
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

.webhook-status {
    font-size: 20px;
    font-weight: bold;
    margin-bottom: 14px;
}

.note {
    color: #6b7280;
    font-size: 14px;
}

.product-select-item {
    display: grid;
    grid-template-columns: 36px 72px 1fr;
    gap: 12px;
    align-items: center;
    padding: 12px;
    border: 1px solid #ddd;
    border-radius: 10px;
    margin-bottom: 10px;
    background: #f9fafb;
}

.product-select-item img {
    width: 72px;
    height: 72px;
    object-fit: cover;
    border-radius: 8px;
    background: #f3f4f6;
}

.product-meta {
    font-size: 13px;
    color: #6b7280;
    margin-top: 4px;
}

.product-link {
    font-weight: bold;
    color: #2563eb;
    text-decoration: none;
}

.product-link:hover {
    text-decoration: underline;
}

#rawOutput {
    display: none;
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
    <h2>② 品牌同步規則</h2>
    <p class="note">每個品牌可以設定一個或多個目標商店，若有多個商店請用逗號分隔。</p>

    <div class="rule-row">
        <div class="rule-brand">DESCENTE</div>
        <input id="rule_DESCENTE" placeholder="target-demo-1-74h5qyuh.myshopify.com">
    </div>

    <div class="rule-row">
        <div class="rule-brand">G/FORE</div>
        <input id="rule_GFORE" placeholder="target-demo-1-74h5qyuh.myshopify.com">
    </div>

    <div class="rule-row">
        <div class="rule-brand">2XU</div>
        <input id="rule_2XU" placeholder="target-demo-1-74h5qyuh.myshopify.com">
    </div>

    <div class="rule-row">
        <div class="rule-brand">CALLAWAY</div>
        <input id="rule_CALLAWAY" placeholder="target-demo-1-74h5qyuh.myshopify.com">
    </div>

    <button onclick="saveBrandRules()">💾 儲存品牌規則</button>
    <button class="gray" onclick="showBrandRules()">📋 查看同步規則</button>
</div>

<div class="card">
    <h2>③ Webhook 自動同步開關</h2>
    <div id="webhookStatus" class="webhook-status">讀取中...</div>
    <button onclick="setWebhook(true)">開啟自動同步</button>
    <button class="off" onclick="setWebhook(false)">關閉自動同步</button>
    <p>關閉後，Shopify 仍會送 Webhook，但系統不會自動執行同步。</p>
</div>

<div class="card">
    <h2>④ 最近商品（100筆）</h2>

    <input
        id="productSearch"
        placeholder="搜尋商品名稱..."
        oninput="renderProductList()"
    >

    <select
        id="brandFilter"
        onchange="renderProductList()"
        style="margin-top:10px;"
    >
        <option value="">全部品牌</option>
        <option value="DESCENTE">DESCENTE</option>
        <option value="GFORE">G/FORE</option>
        <option value="2XU">2XU</option>
        <option value="CALLAWAY">CALLAWAY</option>
    </select>

    <select
        id="sortMode"
        onchange="loadProducts()"
        style="margin-top:10px;"
    >
        <option value="updated">最近更新</option>
        <option value="created">最近新增</option>
    </select>

    <div style="margin-top:12px;">
        <button onclick="loadProducts()">📦 載入最近100筆</button>
        <button class="gray" onclick="selectAllProducts()">☑ 全選本頁</button>
        <button class="gray" onclick="clearAllProducts()">取消全選</button>
    </div>

    <p id="selectedCount" class="note">已選 0 個商品</p>

    <div id="productSelector" style="margin-top:20px;"></div>

    <div style="margin-top:12px;">
        <button class="gray" onclick="prevPage()">上一頁</button>
        <button class="gray" onclick="nextPage()">下一頁</button>
        <span id="pageInfo" class="note"></span>
    </div>

    <button onclick="syncSelectedProducts()">
        🚀 同步已選商品
    </button>
</div>

<div class="card">
    <h2>⑤ 同步結果</h2>

    <div class="summary">
        <div class="summary-box">✅ 成功：<span id="successCount">0</span></div>
        <div class="summary-box">⏭️ 略過：<span id="skippedCount">0</span></div>
        <div class="summary-box">❌ 失敗：<span id="failedCount">0</span></div>
    </div>

    <div id="productCards" class="products-grid">
        <p>尚未執行同步</p>
    </div>
</div>

<pre id="rawOutput">尚未執行同步</pre>

</div>

<script>
const BRANDS = ["DESCENTE", "GFORE", "2XU", "CALLAWAY"];

let allProducts = [];
let currentPage = 1;
const pageSize = 20;

function splitStores(value) {
    return value
        .split(",")
        .map(item => item.trim())
        .filter(item => item.length > 0);
}

function formatDate(value) {
    if (!value) return "-";

    try {
        const date = new Date(value);
        return date.toLocaleString("zh-TW");
    } catch {
        return value;
    }
}

async function loadBrandRules() {
    const response = await fetch("/brand-rules/status");
    const data = await response.json();

    const rules = data.rules || {};

    BRANDS.forEach(brand => {
        const input = document.getElementById("rule_" + brand);
        if (input) {
            input.value = (rules[brand] || []).join(", ");
        }
    });
}

async function saveBrandRules() {
    let rules = {};

    BRANDS.forEach(brand => {
        const input = document.getElementById("rule_" + brand);
        rules[brand] = splitStores(input.value || "");
    });

    const response = await fetch("/brand-rules/save", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            rules: rules
        })
    });

    const data = await response.json();

    if (data.success) {
        alert("品牌同步規則已儲存");
    } else {
        alert("儲存失敗");
    }
}

function showBrandRules() {
    let rules = [];

    BRANDS.forEach(brand => {
        const input = document.getElementById("rule_" + brand);
        const stores = splitStores(input.value || "");

        if (stores.length > 0) {
            rules.push(brand + " → " + stores.join(", "));
        }
    });

    const message =
        rules.length > 0
            ? "目前同步規則：\\n\\n" + rules.join("\\n")
            : "目前沒有設定任何品牌同步規則";

    alert(message);
}

async function loadWebhookStatus() {
    const response = await fetch("/webhook/status");
    const data = await response.json();

    document.getElementById("webhookStatus").textContent =
        data.enabled ? "目前狀態：✅ 自動同步已開啟" : "目前狀態：⏸️ 自動同步已關閉";
}

async function setWebhook(enabled) {
    const response = await fetch("/webhook/toggle", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            enabled: enabled
        })
    });

    const data = await response.json();

    document.getElementById("webhookStatus").textContent =
        data.enabled ? "目前狀態：✅ 自動同步已開啟" : "目前狀態：⏸️ 自動同步已關閉";
}

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

function renderSyncResult(data) {
    const productCards = document.getElementById("productCards");
    const rawOutput = document.getElementById("rawOutput");

    document.getElementById("successCount").textContent =
        data.summary?.success || 0;

    document.getElementById("skippedCount").textContent =
        data.summary?.skipped || 0;

    document.getElementById("failedCount").textContent =
        data.summary?.failed || 0;

    if (rawOutput) {
        rawOutput.textContent =
            "執行狀態：" + (data.success ? "成功" : "失敗") + "\\n\\n" +
            "Return Code：" + data.returncode + "\\n\\n" +
            "同步輸出：\\n" + data.stdout + "\\n\\n" +
            "錯誤訊息：\\n" + data.stderr;
    }

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
}

async function loadProducts() {
    const container = document.getElementById("productSelector");
    const sortMode = document.getElementById("sortMode").value;

    container.innerHTML = "載入中...";

    try {
        const response = await fetch("/products/list?sort=" + sortMode);
        const data = await response.json();

        allProducts = data.products || [];
        currentPage = 1;

        renderProductList();

    } catch (error) {
        container.innerHTML = "商品載入失敗：" + error;
    }
}

function getFilteredProducts() {
    const searchInput = document.getElementById("productSearch");
    const brandSelect = document.getElementById("brandFilter");

    const keyword = searchInput.value.toLowerCase();
    const brand = brandSelect.value;

    return allProducts.filter(product => {
        const title = (product.title || "").toLowerCase();
        const vendor = (product.vendor || "").toUpperCase();

        const titleMatch = title.includes(keyword);
        const brandMatch = !brand || vendor === brand;

        return titleMatch && brandMatch;
    });
}

function renderProductList() {
    const container = document.getElementById("productSelector");
    const pageInfo = document.getElementById("pageInfo");

    const filteredProducts = getFilteredProducts();

    const totalPages = Math.max(1, Math.ceil(filteredProducts.length / pageSize));

    if (currentPage > totalPages) {
        currentPage = totalPages;
    }

    const startIndex = (currentPage - 1) * pageSize;
    const pageProducts = filteredProducts.slice(startIndex, startIndex + pageSize);

    let html = "";

    pageProducts.forEach(product => {
        const image = product.image || "https://cdn.shopify.com/s/files/1/0533/2089/files/placeholder-images-image_large.png";

        html += `
            <div class="product-select-item">
                <input
                    type="checkbox"
                    value="${product.id}"
                    class="productCheck"
                    onchange="updateSelectedCount()"
                >

                <img src="${image}" alt="${product.title}">

                <div>
                    <a
                        href="${product.admin_url}"
                        target="_blank"
                        class="product-link"
                    >
                        ${product.title}
                    </a>

                    <div class="product-meta">品牌：${product.vendor || "-"}</div>
                    <div class="product-meta">狀態：${product.status || "-"}</div>
                    <div class="product-meta">建立：${formatDate(product.created_at)}</div>
                    <div class="product-meta">更新：${formatDate(product.updated_at)}</div>
                </div>
            </div>
        `;
    });

    if (pageProducts.length === 0) {
        html = "<p>找不到符合條件的商品。</p>";
    }

    container.innerHTML = html;
    pageInfo.textContent = "第 " + currentPage + " / " + totalPages + " 頁，共 " + filteredProducts.length + " 筆";

    updateSelectedCount();
}

function prevPage() {
    if (currentPage > 1) {
        currentPage--;
        renderProductList();
    }
}

function nextPage() {
    const filteredProducts = getFilteredProducts();
    const totalPages = Math.max(1, Math.ceil(filteredProducts.length / pageSize));

    if (currentPage < totalPages) {
        currentPage++;
        renderProductList();
    }
}

function selectAllProducts() {
    document.querySelectorAll(".productCheck").forEach(item => {
        item.checked = true;
    });

    updateSelectedCount();
}

function clearAllProducts() {
    document.querySelectorAll(".productCheck").forEach(item => {
        item.checked = false;
    });

    updateSelectedCount();
}

function updateSelectedCount() {
    const count = document.querySelectorAll(".productCheck:checked").length;

    document.getElementById("selectedCount").textContent =
        "已選 " + count + " 個商品";
}

async function syncSelectedProducts() {
    const productCards = document.getElementById("productCards");

    const checks = document.querySelectorAll(".productCheck:checked");
    const productIds = [...checks].map(x => x.value);

    if (productIds.length === 0) {
        alert("請先勾選商品");
        return;
    }

    productCards.innerHTML = "<p>勾選商品同步中，請稍候...</p>";

    try {
        const response = await fetch("/sync-selected", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                product_ids: productIds
            })
        });

        const data = await response.json();

        renderSyncResult(data);

        alert(
            "同步完成\\n已選商品：" +
            productIds.length +
            "\\n成功：" +
            (data.summary?.success || 0)
        );

    } catch (error) {
        productCards.innerHTML = "<p>同步勾選商品失敗。</p>";
    }
}

loadBrandRules();
loadWebhookStatus();
</script>

</body>
</html>
"""


@app.get("/brand-rules/status")
def brand_rules_status():
    return {
        "rules": get_brand_rules()
    }


@app.post("/brand-rules/save")
async def brand_rules_save(request: Request):
    body = await request.json()
    rules = body.get("rules", {})

    cleaned_rules = {}

    for brand, stores in rules.items():
        cleaned_rules[brand.upper()] = [
            store.strip()
            for store in stores
            if isinstance(store, str) and store.strip()
        ]

    set_brand_rules(cleaned_rules)

    return {
        "success": True,
        "rules": get_brand_rules()
    }


@app.get("/webhook/status")
def webhook_status():
    return {
        "enabled": get_webhook_setting()
    }


@app.post("/webhook/toggle")
async def webhook_toggle(request: Request):
    body = await request.json()
    enabled = body.get("enabled", True)

    set_webhook_setting(bool(enabled))

    return {
        "success": True,
        "enabled": get_webhook_setting()
    }


@app.get("/products/list")
def get_products(sort: str = "updated"):
    if not MASTER_SHOP or not MASTER_TOKEN:
        return JSONResponse(
            {
                "success": False,
                "message": "MASTER_SHOP 或 MASTER_TOKEN 未設定"
            },
            status_code=500
        )

    url = f"https://{MASTER_SHOP}/admin/api/{API_VERSION}/products.json?limit=250"

    response = requests.get(
        url,
        headers={
            "X-Shopify-Access-Token": MASTER_TOKEN,
            "Content-Type": "application/json"
        }
    )

    response.raise_for_status()

    products = response.json().get("products", [])

    if sort == "created":
        products.sort(
            key=lambda product: product.get("created_at", ""),
            reverse=True
        )
    else:
        products.sort(
            key=lambda product: product.get("updated_at", ""),
            reverse=True
        )

    products = products[:100]

    shop_short_name = MASTER_SHOP.replace(".myshopify.com", "")

    result = []

    for product in products:
        result.append({
            "id": product["id"],
            "title": product["title"],
            "vendor": product.get("vendor", ""),
            "status": product.get("status", ""),
            "created_at": product.get("created_at", ""),
            "updated_at": product.get("updated_at", ""),
            "image": (
                product["images"][0]["src"]
                if product.get("images")
                else ""
            ),
            "admin_url": f"https://admin.shopify.com/store/{shop_short_name}/products/{product['id']}"
        })

    return {
        "success": True,
        "sort": sort,
        "count": len(result),
        "products": result
    }


@app.post("/sync-selected")
async def sync_selected(request: Request):
    body = await request.json()

    product_ids = body.get("product_ids", [])

    with open(
        SELECTED_PRODUCTS_FILE,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            product_ids,
            file,
            ensure_ascii=False
        )

    return JSONResponse(
        run_sync_script()
    )


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

    if not get_webhook_setting():
        print("⏸️ Webhook 自動同步已關閉")
        return JSONResponse({
            "success": True,
            "event": "products/create",
            "message": "Webhook received, auto sync disabled"
        })

    if os.path.exists(SELECTED_PRODUCTS_FILE):
        os.remove(SELECTED_PRODUCTS_FILE)

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

    if not get_webhook_setting():
        print("⏸️ Webhook 自動同步已關閉")
        return JSONResponse({
            "success": True,
            "event": "products/update",
            "message": "Webhook received, auto sync disabled"
        })

    if os.path.exists(SELECTED_PRODUCTS_FILE):
        os.remove(SELECTED_PRODUCTS_FILE)

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
        "webhook_auto_sync_enabled": get_webhook_setting(),
        "brand_rules": get_brand_rules(),
        "sync_file": SYNC_FILE
    }
