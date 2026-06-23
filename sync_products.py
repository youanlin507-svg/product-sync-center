import os
import json
import requests
from dotenv import load_dotenv
from urllib.parse import quote

load_dotenv()

API_VERSION = "2024-04"

MASTER_SHOP = os.getenv("MASTER_SHOP")
MASTER_TOKEN = os.getenv("MASTER_TOKEN")

SYNC_RESULTS = []

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BRAND_RULES_FILE = os.path.join(BASE_DIR, "brand_rules.json")
SELECTED_PRODUCTS_FILE = os.path.join(BASE_DIR, "selected_products.json")

BRAND_STORE_MAP = {
    "DESCENTE": os.getenv("BRAND_DESCENTE_STORES", ""),
    "GFORE": os.getenv("BRAND_GFORE_STORES", ""),
    "G/FORE": os.getenv("BRAND_GFORE_STORES", ""),
    "2XU": os.getenv("BRAND_2XU_STORES", ""),
    "CALLAWAY": os.getenv("BRAND_CALLAWAY_STORES", ""),
    "ASH": os.getenv("BRAND_ASH_STORES", ""),
}


def get_brand_store_map():
    if os.path.exists(BRAND_RULES_FILE):
        try:
            with open(BRAND_RULES_FILE, "r", encoding="utf-8") as file:
                rules = json.load(file)

            brand_map = {}

            for brand, stores in rules.items():
                if isinstance(stores, list):
                    brand_map[brand.upper()] = ",".join(stores)

            if brand_map:
                print("✅ 使用 brand_rules.json 品牌同步規則")
                return brand_map

        except Exception as error:
            print("⚠️ 讀取 brand_rules.json 失敗，改用環境變數")
            print(str(error))

    print("ℹ️ 使用 Render Environment 品牌同步規則")
    return BRAND_STORE_MAP


def get_selected_product_ids():
    if not os.path.exists(SELECTED_PRODUCTS_FILE):
        return []

    try:
        with open(SELECTED_PRODUCTS_FILE, "r", encoding="utf-8") as file:
            product_ids = json.load(file)

        return [str(product_id) for product_id in product_ids]

    except Exception as error:
        print("⚠️ 讀取 selected_products.json 失敗")
        print(str(error))
        return []


def shopify_headers(token):
    return {
        "X-Shopify-Access-Token": token,
        "Content-Type": "application/json"
    }


def get_target_token(shop):
    env_key = (
        "TARGET_"
        + shop.replace(".myshopify.com", "")
        .replace("-", "_")
        .upper()
        + "_TOKEN"
    )

    return os.getenv(env_key)


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


def get_master_products():
    url = f"https://{MASTER_SHOP}/admin/api/{API_VERSION}/products.json?limit=250"

    response = requests.get(
        url,
        headers=shopify_headers(MASTER_TOKEN)
    )

    response.raise_for_status()

    return response.json().get("products", [])


def find_product_by_title(shop, token, title):
    encoded_title = quote(title)

    url = (
        f"https://{shop}/admin/api/{API_VERSION}/products.json"
        f"?title={encoded_title}&limit=1"
    )

    response = requests.get(
        url,
        headers=shopify_headers(token)
    )

    response.raise_for_status()

    products = response.json().get("products", [])

    return products[0] if products else None


def build_images(product):
    images = []

    for image in product.get("images", []):
        src = image.get("src")

        if src:
            image_data = {
                "src": src
            }

            if image.get("alt"):
                image_data["alt"] = image.get("alt")

            images.append(image_data)

    return images


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
            key: value
            for key, value in new_variant.items()
            if value not in [None, ""]
        }

        variants.append(cleaned)

    return variants


def build_options(product):
    options = []

    for option in product.get("options", []):
        name = option.get("name")

        if name:
            options.append({
                "name": name
            })

    return options


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
        vendor_tag = (
            "brand-"
            + vendor.lower()
            .replace("/", "")
            .replace(" ", "-")
            .replace("_", "-")
        )

        tags.append(vendor_tag)

    unique_tags = []

    for tag in tags:
        if tag not in unique_tags:
            unique_tags.append(tag)

    return ", ".join(unique_tags)


