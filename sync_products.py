import os
import json
import requests
from dotenv import load_dotenv
from urllib.parse import quote

load_dotenv()

API_VERSION = "2024-04"

MASTER_SHOP = os.getenv("MASTER_SHOP")
MASTER_TOKEN = os.getenv("MASTER_TOKEN")

SIZE_CHART_NAMESPACE = os.getenv("SIZE_CHART_NAMESPACE", "custom")
SIZE_CHART_KEY = os.getenv("SIZE_CHART_KEY", "size_chart")

BRAND_TEMPLATE_MAP = {
    "DESCENTE": os.getenv("DESCENTE_TEMPLATE_HANDLE"),
    "G/FORE": os.getenv("GFORE_TEMPLATE_HANDLE"),
    "GFORE": os.getenv("GFORE_TEMPLATE_HANDLE"),
    "2XU": os.getenv("TWOXU_TEMPLATE_HANDLE"),
    "ASH": os.getenv("ASH_TEMPLATE_HANDLE"),
    "ASH GOLF": os.getenv("ASH_TEMPLATE_HANDLE"),
    "CALLAWAY": os.getenv("CALLAWAY_TEMPLATE_HANDLE"),
}

SIZE_CHART_TEMPLATE_MAP = {
    "DESCENTE": os.getenv("DESCENTE_SIZE_CHART_TEMPLATE_HANDLE"),
    "G/FORE": os.getenv("GFORE_SIZE_CHART_TEMPLATE_HANDLE"),
    "GFORE": os.getenv("GFORE_SIZE_CHART_TEMPLATE_HANDLE"),
    "2XU": os.getenv("TWOXU_SIZE_CHART_TEMPLATE_HANDLE"),
    "ASH": os.getenv("ASH_SIZE_CHART_TEMPLATE_HANDLE"),
    "ASH GOLF": os.getenv("ASH_SIZE_CHART_TEMPLATE_HANDLE"),
    "CALLAWAY": os.getenv("CALLAWAY_SIZE_CHART_TEMPLATE_HANDLE"),
}

SYNC_RESULTS = []


def headers(token):
    return {
        "X-Shopify-Access-Token": token,
        "Content-Type": "application/json",
    }


def add_result(title, vendor, target_shop, status, message):
    SYNC_RESULTS.append({
        "title": title,
        "vendor": vendor,
        "target_shop": target_shop,
        "status": status,
        "message": message,
    })


def normalize_brand(vendor):
    return (
        vendor.upper()
        .replace("/", "")
        .replace(" ", "_")
        .replace("-", "_")
    )


def get_shop_token(shop):
    key = (
        "TARGET_"
        + shop.replace(".myshopify.com", "")
        .replace("-", "_")
        .upper()
        + "_TOKEN"
    )
    return os.getenv(key)


def get_target_shops(vendor):
    env_key = f"BRAND_{normalize_brand(vendor)}_STORES"
    stores = os.getenv(env_key, "")
    return [s.strip() for s in stores.split(",") if s.strip()]


def get_products(shop, token):
    url = f"https://{shop}/admin/api/{API_VERSION}/products.json?limit=250"

    response = requests.get(url, headers=headers(token))
    response.raise_for_status()

    return response.json().get("products", [])


def get_product_by_handle(shop, token, handle):
    if not handle:
        return None

    url = f"https://{shop}/admin/api/{API_VERSION}/products.json?handle={handle}"

    response = requests.get(url, headers=headers(token))
    response.raise_for_status()

    products = response.json().get("products", [])

    return products[0] if products else None


def find_product_by_title(shop, token, title):
    encoded_title = quote(title)

    url = (
        f"https://{shop}/admin/api/{API_VERSION}/products.json"
        f"?title={encoded_title}&limit=1"
    )

    response = requests.get(url, headers=headers(token))
    response.raise_for_status()

    products = response.json().get("products", [])

    return products[0] if products else None


def get_product_metafields(shop, token, product_id):
    url = (
        f"https://{shop}/admin/api/{API_VERSION}/products/"
        f"{product_id}/metafields.json"
    )

    response = requests.get(url, headers=headers(token))
    response.raise_for_status()

    return response.json().get("metafields", [])


def get_size_chart_metafield(shop, token, product_id):
    metafields = get_product_metafields(shop, token, product_id)

    for metafield in metafields:
        if (
            metafield.get("namespace") == SIZE_CHART_NAMESPACE
            and metafield.get("key") == SIZE_CHART_KEY
        ):
            return metafield

    return None


