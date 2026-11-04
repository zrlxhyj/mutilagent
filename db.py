import os
from pathlib import Path

from dotenv import load_dotenv
from mysql.connector import connect

# 读取项目根目录的 .env。
load_dotenv(Path(__file__).resolve().parent / ".env")

print("开始执行 db.py", __file__, flush=True)
def main():
    # 建立连接；离开 with 后自动关闭。
    with connect(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE"),
        connection_timeout=10,
        use_pure=True,
    ) as connection:
        print("MySQL 连接成功")

        # cursor 负责执行 SQL、读取结果。
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM orders")
            count = cursor.fetchone()[0]
            print(f"订单数量：{count}")

            cursor.execute("""
                SELECT category, SUM(total_amount) AS total_sales
                FROM orders
                GROUP BY category
                ORDER BY total_sales DESC
            """)

            for category, total_sales in cursor.fetchall():
                print(f"{category}：{total_sales}")


if __name__ == "__main__":
    main()