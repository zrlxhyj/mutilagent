"""内存 SQLite 教学数据：验证数量、日期与参数绑定，不连接 MySQL。"""

import sqlite3
from decimal import Decimal


def money(cents):
    return f"{Decimal(cents) / Decimal(100):.2f}"


def main():
    connection = sqlite3.connect(":memory:")
    try:
        # 以整数分保存金额，避免二进制浮点金额误差。
        connection.execute("""
            CREATE TABLE orders (
                category TEXT,
                price_cents INTEGER,
                quantity INTEGER,
                total_cents INTEGER,
                status TEXT,
                created_at TEXT
            )
        """)
        connection.executemany(
            "INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?)",
            [
                ("数码电子", 899900, 1, 899900, "completed", "2026-01-15 10:30:00"),
                ("数码电子", 1049900, 1, 1049900, "completed", "2026-02-20 14:20:00"),
                ("数码电子", 179900, 2, 359800, "completed", "2026-03-10 09:15:00"),
                ("数码电子", 679900, 1, 679900, "completed", "2026-07-01 15:00:00"),
            ],
        )
        total = connection.execute(
            "SELECT SUM(total_cents) FROM orders WHERE category = ? AND status = ?",
            ("数码电子", "completed"),
        ).fetchone()[0]
        first_half = connection.execute(
            """SELECT SUM(total_cents) FROM orders
               WHERE category = ? AND status = ?
                 AND created_at >= ? AND created_at < ?""",
            ("数码电子", "completed", "2026-01-01", "2026-07-01"),
        ).fetchone()[0]
        wrong_total = connection.execute("SELECT SUM(price_cents) FROM orders").fetchone()[0]
        assert total == 2989500
        assert first_half == 2309600
        assert wrong_total == 2809600
        print("全部金额：", money(total))
        print("上半年金额：", money(first_half))
        print("错误地只合计单价：", money(wrong_total))

        unusual_category = "不存在的类别' OR 1=1 --"
        count = connection.execute(
            "SELECT COUNT(*) FROM orders WHERE category = ?", (unusual_category,)
        ).fetchone()[0]
        assert count == 0
        print("特殊文本作为参数值查询，命中行数：", count)
        print("验证通过：日期与数量口径正确，值参数没有变成 SQL 代码。")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
