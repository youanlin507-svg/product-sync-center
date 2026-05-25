from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

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
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Product Sync Center</title>

<style>
body {
    font-family: Arial, sans-serif;
    background: #f6f6f7;
    padding: 30px;
    margin: 0;
}

.container {
    max-width: 1000px;
    margin: 0 auto;
}

h1 {
    font-size: 36px;
    margin-bottom: 10px;
}

.subtitle {
    color: #666;
    margin-bottom: 30px;
}

.card {
    background: white;
    border-radius: 16px;
    padding: 30px;
    margin-bottom: 24px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}

h2 {
    margin-top: 0;
    font-size: 28px;
}

input, textarea, select {
    width: 100%;
    padding: 14px;
    font-size: 18px;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    box-sizing: border-box;
}

textarea {
    font-family: Consolas, monospace;
}

.checkbox-group {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 14px;
    margin-top: 10px;
}

.checkbox-item {
    display: flex;
    align-items: center;
    background: #f9fafb;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    padding: 12px 16px;
    gap: 10px;
}

.checkbox-item input[type="checkbox"] {
    width: auto;
    transform: scale(1.3);
}

.checkbox-item label {
    font-size: 18px;
    cursor: pointer;
}

button {
    background: #008060;
    color: white;
    border: none;
    padding: 16px 32px;
    font-size: 20px;
    border-radius: 10px;
    cursor: pointer;
    font-weight: bold;
}

button:hover {
    background: #006e52;
}

#result {
    background: #111827;
    color: #10b981;
    padding: 20px;
    border-radius: 10px;
    font-family: Consolas, monospace;
    white-space: pre-wrap;
    min-height: 120px;
    font-size: 16px;
}

.note {
    color: #6b7280;
    font-size: 15px;
    margin-top: 8px;
}
</style>
</head>
<body>
<div class="container">

    <h1>📦 Product Sync Center</h1>
    <div class="subtitle">Shopify 多商店商品同步管理系統</div>

    <!-- 主來源商店 -->
    <div class="card">
        <h2>① 主來源商店</h2>
        <select id="sourceStore">
            <option value="ash-golf-taiwan.myshopify.com" selected>ASH</option>
            <option value="descente-tw.myshopify.com">DESCENTE</option>
            <option value="gfore-tw.myshopify.com">GFORE</option>
            <option value="2xu-tw.myshopify.com">2XU</option>
            <option value="callaway-tw.myshopify.com">CALLAWAY</option>
        </select>
        <div class="note">正式上線後，預設主來源商店為 ASH。</div>
    </div>

    <!-- 目標商店 -->
    <div class="card">
        <h2>② 目標商店（可多選）</h2>

        <div class="checkbox-group">
            <div class="checkbox-item">
                <input type="checkbox" id="store_descente"
                       value="descente-tw.myshopify.com"
                       data-brand="DESCENTE">
                <label for="store_descente">DESCENTE</label>
            </div>

            <div class="checkbox-item">
                <input type="checkbox" id="store_gfore"
                       value="gfore-tw.myshopify.com"
                       data-brand="GFORE">
                <label for="store_gfore">GFORE</label>
            </div>

            <div class="checkbox-item">
                <input type="checkbox" id="store_2xu"
                       value="2xu-tw.myshopify.com"
                       data-brand="2XU">
                <label for="store_2xu">2XU</label>
            </div>

            <div class="checkbox-item">
                <input type="checkbox" id="store_callaway"
                       value="callaway-tw.myshopify.com"
                       data-brand="CALLAWAY">
                <label for="store_callaway">CALLAWAY</label>
            </div>
        </div>
    </div>

    <!-- 品牌規則 -->
    <div class="card">
        <h2>③ 品牌同步規則（自動產生）</h2>
        <textarea id="brandRules" rows="8" readonly></textarea>
    </div>

    <!-- 同步 -->
    <div class="card">
        <button onclick="syncProducts()">🚀 開始同步商品</button>
    </div>

    <!-- 結果 -->
    <div class="card">
        <h2>同步結果</h2>
        <div id="result">等待執行...</div>
    </div>

</div>

<script>
function generateRules() {
    const checked = document.querySelectorAll(
        '.checkbox-group input[type="checkbox"]:checked'
    );

    let rules = [];

    checked.forEach(item => {
        const brand = item.dataset.brand;
        const store = item.value;
        rules.push(`${brand} -> ${store}`);
    });

    document.getElementById('brandRules').value =
        rules.length > 0 ? rules.join('\\n') : '';
}

document.querySelectorAll(
    '.checkbox-group input[type="checkbox"]'
).forEach(item => {
    item.addEventListener('change', generateRules);
});

function syncProducts() {
    const sourceStore =
        document.getElementById('sourceStore').value;

    const checked = document.querySelectorAll(
        '.checkbox-group input[type="checkbox"]:checked'
    );

    const targetStores = [];
    checked.forEach(item => {
        targetStores.push(item.value);
    });

    const brandRules =
        document.getElementById('brandRules').value;

    if (targetStores.length === 0) {
        alert('請至少選擇一個目標商店');
        return;
    }

    const result = document.getElementById('result');

    result.textContent =
`=== 商品同步設定 ===

主來源商店:
${sourceStore}

目標商店:
${targetStores.join('\\n')}

品牌規則:
${brandRules}

同步狀態:
模擬同步完成（正式版可接 Shopify API）
`;

    console.log({
        sourceStore,
        targetStores,
        brandRules
    });
}

// 初始化規則
generateRules();
</script>

</body>
</html>
"""


@app.get("/health")
def health():
    return {
        "app": "Product Sync Center",
        "status": "running",
        "message": "Shopify 商品同步系統已啟動"
    }
