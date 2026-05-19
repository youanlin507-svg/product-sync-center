import sys
sys.stdout.reconfigure(encoding="utf-8")

import os
import requests
from dotenv import load_dotenv
from urllib.parse import quote

load_dotenv()

API_VERSION = "2026-04"

MASTER_SHOP = os.getenv("MASTER_SHOP")
MASTER_TOKEN = os.getenv("MASTER_TOKEN")


def headers(token):
    return {
        "X-Shopify-Access-Token": token,
        "Content-Type": "application/json"
    }


def token_key_for_store(store):
    key = store.replace(".myshopify.com", "")
    key = key.replace("-", "_").upper()
    return f"TARGET_{key}_TOKEN"


def get_brand_target_stores(brand):
    brand_key = brand.replace(" ", "_").replace("-", "_").upper()
    env_key = f"BRAND_{brand_key}_STORES"

    stores = os.getenv(env_key, "")

    return [
        store.strip()
        for store in stores.split(",")
        if store.strip()
    ]


def get_products():
    print("📥 正在讀取主商店商品...")

    url = f"https://{MASTER_SHOP}/admin/api/{API_VERSION}/products.json?limit=250"
    response = requests.get(url, headers=headers(MASTER_TOKEN))
    response.raise_for_status()

    products = response.json().get("products", [])
    print(f"找到 {len(products)} 個商品")
    return products


def product_exists(target_shop, target_token, title):
    encoded_title = quote(title)

    url = (
        f"https://{target_shop}/admin/api/{API_VERSION}/products.json"
        f"?title={encoded_title}&limit=1"
    )

    response = requests.get(url, headers=headers(target_token))
    response.raise_for_status()

    products = response.json().get("products", [])
    return len(products) > 0


def extract_images(product):
    images = []

    for img in product.get("images", []):
        src = img.get("src")
        if src:
            images.append({"src": src})

    return images


def create_product(target_shop, target_token, product):
    if not product.get("variants"):
        print(f"⚠️ 無 variant，跳過：{product['title']}")
        return

    first_variant = product["variants"][0]
    images = extract_images(product)

    payload = {
        "product": {
            "title": product["title"],
            "body_html": product.get("body_html", ""),
            "vendor": product.get("vendor", ""),
            "product_type": product.get("product_type", ""),
            "tags": product.get("tags", ""),
            "status": "active",
            "variants": [
                {
                    "title": first_variant.get("title", "Default Title"),
                    "price": first_variant.get("price", "0.00"),
                    "sku": first_variant.get("sku", ""),
                    "barcode": first_variant.get("barcode", ""),
                    "fulfillment_service": "manual",
                    "inventory_policy": "deny",
                    "requires_shipping": first_variant.get("requires_shipping", True),
                    "taxable": first_variant.get("taxable", True),
                }
            ],
            "images": images
        }
    }

    url = f"https://{target_shop}/admin/api/{API_VERSION}/products.json"
    response = requests.post(url, headers=headers(target_token), json=payload)

    if response.status_code in [200, 201]:
        print(f"✅ [{target_shop}] 已同步：{product['title']}")
        if images:
            print(f"🖼️ [{target_shop}] 已同步圖片 {len(images)} 張")
    else:
        print(f"❌ [{target_shop}] 同步失敗：{product['title']}")
        print(response.text)


def sync_product_to_store(product, target_shop):
    token_key = token_key_for_store(target_shop)
    target_token = os.getenv(token_key)

    if not target_token:
        print(f"❌ 找不到 {target_shop} 的 Token")
        print(f"請在 .env 加上：{token_key}=你的Token")
        return

    title = product["title"]

    if product_exists(target_shop, target_token, title):
        print(f"⏭️ [{target_shop}] 已存在，跳過：{title}")
        return

    create_product(target_shop, target_token, product)


def main():
    products = get_products()

    for product in products:
        title = product["title"]
        brand = product.get("vendor", "").strip()

        if not brand:
            print(f"⚠️ 無品牌 vendor，跳過：{title}")
            continue

        target_stores = get_brand_target_stores(brand)

        if not target_stores:
            print(f"⚠️ 品牌沒有設定目標店，跳過：{title} / vendor={brand}")
            continue

        print(f"\n🏷 品牌：{brand}")
        print(f"📦 商品：{title}")

        for target_shop in target_stores:
            sync_product_to_store(product, target_shop)

    print("\n🎉 品牌分組同步完成！")


if __name__ == "__main__":
    main()