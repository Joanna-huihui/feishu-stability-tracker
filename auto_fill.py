#!/usr/bin/env python3
"""
稳定性测试每日跟踪表 — GitHub Actions 自动补齐脚本
每天北京时间 08:00 自动执行，通过飞书 API（tenant_access_token）写入数据。
不依赖 lark-cli，不依赖沙盒环境，纯 Python + requests 实现。
"""
import requests
import json
import datetime
import os
import sys
import time

# ============ 配置 ============
APP_ID = os.environ.get("FEISHU_APP_ID", "")
APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "")
SPREADSHEET_TOKEN = "B4U8sm7GEhhFU5tMIrEcnPbJnZg"
SHEET_ID = "15bd2e"
START_DATE = datetime.date(2026, 7, 14)  # 追踪起始日期

TEST_ITEMS = [
    "建图", "清扫", "定位", "重定位", "配网&连接", "OTA",
    "避障", "地毯", "污渍", "颗粒物", "视频管家", "即时清洁",
    "ERP", "YIKO唤醒转向", "可通过性", "开机速度",
    "全嵌基站配对&重连", "全嵌舱门"
]

BG_COLORS = [
    "#E3F2FD", "#E8F5E9", "#FFF3E0", "#F3E5F5", "#FFFDE7",
    "#FBE9E7", "#E0F7FA", "#F1F8E9", "#FCE4EC", "#E8EAF6",
]

BASE_URL = "https://open.feishu.cn/open-apis"

def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

def fmt_date(d):
    return f"{d.year}/{d.month}/{d.day}"

# ============ 飞书 API ============

_token_cache = {"token": None, "expire": 0}

def get_tenant_access_token():
    """获取 tenant_access_token（应用身份）"""
    if _token_cache["token"] and time.time() < _token_cache["expire"]:
        return _token_cache["token"]

    url = f"{BASE_URL}/auth/v3/tenant_access_token/internal"
    resp = requests.post(url, json={
        "app_id": APP_ID,
        "app_secret": APP_SECRET
    }, timeout=30)

    data = resp.json()
    if data.get("code") != 0:
        log(f"❌ 获取token失败: {data}")
        sys.exit(1)

    token = data["tenant_access_token"]
    _token_cache["token"] = token
    _token_cache["expire"] = time.time() + data.get("expire", 7200) - 300
    log("✅ 获取 tenant_access_token 成功")
    return token

def api_headers():
    return {
        "Authorization": f"Bearer {get_tenant_access_token()}",
        "Content-Type": "application/json"
    }

def sheet_read(range_str):
    """读取表格数据"""
    url = f"{BASE_URL}/sheets/v2/spreadsheets/{SPREADSHEET_TOKEN}/values/{range_str}"
    params = {"valueRenderOption": "ToString"}
    resp = requests.get(url, headers=api_headers(), params=params, timeout=30)
    data = resp.json()
    if data.get("code") != 0:
        log(f"❌ 读取失败: {data.get('msg')}")
        return None
    return data["data"]["valueRange"]["values"]

def sheet_write(range_str, values):
    """写入表格数据"""
    url = f"{BASE_URL}/sheets/v2/spreadsheets/{SPREADSHEET_TOKEN}/values"
    body = {
        "valueRange": {
            "range": range_str,
            "values": values
        }
    }
    resp = requests.put(url, headers=api_headers(), json=body, timeout=30)
    data = resp.json()
    if data.get("code") != 0:
        log(f"❌ 写入失败: {data.get('msg')}")
        return None
    return data["data"]

def sheet_set_style(range_str, back_color):
    """设置单元格底色"""
    url = f"{BASE_URL}/sheets/v2/spreadsheets/{SPREADSHEET_TOKEN}/style"
    body = {
        "appendStyle": {
            "style": {"backColor": back_color},
            "range": range_str
        }
    }
    resp = requests.put(url, headers=api_headers(), json=body, timeout=30)
    data = resp.json()
    return data.get("code") == 0

