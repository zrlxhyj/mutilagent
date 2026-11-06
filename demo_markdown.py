import json
from uuid import uuid4

from api.context import (
    reset_session_dir,
    reset_thread_id,
    set_session_dir,
    set_thread_id,
)
from tools.markdown_tools import (
    generate_markdown,
    prepare_session_dir,
)


def main():
    # 每次使用新编号，避免重复测试产生同名文件冲突。
    session_id = f"markdown-test-{uuid4().hex[:8]}"
    directory = prepare_session_dir(session_id)

    thread_token = set_thread_id(session_id)
    directory_token = set_session_dir(str(directory))

    content = """# Markdown保存测试

## 测试目标

验证当前会话可以保存中文Markdown文件。

## 测试内容

- 中文显示正常。
- 文件保存在当前会话目录。
- 不调用真实模型。
"""

    try:
        result = generate_markdown.invoke({
            "content": content,
            "filename": "保存测试.md",
        })

        print(json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        ))

        # 工具失败时可能返回错误字符串，不是成功字典。
        if not isinstance(result, dict):
            raise RuntimeError(f"保存失败：{result}")

        saved_file = directory / result["filename"]

        assert saved_file.is_file(), "文件没有实际生成"
        assert (
            saved_file.read_text(encoding="utf-8") == content
        ), "保存内容与输入不一致"

        print("验证通过，实际保存位置：")
        print(saved_file)

    finally:
        # 按各自对应的token恢复上下文。
        reset_session_dir(directory_token)
        reset_thread_id(thread_token)


if __name__ == "__main__":
    main()