# 11：文件上传、读取、生成与路径

[上一章](10-information-sources.md) · [目录](README.md) · [下一章](12-setup-debug.md)

## 1. 文件经过哪些位置

```text
浏览器/接口上传
→ updated/session_ID/文件
→ run_deep_agent 复制
→ output/session_ID/文件
→ read_file_content 提取文字
→ 模型阅读工具结果
→ generate_markdown 写报告
→ 可选 PDF 转换
→ 文件列表/下载接口
```

上传文件不是自动解析，解析文本不是自动验证事实，模型声称生成文件也不是文件存在证明。每一阶段都需要对应实际操作。

## 2. 读取工具的能力边界

| 格式 | 当前读取方式 | 不能默认获得的内容 |
|---|---|---|
| Markdown / TXT | UTF-8 文本读取 | 自动业务分析 |
| DOCX | doc.paragraphs | 表格、文本框等全部结构 |
| PDF | pypdf extract_text | 扫描图像 OCR |
| XLSX / XLS | pandas.read_excel 后 head 与 describe | 全部记录逐条分析、多工作表完整解析 |
| 其他 | 尝试 UTF-8 文本 | 图片理解或任意二进制解析 |

`pandas.read_excel` 不代表 `.xls` 所需引擎一定已经安装；要根据文件格式和依赖确认。数值 describe 的统计也不等于按业务口径计算销售额。

`instruction` 参数目前没有驱动不同提取算法。它只是被记录进监控信息，不能承诺“传统计指令就会执行统计”。

## 3. Markdown 工具做了什么

[markdown_tools.py](../../tools/markdown_tools.py) 接收 content、filename 和 path。检查扩展名，读取上下文目录，合成路径，经 resolve_path 处理，创建父目录，再 write_text。

报告内容主要由模型产生；工具负责落盘。文件写入成功证明内容已保存，不证明分析结论正确。

当前同名路径会被覆盖，默认没有版本号。监控上报包含完整写入内容，也可能使日志变大。改进时可上报字数、文件名和内容摘要，而不是所有正文。

## 4. PDF 实际使用 Word

[pdf_tools.py](../../tools/pdf_tools.py) 调用 [word_converter.py](../../utils/word_converter.py)：Markdown 转 HTML，写临时 HTML，通过 Word COM 打开，再导出 PDF，最后清理 Word 与临时文件。

所以实际链路是 Markdown → HTML → Word → PDF。安装了 WeasyPrint 不会让这段代码自动改用 WeasyPrint。

Word COM 依赖 Windows 和可用的 Microsoft Word 环境，仅安装 pywin32 不等于具备 Word。模块导入失败被 pass 后，后续可能表现为未定义名字等错误，而不是友好的缺依赖信息。

共享同名临时文件、多个 Word 操作并发、输出目录不存在等也应通过实际测试验证。

## 5. resolve_path 是路径整理器

[path_utils.py](../../utils/path_utils.py) 清理 `/workspace`、`/mnt/data` 等前缀，处理 output/session 名重复，并拼接相对路径。

但它保留会话外的部分绝对路径；包含 updated/ 的路径可能相对进程当前目录解释；普通相对路径也没有统一拒绝 `..`。因此不能把它当成严格的文件隔离器。

文件头还有一个同名的简短定义，后续定义覆盖前者。实际调用使用后面的完整函数，这是 Python 名字绑定规则，不是两个函数轮流执行。

## 6. 路径边界应该怎样验证

教学代码：

```python
def resolve_inside(root, relative_name):
    base = Path(root).resolve()
    relative = Path(relative_name)
    if relative.is_absolute() or relative.drive or relative.root:
        raise ValueError("仅接受相对路径")
    target = (base / relative).resolve()
    if not target.is_relative_to(base):
        raise ValueError("路径超出允许目录")
    return target
```

这是更明确的目录边界示例，尚未替换项目函数。实验 03 会实际演示正常路径和越界路径。

它仍不是完整的操作系统隔离：恶意并发修改符号链接、用户身份校验、文件大小、允许扩展名、覆盖策略等需要分别设计。不要把字符串前缀检查当成目录关系检查，例如 `output-other` 可能同样以 `output` 开头。

## 7. 上传与下载的边界不同

上传接口把客户端提供的 thread_id 和 filename 拼进路径，当前没有完整的文件名、ID、大小与归属校验。

下载接口检查解析后路径是否处于整个 output 下，这可以阻止部分目录外访问，但不是“只能下载当前用户自己的会话文件”。静态 `/output` 挂载也需要考虑同样的访问权限。

文件列表默认递归列出整个 output。前端把当前会话排在前面是展示排序，不是权限隔离。

## 8. URL 编码与路径不是一回事

当前页面创建下载按钮时对路径调用 encodeURIComponent，downloadFile 内部又调用一次，存在双重编码的代码路径。后端通常只解析一层 URL 编码，可能收到仍带 `%3A` 等字符的路径。

可用浏览器 Network 对比请求参数与文件列表原始 path 来验证。改进方向是约定路径在一个边界只编码一次，而不是遇到错误就反复 encode/decode。

## 9. 自测

1. 为什么扫描 PDF 可能提取不到文字？
2. Markdown 写成功能证明模型使用了正确数据吗？
3. 下载只限制 output 是否就实现用户隔离？
4. 安装 WeasyPrint 能让当前 PDF 工具直接跨平台吗？
