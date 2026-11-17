---
name: video-subtitle
description: |
  生成视频字幕/转录文字。当用户提到"字幕"、"转录"、"transcribe"、
  "subtitle"、"caption"、"语音识别"、"提取视频文字"、"生成SRT"等关键词时触发。
  也适用于用户想从本地视频文件中提取语音并转为文字的场景。
  支持生成纯文本(.txt)和标准SRT字幕(.srt)格式。
  确保在运行前检查环境并自动安装 Whisper 依赖。
---

# Video Subtitle Generator

为本地视频文件生成字幕/转录文本。输出标准 SRT 格式字幕文件和纯文本文件。

## 环境检查与准备

### 1. 检查虚拟环境

虚拟环境路径固定为 `~/.whisper-venv`。

```bash
if [ -d "$HOME/.whisper-venv" ]; then
  echo "venv exists"
else
  echo "venv missing"
fi
```

### 2. 检查 Python 版本

需要 Python 3.10-3.13（3.14 不兼容 numba）。查找顺序：
1. `python3.10`
2. `python3.11`
3. `python3.12`
4. `python3.13`
5. 回退到 `python3`

如果找不到可用 Python，提示用户安装 Python 3.10+。

### 3. 自动安装（环境不存在时）

如果 `~/.whisper-venv` 不存在：

```bash
# 找到合适的 Python
PYTHON_BIN=$(find_python)

# 创建虚拟环境并安装
$PYTHON_BIN -m venv ~/.whisper-venv
source ~/.whisper-venv/bin/activate
pip install openai-whisper
```

**注意**：如果系统有代理限制或 SSL 证书问题，安装时可能需要代理。先尝试直接安装，失败后再询问用户是否需要代理。

### 4. 检查模型文件

模型存放路径：`~/.cache/whisper/`

检查用户指定的模型（或默认 `medium`）是否存在：

```bash
ls ~/.cache/whisper/${MODEL}.pt
```

如果模型不存在，告知用户需要下载并提供命令：

```bash
mkdir -p ~/.cache/whisper
curl -L -o ~/.cache/whisper/medium.pt \
  "https://openaipublic.azureedge.net/main/whisper/models/345ae4da62f9b3d59415adc60127b97c714f32e89e936602e85993674d08dcb1/medium.pt"
```

可用模型列表：

| 模型 | 大小 | 准确度 | 适用场景 |
|------|------|--------|----------|
| tiny | 75MB | 低 | 快速测试 |
| base | 150MB | 一般 | 草稿 |
| small | 483MB | 较好 | 日常 |
| medium | 1.5GB | 高 | **推荐** |
| large-v3 | 3GB | 最高 | 极高要求 |

## 转录流程

### 1. 解析用户输入

从用户消息中提取：
- **视频文件路径**：必需。支持绝对路径和相对路径。如果找不到文件，尝试在当前目录和 `~` 下搜索。
- **语言**：可选。默认自动检测。常用：`zh`（中文）、`en`（英文）、`ja`（日文）等。
- **模型**：可选。默认 `medium`。
- **输出格式**：
  - `srt`（默认）- 标准 SRT 字幕文件
  - `txt` - 纯文本，无时间轴
  - `both` - 同时生成 SRT 和 TXT

### 2. 执行转录

激活虚拟环境后运行 whisper：

```bash
source ~/.whisper-venv/bin/activate
whisper "video.mp4" \
  --model medium \
  --language en \
  --output_format srt
```

生成多种格式时，分别执行：

```bash
# 先生成 SRT
whisper "$VIDEO" --model $MODEL --language $LANG --output_format srt

# 再生成 TXT
whisper "$VIDEO" --model $MODEL --language $LANG --output_format txt
```

> Whisper 会在视频同目录下输出文件，如 `video.srt`、`video.txt`。

### 3. 处理常见问题

**SSL 证书错误**：
如果模型下载时出现 SSL 错误，提示用户手动下载或检查代理设置。

**模型下载慢**：
建议使用断点续传：
```bash
curl -L -C - -o ~/.cache/whisper/medium.pt <url>
```

**FP16 警告**：
CPU 运行时会提示 `FP16 is not supported on CPU; using FP32 instead`，这是正常现象，忽略即可。

## 输出

转录完成后，向用户汇报：
1. 生成的文件路径
2. 文件格式
3. 字幕条数（如果是 SRT）

示例汇报：
> 字幕生成完成！
> - `video.srt` - 标准 SRT 字幕，13 条
> - `video.txt` - 纯文本转录

## 完整示例

**用户**：给这个视频生成字幕 `/path/to/video.mp4`，英文的

**执行**：
```bash
# 检查环境
source ~/.whisper-venv/bin/activate

# 生成 SRT
whisper "/path/to/video.mp4" --model medium --language en --output_format srt

# 生成 TXT
whisper "/path/to/video.mp4" --model medium --language en --output_format txt
```

**输出**：`/path/to/video.srt`、`/path/to/video.txt`
