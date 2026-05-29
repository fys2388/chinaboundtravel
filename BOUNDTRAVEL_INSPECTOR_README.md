# BoundTravel 每日巡检机器人

## 功能概览

自动化检查 chinaboundtravel.com 网站的运行状态和内容质量。

### 检查项目

1. **网站可访问性** - 检查网站是否正常打开、SSL证书是否有效
2. **内部链接检查** - 检查首页内链是否正常跳转
3. **乱码检查** - 检查所有 Markdown 文件是否包含乱码字符
4. **博客文章检查** - 检查文章总数和最近更新时间
5. **Front Matter 检查** - 检查文章元数据是否完整

---

## 使用方法

### 1. 本地运行

```bash
cd E:\AI\dulizhan\travel-blog
python boundtravel_daily_inspector.py
```

### 2. 查看报告

报告自动生成在：
```
reports/01 每日巡检报告/BoundTravel巡检报告_YYYY-MM-DD.md
```

---

## 定时任务配置

### Windows 任务计划程序

1. 打开「任务计划程序」
2. 创建基本任务
3. 设置：
   - **名称**: BoundTravel 每日巡检
   - **触发器**: 每天 12:00
   - **操作**: 启动程序
     - 程序: `python.exe`
     - 参数: `boundtravel_daily_inspector.py`
     - 起始于: `E:\AI\dulizhan\travel-blog`

### Linux/macOS crontab

```bash
# 每天 12:00 运行
0 12 * * * cd /path/to/travel-blog && python boundtravel_daily_inspector.py >> /var/log/boundtravel_inspector.log 2>&1
```

---

## 排班规则

- **双休周**（本周）: 周一到周五巡检
- **单休周**（下周）: 周一到周六巡检
- 每周日晚间切换周六的勾选状态

---

## 检查结果说明

### 正常状态

```
[OK] 全部检查项通过 - 网站运行正常
```

### 异常状态

发现问题后，报告会显示：
- **[FAIL]** - 严重问题，需要立即处理
- **[WARN]** - 警告问题，建议处理

### 常见问题及解决方案

| 问题 | 解决方案 |
|------|----------|
| 乱码字符 | 运行 `python fix_garbled_precise.py` |
| Front Matter 缺失 | 手动补充缺失的元数据字段 |
| 网站无法访问 | 检查网络或联系托管服务商 |
| SSL证书错误 | 更新或重新配置 SSL 证书 |

---

## 报告示例

```markdown
# BoundTravel 每日巡检报告

**巡检日期**: 2026-05-29
**巡检时间**: 01:13:03
**当前周期**: 【双休周】

## 总体状态

| 状态 | 说明 |
|------|------|
| [OK] 全部正常 | 所有检查项通过 |

## 检查结果

| 检查项 | 状态 | 详情 |
|--------|------|------|
| 站点访问 | OK | Site is accessible |
| SSL证书 | OK | SSL Certificate Valid |
| 乱码检查 | [OK] 无乱码 | 0 个乱码字符 |
| 博客文章 | 15 | - |
```

---

## 相关文件

| 文件 | 说明 |
|------|------|
| `boundtravel_daily_inspector.py` | 巡检主脚本 |
| `boundtravel_inspector.log` | 运行日志 |
| `fix_garbled_precise.py` | 乱码修复工具 |
| `daily_inspection.py` | 增强版巡检脚本 |

---

**最后更新**: 2026-05-29
