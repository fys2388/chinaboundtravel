# ============================================
# chinaboundtravel.com - 飞书机器人配置
# ============================================

# ------------------------
# 飞书机器人基础配置
# ------------------------
FEISHU_ROBOT = {
    "enabled": True,
    "name": "ChinaBound Travel 运营机器人",
    "webhook_url": "",  # 需要在飞书后台配置后填入
    "secret": "",       # 需要在飞书后台配置后填入
    "avatar_url": ""    # 可选：机器人头像URL
}

# ------------------------
# 飞书云文档配置
# ------------------------
FEISHU_DOCUMENT = {
    "enabled": True,
    "app_id": "",       # 需要在飞书开放平台创建应用后填入
    "app_secret": "",   # 需要在飞书开放平台创建应用后填入
    "folder_root": "chinaboundtravel 运营报告",
    "folders": {
        "daily": "01 每日巡检报告",
        "weekly": "02 每周运营报告",
        "monthly": "03 月度深度复盘",
        "yearly": "04 年度全域总结",
        "ledger": "运营数据总台账"
    }
}

# ------------------------
# 报告推送模板
# ------------------------
FEISHU_MESSAGE_TEMPLATES = {
    "daily": {
        "title": "📊 每日巡检报告已生成",
        "format": "{report_name}\n{document_link}\n\n{conclusion}"
    },
    "weekly": {
        "title": "📈 每周运营报告已生成",
        "format": "{report_name}\n{document_link}\n\n本周评级：{rating}"
    },
    "monthly": {
        "title": "📉 月度复盘报告已生成",
        "format": "{report_name}\n{document_link}\n\n{key_conclusion}"
    },
    "yearly": {
        "title": "🎯 年度总结报告已生成",
        "format": "{report_name}\n{document_link}\n\n{annual_summary}"
    }
}

# ------------------------
# 告警消息模板
# ------------------------
FEISHU_ALERT_TEMPLATES = {
    "critical": {
        "title": "🔴 紧急告警",
        "color": "#ff0000"
    },
    "warning": {
        "title": "🟡 警告提醒",
        "color": "#ffaa00"
    },
    "info": {
        "title": "🔵 信息通知",
        "color": "#0088ff"
    }
}

# ------------------------
# 文档格式配置
# ------------------------
DOCUMENT_FORMAT = {
    "title_level_1": "# ",
    "title_level_2": "## ",
    "title_level_3": "### ",
    "bold": "**{}**",
    "italic": "*{}*",
    "highlight_red": "<font color=\"#ff0000\">{}</font>",
    "table_header": "| {} |",
    "table_separator": "| --- |",
    "list_bullet": "- ",
    "list_number": "{}. ",
    "link": "[{}]({})"
}

# ------------------------
# 权限配置
# ------------------------
PERMISSIONS = {
    "document_edit": ["本人"],
    "document_view": ["本人"],
    "robot_message": ["运营群", "个人通知"]
}