def build_product_data(product):
    vendor = product.get("vendor", "")

    return {
        "title": product.get("title"),
        "body_html": product.get("body_html"),
        "vendor": vendor,
        "product_type": product.get("product_type"),
        "tags": build_tags(product, vendor),
        "images": build_images(product),
        "variants": build_variants(product),
        "options": build_options(product),
        "status": product.get("status", "draft")
    }


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


def update_product_basic(shop, token, product_id, product_data):
    url = f"https://{shop}/admin/api/{API_VERSION}/products/{product_id}.json"

    payload = {
        "product": {
            "id": product_id,
            "title": product_data["title"],
            "body_html": product_data["body_html"],
            "vendor": product_data["vendor"],
            "product_type": product_data["product_type"],
            "tags": product_data["tags"],
            "status": product_data["status"]
        }
    }

    response = requests.put(
        url,
        headers=shopify_headers(token),
        json=payload
    )

    response.raise_for_status()

    return response.json()["product"]


def delete_product_images(shop, token, product_id, existing_images):
    for image in existing_images:
        image_id = image.get("id")

        if not image_id:
            continue

        url = (
            f"https://{shop}/admin/api/{API_VERSION}/products/"
            f"{product_id}/images/{image_id}.json"
        )

        response = requests.delete(
            url,
            headers=shopify_headers(token)
        )

        if response.status_code not in [200, 204]:
            print(f"⚠️ 刪除圖片失敗：{image_id}")
            print(response.text)


def add_product_images(shop, token, product_id, images):
    for image in images:
        url = (
            f"https://{shop}/admin/api/{API_VERSION}/products/"
            f"{product_id}/images.json"
        )

        response = requests.post(
            url,
            headers=shopify_headers(token),
            json={
                "image": image
            }
        )

        if not response.ok:
            print("⚠️ 新增圖片失敗")
            print(response.text)

        response.raise_for_status()


def replace_product_images(shop, token, product_id, source_images, existing_images):
    delete_product_images(
        shop,
        token,
        product_id,
        existing_images
    )

    add_product_images(
        shop,
        token,
        product_id,
        source_images
    )


def get_product_variants(shop, token, product_id):
    url = (
        f"https://{shop}/admin/api/{API_VERSION}/products/"
        f"{product_id}/variants.json?limit=250"
    )

    response = requests.get(
        url,
        headers=shopify_headers(token)
    )

    response.raise_for_status()

    return response.json().get("variants", [])


def update_variant(shop, token, variant_id, variant_data):
    url = f"https://{shop}/admin/api/{API_VERSION}/variants/{variant_id}.json"

    payload = {
        "variant": {
            "id": variant_id,
            **variant_data
        }
    }

    response = requests.put(
        url,
        headers=shopify_headers(token),
        json=payload
    )

    if not response.ok:
        print(f"⚠️ 更新 Variant 失敗：{variant_id}")
        print(response.text)

    response.raise_for_status()


def create_variant(shop, token, product_id, variant_data):
    url = (
        f"https://{shop}/admin/api/{API_VERSION}/products/"
        f"{product_id}/variants.json"
    )

    response = requests.post(
        url,
        headers=shopify_headers(token),
        json={
            "variant": variant_data
        }
    )

    if not response.ok:
        print("⚠️ 新增 Variant 失敗")
        print(response.text)

    response.raise_for_status()


def sync_variants(shop, token, product_id, source_variants):
    existing_variants = get_product_variants(
        shop,
        token,
        product_id
    )

    existing_by_sku = {}

    for variant in existing_variants:
        sku = (variant.get("sku") or "").strip()

        if sku:
            existing_by_sku[sku] = variant

    for source_variant in source_variants:
        sku = (source_variant.get("sku") or "").strip()

        if not sku:
            print("⚠️ Variant 沒有 SKU，跳過")
            continue

        if sku in existing_by_sku:
            existing_variant = existing_by_sku[sku]

            update_payload = {
                "price": source_variant.get("price"),
                "compare_at_price": source_variant.get("compare_at_price"),
                "barcode": source_variant.get("barcode"),
                "weight": source_variant.get("weight"),
                "weight_unit": source_variant.get("weight_unit"),
                "taxable": source_variant.get("taxable"),
                "requires_shipping": source_variant.get("requires_shipping")
            }

            cleaned_payload = {
                key: value
                for key, value in update_payload.items()
                if value not in [None, ""]
            }

            update_variant(
                shop,
                token,
                existing_variant["id"],
                cleaned_payload
            )

            print(f"🔄 更新 Variant SKU：{sku}")

        else:
            create_variant(
                shop,
                token,
                product_id,
                source_variant
            )

            print(f"✅ 新增 Variant SKU：{sku}")


