"""按用户问题范围筛选产品工具结果的公共规则。"""


def select_product_fields_for_answer(
    product_tool_result: dict[str, object],
    product_user_question: str,
) -> dict[str, object]:
    """仅保留回答当前问题所需的产品字段。"""

    # 工具失败时保留完整错误，以便模型能够说明失败原因。
    if not product_tool_result.get("success", False):
        return product_tool_result

    # 成功结果的业务数据位于外层 data 字段中。
    product_data = product_tool_result.get("data")

    # 数据结构异常时不裁剪，避免掩盖工具返回问题。
    if not isinstance(product_data, dict):
        return product_tool_result

    # 未找到产品时保留 found 为 false 的完整结果，防止模型编造数据。
    if not product_data.get("found", False):
        return product_tool_result

    # 统一问题文本的大小写和首尾空白，便于关键词匹配。
    product_clean_question = product_user_question.strip().casefold()

    # 用户要求完整资料时，返回工具提供的所有产品字段。
    product_full_detail_keywords = (
        "全部",
        "详情",
        "完整",
        "所有",
        "参数",
    )
    if any(
        product_detail_keyword in product_clean_question
        for product_detail_keyword in product_full_detail_keywords
    ):
        return product_tool_result

    # 为每个可回答字段定义中文业务关键词。
    product_field_keyword_groups = {
        "unit_price_usd": (
            "价格",
            "报价",
            "单价",
            "多少钱",
        ),
        "stock_square_meters": (
            "库存",
            "现货",
            "余量",
        ),
        "size_mm": (
            "规格",
            "尺寸",
            "大小",
            "厚度",
        ),
        "surface": (
            "表面",
            "工艺",
            "抛光",
            "哑光",
        ),
        "min_order_square_meters": (
            "起订量",
            "最小订量",
            "最少订",
        ),
        "lead_time_days": (
            "交期",
            "多久交货",
            "交货时间",
        ),
    }

    # 收集用户明确询问的业务字段。
    product_requested_fields = []
    for product_field_name, product_field_keywords in (
        product_field_keyword_groups.items()
    ):
        if any(
            product_field_keyword in product_clean_question
            for product_field_keyword in product_field_keywords
        ):
            product_requested_fields.append(product_field_name)

    # 未识别到具体字段时保留完整结果，以免遗漏用户意图。
    if not product_requested_fields:
        return product_tool_result

    # 始终保留产品身份与测试数据提示，使裁剪后的结果仍可被正确解释。
    product_answer_field_names = [
        "found",
        "product_id",
        "product_name_cn",
        "product_name_en",
        *product_requested_fields,
        "data_notice",
    ]

    # 仅复制数据中实际存在且用户当前需要的字段。
    product_selected_data = {
        product_field_name: product_data[product_field_name]
        for product_field_name in product_answer_field_names
        if product_field_name in product_data
    }

    # 返回与原工具结果兼容的外层结构。
    return {
        **product_tool_result,
        "data": product_selected_data,
    }
