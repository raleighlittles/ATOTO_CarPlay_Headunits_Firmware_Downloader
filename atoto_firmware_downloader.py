import datetime
import os
import pdb
import requests
import string
import time

SLEEP_TIME_SECS_BETWEEN_REQUESTS = 5

# ============ Helper functions ============ #


def get_firmware_release_page_url(product_model: str, mcu_version: str) -> str:
    return f"https://resources.myatoto.com/atoto-product-ibook/ibMobile/getIbookList?skuModel={product_model}&mcuVersion={mcu_version}&langType=1&iBookType=2"


def get_firmware_download_rel_dest_path(product_model, firmware_url) -> os.path:
    """
    Given a product model name, and,
    a URL, like: https://atoto-usa.oss-us-west-1.aliyuncs.com/2022/library/33320356/filename.zip
    return a path that is: <product model>/filename.zip
    """

    return os.path.join(product_model, firmware_url.split("/")[-1])


def download_firmware(top_level_firmware_dir, product_model, firmware_url) -> None:

    # Make sure the folder exists before downloading into it. I put this here instead of
    # using it with `firmware_dload_full_path` because I encountered a weird issue where os.makedirs(),
    # if passed in a full filename, i.e. /dir1/dir2/file.txt, would incorrectly
    # create the `file.txt` portion in the example, as a directory, and not a file,
    # causing the later call to open() to fail with IsADirectoryError: [Errno 21] Is a directory:
    os.makedirs(os.path.join(top_level_firmware_dir,
                product_model), exist_ok=True)

    firmware_dload_full_path = os.path.join(
        top_level_firmware_dir, get_firmware_download_rel_dest_path(product_model, firmware_url))

    print(f"[DEBUG] Downloading firmware to {firmware_dload_full_path}")

    firmware_dload_req = requests.get(firmware_url)

    if firmware_dload_req.ok:

        with open(firmware_dload_full_path, 'wb') as firmware_file:
            firmware_file.write(firmware_dload_req.content)

    else:
        print(
            f"[ERROR] Failed to download firmware from URL! Server sent HTTP{firmware_dload_req.status_code}")

    time.sleep(SLEEP_TIME_SECS_BETWEEN_REQUESTS)


def main_discover_and_dload_all_firmware(top_level_firmware_dload_folder):

    all_product_models = set()

    for keyword_str in string.ascii_uppercase:

        base_website_url = f"https://resources.myatoto.com/atoto-product-ibook/ibMobile/getSkuModelList?keyword={keyword_str}&iBookType=2"

        model_list_req = requests.get(base_website_url)
        # response looks something like:
        """
        {'code': 200, 'message': '操作成功', 'data': ['A6G209PF', 'A6G2A7KL', 'A6G2A7PF', ...]}
        """

        if model_list_req.ok:
            products_matching_keyword = model_list_req.json()['data']

            for model_num in products_matching_keyword:
                all_product_models.add(model_num)

        else:
            print(
                f"Error with query to {base_website_url}, page returned HTTP {model_list_req.status_code}")
            return 2

        # To avoid overloading server
        time.sleep(SLEEP_TIME_SECS_BETWEEN_REQUESTS)

    print(f"[DEBUG] Discovered {len(all_product_models)} products")

    for product_model in all_product_models:

        version_list_url = f"https://resources.myatoto.com/atoto-product-ibook/ibMobile/getMcuVersionBySku?skuModel={product_model}&iBookType=2"

        version_list_req = requests.get(version_list_url)
        time.sleep(SLEEP_TIME_SECS_BETWEEN_REQUESTS)

        if version_list_req.ok:

            # Response looks something like:
            """
            {'code': 200, 'message': '操作成功', 'data': {'systemVersion': 'Linux', 'mcuVersionList': []}}
            """
            # but `mcuVersionList` might not be empty, depending on the model

            try:
                models_fw_version_list = version_list_req.json()[
                    "data"]["mcuVersionList"]

                # If the version list is empty, that means this product just has one version of firmware
                # available, so retrieve it
                if not models_fw_version_list:

                    firmware_release_page_url = get_firmware_release_page_url(
                        product_model, "")

                    firmware_release_page_req = requests.get(
                        firmware_release_page_url)
                    time.sleep(SLEEP_TIME_SECS_BETWEEN_REQUESTS)

                    if firmware_release_page_req.ok:

                        firmware_url = firmware_release_page_req.json(
                        )["data"]["softwareVo"]["socVo"]["socUrl"]

                        print(
                            f"[DEBUG] Firmware URL for {product_model} is {firmware_url}")

                        download_firmware(
                            top_level_firmware_dload_folder, product_model, firmware_url)

                else:
                    for firmware_ver in models_fw_version_list:

                        firmware_release_page_url = get_firmware_release_page_url(
                            product_model, firmware_ver)

                        firmware_release_page_req = requests.get(
                            firmware_release_page_url, firmware_ver)
                        time.sleep(SLEEP_TIME_SECS_BETWEEN_REQUESTS)

                        if firmware_release_page_req.ok:

                            firmware_url = firmware_release_page_req.json(
                            )["data"]["softwareVo"]["mcuVo"]["mcuUrl"]

                            print(
                                f"[DEBUG] Firmware URL for {product_model} is {firmware_url}")

                            download_firmware(
                                top_level_firmware_dload_folder, product_model, firmware_url)

            except TypeError as e:

                print(
                    f"[ERROR] Website response from {version_list_url} did not match expected format. Error: {str(e)}")
                # return 3
                continue

            time.sleep(SLEEP_TIME_SECS_BETWEEN_REQUESTS)

        else:
            print(
                f"[ERROR] Couldn't get list of versions for product model'{product_model} from URL {version_list_url}")


if __name__ == "__main__":
    main_discover_and_dload_all_firmware(
        "firmware__" + datetime.datetime.now().strftime("%Y%m%d"))
