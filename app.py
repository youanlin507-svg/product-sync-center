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
body { font-family: Arial, sans-serif; padding: 40px; background:#f6f6f7; }
.card { background:white; padding:24px; border-radius:12px; margin-bottom:20px; border:1px solid #ddd; }
input, textarea { width:100%; padding:12px; margin:8px 0 16px; border:1px solid #ccc; border-radius:6px; }
button { background:#008060; color:white; padding:14px 24px; border:none; border-radius:8px; cursor:pointer; font-size:16px; }
pre { background:#f1f1f1; padding:20px; border-radius:8px; white-space:pre-wrap; }
</style>
</head>
<body>

<h1>🛍 Product Sync Center</h1>
<p>Shopify 多商店商品同步管理介面</p>

<div class="card">
<h2>① 主來源商店</h2>
<input id="sourceStore" value="master-demo-lflzyu3e.myshopify.com">
</div>

<div class="card">
<h2>② 目標商店</h2>
<textarea id="targetStores" rows="4">target-demo-1-74h5qyuh.myshopify.com</textarea>
</div>

<div class="card">
<h2>③ 品牌同步規則</h2>
<textarea id="brandRules" rows="6">DESCENTE -> target-demo-1-74h5qyuh.myshopify.com
GFORE -> target-demo-1-74h5qyuh.myshopify.com
2XU -> target-demo-1-74h5qyuh.myshopify.com
CALLAWAY -> target-demo-1-74h5qyuh.myshopify.com</textarea>
</div>

<button onclick="syncProducts()">🚀 開始同步商品</button>

<h2>同步結果</h2>
<pre id="result">尚未執行</pre>

<script>
async function syncProducts() {
  document.getElementById("result").innerText = "同步中，請稍候...";

  try {
    const res = await fetch("/sync", { method: "POST" });
    const data = await res.json();

    document.getElementById("result").innerText =
      "success: " + data.success + "\\n\\n" +
      "stdout:\\n" + data.stdout + "\\n\\n" +
      "stderr:\\n" + data.stderr;
  } catch (err) {
    document.getElementById("result").innerText = "同步失敗：" + err;
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
