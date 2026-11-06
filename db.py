from tools.db_tools import list_curr_table,get_table_data,execute_limit_sql
import json

if __name__ =="__main__":
#@tool包装之后需要通过invoke（）调用
    result = execute_limit_sql.invoke({
        "query": (
            "SELECT category, SUM(total_amount) AS total_sales "
            "FROM orders GROUP BY category ORDER BY total_sales DESC"
        )
    })

    print(json.dumps(result, ensure_ascii=False, indent=2))