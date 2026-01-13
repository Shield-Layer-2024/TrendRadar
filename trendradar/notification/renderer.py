# coding=utf-8
"""
通知内容渲染模块

提供多平台通知内容渲染功能，生成格式化的推送消息
"""

from datetime import datetime
from typing import Dict, Optional, Callable

from trendradar.report.formatter import format_title_for_platform


def render_feishu_content(
    report_data: Dict,
    update_info: Optional[Dict] = None,
    mode: str = "daily",
    separator: str = "---",
    reverse_content_order: bool = False,
    max_total_news_in_push: int = 0,
    show_stats_in_push: bool = True,
    get_time_func: Optional[Callable[[], datetime]] = None,
) -> str:
    """渲染飞书通知内容

    Args:
        report_data: 报告数据字典，包含 stats, new_titles, failed_ids, total_new_count
        update_info: 版本更新信息（可选）
        mode: 报告模式 ("daily", "incremental", "current")
        separator: 内容分隔符
        reverse_content_order: 是否反转内容顺序（新增在前）
        max_total_news_in_push: 推送中最大新闻总数（0=不限制）
        show_stats_in_push: 是否在推送中展示热点词汇统计
        get_time_func: 获取当前时间的函数（可选，默认使用 datetime.now()）

    Returns:
        格式化的飞书消息内容
    """
    # 限制新闻总数并处理显示模式
    total_news_count = 0
    truncated_stats = []
    truncated_new_titles = []
    original_total_new_count = report_data.get("total_new_count", 0)
    
    # 如果不显示统计分组，将 stats 中的新闻转换为完全平铺格式（不分平台）
    if not show_stats_in_push and report_data["stats"]:
        # 收集所有匹配的新闻到一个列表（完全平铺，不分组）
        all_titles = []
        for stat in report_data["stats"]:
            for title_data in stat["titles"]:
                all_titles.append(title_data)
        
        # 转换为平铺格式（单个分组，包含所有新闻）
        flattened_titles = [{
            "source_name": "匹配的新闻",  # 不显示平台，统一标题
            "titles": all_titles
        }]
        
        # 合并到 new_titles
        if report_data["new_titles"]:
            all_new_titles = flattened_titles + report_data["new_titles"]
        else:
            all_new_titles = flattened_titles
        
        # 更新总数
        original_total_new_count = len(all_titles) + report_data.get("total_new_count", 0)
    else:
        all_new_titles = report_data["new_titles"]
    
    if max_total_news_in_push > 0:
        # 统计并截断 stats 中的新闻
        if show_stats_in_push and report_data["stats"]:
            for stat in report_data["stats"]:
                if total_news_count >= max_total_news_in_push:
                    break
                remaining = max_total_news_in_push - total_news_count
                truncated_titles = stat["titles"][:remaining]
                if truncated_titles:
                    truncated_stats.append({
                        "word": stat["word"],
                        "count": len(truncated_titles),
                        "titles": truncated_titles
                    })
                    total_news_count += len(truncated_titles)
        
        # 统计并截断 new_titles 中的新闻
        if all_new_titles:
            for source_data in all_new_titles:
                if total_news_count >= max_total_news_in_push:
                    break
                remaining = max_total_news_in_push - total_news_count
                truncated_titles = source_data["titles"][:remaining]
                if truncated_titles:
                    truncated_new_titles.append({
                        "source_name": source_data["source_name"],
                        "titles": truncated_titles
                    })
                    total_news_count += len(truncated_titles)
    else:
        # 不限制数量
        truncated_stats = report_data["stats"] if show_stats_in_push else []
        truncated_new_titles = all_new_titles

    # 生成热点词汇统计部分
    stats_content = ""
    if show_stats_in_push and truncated_stats:
        stats_content += "📊 **热点词汇统计**\n\n"

        total_count = len(truncated_stats)

        for i, stat in enumerate(truncated_stats):
            word = stat["word"]
            count = stat["count"]

            sequence_display = f"<font color='grey'>[{i + 1}/{total_count}]</font>"

            if count >= 10:
                stats_content += f"🔥 {sequence_display} **{word}** : <font color='red'>{count}</font> 条\n\n"
            elif count >= 5:
                stats_content += f"📈 {sequence_display} **{word}** : <font color='orange'>{count}</font> 条\n\n"
            else:
                stats_content += f"📌 {sequence_display} **{word}** : {count} 条\n\n"

            for j, title_data in enumerate(stat["titles"], 1):
                formatted_title = format_title_for_platform(
                    "feishu", title_data, show_source=True
                )
                stats_content += f"  {j}. {formatted_title}\n"

                if j < len(stat["titles"]):
                    stats_content += "\n"

            if i < len(truncated_stats) - 1:
                stats_content += f"\n{separator}\n\n"

    # 生成新增新闻部分
    new_titles_content = ""
    if truncated_new_titles:
        # 统计所有新闻的总序号
        total_index = 0
        for source_data in truncated_new_titles:
            # 如果是平铺模式（不分平台），不显示任何标题
            if source_data['source_name'] != "匹配的新闻":
                # 非平铺模式：显示平台分类标题
                new_titles_content += (
                    f"**{source_data['source_name']}** ({len(source_data['titles'])} 条):\n"
                )
                indent = "  "
            else:
                # 平铺模式：不显示标题，直接显示新闻
                indent = ""

            for title_data in source_data["titles"]:
                total_index += 1
                title_data_copy = title_data.copy()
                title_data_copy["is_new"] = False
                formatted_title = format_title_for_platform(
                    "feishu", title_data_copy, show_source=True  # 平铺模式显示来源
                )
                new_titles_content += f"{indent}{total_index}. {formatted_title}\n"

            # 只在非平铺模式下添加换行
            if source_data['source_name'] != "匹配的新闻":
                new_titles_content += "\n"

    # 根据配置决定内容顺序
    text_content = ""
    if reverse_content_order:
        # 新增热点在前，热点词汇统计在后
        if new_titles_content:
            text_content += new_titles_content
            if stats_content:
                text_content += f"\n{separator}\n\n"
        if stats_content:
            text_content += stats_content
    else:
        # 默认：热点词汇统计在前，新增热点在后
        if stats_content:
            text_content += stats_content
            if new_titles_content:
                text_content += f"\n{separator}\n\n"
        if new_titles_content:
            text_content += new_titles_content

    if not text_content:
        if mode == "incremental":
            mode_text = "增量模式下暂无新增匹配的热点词汇"
        elif mode == "current":
            mode_text = "当前榜单模式下暂无匹配的热点词汇"
        else:
            mode_text = "暂无匹配的热点词汇"
        text_content = f"📭 {mode_text}\n\n"

    if report_data["failed_ids"]:
        if text_content and "暂无匹配" not in text_content:
            text_content += f"\n{separator}\n\n"

        text_content += "⚠️ **数据获取失败的平台：**\n\n"
        for i, id_value in enumerate(report_data["failed_ids"], 1):
            text_content += f"  • <font color='red'>{id_value}</font>\n"

    # 获取当前时间
    now = get_time_func() if get_time_func else datetime.now()
    text_content += (
        f"\n\n<font color='grey'>更新时间：{now.strftime('%Y-%m-%d %H:%M:%S')}</font>"
    )

    if update_info:
        text_content += f"\n<font color='grey'>TrendRadar 发现新版本 {update_info['remote_version']}，当前 {update_info['current_version']}</font>"

    return text_content


