import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.tools import tool
from mysql.connector import connect
from api.monitor import monitor


#从env中加载到系统变量中
load_dotenv(Path(__file__).resolve().parents[1]/".env")
def get_db_config():
    #获取数据库连接时的基本信息
    return {
        "host":os.getenv("MYSQL_HOST","127.0.0.1"),#去系统变量中拿到，，后面是说没有的话就用默认值
        "port":os.getenv("MYSQL_PORT"),
        "user": os.getenv("MYSQL_USER"),
        "password": os.getenv("MYSQL_PASSWORD"),
        "database": os.getenv("MYSQL_DATABASE"),
        "connection_timeout":10,
        "use_pure":True,
    }
@tool
def list_curr_table():
    """列出当前数据库的名称，方便后面调用"""
    monitor.report_tool("数据库表名查询：list_curr_table")

    #建立连接
    with connect(**get_db_config()) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            rows=cursor.fetchall()
    # 数据库返回 [('orders',)]，转换为 ['orders']。
    return [row[0] for row in rows]

@tool
def get_table_data(table_name,limit:int =5):
    """获得表中的数据"""
    if table_name!="orders":
        raise ValueError("当前只允许查询order表")
    if not 1<=limit<100:
        raise ValueError("limit得到1到100之间")
    monitor.report_tool(f"数据库信息预览：{table_name}")
    with connect(**get_db_config()) as connection:
        with connection.cursor() as cursor:
            # 先读取字段结构。
            cursor.execute("SHOW COLUMNS FROM orders")
            schema=[
                {
                    "name":row[0],
                    "type":row[1],
                }
                for row in cursor.fetchall()
            ]
            # %s 是参数占位符，参数值由驱动处理。
            cursor.execute(
                "SELECT * FROM orders ORDER BY id LIMIT %s",
                (limit,),
            )
            # description 保存当前查询结果的列信息。
            columns = [column[0] for column in cursor.description]

            # 金额、日期等统一转为文本，方便当前练习查看。
            rows = [
                [str(value) if value is not None else None for value in row]
                for row in cursor.fetchall()
            ]

    return {
        "table": table_name,
        "schema": schema,
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
    }

# 允许执行的查询。只有这里列出的 SQL 才能执行。
ALLOWED_QUERIES = {
    "SELECT COUNT(*) AS order_count FROM orders",
    (
        "SELECT category, SUM(total_amount) AS total_sales "
        "FROM orders GROUP BY category ORDER BY total_sales DESC"
    ),
}


def normalize_sql(sql: str) -> str:
    """统一大小写和空白，允许末尾有一个分号。"""
    return " ".join(sql.strip().removesuffix(";").split()).lower()
@tool
def execute_limit_sql(query):
    """执行受限的订单统计查询。

    当前只支持：
    1. SELECT COUNT(*) AS order_count FROM orders
    2. SELECT category, SUM(total_amount) AS total_sales FROM orders
       GROUP BY category ORDER BY total_sales DESC
    """
    # 匹配成功后，执行白名单中的原始语句。
    allowed={
        normalize_sql(sql):sql
        for sql in ALLOWED_QUERIES
    }
    sql=allowed.get(normalize_sql(query))
    if sql is None:
        raise ValueError("当前只允许查询订单总数或各品类销售额")
    monitor.report_tool("数据库统计：execute_sql_query")
    with connect(**get_db_config()) as connection:
        # 数据库层也使用只读事务。
        connection.start_transaction(readonly=True)
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql)
                columns = [
                    column[0]
                    for column in cursor.description
                ]

                rows = [
                    [
                        str(value) if value is not None else None
                        for value in row
                    ]
                    for row in cursor.fetchall()
                ]
        finally:
            connection.rollback()
    return {
        "sql": sql,
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
    }