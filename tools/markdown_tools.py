# - 普通函数 prepare_session_directory()：创建会话目录。
# - Agent 工具 generate_markdown()：保存报告。
import re
from pathlib import Path
from langchain_core.tools import ToolException,tool

from api.monitor import monitor
from api.context import get_session_dir

PROJECT_ROOT=Path(__file__).resolve().parents[1]
OUTPUT_ROOT=PROJECT_ROOT/"output"
# Windows不允许用作普通文件基本名称的保留名称。
RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}

def prepare_session_dir(session_id):
    """创建当前会话的目录，只接受简单的编号"""
    if not isinstance(session_id,str):
        raise ValueError("会话编号必须是字符串")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", session_id):
        raise ValueError(
            "会话编号只能包含字母、数字、下划线和连字符，"
            "长度为1到100"
        )
    OUTPUT_ROOT.mkdir(parents=True,exist_ok=True)
    output_root=OUTPUT_ROOT.resolve()
    directory = (
        output_root / f"session_{session_id}"
    ).resolve()
    # 防止已有目录链接等情况使最终位置跳出output。
    if not directory.is_relative_to(output_root):
        raise ValueError("会话目录不能位于output之外")

    directory.mkdir(parents=True, exist_ok=True)
    return directory
def validate_markdown_filename(filename):

    """只允许简单的Markdown文件名，不允许传目录。"""
    filename = filename.strip()
    if not filename or len(filename)>100:
        raise ToolException("文件名不能为空，且不能超出100")
    # 拦截Windows非法字符、路径分隔符和控制字符。
    if re.search(r'[<>:"/\\|?*\x00-\x1f]', filename):
        raise ToolException(
            "文件名不能包含路径分隔符或非法字符"
        )
    if filename.endswith((" ",".")):
        raise ToolException("文件名不能以空格或句点结尾")
    path=Path(filename)
    if path.is_absolute() or path.name !=filename:
        raise ToolException("只能提供文件名，不能提供路径")

    # 没写扩展名时自动补.md；写了其他扩展名则拒绝。
    if not path.suffix:
        filename += ".md"
    elif path.suffix.lower() != ".md":
        raise ToolException("当前只支持.md文件")
    # CON.md、CON.report.md等也不允许。
    basic_name = filename.split(".", 1)[0].upper()
    if basic_name in RESERVED_NAMES:
        raise ToolException("该文件名是系统保留名称，请换一个")

    return filename
    
@tool
def generate_markdown(content:str,filename):
    """将完整报告内容保存为当前会话的Markdown文件。

    content必须是完整的Markdown正文，不能仅提供摘要或占位文字。
    filename只能是文件名，例如“运营分析.md”，不能包含目录。
    同名文件不会被覆盖，应更换文件名后重试。
    """
    if not content.strip():
        raise ToolException("报告内容不能为空")
    filename=validate_markdown_filename(filename)
    dir=get_session_dir()
    if dir is None:
         raise ToolException("当前任务没有设置输出目录")

    base_dir=Path(dir).resolve()
    output_root=OUTPUT_ROOT.resolve()
    if (
        base_dir == output_root
        or not base_dir.is_relative_to(output_root)
    ):
        raise ToolException("输出目录必须位于output的会话目录内")
    file_path = (base_dir / filename).resolve()
    if not file_path.is_relative_to(base_dir):
        raise ToolException("文件不能保存到当前会话目录之外")
    monitor.report_tool(f"markdown已经生成：{filename}")
    try:
        base_dir.mkdir(parents=True,exist_ok=True)
        # x表示仅创建新文件，已有同名文件时拒绝覆盖。
        with file_path.open(
            mode="x",
            encoding="utf-8",
        ) as file:
            file.write(content)

        size_bytes = file_path.stat().st_size

    except FileExistsError as exc:
        raise ToolException(
            f"文件“{filename}”已存在，请使用其他文件名"
        ) from exc

    except OSError as exc:
        raise ToolException(
            "报告写入失败，请检查目录权限、磁盘空间和文件状态"
        ) from exc
    # 只有真正写入成功后，才上报保存成功。
    monitor._emit(
        "file_created",
        f"Markdown报告已保存：{filename}",
    )
    return {
        "status": "saved",
        "filename": filename,
        "relative_path": file_path.relative_to(
            output_root
        ).as_posix(),
        "size_bytes": size_bytes,
    }


generate_markdown.handle_tool_error = True
