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
