# sync_products.py
# ==========================================================
# 功能：
# 1. 從主來源商店讀取所有商品
# 2. 依商品 Vendor 判斷品牌
# 3. 根據 .env 中 BRAND_XXX_STORES 決定同步到哪些商店
# 4. 讀取目標商店的範本商品 body_html
# 5. 套用範本格式
# 6. 同步商品圖片、描述、價格、SKU、Barcode、規格
# 7. 避免重複建立商品
# ==========================================================

import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_VERSION = "2024-04"

MASTER_SHOP = os.getenv("MASTER_SHOP")
MASTER_TOKEN = os.getenv("MASTER_TOKEN")


# ==========================================================
# 品牌 → 範本商品 Handle
# ==========================================================
BRAND_TEMPLATE_MAP = {
    "DESCENTE": os.getenv("DESCENTE_TEMPLATE_HANDLE"),
    "G/FORE": os.getenv("GFORE_TEMPLATE_HANDLE"),
    "GFORE": os.getenv("GFORE_TEMPLATE_HANDLE"),
    "2XU": os.getenv("2XU_TEMPLATE_HANDLE"),
    "ASH": os.getenv("ASH_TEMPLATE_HANDLE"),
    "ASH GOLF": os.getenv("ASH_TEMPLATE_HANDLE"),
    "CALLAWAY": os.getenv("CALLAWAY_TEMPLATE_HANDLE"),
}


# ==========================================================
# 共用 Header
# ==========================================================
def get_headers(token):
    return {
        "X-Shopify-Access-Token": token,
        "Content-Type": "application/json",
    }


# ==========================================================
# 根據商店網址取得 Token
# 例如：
# target-demo-1-74h5qyuh.myshopify.com
# →
# TARGET_TARGET_DEMO_1_74H5QYUH_TOKEN
# ==========================================================
def get_shop_token(shop):
    env_key = (
        "TARGET_"
        + shop.replace(".myshopify.com", "")
        .replace("-", "_")
        .upper()
        + "_TOKEN"
    )
    return os.getenv(env_key)


# ==========================================================
# 讀取商店商品
# ==========================================================
def get_products(shop, token):
    url = f"https://{shop}/admin/api/{API_VERSION}/products.json?limit=250"
    response = requests.get(url, headers=get_headers(token))
    response.raise_for_status()
    return response.json().get("products", [])


# ==========================================================
# 用 Handle 取得指定商品（作為範本）
# ==========================================================
def get_product_by_handle(shop, token, handle):
    if not handle:
        return None

    url = f"https://{shop}/admin/api/{API_VERSION}/products.json?handle={handle}"
    response = requests.get(url, headers=get_headers(token))
    response.raise_for_status()

    products = response.json().get("products", [])
    if products:
        return products[0]
    return None


# ==========================================================
# 根據 Vendor 取得要同步到哪些商店
# Vendor = DESCENTE
# → 讀取 BRAND_DESCENTE_STORES
# ==========================================================
def get_target_shops(vendor):
    if not vendor:
        return []

    normalized = (
        vendor.upper()
        .replace("/", "")
        .replace(" ", "_")
    )

    env_key = f"BRAND_{normalized}_STORES"
    value = os.getenv(env_key, "")

    if not value:
        return []

    return [
        shop.strip()
        for shop in value.split(",")
        if shop.strip()
    ]


# ==========================================================
# 將商品圖片轉成 HTML
# ==========================================================
def build_images_html(product):
    html = ""

    for image in product.get("images", []):
        src = image.get("src")
        if src:
            html += f"""
<p>
  <img src="{src}" style="max-width:100%; height:auto;" />
</p>
"""

    return html


# ==========================================================
# 套用範本商品格式
# ==========================================================
def format_description_with_template(
    source_product,
    template_product
):
    title = source_product.get("title", "")
    body_html = source_product.get("body_html", "") or ""
    vendor = source_product.get("vendor", "") or ""
    product_type = source_product.get("product_type", "") or ""

    images_html = build_images_html(source_product)

    # 沒有範本商品時，使用基本格式
    if not template_product:
        return f"""
<h3>{title}</h3>

<div>
{body_html}
</div>

{images_html}
"""

    # 取得範本商品 HTML（僅作為格式參考）
    template_html = template_product.get("body_html", "") or ""

    # 實際輸出的 HTML
    formatted_html = f"""
<h3>{title}</h3>

<div>
{body_html}
</div>

<h3>商品資訊</h3>
<p>品牌：{vendor}</p>
<p>類型：{product_type}</p>

{images_html}

<!-- 以下保留範本商品 HTML 作為格式參考 -->
<div style="display:none;">
{template_html}
</div>
"""

    return formatted_html