def create_product_metafield(shop, token, product_id, metafield):
    url = (
        f"https://{shop}/admin/api/{API_VERSION}/products/"
        f"{product_id}/metafields.json"
    )

    payload = {
        "metafield": {
            "namespace": metafield.get("namespace"),
            "key": metafield.get("key"),
            "value": metafield.get("value"),
            "type": metafield.get(
                "type",
                "multi_line_text_field"
            ),
        }
    }

    response = requests.post(
        url,
        headers=headers(token),
        json=payload
    )

    response.raise_for_status()

    return response.json()


def build_images(source_product):
    images = []

    for image in source_product.get("images", []):
        src = image.get("src")

        if src:
            image_data = {"src": src}

            if image.get("alt"):
                image_data["alt"] = image.get("alt")

            images.append(image_data)

    return images


def build_images_html(source_product):
    html = ""

    for image in source_product.get("images", []):
        src = image.get("src")
        alt = image.get("alt") or ""

        if src:
            html += f"""
<p>
  <img src="{src}" alt="{alt}" style="max-width:100%; height:auto;" />
</p>
"""

    return html


def format_description_with_template(source_product, template_product):
    title = source_product.get("title", "")
    body_html = source_product.get("body_html", "") or ""
    vendor = source_product.get("vendor", "") or ""
    product_type = source_product.get("product_type", "") or ""
    images_html = build_images_html(source_product)

    if not template_product:
        return f"""
<h3>{title}</h3>

<div>
{body_html}
</div>

{images_html}
"""

    template_html = template_product.get("body_html", "") or ""

    return f"""
<h3>{title}</h3>

<div>
{body_html}
</div>

<h3>商品資訊</h3>
<p>品牌：{vendor}</p>
<p>類型：{product_type}</p>

{images_html}

<div style="display:none;">
{template_html}
</div>
"""


def build_tags(source_product, target_shop):
    raw_tags = source_product.get("tags", "") or ""

    tags = []

    if raw_tags:
        tags.extend([
            tag.strip()
            for tag in raw_tags.split(",")
            if tag.strip()
        ])

    tags.append("synced-from-ash")

    vendor = (source_product.get("vendor") or "").strip()

    if vendor:
        vendor_tag = (
            "vendor-"
            + vendor.lower()
            .replace("/", "")
            .replace(" ", "-")
        )

        tags.append(vendor_tag)

    shop = target_shop.lower()

    if "descente" in shop:
        tags.append("descente")

    elif "gfore" in shop:
        tags.append("gfore")

    elif "2xu" in shop:
        tags.append("2xu")

    elif "callaway" in shop:
        tags.append("callaway")

    elif "ash" in shop:
        tags.append("ash")

    unique_tags = []

    for tag in tags:
        if tag not in unique_tags:
            unique_tags.append(tag)

    return ", ".join(unique_tags)


def build_options(source_product):
    options = []

    for option in source_product.get("options", []):
        name = option.get("name")

        if name:
            options.append({
                "name": name
            })

    return options


def build_variants(source_product):
    variants = []

    for variant in source_product.get("variants", []):
        new_variant = {
            "option1": variant.get("option1"),
            "option2": variant.get("option2"),
            "option3": variant.get("option3"),

            "sku": variant.get("sku"),
            "barcode": variant.get("barcode"),

            "price": variant.get("price"),
            "compare_at_price": variant.get("compare_at_price"),

            "weight": variant.get("weight"),
            "weight_unit": variant.get("weight_unit"),

            "inventory_management": variant.get("inventory_management"),
            "inventory_policy": variant.get("inventory_policy"),

            "taxable": variant.get("taxable"),
            "requires_shipping": variant.get("requires_shipping"),
        }

        cleaned_variant = {
            key: value
            for key, value in new_variant.items()
            if value is not None and value != ""
        }

        variants.append(cleaned_variant)

    return variants


def build_product_data(source_product, target_shop, target_token):
    vendor = (source_product.get("vendor") or "").strip()

    template_handle = (
        BRAND_TEMPLATE_MAP.get(vendor.upper())
        or BRAND_TEMPLATE_MAP.get(vendor)
    )

    template_product = get_product_by_handle(
        target_shop,
        target_token,
        template_handle
    )

    product_data = {
        "title": source_product.get("title"),
        "body_html": format_description_with_template(
            source_product,
            template_product
        ),
        "vendor": source_product.get("vendor"),
        "product_type": source_product.get("product_type"),
        "tags": build_tags(source_product, target_shop),
        "status": "active",
        "images": build_images(source_product),
        "variants": build_variants(source_product),
    }

    options = build_options(source_product)

    if options:
        product_data["options"] = options

    return product_data


