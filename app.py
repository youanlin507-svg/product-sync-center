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
table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 20px;
}
th, td {
    border-bottom: 1px solid #ddd;
    padding: 12px;
    text-align: left;
}
.success { color: green; font-weight: bold; }
.skipped { color: orange; font-weight: bold; }
.failed { color: red; font-weight: bold; }
pre {
    background: #111827;
    color: #10b981;
    padding: 20px;
    border-radius: 8px;
    white-space: pre-wrap;
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
    <h2>同步摘要</h2>
    <p>成功：<span id="successCount">0</span></p>
    <p>略過：<span id="skippedCount">0</span></p>
    <p>失敗：<span id="failedCount">0</span></p>
</div>

<div class="card">
    <h2>同步結果</h2>
    <table>
        <thead>
            <tr>
                <th>商品名稱</th>
                <th>品牌</th>
                <th>目標商店</th>
                <th>狀態</th>
                <th>訊息</th>
            </tr>
        </thead>
        <tbody id="resultTable">
            <tr>
                <td colspan="5">尚未執行同步</td>
            </tr>
        </tbody>
    </table>
</div>

<div class="card">
    <h2>原始輸出</h2>
    <pre id="rawOutput">尚未執行</pre>
</div>

<script>
async function runSync() {
    document.getElementById("rawOutput").textContent = "同步中，請稍候...";
    document.getElementById("resultTable").innerHTML =
        '<tr><td colspan="5">同步中...</td></tr>';

    const response = await fetch("/sync", { method: "POST" });
    const data = await response.json();

    document.getElementById("rawOutput").textContent =
        data.stdout || JSON.stringify(data, null, 2);

    document.getElementById("successCount").textContent = data.summary.success;
    document.getElementById("skippedCount").textContent = data.summary.skipped;
    document.getElementById("failedCount").textContent = data.summary.failed;

    const tbody = document.getElementById("resultTable");
    tbody.innerHTML = "";

    if (!data.results || data.results.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5">沒有同步資料</td></tr>';
        return;
    }

    data.results.forEach(item => {
        let statusClass = "";
        if (item.status === "success") statusClass = "success";
        if (item.status === "skipped") statusClass = "skipped";
        if (item.status === "failed") statusClass = "failed";

        tbody.innerHTML += `
            <tr>
                <td>${item.title}</td>
                <td>${item.vendor}</td>
                <td>${item.target_shop}</td>
                <td class="${statusClass}">${item.status}</td>
                <td>${item.message}</td>
            </tr>
        `;
    });
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

    try:
        json_start = result.stdout.rfind("SYNC_RESULT_JSON_START")
        json_end = result.stdout.rfind("SYNC_RESULT_JSON_END")

        if json_start != -1 and json_end != -1:
            json_text = result.stdout[
                json_start + len("SYNC_RESULT_JSON_START"):json_end
            ].strip()
            sync_data = json.loads(json_text)
        else:
            sync_data = {
                "summary": {"success": 0, "skipped": 0, "failed": 0},
                "results": []
            }

    except Exception:
        sync_data = {
            "summary": {"success": 0, "skipped": 0, "failed": 1},
            "results": []
        }

    return JSONResponse({
        "success": result.returncode == 0,
        "summary": sync_data["summary"],
        "results": sync_data["results"],
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode
    })
