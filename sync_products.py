import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

API_VERSION = "2024-04"

MASTER_SHOP = os.getenv("MASTER_SHOP")
MASTER_TOKEN = os.getenv("MASTER_TOKEN")

SYNC_RESULTS = []

# =========================
# 品牌同步商店設定
# =========================

BRAND_STORE_MAP = {
    "DESCENTE": os.getenv("BRAND_DESCENTE_STORES", ""),
    "GFORE": os.getenv("BRAND_GFORE_STORES", ""),
    "2XU": os.getenv("BRAND_2XU_STORES", ""),
    "CALLAWAY": os.getenv("BRAND_CALLAWAY_STORES", ""),
    "ASH": os.getenv("BRAND_ASH_STORES", ""),
}

# =========================
# 尺寸表設定
# =========================

SIZE_CHART_NAMESPACE = "custom"
SIZE_CHART_KEY = "size_chart"

# =========================
# Shopify Headers
# =========================

def shopify_headers(token):
    return {
        "X-Shopify-Access-Token": token,
        "Content-Type": "application/json"
    }

# =========================
# 取得商店 Token
# =========================

def get_target_token(shop):

    env_key = (
        "TARGET_"
        + shop.replace(".myshopify.com", "")
        .replace("-", "_")
        .upper()
        + "_TOKEN"
    )

    return os.getenv(env_key)

# =========================
# 加入同步結果
# =========================

def add_result(
    title,
    vendor,
    target_shop,
    status,
    message,
    image="",
    product_url=""
):

    SYNC_RESULTS.append({
        "title": title,
        "vendor": vendor,
        "target_shop": target_shop,
        "status": status,
        "message": message,
        "image": image,
        "product_url": product_url
    })

# =========================
# 取得主商店商品
# =========================

def get_master_products():

    url = f"https://{MASTER_SHOP}/admin/api/{API_VERSION}/products.json?limit=250"

    response = requests.get(
        url,
        headers=shopify_headers(MASTER_TOKEN)
    )

    response.raise_for_status()

    return response.json().get("products", [])

# =========================
# 尋找商品
# =========================

def find_product_by_title(shop, token, title):

    url = (
        f"https://{shop}/admin/api/{API_VERSION}/products.json"
        f"?title={title}"
    )

    response = requests.get(
        url,
        headers=shopify_headers(token)
    )

    response.raise_for_status()

    products = response.json().get("products", [])

    return products[0] if products else None

# =========================
# 建立商品圖片
# =========================

def build_images(product):

    images = []

    for image in product.get("images", []):

        src = image.get("src")

        if src:
            images.append({
                "src": src,
                "alt": image.get("alt", "")
            })

    return images

# =========================
# 商品變體同步
# =========================

def build_variants(product):

    variants = []

    for variant in product.get("variants", []):

        new_variant = {
            "option1": variant.get("option1"),
            "option2": variant.get("option2"),
            "option3": variant.get("option3"),

            "price": variant.get("price"),
            "compare_at_price": variant.get("compare_at_price"),

            "sku": variant.get("sku"),
            "barcode": variant.get("barcode"),

            "inventory_management": variant.get("inventory_management"),
            "inventory_policy": variant.get("inventory_policy"),

            "weight": variant.get("weight"),
            "weight_unit": variant.get("weight_unit"),

            "taxable": variant.get("taxable"),
            "requires_shipping": variant.get("requires_shipping")
        }

        cleaned = {
            k: v for k, v in new_variant.items()
            if v not in [None, ""]
        }

        variants.append(cleaned)

    return variants

# =========================
# 商品 Options
# =========================

def build_options(product):

    options = []

    for option in product.get("options", []):

        name = option.get("name")

        if name:
            options.append({
                "name": name
            })

    return options

# =========================
# Tags 處理
# =========================

def build_tags(product, vendor):

    tags = []

    raw_tags = product.get("tags", "")

    if raw_tags:

        for tag in raw_tags.split(","):

            tag = tag.strip()

            if tag:
                tags.append(tag)

    tags.append("synced-from-ash")

    if vendor:
        tags.append(f"brand-{vendor.lower()}")

    unique_tags = []

    for tag in tags:
        if tag not in unique_tags:
            unique_tags.append(tag)

    return ", ".join(unique_tags)

# =========================
# 商品系列同步
# =========================

def build_collections(product):

    collections = []

    product_type = product.get("product_type")

    if product_type:
        collections.append(product_type)

    return collections

# =========================
# 尺寸表同步
# =========================

def get_size_chart_metafield(product_id):

    url = (
        f"https://{MASTER_SHOP}/admin/api/{API_VERSION}"
        f"/products/{product_id}/metafields.json"
    )

    response = requests.get(
        url,
        headers=shopify_headers(MASTER_TOKEN)
    )

    response.raise_for_status()

    metafields = response.json().get("metafields", [])

    for metafield in metafields:

        if (
            metafield.get("namespace") == SIZE_CHART_NAMESPACE
            and metafield.get("key") == SIZE_CHART_KEY
        ):
            return metafield

    return None

# =========================
# 新增尺寸表
# =========================

