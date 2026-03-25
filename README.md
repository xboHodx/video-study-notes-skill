# video-study-notes-skill
这是一个可以让ai自动从b站、油管等视频网站下载视频、音频、字幕，分析内容，最终生成一份带截图的高质量笔记的skill。

推荐在linux环境中使用，若需要在windows或者mac环境下使用，让ai自己修改python脚本

## 1. Skill 使用（推荐）
前置依赖：
- `ffmpeg`
- `uv`
- `python3`

准备步骤：
1. 克隆本仓库
2. 运行 `./scripts/bootstrap_linux.sh`
3. 参考 `./cookies.example.txt` 写一份 Netscape 格式 `cookies.txt`（站点需要登录时使用），推荐使用 **Cookie-Editor** 这个浏览器插件一键导出并复制进去
4. 在 Claude Code 或 Codex 中触发 skills：`video-study-notes <视频链接>`

## 2. CLI 安装与命令
本项目支持 `uv tool install`，会安装全局命令：
- `video-notes`
- `video-study-notes`（别名）
安装：
```bash
uv tool install git+https://github.com/xboHodx/video-study-notes-skill
```
快速查看：
```bash
video-notes --help
video-notes check
video-notes prepare-audio --help
video-notes extract-keyframes --help
video-notes install-skill --help
```

## 3. install-skill：安装到 AI 项目目录
`install-skill` 用于把 skill 文件安装到目标项目的 AI 技能目录。
示例：
```bash
# codex -> <project>/.agents/skills/video-study-notes
video-notes install-skill --ai codex --project /path/to/project
# claude -> <project>/.claude/skills/video-study-notes
video-notes install-skill --ai claude --project /path/to/project
# 当前目录就是目标项目时，可省略 --project
video-notes install-skill --ai codex
```
常用参数：
- `--ai`：目标 AI（如 `codex`、`claude`、`gemini`、`cursor-agent`、`kiro-cli`）
- `--project`：目标项目根目录
- `--source`：显式指定 skill 源目录（需包含 `SKILL.md`）
- `--mode symlink|copy`：安装方式（默认 `symlink`）
- `--force`：覆盖已存在目标

## 4. 两种脚本来源模式
- 源码仓库模式：
  - 当 `--source` 指向本仓库时，安装的是仓库内当前脚本与模板。
- wheel 模板模式：
  - 未提供有效 `--source` 时，使用包内 `skill_template`。
  - 会同时下发 `skill_template/src/video_study_notes` 运行模块，`scripts/*.py` 可本地导入执行。
  - 若本地导入不可用，`scripts/*.py` 会回退调用全局 `video-notes` 子命令。

## 5. 注意事项
- 建议在仓库根目录执行 `install-skill`，或显式传 `--source <skill目录>`。
- Windows 下如果没有创建符号链接权限，会自动回退为 `copy`。
- 安装后请重启 AI 会话，确保新 skill 被重新发现。

## 6. 本地开发（可编辑安装）
```bash
uv tool install --editable . --force
```