def create_product(shop, token, product_data):
    url = f"https://{shop}/admin/api/{API_VERSION}/products.json"

    response = requests.post(
        url,
        headers=headers(token),
        json={"product": product_data}
    )

    response.raise_for_status()

    return response.json()


def build_size_chart_metafield(
    source_product,
    target_shop,
    target_token
):
    source_product_id = source_product.get("id")

    if not source_product_id:
        return None

    source_size_chart = get_size_chart_metafield(
        MASTER_SHOP,
        MASTER_TOKEN,
        source_product_id
    )

    if not source_size_chart:
        return None

    vendor = (source_product.get("vendor") or "").strip()

    template_handle = (
        SIZE_CHART_TEMPLATE_MAP.get(vendor.upper())
        or SIZE_CHART_TEMPLATE_MAP.get(vendor)
    )

    if not template_handle:
        return {
            "namespace": source_size_chart.get("namespace"),
            "key": source_size_chart.get("key"),
            "value": source_size_chart.get("value"),
            "type": source_size_chart.get(
                "type",
                "multi_line_text_field"
            ),
        }

    template_product = get_product_by_handle(
        target_shop,
        target_token,
        template_handle
    )

    if not template_product:
        return None

    template_size_chart = get_size_chart_metafield(
        target_shop,
        target_token,
        template_product.get("id")
    )

    if not template_size_chart:
        return None

    return {
        "namespace": template_size_chart.get("namespace"),
        "key": template_size_chart.get("key"),
        "value": source_size_chart.get("value"),
        "type": template_size_chart.get(
            "type",
            "multi_line_text_field"
        ),
    }


def sync_size_chart(
    source_product,
    target_shop,
    target_token,
    target_product_id
):
    metafield = build_size_chart_metafield(
        source_product,
        target_shop,
        target_token
    )

    if not metafield:
        return

    create_product_metafield(
        target_shop,
        target_token,
        target_product_id,
        metafield
    )


def print_sync_summary():
    success = len([
        r for r in SYNC_RESULTS
        if r["status"] == "success"
    ])

    skipped = len([
        r for r in SYNC_RESULTS
        if r["status"] == "skipped"
    ])

    failed = len([
        r for r in SYNC_RESULTS
        if r["status"] == "failed"
    ])

    summary = {
        "summary": {
            "success": success,
            "skipped": skipped,
            "failed": failed,
        },
        "results": SYNC_RESULTS
    }

    print("\nSYNC_RESULT_JSON_START")
    print(json.dumps(summary, ensure_ascii=False))
    print("SYNC_RESULT_JSON_END\n")


def main():
    if not MASTER_SHOP or not MASTER_TOKEN:
        print("❌ MASTER_SHOP 或 MASTER_TOKEN 未設定")
        return

    print("📦 開始同步商品")

    products = get_products(MASTER_SHOP, MASTER_TOKEN)

    print(f"找到 {len(products)} 個商品")

    for product in products:
        title = product.get("title")
        vendor = (product.get("vendor") or "").strip()

        target_shops = get_target_shops(vendor)

        if not target_shops:
            add_result(
                title,
                vendor,
                "-",
                "failed",
                "找不到目標商店"
            )
            continue

        for target_shop in target_shops:
            target_token = get_shop_token(target_shop)

            if not target_token:
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

            if existing_product:
                add_result(
                    title,
                    vendor,
                    target_shop,
                    "skipped",
                    "商品已存在"
                )
                continue

            try:
                product_data = build_product_data(
                    product,
                    target_shop,
                    target_token
                )

                created_product = create_product(
                    target_shop,
                    target_token,
                    product_data
                )

                target_product_id = created_product["product"]["id"]

                sync_size_chart(
                    product,
                    target_shop,
                    target_token,
                    target_product_id
                )

                add_result(
                    title,
                    vendor,
                    target_shop,
                    "success",
                    "同步成功"
                )

            except Exception as error:
                add_result(
                    title,
                    vendor,
                    target_shop,
                    "failed",
                    str(error)
                )

    print_sync_summary()


if __name__ == "__main__":
    main()
