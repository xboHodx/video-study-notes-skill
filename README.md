# video-study-notes-skill  
这是一个可以让ai自动从b站、油管等视频网站下载视频、音频、字幕，分析内容，最终生成一份带截图的高质量笔记的skill。
推荐在linux环境中使用，若需要在windows或者mac环境下使用，让ai自己修改python脚本

## 食用方法
1. 需要的全局环境：ffmpeg、uv、python3
2. clone下来
3. 运行 `./scripts/bootstrap_linux.sh`
4. 参考 `./cookies.example.txt` 写一份Netscape格式的cookies.txt，推荐使用 **Cookie-Editor** 这个浏览器插件一键导出并复制进去
5. 启动 claude code 或者 codex，输入prompt：`video-study-notes <网址链接>`

## 实现细节
- 使用uv来管理python环境
- 使用yt-dlp来下载资源
- 使用faster_whisper来转录音频，自动检测是否有英伟达gpu，以此来加速

## 支持 `uv tool install`
本项目已提供标准 Python 包入口点，可直接通过 `uv tool install` 安装为全局命令。
### 从 GitHub 安装
```bash
uv tool install git+https://github.com/xboHodx/video-study-notes-skill
```
安装后可用命令：
- `video-notes`
- `video-study-notes`（别名）
示例：
```bash
video-notes --help
video-notes check
video-notes install-skill --ai codex
video-notes prepare-audio --help
video-notes extract-keyframes --help
```

`install-skill` 用于把本仓库作为 skill 安装到 AI 客户端目录：
```bash
# codex -> <project>/.agents/skills/video-study-notes
video-notes install-skill --ai codex --project /path/to/your-project
# claude -> <project>/.claude/skills/video-study-notes
video-notes install-skill --ai claude --project /path/to/your-project
# 如果你就在目标项目根目录，可省略 --project
video-notes install-skill --ai codex
```

脚本来源说明（避免混淆）：
- 源码仓库模式：`--source` 指向本仓库时，安装到目标项目的是当前仓库里的脚本与模板。
- wheel 模板模式：未提供有效 `--source` 时，会使用 `video-notes` 包内的 `skill_template` 进行安装。
- 在 wheel 模板模式下，会同时下发 `skill_template/src/video_study_notes` 运行模块，`scripts/*.py` 可直接本地导入执行。
- 若本地导入不可用，`scripts/*.py` 仍会自动回退调用全局 `video-notes` 子命令。

说明：
- 建议在仓库根目录执行该命令，或显式传 `--source <skill目录>`
- Windows 下若无创建符号链接权限，会自动回退为复制安装
- `--ai` 支持部分 agent 名称映射（如 `codex`, `claude`, `gemini`, `cursor-agent`, `kiro-cli` 等）
- 通过 `uv tool install` 安装后，即使本地没有源码目录，也可使用包内自带模板完成安装
- 安装完成后重启 AI 会话，即可让 skill 被重新发现

### 本地开发测试（可编辑安装）
在仓库根目录执行：
```bash
uv tool install --editable . --force
```