def get_product_admin_url(shop, product_id):
    return (
        f"https://admin.shopify.com/store/"
        f"{shop.replace('.myshopify.com', '')}"
        f"/products/{product_id}"
    )


def get_first_image(product):
    if product.get("images"):
        return product["images"][0].get("src", "")

    return ""


def sync_one_product(product, brand_store_map):
    title = product.get("title")
    vendor = (product.get("vendor") or "").strip().upper()
    first_image = get_first_image(product)

    print("\n====================================================")
    print(f"商品名稱：{title}")
    print(f"品牌 Vendor：{vendor}")
    print(f"來源狀態：{product.get('status')}")
    print(f"商品 ID：{product.get('id')}")

    target_shops_raw = brand_store_map.get(vendor, "")

    if not target_shops_raw:
        print("❌ 找不到品牌對應商店")

        add_result(
            title,
            vendor,
            "-",
            "failed",
            "找不到品牌對應商店",
            first_image
        )

        return

    target_shops = [
        shop.strip()
        for shop in target_shops_raw.split(",")
        if shop.strip()
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
                "找不到商店 Token",
                first_image
            )

            continue

        try:
            product_data = build_product_data(product)

            existing_product = find_product_by_title(
                target_shop,
                target_token,
                title
            )

            if existing_product:
                target_product_id = existing_product["id"]

                updated_product = update_product_basic(
                    target_shop,
                    target_token,
                    target_product_id,
                    product_data
                )

                replace_product_images(
                    target_shop,
                    target_token,
                    target_product_id,
                    product_data["images"],
                    existing_product.get("images", [])
                )

                sync_variants(
                    target_shop,
                    target_token,
                    target_product_id,
                    product_data["variants"]
                )

                product_url = get_product_admin_url(
                    target_shop,
                    updated_product["id"]
                )

                print(f"🔄 已更新：{target_shop}")

                add_result(
                    title,
                    vendor,
                    target_shop,
                    "success",
                    f"商品已存在，已更新，狀態：{product_data['status']}",
                    first_image,
                    product_url
                )

            else:
                created_product = create_product(
                    target_shop,
                    target_token,
                    product_data
                )

                product_url = get_product_admin_url(
                    target_shop,
                    created_product["id"]
                )

                print(f"✅ 已新增到：{target_shop}")

                add_result(
                    title,
                    vendor,
                    target_shop,
                    "success",
                    f"新增商品成功，狀態：{product_data['status']}",
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


def sync_products():
    print("📦 開始讀取主來源商店商品...")

    brand_store_map = get_brand_store_map()

    products = get_master_products()

    selected_ids = get_selected_product_ids()

    if selected_ids:
        products = [
            product for product in products
            if str(product.get("id")) in selected_ids
        ]

        print(f"🎯 只同步勾選商品，共 {len(products)} 個")

    else:
        print("📦 沒有勾選商品設定，執行全部同步")

    print(f"找到 {len(products)} 個商品")

    for product in products:
        sync_one_product(
            product,
            brand_store_map
        )

    print("\n🎉 商品同步完成")


def print_result_json():
    summary = {
        "success": len([
            result for result in SYNC_RESULTS
            if result["status"] == "success"
        ]),
        "skipped": len([
            result for result in SYNC_RESULTS
            if result["status"] == "skipped"
        ]),
        "failed": len([
            result for result in SYNC_RESULTS
            if result["status"] == "failed"
        ])
    }

    result = {
        "summary": summary,
        "results": SYNC_RESULTS
    }

    print("\nSYNC_RESULT_JSON_START")
    print(json.dumps(result, ensure_ascii=False))
    print("SYNC_RESULT_JSON_END")


if __name__ == "__main__":
    sync_products()
    print_result_json()
