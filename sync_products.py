import os
import requests
from dotenv import load_dotenv
from urllib.parse import quote

load_dotenv()

API_VERSION = "2024-04"

MASTER_SHOP = os.getenv("MASTER_SHOP")
MASTER_TOKEN = os.getenv("MASTER_TOKEN")


BRAND_TEMPLATE_MAP = {
    "DESCENTE": os.getenv("DESCENTE_TEMPLATE_HANDLE"),
    "G/FORE": os.getenv("GFORE_TEMPLATE_HANDLE"),
    "GFORE": os.getenv("GFORE_TEMPLATE_HANDLE"),
    "2XU": os.getenv("TWOXU_TEMPLATE_HANDLE"),
    "ASH": os.getenv("ASH_TEMPLATE_HANDLE"),
    "ASH GOLF": os.getenv("ASH_TEMPLATE_HANDLE"),
    "CALLAWAY": os.getenv("CALLAWAY_TEMPLATE_HANDLE"),
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


def product_exists(shop, token, title):
    encoded_title = quote(title)
    url = (
        f"https://{shop}/admin/api/{API_VERSION}/products.json"
        f"?title={encoded_title}&limit=1"
    )

    response = requests.get(url, headers=headers(token))
    response.raise_for_status()

    products = response.json().get("products", [])
    return len(products) > 0


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

        print("目標商店：")

        for shop in target_shops:
            print(f" - {shop}")

        for target_shop in target_shops:
            target_token = get_shop_token(target_shop)

            if not target_token:
                print(f"⚠️ 找不到 {target_shop} 的 Token，略過")
                continue

            if product_exists(target_shop, target_token, title):
                print(f"⏭️ 已存在，略過：{target_shop}")
                continue

            try:
                product_data = build_product_data(
                    product,
                    target_shop,
                    target_token
                )

                create_product(
                    target_shop,
                    target_token,
                    product_data
                )

                print(f"✅ 已同步到：{target_shop}")

            except Exception as error:
                print(f"❌ 同步失敗：{target_shop}")
                print(str(error))

    print("\n🎉 商品同步完成")


if __name__ == "__main__":
    main()
