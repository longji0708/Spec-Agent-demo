# 图片存放说明

本目录用于统一存放 README 和项目展示需要的图片。

## 已生成图片

| 文件 | 说明 | 状态 |
| --- | --- | --- |
| `architecture.png` | 中文版系统架构图 | 已生成 |
| `workflow.png` | 从想法到文档的核心流程闭环 | 已生成 |
| `output-preview.png` | 规格定义文档输出预览示例 | 已生成 |

## 建议补充的真实截图

以下截图需要你在本地实际运行后手动补充，图片命名建议保持一致。

| 文件名 | 截图内容 | 建议尺寸 | 说明 |
| --- | --- | --- | --- |
| `cli-demo.png` | 运行 `--demo` 或真实模型的终端交互 | 宽 900-1400px | 建议展示一轮包含工具调用的完整问答 |
| `cli-help.png` | `spec-agent --help` 输出 | 宽 800-1200px | 让访问者快速了解 CLI 参数 |
| `langsmith-trace.png` | LangSmith Trace 面板中的 Graph 调用链 | 宽 1200-1600px | 展示 Agent 节点和 ToolNode 的路由过程 |
| `specification-sample.png` | 最终生成的 `specification.md` 或 `specification.html` | 宽 1000-1400px | 建议同时截取一段需求内容 |
| `ci-result.png` | GitHub Actions 测试通过页面 | 宽 1000-1400px | 证明测试、lint、类型检查正常 |

## 截图建议

1. 不要在截图中暴露真实 API Key、LangSmith Key 或敏感项目信息。
2. 优先使用浅色终端主题，保证 README 中文字清晰。
3. Windows 终端如果出现中文乱码，可先设置 `PYTHONIOENCODING=utf-8`：

   ```powershell
   $env:PYTHONIOENCODING = "utf-8"
   python -X utf8 -m spec_agent --demo --prompt "你的演示输入"
   ```

4. 截图命名使用小写英文和短横线，避免空格。
5. 图片尽量控制在 1MB 以内，超出时先压缩再提交。

## 在 README 中引用

相对路径引用示例：

```markdown
![CLI Demo](images/cli-demo.png)
```