# ============ 业务逻辑 ============

def get_existing_dates():
    """获取表格中所有已有日期和最后一行行号，同时修复序列号格式的日期"""
    values = sheet_read(f"{SHEET_ID}!A4:A500")
    if not values:
        return set(), 0

    dates = set()
    last_row = 0
    serial_fixes = {}  # row_num -> date_str

    for i, row in enumerate(values, 4):
        if row and row[0] is not None and str(row[0]).strip() != "":
            val = str(row[0]).strip()
            # 检测并修复 Excel 序列号格式
            if val.isdigit() and len(val) >= 5:
                try:
                    d = datetime.date(1899, 12, 30) + datetime.timedelta(days=int(val))
                    date_str = fmt_date(d)
                    serial_fixes[i] = date_str
                    val = date_str
                except:
                    pass
            dates.add(val)
            last_row = i

    # 批量修复序列号格式的日期
    if serial_fixes:
        log(f"发现 {len(serial_fixes)} 行序列号格式日期，正在修复...")
        for row_num, date_str in sorted(serial_fixes.items()):
            sheet_write(f"{SHEET_ID}!A{row_num}:A{row_num}", [[date_str]])
        log(f"序列号修复完成")

    return dates, last_row

def find_missing_dates(existing_dates):
    """找出从 START_DATE 到今天所有缺失的日期"""
    today = datetime.date.today()
    missing = []
    d = START_DATE
    while d <= today:
        if fmt_date(d) not in existing_dates:
            missing.append(d)
        d += datetime.timedelta(days=1)
    return missing

def append_date_block(target_date, start_row):
    """追加一个日期的18行数据，返回结束行号"""
    date_str = fmt_date(target_date)
    end_row = start_row + 17

    rows = []
    for idx, item in enumerate(TEST_ITEMS, 1):
        rows.append([date_str, idx, item] + [""] * 11)

    write_range = f"{SHEET_ID}!A{start_row}:N{end_row}"
    result = sheet_write(write_range, rows)

    if not result:
        log(f"  ❌ 写入失败: {date_str}")
        return start_row

    log(f"  ✅ 写入成功: {date_str}, Row {start_row}~{end_row}, 18行")

    # 设置底色
    existing_dates, _ = get_existing_dates()
    color_idx = (len(existing_dates) - 1) % len(BG_COLORS)
    if color_idx < 0:
        color_idx = 0
    bg_color = BG_COLORS[color_idx]
    if sheet_set_style(write_range, bg_color):
        log(f"  🎨 底色: {bg_color}")
    else:
        log(f"  ⚠️ 底色设置失败")

    return end_row

def main():
    log("=" * 50)
    log("稳定性测试数据自动补齐（GitHub Actions）")
    today = datetime.date.today()
    log(f"今天: {fmt_date(today)}")

    if not APP_ID or not APP_SECRET:
        log("❌ 未配置 FEISHU_APP_ID / FEISHU_APP_SECRET 环境变量")
        sys.exit(1)

    # Step 1: 获取已有日期
    existing_dates, last_row = get_existing_dates()
    log(f"表格已有日期: {sorted(existing_dates)}")
    log(f"当前最后一行: {last_row}")

    # Step 2: 找缺失日期
    missing = find_missing_dates(existing_dates)

    if not missing:
        log("✅ 所有日期数据完整，无需补齐")
        log("=" * 50)
        return

    log(f"缺失日期: {[fmt_date(d) for d in missing]}")
    log(f"需要补齐 {len(missing)} 个日期，共 {len(missing) * 18} 行")

    # Step 3: 逐个补齐
    current_row = last_row + 1
    for d in missing:
        log(f"补齐 {fmt_date(d)}:")
        current_row = append_date_block(d, current_row) + 1

    log(f"补齐完成! 共追加 {len(missing) * 18} 行")
    log("=" * 50)

if __name__ == "__main__":
    main()