def render_dingtalk_content(
    report_data: Dict,
    update_info: Optional[Dict] = None,
    mode: str = "daily",
    reverse_content_order: bool = False,
    max_total_news_in_push: int = 0,
    show_stats_in_push: bool = True,
    get_time_func: Optional[Callable[[], datetime]] = None,
) -> str:
    """渲染钉钉通知内容

    Args:
        report_data: 报告数据字典，包含 stats, new_titles, failed_ids, total_new_count
        update_info: 版本更新信息（可选）
        mode: 报告模式 ("daily", "incremental", "current")
        reverse_content_order: 是否反转内容顺序（新增在前）
        max_total_news_in_push: 推送中最大新闻总数（0=不限制）
        show_stats_in_push: 是否在推送中展示热点词汇统计
        get_time_func: 获取当前时间的函数（可选，默认使用 datetime.now()）

    Returns:
        格式化的钉钉消息内容
    """
    # 限制新闻总数并处理显示模式
    total_news_count = 0
    truncated_stats = []
    truncated_new_titles = []
    original_total_new_count = report_data.get("total_new_count", 0)
    
    # 如果不显示统计分组，将 stats 中的新闻转换为完全平铺格式（不分平台）
    if not show_stats_in_push and report_data["stats"]:
        # 收集所有匹配的新闻到一个列表（完全平铺，不分组）
        all_titles = []
        for stat in report_data["stats"]:
            for title_data in stat["titles"]:
                all_titles.append(title_data)
        
        # 转换为平铺格式（单个分组，包含所有新闻）
        flattened_titles = [{
            "source_name": "匹配的新闻",  # 不显示平台，统一标题
            "titles": all_titles
        }]
        
        # 合并到 new_titles
        if report_data["new_titles"]:
            all_new_titles = flattened_titles + report_data["new_titles"]
        else:
            all_new_titles = flattened_titles
        
        # 更新总数
        original_total_new_count = len(all_titles) + report_data.get("total_new_count", 0)
    else:
        all_new_titles = report_data["new_titles"]
    
    if max_total_news_in_push > 0:
        # 统计并截断 stats 中的新闻
        if show_stats_in_push and report_data["stats"]:
            for stat in report_data["stats"]:
                if total_news_count >= max_total_news_in_push:
                    break
                remaining = max_total_news_in_push - total_news_count
                truncated_titles = stat["titles"][:remaining]
                if truncated_titles:
                    truncated_stats.append({
                        "word": stat["word"],
                        "count": len(truncated_titles),
                        "titles": truncated_titles
                    })
                    total_news_count += len(truncated_titles)
        
        # 统计并截断 new_titles 中的新闻
        if all_new_titles:
            for source_data in all_new_titles:
                if total_news_count >= max_total_news_in_push:
                    break
                remaining = max_total_news_in_push - total_news_count
                truncated_titles = source_data["titles"][:remaining]
                if truncated_titles:
                    truncated_new_titles.append({
                        "source_name": source_data["source_name"],
                        "titles": truncated_titles
                    })
                    total_news_count += len(truncated_titles)
    else:
        # 不限制数量
        truncated_stats = report_data["stats"] if show_stats_in_push else []
        truncated_new_titles = all_new_titles

    total_titles = sum(
        len(stat["titles"]) for stat in truncated_stats if stat["count"] > 0
    )
    now = get_time_func() if get_time_func else datetime.now()

    # 头部信息
    header_content = f"**总新闻数：** {total_titles}\n\n"
    header_content += f"**时间：** {now.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    header_content += "**类型：** 热点分析报告\n\n"
    header_content += "---\n\n"

    # 生成热点词汇统计部分
    stats_content = ""
    if show_stats_in_push and truncated_stats:
        stats_content += "📊 **热点词汇统计**\n\n"

        total_count = len(truncated_stats)

        for i, stat in enumerate(truncated_stats):
            word = stat["word"]
            count = stat["count"]

            sequence_display = f"[{i + 1}/{total_count}]"

            if count >= 10:
                stats_content += f"🔥 {sequence_display} **{word}** : **{count}** 条\n\n"
            elif count >= 5:
                stats_content += f"📈 {sequence_display} **{word}** : **{count}** 条\n\n"
            else:
                stats_content += f"📌 {sequence_display} **{word}** : {count} 条\n\n"

            for j, title_data in enumerate(stat["titles"], 1):
                formatted_title = format_title_for_platform(
                    "dingtalk", title_data, show_source=True
                )
                stats_content += f"  {j}. {formatted_title}\n"

                if j < len(stat["titles"]):
                    stats_content += "\n"

            if i < len(truncated_stats) - 1:
                stats_content += "\n---\n\n"

    # 生成新增新闻部分
    new_titles_content = ""
    if truncated_new_titles:
        # 统计所有新闻的总序号
        total_index = 0
        for source_data in truncated_new_titles:
            # 如果是平铺模式（不分平台），不显示任何标题
            if source_data['source_name'] != "匹配的新闻":
                # 非平铺模式：显示平台分类标题
                new_titles_content += f"**{source_data['source_name']}** ({len(source_data['titles'])} 条):\n\n"
                indent = "  "
            else:
                # 平铺模式：不显示标题，直接显示新闻
                indent = ""

            for title_data in source_data["titles"]:
                total_index += 1
                title_data_copy = title_data.copy()
                title_data_copy["is_new"] = False
                formatted_title = format_title_for_platform(
                    "dingtalk", title_data_copy, show_source=True  # 平铺模式显示来源
                )
                new_titles_content += f"{indent}{total_index}. {formatted_title}\n"

            # 只在非平铺模式下添加换行
            if source_data['source_name'] != "匹配的新闻":
                new_titles_content += "\n"

    # 根据配置决定内容顺序
    text_content = header_content
    if reverse_content_order:
        # 新增热点在前，热点词汇统计在后
        if new_titles_content:
            text_content += new_titles_content
            if stats_content:
                text_content += "\n---\n\n"
        if stats_content:
            text_content += stats_content
    else:
        # 默认：热点词汇统计在前，新增热点在后
        if stats_content:
            text_content += stats_content
            if new_titles_content:
                text_content += "\n---\n\n"
        if new_titles_content:
            text_content += new_titles_content

    if not stats_content and not new_titles_content:
        if mode == "incremental":
            mode_text = "增量模式下暂无新增匹配的热点词汇"
        elif mode == "current":
            mode_text = "当前榜单模式下暂无匹配的热点词汇"
        else:
            mode_text = "暂无匹配的热点词汇"
        text_content += f"📭 {mode_text}\n\n"

    if report_data["failed_ids"]:
        if "暂无匹配" not in text_content:
            text_content += "\n---\n\n"

        text_content += "⚠️ **数据获取失败的平台：**\n\n"
        for i, id_value in enumerate(report_data["failed_ids"], 1):
            text_content += f"  • **{id_value}**\n"

    text_content += f"\n\n> 更新时间：{now.strftime('%Y-%m-%d %H:%M:%S')}"

    if update_info:
        text_content += f"\n> TrendRadar 发现新版本 **{update_info['remote_version']}**，当前 **{update_info['current_version']}**"

    return text_content