# ==========================================================
# 將來源商品整理成可建立的新商品資料
# ==========================================================
def build_product_data(
    source_product,
    target_shop,
    target_token
):
    vendor = (source_product.get("vendor") or "").strip()

    # 找對應的範本商品 Handle
    template_handle = (
        BRAND_TEMPLATE_MAP.get(vendor.upper())
        or BRAND_TEMPLATE_MAP.get(vendor)
    )

    # 讀取目標商店中的範本商品
    template_product = get_product_by_handle(
        target_shop,
        target_token,
        template_handle
    )

    new_product = {
        "title": source_product.get("title"),
        "body_html": format_description_with_template(
            source_product,
            template_product
        ),
        "vendor": source_product.get("vendor"),
        "product_type": source_product.get("product_type"),
        "tags": source_product.get("tags"),
        "status": "active",
        "images": [],
        "variants": [],
    }

    # ======================================================
    # 同步圖片
    # ======================================================
    for image in source_product.get("images", []):
        src = image.get("src")
        if src:
            new_product["images"].append({
                "src": src
            })

    # ======================================================
    # 同步規格
    # ======================================================
    for variant in source_product.get("variants", []):
        new_variant = {
            "option1": variant.get("option1"),
            "option2": variant.get("option2"),
            "option3": variant.get("option3"),
            "price": variant.get("price"),
            "compare_at_price": variant.get("compare_at_price"),
            "sku": variant.get("sku"),
            "barcode": variant.get("barcode"),
            "weight": variant.get("weight"),
            "weight_unit": variant.get("weight_unit"),
            "inventory_management": variant.get("inventory_management"),
            "inventory_policy": variant.get("inventory_policy"),
            "taxable": variant.get("taxable"),
            "requires_shipping": variant.get("requires_shipping"),
        }

        # 移除 None 值
        cleaned_variant = {
            k: v
            for k, v in new_variant.items()
            if v is not None
        }

        new_product["variants"].append(cleaned_variant)

    # ======================================================
    # 同步選項（尺寸 / 顏色）
    # ======================================================
    if source_product.get("options"):
        new_product["options"] = [
            {
                "name": option.get("name")
            }
            for option in source_product.get("options", [])
        ]

    return new_product


# ==========================================================
# 檢查商品是否已存在（用 Title 判斷）
# ==========================================================
def product_exists(shop, token, title):
    url = f"https://{shop}/admin/api/{API_VERSION}/products.json?title={title}"
    response = requests.get(url, headers=get_headers(token))
    response.raise_for_status()

    products = response.json().get("products", [])
    return len(products) > 0


# ==========================================================
# 建立商品
# ==========================================================
def create_product(shop, token, product_data):
    url = f"https://{shop}/admin/api/{API_VERSION}/products.json"

    response = requests.post(
        url,
        headers=get_headers(token),
        json={"product": product_data}
    )

    if not response.ok:
        print(f"❌ 建立商品失敗：{shop}")
        print(response.text)

    response.raise_for_status()
    return response.json()


# ==========================================================
# 主程式
# ==========================================================
def main():
    if not MASTER_SHOP or not MASTER_TOKEN:
        print("❌ 請先設定 MASTER_SHOP 與 MASTER_TOKEN")
        return

    print("📦 開始讀取主來源商店商品...")
    print(f"主來源商店：{MASTER_SHOP}")

    products = get_products(MASTER_SHOP, MASTER_TOKEN)

    print(f"找到 {len(products)} 個商品")

    for product in products:
        title = product.get("title")
        vendor = (product.get("vendor") or "").strip()

        print("\n" + "=" * 60)
        print(f"商品名稱：{title}")
        print(f"品牌 Vendor：{vendor}")

        # 根據 Vendor 找目標商店
        target_shops = get_target_shops(vendor)

        if not target_shops:
            print("⚠️ 找不到此品牌對應的目標商店，略過")
            continue

        print("目標商店：")
        for shop in target_shops:
            print(f" - {shop}")

        # 同步到每個目標商店
        for target_shop in target_shops:
            target_token = get_shop_token(target_shop)

            if not target_token:
                print(f"⚠️ 找不到 {target_shop} 的 Token，略過")
                continue

            # 檢查是否已存在
            if product_exists(
                target_shop,
                target_token,
                title
            ):
                print(f"⏭️ 已存在，略過：{target_shop}")
                continue

            try:
                # 建立商品資料
                product_data = build_product_data(
                    product,
                    target_shop,
                    target_token
                )

                # 建立商品
                create_product(
                    target_shop,
                    target_token,
                    product_data
                )

                print(f"✅ 已同步到：{target_shop}")

            except Exception as e:
                print(f"❌ 同步失敗：{target_shop}")
                print(str(e))

    print("\n🎉 商品同步完成")


# ==========================================================
# 程式進入點
# ==========================================================
if __name__ == "__main__":
    main()