def create_size_chart_metafield(
    shop,
    token,
    product_id,
    metafield
):

    url = (
        f"https://{shop}/admin/api/{API_VERSION}"
        f"/products/{product_id}/metafields.json"
    )

    payload = {
        "metafield": {
            "namespace": metafield.get("namespace"),
            "key": metafield.get("key"),
            "value": metafield.get("value"),
            "type": metafield.get(
                "type",
                "multi_line_text_field"
            )
        }
    }

    response = requests.post(
        url,
        headers=shopify_headers(token),
        json=payload
    )

    response.raise_for_status()

# =========================
# 建立商品資料
# =========================

def build_product_data(product):

    vendor = product.get("vendor", "")

    first_image = ""

    if product.get("images"):
        first_image = product["images"][0].get("src", "")

    return {
        "title": product.get("title"),
        "body_html": product.get("body_html"),
        "vendor": vendor,
        "product_type": product.get("product_type"),
        "tags": build_tags(product, vendor),
        "images": build_images(product),
        "variants": build_variants(product),
        "options": build_options(product),
        "status": "active",
        "image": first_image
    }

# =========================
# 建立商品
# =========================

def create_product(shop, token, product_data):

    url = f"https://{shop}/admin/api/{API_VERSION}/products.json"

    payload = {
        "product": {
            "title": product_data["title"],
            "body_html": product_data["body_html"],
            "vendor": product_data["vendor"],
            "product_type": product_data["product_type"],
            "tags": product_data["tags"],
            "status": product_data["status"],
            "images": product_data["images"],
            "variants": product_data["variants"],
            "options": product_data["options"]
        }
    }

    response = requests.post(
        url,
        headers=shopify_headers(token),
        json=payload
    )

    response.raise_for_status()

    return response.json()["product"]

# =========================
# 主同步流程
# =========================

def sync_products():

    print("📦 開始讀取主來源商店商品...")

    products = get_master_products()

    print(f"找到 {len(products)} 個商品")

    for product in products:

        title = product.get("title")
        vendor = product.get("vendor", "").upper()

        print("\\n====================================================")
        print(f"商品名稱：{title}")
        print(f"品牌 Vendor：{vendor}")

        target_shops_raw = BRAND_STORE_MAP.get(vendor, "")

        if not target_shops_raw:

            print("❌ 找不到品牌對應商店")

            add_result(
                title,
                vendor,
                "-",
                "failed",
                "找不到品牌對應商店"
            )

            continue

        target_shops = [
            s.strip()
            for s in target_shops_raw.split(",")
            if s.strip()
        ]

        for target_shop in target_shops:

            target_token = get_target_token(target_shop)

            if not target_token:

                print(f"❌ 找不到 Token：{target_shop}")

                add_result(
                    title,
                    vendor,
                    target_shop,
                    "failed",
                    "找不到商店 Token"
                )

                continue

            existing_product = find_product_by_title(
                target_shop,
                target_token,
                title
            )

            first_image = ""

            if product.get("images"):
                first_image = product["images"][0].get("src", "")

            if existing_product:

                print(f"⏭️ 已存在，略過：{target_shop}")

                product_url = (
                    f"https://admin.shopify.com/store/"
                    f"{target_shop.replace('.myshopify.com', '')}"
                    f"/products/{existing_product['id']}"
                )

                add_result(
                    title,
                    vendor,
                    target_shop,
                    "skipped",
                    "商品已存在",
                    first_image,
                    product_url
                )

                continue

            try:

                product_data = build_product_data(product)

                created_product = create_product(
                    target_shop,
                    target_token,
                    product_data
                )

                source_size_chart = get_size_chart_metafield(
                    product["id"]
                )

                if source_size_chart:

                    create_size_chart_metafield(
                        target_shop,
                        target_token,
                        created_product["id"],
                        source_size_chart
                    )

                product_url = (
                    f"https://admin.shopify.com/store/"
                    f"{target_shop.replace('.myshopify.com', '')}"
                    f"/products/{created_product['id']}"
                )

                print(f"✅ 已同步到：{target_shop}")

                add_result(
                    title,
                    vendor,
                    target_shop,
                    "success",
                    "同步成功",
                    first_image,
                    product_url
                )

            except Exception as error:

                print(f"❌ 同步失敗：{str(error)}")

                add_result(
                    title,
                    vendor,
                    target_shop,
                    "failed",
                    str(error),
                    first_image
                )

    print("\\n🎉 商品同步完成")

# =========================
# 輸出同步結果 JSON
# =========================

def print_result_json():

    summary = {
        "success": len([
            r for r in SYNC_RESULTS
            if r["status"] == "success"
        ]),
        "skipped": len([
            r for r in SYNC_RESULTS
            if r["status"] == "skipped"
        ]),
        "failed": len([
            r for r in SYNC_RESULTS
            if r["status"] == "failed"
        ])
    }

    result = {
        "summary": summary,
        "results": SYNC_RESULTS
    }

    print("\\nSYNC_RESULT_JSON_START")
    print(json.dumps(result, ensure_ascii=False))
    print("SYNC_RESULT_JSON_END")

# =========================
# 執行
# =========================

if __name__ == "__main__":

    sync_products()

    print_result_json()
