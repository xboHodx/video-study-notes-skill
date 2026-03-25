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
video-notes prepare-audio --help
video-notes extract-keyframes --help
```

### 本地开发测试（可编辑安装）
在仓库根目录执行：
```bash
uv tool install --editable . --force
```
