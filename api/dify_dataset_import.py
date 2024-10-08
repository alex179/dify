#!/usr/bin/env python3
import argparse
import json
import logging
import math
import time
from datetime import date, datetime, timedelta

import pymysql
import requests

# 日志设置
logging.basicConfig(filename='database_import.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# 数据库连接配置
db_config = {
    'host': 'rm-bp15w3i0gnod61710.mysql.rds.aliyuncs.com',
    'user': 'bookstack_usr',
    'password': 'X4aHy48nYsyL',
    'database': 'bookstack',
    'charset': 'utf8mb4'
}

# API端点和授权令牌
api_url = 'https://dai.dhb168.com/v1/datasets/a3476ee2-b5ea-4de4-851a-73d44d152ce0/document/create_by_json'
headers = {
    'Authorization': 'Bearer dataset-44K1dHczm1aeuFi9wnCaMIJo',
    'Content-Type': 'application/json'
}

# 处理的批次大小
batch_size = 10


def process_date_range(start_date, end_date):
    connection = pymysql.connect(**db_config)

    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            current_date = start_date
            while current_date <= end_date:
                logging.info(f"处理日期 {current_date} 的数据")

                # 获取当前日期更新的所有页面
                cursor.execute("""
                    SELECT * FROM pages 
                    WHERE DATE(updated_at) = %s 
                    AND deleted_at IS NULL 
                    AND draft = 0 
                """, (current_date,))
                pages = cursor.fetchall()

                # 获取已经处理的页面ID
                cursor.execute("""
                    SELECT page_id FROM processed_pages 
                    WHERE processed_date = %s
                """, (current_date,))
                processed_pages = {row['page_id'] for row in cursor.fetchall()}

                # 过滤掉已处理的页面
                pages_to_process = [page for page in pages if page['id'] not in processed_pages]

                total_pages = len(pages_to_process)
                total_batches = math.ceil(total_pages / batch_size)

                logging.info(
                    f"日期 {current_date} 的总页面数: {total_pages}, "
                    f"将以 {batch_size} 为批次处理，共 {total_batches} 批次。")

                for batch_num in range(total_batches):
                    offset = batch_num * batch_size
                    batch_pages = pages_to_process[offset:offset + batch_size]
                    processed_batch_ids = []

                    for page in batch_pages:
                        cursor.execute("SELECT slug FROM books WHERE id = %s", (page['book_id'],))
                        book = cursor.fetchone()

                        if book:
                            body = {
                                "name": page['name'],
                                "text": page['text'],
                                "indexing_technique": "high_quality",
                                "process_rule": {
                                    "mode": "automatic"
                                },
                                "job_id": f"job_{datetime.now().strftime('%Y%m%d%H%M%S')}_{page['id']}",
                                "provider": "database_import",
                                "only_main_content": True,
                                "urls": [
                                    f"https://docs.dhb168.com/books/{book['slug']}/page/{page['slug']}"
                                ],
                                "titles": [
                                    page['name']
                                ]
                            }

                            response = requests.post(api_url, headers=headers, data=json.dumps(body))
                            logging.info(
                                f"页面ID: {page['id']}, 状态码: {response.status_code}, 响应: {response.text}")

                            if response.status_code == 200:
                                # 仅在请求成功时才将ID加入已处理列表
                                processed_batch_ids.append(page['id'])

                    # 如果有已处理的ID，则插入到数据库
                    if processed_batch_ids:
                        for page_id in processed_batch_ids:
                            cursor.execute("""
                                INSERT INTO processed_pages (page_id, processed_date)
                                VALUES (%s, %s)
                            """, (page_id, current_date))
                        connection.commit()

                    logging.info(f"批次 {batch_num + 1}/{total_batches} 已处理完成。")
                    time.sleep(1)

                current_date += timedelta(days=1)

    finally:
        connection.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="在指定日期范围内处理数据库记录。")
    parser.add_argument("--start_date", type=str, help="起始日期，格式为 YYYY-MM-DD (默认: 今天)",
                        default=date.today().isoformat())
    parser.add_argument("--end_date", type=str, help="结束日期，格式为 YYYY-MM-DD (默认: 今天)",
                        default=date.today().isoformat())

    args = parser.parse_args()

    start_date = datetime.strptime(args.start_date, "%Y-%m-%d").date()
    end_date = datetime.strptime(args.end_date, "%Y-%m-%d").date()

    if start_date > end_date:
        logging.error("错误: 起始日期不能晚于结束日期。")
        exit(1)

    process_date_range(start_date, end_date)