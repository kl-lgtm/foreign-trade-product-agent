# 导入csv模块，用于读取CSV格式的产品数据
import csv

# 导入json模块，用于格式化显示工具测试结果
import json

# 导入Path，用于构造产品数据库文件路径
from pathlib import Path


# 取得当前代码文件的绝对路径
product_tools_file = Path(__file__).resolve()

# 向上两级取得项目根目录
product_project_root = product_tools_file.parent.parent

# 构造模拟产品CSV数据库的完整路径
TRADE_PRODUCT_DATA_PATH = (
    product_project_root
    / "trade_data"
    / "structured_data"
    / "trade_products.csv"
)


def load_product_records() -> list[dict[str, str]]:
    """从CSV文件中读取全部模拟产品记录。"""

    # 检查产品数据文件是否真实存在
    if not TRADE_PRODUCT_DATA_PATH.exists():
        raise FileNotFoundError(
            f"找不到产品数据文件："
            f"{TRADE_PRODUCT_DATA_PATH}"
        )

    # 以只读方式打开CSV文件
    # utf-8-sig可以兼容普通UTF-8和带BOM的UTF-8文件
    with TRADE_PRODUCT_DATA_PATH.open(
        mode="r",
        encoding="utf-8-sig",
        newline="",
    ) as product_file:

        # 创建按表头读取数据的CSV阅读器
        product_reader = csv.DictReader(
            product_file
        )

        # 将CSV中的全部产品行转换成字典列表
        product_records = list(
            product_reader
        )

    # 如果CSV文件只有表头而没有产品数据，则主动报错
    if not product_records:
        raise ValueError(
            "产品数据文件中没有有效产品记录。"
        )

    # 返回全部产品记录
    return product_records


def query_product(
    product_id: str,
) -> dict[str, object]:
    """根据产品编号精确查询价格、库存和交期。"""

    # 删除产品编号首尾空格并转换成大写
    # 这样a001、A001和 A001 都可以正常查询
    product_clean_product_id = (
        product_id.strip().upper()
    )

    # 禁止使用空产品编号调用工具
    if not product_clean_product_id:
        raise ValueError("产品编号不能为空。")

    # 从CSV文件中读取全部产品记录
    product_records = (
        load_product_records()
    )

    # 逐个检查产品编号是否匹配
    for product_record in product_records:

        # 读取当前记录的产品编号并进行标准化
        product_record_product_id = (
            product_record
            .get("product_id", "")
            .strip()
            .upper()
        )

        # 如果编号匹配，就整理并返回产品信息
        if (
            product_record_product_id
            == product_clean_product_id
        ):

            # found表示工具成功找到了对应产品
            return {
                # 标记本次查询成功
                "found": True,

                # 返回标准化后的产品编号
                "product_id": product_record_product_id,

                # 返回中文产品名称
                "product_name_cn": (
                    product_record[
                        "product_name_cn"
                    ]
                ),

                # 返回英文产品名称
                "product_name_en": (
                    product_record[
                        "product_name_en"
                    ]
                ),

                # 返回产品尺寸
                "size_mm": (
                    product_record["size_mm"]
                ),

                # 返回表面工艺
                "surface": (
                    product_record["surface"]
                ),

                # 将价格由字符串转换成浮点数
                "unit_price_usd": float(
                    product_record[
                        "unit_price_usd"
                    ]
                ),

                # 将库存由字符串转换成整数
                "stock_square_meters": int(
                    product_record[
                        "stock_square_meters"
                    ]
                ),

                # 将最小起订量转换成整数
                "min_order_square_meters": int(
                    product_record[
                        "min_order_square_meters"
                    ]
                ),

                # 将交期天数转换成整数
                "lead_time_days": int(
                    product_record[
                        "lead_time_days"
                    ]
                ),

                # 提醒使用者当前数据仅用于学习测试
                "data_notice": (
                    "模拟测试数据，不代表真实企业。"
                ),
            }

    # 遍历完成仍未匹配时，返回未找到结果
    return {
        # 标记本次查询没有找到产品
        "found": False,

        # 返回用户实际查询的标准化编号
        "product_id": product_clean_product_id,

        # 返回便于用户理解的提示
        "message": (
            f"产品数据库中不存在编号"
            f"{product_clean_product_id}。"
        ),
    }


# 只有直接运行当前模块时，才执行工具测试
if __name__ == "__main__":

    # 准备两个存在的编号和一个不存在的编号
    product_test_product_ids = [
        "A001",
        "a002",
        "A999",
    ]

    # 逐个测试产品查询工具
    for product_test_product_id in product_test_product_ids:

        # 显示当前正在测试的产品编号
        print("\n" + "=" * 60)
        print(
            f"测试产品编号："
            f"{product_test_product_id}"
        )

        try:
            # 调用产品精确查询工具
            product_tool_result = query_product(
                product_test_product_id
            )

        # 捕获文件读取或数据转换错误
        except Exception as product_tool_error:

            # 输出具体错误原因
            print(
                f"产品工具调用失败："
                f"{product_tool_error}"
            )

        else:
            # 将查询结果格式化成带缩进的中文JSON
            product_result_json = json.dumps(
                product_tool_result,

                # 保留中文字符，避免转换成Unicode编码
                ensure_ascii=False,

                # 使用两个空格进行缩进
                indent=2,
            )

            # 输出产品查询结果
            print(product_result_json)
