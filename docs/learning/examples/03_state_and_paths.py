"""临时 SQLite 与目录边界教学；不操作项目真实状态数据库。"""

import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory


def resolve_inside(root, relative_name):
    """教学边界校验；不声称提供完整操作系统隔离。"""
    base = Path(root).resolve()
    relative = Path(relative_name)
    if relative.is_absolute() or relative.drive or relative.root:
        raise ValueError("仅接受相对路径")
    target = (base / relative).resolve()
    if not target.is_relative_to(base):
        raise ValueError("路径超出允许目录")
    return target


def demonstrate_persistence(db_path):
    connection = sqlite3.connect(db_path)
    try:
        connection.execute(
            "CREATE TABLE messages (id INTEGER PRIMARY KEY, thread_id TEXT, content TEXT)"
        )
        connection.executemany(
            "INSERT INTO messages (thread_id, content) VALUES (?, ?)",
            [("A", "偏好简短回答"), ("B", "偏好详细回答"), ("A", "分析样例数据")],
        )
        connection.commit()
    finally:
        connection.close()

    # 重新建立连接，验证数据来自磁盘，不依赖原连接对象。
    reopened = sqlite3.connect(db_path)
    try:
        histories = {}
        for thread_id in ("A", "B", "C"):
            rows = reopened.execute(
                "SELECT content FROM messages WHERE thread_id = ? ORDER BY id", (thread_id,)
            ).fetchall()
            histories[thread_id] = [row[0] for row in rows]
        assert histories["A"] == ["偏好简短回答", "分析样例数据"]
        assert histories["B"] == ["偏好详细回答"]
        assert histories["C"] == []
        print("重新连接后的历史：", histories)
    finally:
        reopened.close()


def demonstrate_paths(root):
    root.mkdir()
    normal = resolve_inside(root, "reports/demo.md")
    normal.parent.mkdir()
    normal.write_text("# 临时教学报告\n", encoding="utf-8")
    assert normal.is_file()
    print("正常路径已接受：", normal.name)
    for invalid in ("../outside.txt", str(root.parent / "outside.txt")):
        try:
            resolve_inside(root, invalid)
        except ValueError as exc:
            print("已拒绝越界/绝对路径：", exc)
        else:
            raise AssertionError("不合法路径未被拒绝")
    assert not (root.parent / "outside.txt").exists()


def main():
    # TemporaryDirectory 仅清理自己创建的临时目录。
    with TemporaryDirectory(prefix="multiagent-learning-") as temporary:
        base = Path(temporary)
        demonstrate_persistence(base / "lesson.db")
        demonstrate_paths(base / "session_A")
    print("验证通过：历史分开保存，目录边界生效，临时数据已清理。")


if __name__ == "__main__":
    main()
