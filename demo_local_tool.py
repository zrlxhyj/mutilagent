import json

from tools.raglocal_tools import ask_local_rag_base

if __name__ == "__main__":
    result = ask_local_rag_base.invoke({
        "question": "新人优惠券与满额赠券的面额、使用门槛和有效期分别是什么？"
    })

    print(json.dumps(
        result,
        ensure_ascii=False,
        indent=2,
    ))