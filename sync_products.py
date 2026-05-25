import os
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


def headers(token):
    return {
        "X-Shopify-Access-Token": token,
        "Content-Type": "application/json",
    }


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
    url = f"https://{shop}/admin/api/{API_VERSION}/products/{product_id}/metafields.json"
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
    url = f"https://{shop}/admin/api/{API_VERSION}/products/{product_id}/metafields.json"

    payload = {
        "metafield": {
            "namespace": metafield.get("namespace"),
            "key": metafield.get("key"),
            "value": metafield.get("value"),
            "type": metafield.get("type", "multi_line_text_field"),
        }
    }

    response = requests.post(url, headers=headers(token), json=payload)

    if not response.ok:
        print("⚠️ Metafield 同步失敗")
        print(response.text)

    response.raise_for_status()
    return response.json()


def get_source_product_collects(product_id):
    url = (
        f"https://{MASTER_SHOP}/admin/api/{API_VERSION}/collects.json"
        f"?product_id={product_id}&limit=250"
    )
    response = requests.get(url, headers=headers(MASTER_TOKEN))
    response.raise_for_status()
    return response.json().get("collects", [])


def get_custom_collection(shop, token, collection_id):
    url = f"https://{shop}/admin/api/{API_VERSION}/custom_collections/{collection_id}.json"
    response = requests.get(url, headers=headers(token))

    if response.status_code == 404:
        return None

    response.raise_for_status()
    return response.json().get("custom_collection")


def get_smart_collection(shop, token, collection_id):
    url = f"https://{shop}/admin/api/{API_VERSION}/smart_collections/{collection_id}.json"
    response = requests.get(url, headers=headers(token))

    if response.status_code == 404:
        return None

    response.raise_for_status()
    return response.json().get("smart_collection")


def get_source_product_collections(source_product):
    product_id = source_product.get("id")

    if not product_id:
        return []

    collects = get_source_product_collects(product_id)

    collections = []

    for collect in collects:
        collection_id = collect.get("collection_id")

        if not collection_id:
            continue

        custom_collection = get_custom_collection(
            MASTER_SHOP,
            MASTER_TOKEN,
            collection_id
        )

        if custom_collection:
            collections.append({
                "type": "custom",
                "title": custom_collection.get("title"),
                "handle": custom_collection.get("handle"),
            })
            continue

        smart_collection = get_smart_collection(
            MASTER_SHOP,
            MASTER_TOKEN,
            collection_id
        )

        if smart_collection:
            collections.append({
                "type": "smart",
                "title": smart_collection.get("title"),
                "handle": smart_collection.get("handle"),
            })

    return collections


def find_target_custom_collection(shop, token, handle, title):
    url = f"https://{shop}/admin/api/{API_VERSION}/custom_collections.json?limit=250"
    response = requests.get(url, headers=headers(token))
    response.raise_for_status()

    collections = response.json().get("custom_collections", [])

    for collection in collections:
        if handle and collection.get("handle") == handle:
            return collection

    for collection in collections:
        if title and collection.get("title") == title:
            return collection

    return None


def add_product_to_collection(shop, token, product_id, collection_id):
    url = f"https://{shop}/admin/api/{API_VERSION}/collects.json"

    payload = {
        "collect": {
            "product_id": product_id,
            "collection_id": collection_id
        }
    }

    response = requests.post(url, headers=headers(token), json=payload)

    if response.status_code == 422:
        print("ℹ️ 商品可能已經在此商品系列中")
        return None

    if not response.ok:
        print("⚠️ 商品系列同步失敗")
        print(response.text)

    response.raise_for_status()
    return response.json()


def sync_collections(source_product, target_shop, target_token, target_product_id):
    collections = get_source_product_collections(source_product)

    if not collections:
        print("ℹ️ 沒有商品系列可同步")
        return

    for collection in collections:
        title = collection.get("title")
        handle = collection.get("handle")
        collection_type = collection.get("type")

        if collection_type == "smart":
            print(f"ℹ️ 智慧商品系列不手動加入：{title}")
            continue

        target_collection = find_target_custom_collection(
            target_shop,
            target_token,
            handle,
            title
        )

        if not target_collection:
            print(f"⚠️ 目標商店找不到同名商品系列：{title}")
            continue

        add_product_to_collection(
            target_shop,
            target_token,
            target_product_id,
            target_collection.get("id")
        )

        print(f"📁 已加入商品系列：{title}")


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

<!-- 範本商品格式參考 -->
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
            .replace("_", "-")
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
            options.append({"name": name})

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

    if not response.ok:
        print(f"❌ 建立商品失敗：{shop}")
        print(response.text)

    response.raise_for_status()
    return response.json()


def build_size_chart_metafield(source_product, target_shop, target_token):
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
            "type": source_size_chart.get("type", "multi_line_text_field"),
        }

    template_product = get_product_by_handle(
        target_shop,
        target_token,
        template_handle
    )

    if not template_product:
        return {
            "namespace": source_size_chart.get("namespace"),
            "key": source_size_chart.get("key"),
            "value": source_size_chart.get("value"),
            "type": source_size_chart.get("type", "multi_line_text_field"),
        }

    template_size_chart = get_size_chart_metafield(
        target_shop,
        target_token,
        template_product.get("id")
    )

    if not template_size_chart:
        return {
            "namespace": source_size_chart.get("namespace"),
            "key": source_size_chart.get("key"),
            "value": source_size_chart.get("value"),
            "type": source_size_chart.get("type", "multi_line_text_field"),
        }

    return {
        "namespace": template_size_chart.get("namespace"),
        "key": template_size_chart.get("key"),
        "value": source_size_chart.get("value"),
        "type": template_size_chart.get(
            "type",
            source_size_chart.get("type", "multi_line_text_field")
        ),
    }


def sync_size_chart(source_product, target_shop, target_token, target_product_id):
    size_chart_metafield = build_size_chart_metafield(
        source_product,
        target_shop,
        target_token
    )

    if not size_chart_metafield:
        print("ℹ️ 沒有尺寸表可同步")
        return

    try:
        create_product_metafield(
            target_shop,
            target_token,
            target_product_id,
            size_chart_metafield
        )
        print("📏 尺寸表同步完成")

    except Exception as error:
        print("⚠️ 尺寸表同步失敗")
        print(str(error))


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

        target_shops = get_target_shops(vendor)

        if not target_shops:
            print("⚠️ 找不到此品牌對應的目標商店，略過")
            continue

        for target_shop in target_shops:
            target_token = get_shop_token(target_shop)

            if not target_token:
                print(f"⚠️ 找不到 {target_shop} 的 Token，略過")
                continue

            existing_product = find_product_by_title(
                target_shop,
                target_token,
                title
            )

            if existing_product:
                print(f"⏭️ 已存在，略過：{target_shop}")
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

                sync_collections(
                    product,
                    target_shop,
                    target_token,
                    target_product_id
                )

                print(f"✅ 已同步到：{target_shop}")

            except Exception as error:
                print(f"❌ 同步失敗：{target_shop}")
                print(str(error))

    print("\n🎉 商品同步完成")


if __name__ == "__main__":
    main()
