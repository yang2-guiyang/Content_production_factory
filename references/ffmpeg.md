# FFmpeg 视频剪辑能力手册

对标剪映功能体系，说明 FFmpeg 能做什么、不能做什么、怎么做。FFmpeg 直接使用 CLI，无需 Python 封装。

> **安装与检查**：首次使用前运行 `ffmpeg -version`。未安装则执行 `winget install ffmpeg`，安装后重启终端。

---

## 1. 信息查看

在动手之前看清视频参数，知道该用什么编码和参数。

```powershell
# 完整 JSON 元信息
ffprobe -v quiet -print_format json -show_format -show_streams "video.mp4"

# 关键信息摘要
ffprobe -v error -show_entries format=duration,size,bit_rate:stream=codec_name,width,height,r_frame_rate -of default=noprint_wrappers=1 "video.mp4"
```

---

## 2. 剪辑

### 2.1 分割 / 截取

```powershell
# 按时间截取（00:01:30 到 00:03:00），无损
ffmpeg -i "input.mp4" -ss 00:01:30 -to 00:03:00 -c copy "output.mp4"

# 按秒数截取（从第 10 秒开始，取 20 秒），无损
ffmpeg -i "input.mp4" -ss 10 -t 20 -c copy "output.mp4"

# -ss 放在 -i 前面：不解码直接 seek（更快，但可能不精确到帧）
ffmpeg -ss 10 -i "input.mp4" -to 30 -c copy "output.mp4"

# -ss 放在 -i 后面：解码后精确定位（慢但精确）
ffmpeg -i "input.mp4" -ss 00:01:30.500 -to 00:03:00.000 -c copy "output.mp4"
```

### 2.2 拼接 / 合并

```powershell
# 无损拼接（要求编码、分辨率、帧率完全一致）
# 先创建 files.txt：
#   file 'C:/path/to/part1.mp4'
#   file 'C:/path/to/part2.mp4'
#   file 'C:/path/to/part3.mp4'
ffmpeg -f concat -safe 0 -i "files.txt" -c copy "output.mp4"

# 参数不一致的视频拼接（先统一转码再 concat）
# 第一步：统一转中间格式
ffmpeg -i "clip1.mp4" -vf "scale=1920:1080,fps=30" -c:v libx264 -crf 18 -c:a aac -b:a 192k "tmp1.mp4"
ffmpeg -i "clip2.mp4" -vf "scale=1920:1080,fps=30" -c:v libx264 -crf 18 -c:a aac -b:a 192k "tmp2.mp4"
# 第二步：拼接
ffmpeg -f concat -safe 0 -i "files.txt" -c copy "output.mp4"
```

### 2.3 倒放

```powershell
# 视频倒放（需重编码）
ffmpeg -i "input.mp4" -vf "reverse" -af "areverse" -c:v libx264 -crf 18 "output.mp4"

# 仅视频倒放
ffmpeg -i "input.mp4" -vf "reverse" -c:v libx264 -crf 18 -c:a copy "output.mp4"
```

### 2.4 定格 / 冻结帧

```powershell
# 第 5 秒处定格 3 秒（画面停在第 5 秒，音频继续或静音）
ffmpeg -i "input.mp4" \
  -filter_complex "[0:v]trim=0:5,setpts=PTS-STARTPTS[v1];[0:v]trim=5:5.1,setpts=PTS-STARTPTS,loop=90:1:0,trim=0:3,setpts=PTS-STARTPTS[v2];[0:v]trim=5:999,setpts=PTS-STARTPTS[v3];[v1][v2][v3]concat=n=3:v=1:a=0[v]" \
  -map "[v]" -c:v libx264 -crf 18 "output.mp4"
```

### 2.5 删除中间片段

```powershell
# 删除 10s-20s 的片段，保留 0-10s 和 20s-结束
ffmpeg -i "input.mp4" \
  -filter_complex "[0:v]trim=0:10,setpts=PTS-STARTPTS[v1];[0:v]trim=20:99999,setpts=PTS-STARTPTS[v2];[v1][v2]concat=n=2:v=1:a=0[v];[0:a]atrim=0:10,asetpts=PTS-STARTPTS[a1];[0:a]atrim=20:99999,asetpts=PTS-STARTPTS[a2];[a1][a2]concat=n=2:v=0:a=1[a]" \
  -map "[v]" -map "[a]" -c:v libx264 -crf 18 -c:a aac -b:a 192k "output.mp4"
```

---

## 3. 画面

### 3.1 缩放

```powershell
# 指定宽度，高度自动等比
ffmpeg -i "input.mp4" -vf "scale=1920:-2" -c:v libx264 -crf 18 -c:a copy "output.mp4"

# 指定高度，宽度自动等比
ffmpeg -i "input.mp4" -vf "scale=-2:1080" -c:v libx264 -crf 18 -c:a copy "output.mp4"

# 强制固定尺寸（会变形）
ffmpeg -i "input.mp4" -vf "scale=1920:1080" -c:v libx264 -crf 18 "output.mp4"

# 等比缩放 + 黑边填充到目标尺寸（不变形，如 9:16 竖屏适配）
ffmpeg -i "input.mp4" \
  -vf "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black" \
  -c:v libx264 -crf 18 "output.mp4"
```

### 3.2 裁切

```powershell
# crop=输出宽:输出高:左上角x:左上角y
ffmpeg -i "input.mp4" -vf "crop=1080:1080:420:0" -c:v libx264 -crf 18 "output.mp4"

# 居中裁切（自动计算偏移）
ffmpeg -i "input.mp4" -vf "crop=1080:1080" -c:v libx264 -crf 18 "output.mp4"

# 裁切后缩放
ffmpeg -i "input.mp4" -vf "crop=1920:800:0:140,scale=1920:1080" -c:v libx264 -crf 18 "output.mp4"
```

### 3.3 旋转 / 翻转

```powershell
# 顺时针 90°
ffmpeg -i "input.mp4" -vf "transpose=1" -c:v libx264 -crf 18 "output.mp4"

# 逆时针 90°
ffmpeg -i "input.mp4" -vf "transpose=2" -c:v libx264 -crf 18 "output.mp4"

# 水平翻转（镜像）
ffmpeg -i "input.mp4" -vf "hflip" -c:v libx264 -crf 18 "output.mp4"

# 垂直翻转
ffmpeg -i "input.mp4" -vf "vflip" -c:v libx264 -crf 18 "output.mp4"

# 任意角度旋转（弧度制，45° = PI/4）
ffmpeg -i "input.mp4" -vf "rotate=45*PI/180:fillcolor=black" -c:v libx264 -crf 18 "output.mp4"
```

### 3.4 比例转换（横屏 ↔ 竖屏）

```powershell
# 16:9 横屏 → 9:16 竖屏（居中裁切）
ffmpeg -i "16_9.mp4" -vf "crop=ih*9/16:ih,scale=1080:1920" -c:v libx264 -crf 18 "9_16.mp4"

# 16:9 横屏 → 9:16 竖屏（等比缩放 + 模糊背景填充）
ffmpeg -i "16_9.mp4" \
  -filter_complex "[0:v]split=2[fg][bg];[bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=30[blur];[fg]scale=1080:1920:force_original_aspect_ratio=decrease[fg_scaled];[blur][fg_scaled]overlay=(W-w)/2:(H-h)/2" \
  -c:v libx264 -crf 18 "9_16.mp4"

# 9:16 竖屏 → 16:9 横屏（等比缩放 + 模糊背景填充）
ffmpeg -i "9_16.mp4" \
  -filter_complex "[0:v]split=2[fg][bg];[bg]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,boxblur=30[blur];[fg]scale=1920:1080:force_original_aspect_ratio=decrease[fg_scaled];[blur][fg_scaled]overlay=(W-w)/2:(H-h)/2" \
  -c:v libx264 -crf 18 "16_9.mp4"
```

---

## 4. 变速

### 4.1 匀速变速

```powershell
# 2 倍速（视频 + 音频同步）
ffmpeg -i "input.mp4" -filter_complex "[0:v]setpts=0.5*PTS[v];[0:a]atempo=2.0[a]" -map "[v]" -map "[a]" "output.mp4"

# 0.5 倍速（慢放）
ffmpeg -i "input.mp4" -filter_complex "[0:v]setpts=2.0*PTS[v];[0:a]atempo=0.5[a]" -map "[v]" -map "[a]" "output.mp4"

# 4 倍速（atempo 单次最大 2.0，需串联）
ffmpeg -i "input.mp4" -filter_complex "[0:v]setpts=0.25*PTS[v];[0:a]atempo=2.0,atempo=2.0[a]" -map "[v]" -map "[a]" "output.mp4"
```

### 4.2 曲线变速（分段实现）

```powershell
# 先快后慢：0s-5s 为 2 倍速，5s-结束为 0.5 倍速
ffmpeg -i "input.mp4" \
  -filter_complex "[0:v]trim=0:5,setpts=0.5*(PTS-STARTPTS),setpts=PTS-STARTPTS[v1];[0:v]trim=5:99999,setpts=2.0*(PTS-STARTPTS),setpts=PTS-STARTPTS[v2];[v1][v2]concat=n=2:v=1:a=0[v];[0:a]atrim=0:5,atempo=2.0,asetpts=PTS-STARTPTS[a1];[0:a]atrim=5:99999,atempo=0.5,asetpts=PTS-STARTPTS[a2];[a1][a2]concat=n=2:v=0:a=1[a]" \
  -map "[v]" -map "[a]" -c:v libx264 -crf 18 "output.mp4"
```

> 曲线变速需要将视频按时间点切成多段，每段分别变速再拼接。建议写脚本循环处理。

---

## 5. 音频

### 5.1 音量调节

```powershell
# 提高 2 倍
ffmpeg -i "input.mp4" -af "volume=2.0" -c:v copy "output.mp4"

# 降低一半
ffmpeg -i "input.mp4" -af "volume=0.5" -c:v copy "output.mp4"

# 静音
ffmpeg -i "input.mp4" -af "volume=0" -c:v copy "output.mp4"
```

### 5.2 淡入淡出

```powershell
# 音频淡入 3 秒，淡出 5 秒
ffmpeg -i "input.mp4" -af "afade=t=in:d=3,afade=t=out:st=25:d=5" -c:v copy "output.mp4"

# 视频淡入淡出（黑场），2 秒淡入，距结束 2 秒淡出
ffmpeg -i "input.mp4" -vf "fade=t=in:d=2,fade=t=out:st=28:d=2" -c:a copy "output.mp4"
```

### 5.3 替换音轨

```powershell
# 完全替换（丢弃原音轨）
ffmpeg -i "video.mp4" -i "new_audio.mp3" -c:v copy -map 0:v:0 -map 1:a:0 -shortest "output.mp4"
```

### 5.4 背景音乐混音

```powershell
# 原音轨 + BGM（BGM 音量 30%）
ffmpeg -i "video.mp4" -i "bgm.mp3" \
  -filter_complex "[1:a]volume=0.3[bgm];[0:a][bgm]amix=inputs=2:duration=first" \
  -c:v copy "output.mp4"

# 原音轨 + BGM（BGM 循环到视频结束 + 末尾淡出）
ffmpeg -i "video.mp4" -stream_loop -1 -i "bgm.mp3" \
  -filter_complex "[1:a]volume=0.3,afade=t=out:st=25:d=3[bgm];[0:a][bgm]amix=inputs=2:duration=first" \
  -c:v copy -shortest "output.mp4"
```

### 5.5 音频降噪

```powershell
# 轻度降噪
ffmpeg -i "input.mp4" -af "anlmdn=s=0.00001" -c:v copy "output.mp4"

# 强力降噪
ffmpeg -i "input.mp4" -af "afftdn=nr=30" -c:v copy "output.mp4"

# 高通滤波去除低频噪音（如风声、空调声）
ffmpeg -i "input.mp4" -af "highpass=f=200" -c:v copy "output.mp4"
```

### 5.6 变声

```powershell
# 升高音调（萝莉音，tempo 保持不变）
ffmpeg -i "input.mp4" -af "asetrate=44100*1.5,aresample=44100" -c:v copy "output.mp4"

# 降低音调（大叔音）
ffmpeg -i "input.mp4" -af "asetrate=44100*0.7,aresample=44100" -c:v copy "output.mp4"

# 机器人音效
ffmpeg -i "input.mp4" -af "aecho=0.8:0.88:60:0.4" -c:v copy "output.mp4"
```

---

## 6. 画中画 / 叠加

### 6.1 图片水印

```powershell
# 左上角，距边缘 20px
ffmpeg -i "input.mp4" -i "logo.png" \
  -filter_complex "overlay=20:20" \
  -c:v libx264 -crf 18 -c:a copy "output.mp4"

# 右下角
ffmpeg -i "input.mp4" -i "logo.png" \
  -filter_complex "overlay=W-w-20:H-h-20" \
  -c:v libx264 -crf 18 -c:a copy "output.mp4"

# 水印半透明
ffmpeg -i "input.mp4" -i "logo.png" \
  -filter_complex "[1:v]format=rgba,colorchannelmixer=aa=0.5[wm];[0:v][wm]overlay=W-w-20:H-h-20" \
  -c:v libx264 -crf 18 -c:a copy "output.mp4"
```

### 6.2 画中画（视频叠加视频）

```powershell
# 小窗放在右下角，缩放为 320 宽
ffmpeg -i "main.mp4" -i "pip.mp4" \
  -filter_complex "[1:v]scale=320:-2[pip];[0:v][pip]overlay=W-w-20:H-h-20" \
  -c:v libx264 -crf 18 -c:a copy "output.mp4"

# 多个画中画（2 个小窗）
ffmpeg -i "main.mp4" -i "pip1.mp4" -i "pip2.mp4" \
  -filter_complex "[1:v]scale=320:-2[p1];[2:v]scale=320:-2[p2];[0:v][p1]overlay=W-w-20:20[o1];[o1][p2]overlay=W-w-20:H-h-20" \
  -c:v libx264 -crf 18 -c:a copy "output.mp4"
```

### 6.3 分屏

```powershell
# 左右分屏
ffmpeg -i "left.mp4" -i "right.mp4" \
  -filter_complex "[0:v]scale=960:1080[l];[1:v]scale=960:1080[r];[l][r]hstack" \
  -c:v libx264 -crf 18 "output.mp4"

# 上下分屏
ffmpeg -i "top.mp4" -i "bottom.mp4" \
  -filter_complex "[0:v]scale=1920:540[t];[1:v]scale=1920:540[b];[t][b]vstack" \
  -c:v libx264 -crf 18 "output.mp4"

# 四宫格
ffmpeg -i "1.mp4" -i "2.mp4" -i "3.mp4" -i "4.mp4" \
  -filter_complex "[0:v]scale=960:540[a];[1:v]scale=960:540[b];[2:v]scale=960:540[c];[3:v]scale=960:540[d];[a][b]hstack[top];[c][d]hstack[bot];[top][bot]vstack" \
  -c:v libx264 -crf 18 "output.mp4"
```

---

## 7. 文字

### 7.1 文字叠加（drawtext）

```powershell
# 底部居中文字
ffmpeg -i "input.mp4" \
  -vf "drawtext=fontfile='C\:/Windows/Fonts/msyh.ttc':text='字幕文字':fontsize=48:fontcolor=white:x=(w-text_w)/2:y=h-th-60" \
  -c:v libx264 -crf 18 -c:a copy "output.mp4"

# 带阴影的标题
ffmpeg -i "input.mp4" \
  -vf "drawtext=fontfile='C\:/Windows/Fonts/msyh.ttc':text='标题':fontsize=64:fontcolor=white:shadowcolor=black:shadowx=3:shadowy=3:x=(w-text_w)/2:y=80" \
  -c:v libx264 -crf 18 -c:a copy "output.mp4"

# 带背景框
ffmpeg -i "input.mp4" \
  -vf "drawtext=fontfile='C\:/Windows/Fonts/msyh.ttc':text='标题':fontsize=48:fontcolor=white:box=1:boxcolor=black@0.6:boxborderw=10:x=(w-text_w)/2:y=80" \
  -c:v libx264 -crf 18 -c:a copy "output.mp4"

# 时间码
ffmpeg -i "input.mp4" \
  -vf "drawtext=fontfile='C\:/Windows/Fonts/consola.ttf':text='%{pts\:hms}':fontsize=32:fontcolor=white:x=20:y=20" \
  -c:v libx264 -crf 18 -c:a copy "output.mp4"

# 多行文字（用 \n 换行）
ffmpeg -i "input.mp4" \
  -vf "drawtext=fontfile='C\:/Windows/Fonts/msyh.ttc':text='第一行\n第二行':fontsize=36:fontcolor=white:line_spacing=10:x=(w-text_w)/2:y=h-th-100" \
  -c:v libx264 -crf 18 -c:a copy "output.mp4"
```

> **Windows 字体路径**：微软雅黑 `C:/Windows/Fonts/msyh.ttc`，黑体 `C:/Windows/Fonts/simhei.ttf`，宋体 `C:/Windows/Fonts/simsun.ttc`，Consolas `C:/Windows/Fonts/consola.ttf`。

### 7.2 SRT 字幕烧录

```powershell
# 烧录 SRT（包含样式）
ffmpeg -i "video.mp4" \
  -vf "subtitles='C\:/path/to/subtitles.srt':force_style='FontName=微软雅黑,FontSize=24,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Alignment=2'" \
  -c:v libx264 -crf 18 -c:a copy "output.mp4"
```

> `Alignment=2` 底部居中，`=6` 顶部居中，`=8` 顶部居中（ASS 坐标系）。本项目 `speech transcribe-long` 生成的 SRT 可直接用于此命令。

---

## 8. 转场

### 8.1 常用转场效果

| 效果 | xfade transition 值 | 说明 |
|---|---|---|
| 淡入淡出 | `fade` | 渐隐渐显，最常用 |
| 闪黑 | `fadeblack` | 经黑色过渡 |
| 闪白 | `fadewhite` | 经白色过渡 |
| 溶解 | `dissolve` | 像素交叉溶解 |
| 左滑 | `slideleft` | 新画面从左滑入 |
| 右滑 | `slideright` | 新画面从右滑入 |
| 上滑 | `slideup` | 新画面从下滑入 |
| 下滑 | `slidedown` | 新画面从上滑入 |
| 左擦除 | `wipeleft` | 擦除式从左过渡 |
| 右擦除 | `wiperight` | 擦除式从右过渡 |
| 上擦除 | `wipeup` | 擦除式从下过渡 |
| 下擦除 | `wipedown` | 擦除式从上过渡 |
| 像素化 | `pixelize` | 马赛克过渡 |
| 径向 | `radial` | 圆形扩散 |
| 窗格 | `windowslice` | 百叶窗效果 |

完整列表可通过 `ffmpeg -h filter=xfade` 查看。

### 8.2 转场命令

```powershell
# 两段视频 + 1 秒淡入淡出转场
# offset 是第一段的实际时长减去转场时长
ffmpeg -i "clip1.mp4" -i "clip2.mp4" \
  -filter_complex "[0:v][1:v]xfade=transition=fade:duration=1:offset=9[v];[0:a][1:a]acrossfade=d=1[a]" \
  -map "[v]" -map "[a]" -c:v libx264 -crf 18 "output.mp4"

# 多段视频连续转场（三段 + 两个转场）
ffmpeg -i "c1.mp4" -i "c2.mp4" -i "c3.mp4" \
  -filter_complex "[0:v][1:v]xfade=transition=slideleft:duration=1:offset=3[v1];[v1][2:v]xfade=transition=fade:duration=1:offset=6[v]" \
  -map "[v]" -c:v libx264 -crf 18 "output.mp4"
```

---

## 9. 调色与滤镜

### 9.1 基础调色

```powershell
# 亮度、对比度、饱和度（取值范围 -1.0 ~ 1.0）
ffmpeg -i "input.mp4" -vf "eq=brightness=0.05:contrast=1.1:saturation=1.2" -c:v libx264 -crf 18 -c:a copy "output.mp4"

# 色温调节（偏暖：降低色温，偏冷：升高色温）
ffmpeg -i "input.mp4" -vf "colorbalance=rs=0.1:gs=-0.1:bs=-0.1" -c:v libx264 -crf 18 -c:a copy "output.mp4"

# 色相旋转（Hue 旋转，0-360）
ffmpeg -i "input.mp4" -vf "hue=h=30:s=1.2" -c:v libx264 -crf 18 -c:a copy "output.mp4"

# Gamma 校正
ffmpeg -i "input.mp4" -vf "eq=gamma=1.2" -c:v libx264 -crf 18 -c:a copy "output.mp4"
```

### 9.2 曲线（curves filter）

```powershell
# 提亮暗部（S 曲线）
ffmpeg -i "input.mp4" -vf "curves=all='0/0 0.3/0.5 0.7/0.8 1/1'" -c:v libx264 -crf 18 -c:a copy "output.mp4"

# 降低高光
ffmpeg -i "input.mp4" -vf "curves=all='0/0 0.5/0.6 0.8/0.85 1/0.9'" -c:v libx264 -crf 18 -c:a copy "output.mp4"

# RGB 分别调色
ffmpeg -i "input.mp4" -vf "curves=r='0/0 1/1':g='0/0 0.5/0.6 1/1':b='0/0 0.5/0.4 1/1'" -c:v libx264 -crf 18 "output.mp4"
```

### 9.3 LUT 调色

```powershell
# 应用 .cube LUT 文件
ffmpeg -i "input.mp4" -vf "lut3d='C\:/path/to/lut.cube'" -c:v libx264 -crf 18 -c:a copy "output.mp4"

# LUT 强度 50%
ffmpeg -i "input.mp4" \
  -filter_complex "[0:v]split[v1][v2];[v1]lut3d='C\:/path/to/lut.cube'[lut];[v2][lut]blend=all_mode=overlay:all_opacity=0.5" \
  -c:v libx264 -crf 18 -c:a copy "output.mp4"
```

### 9.4 风格化滤镜

```powershell
# 灰度 / 黑白
ffmpeg -i "input.mp4" -vf "hue=s=0" -c:v libx264 -crf 18 -c:a copy "output.mp4"

# 老电影效果（降低帧率 + 棕褐色调 + 噪点）
ffmpeg -i "input.mp4" \
  -vf "fps=18,colorchannelmixer=rr=0.5:gg=0.4:bb=0.2,noise=alls=10:allf=t,drawtext=fontfile='C\:/Windows/Fonts/consola.ttf':text='':fontsize=24" \
  -c:v libx264 -crf 18 -c:a copy "output.mp4"

# 锐化
ffmpeg -i "input.mp4" -vf "unsharp=5:5:1.0:5:5:0.0" -c:v libx264 -crf 18 -c:a copy "output.mp4"

# 模糊
ffmpeg -i "input.mp4" -vf "boxblur=5:1" -c:v libx264 -crf 18 -c:a copy "output.mp4"

# 毛玻璃效果
ffmpeg -i "input.mp4" -vf "gblur=sigma=10" -c:v libx264 -crf 18 -c:a copy "output.mp4"

# 卡通化
ffmpeg -i "input.mp4" -vf "edgedetect=low=0.1:high=0.3" -c:v libx264 -crf 18 -c:a copy "output.mp4"

# 负片
ffmpeg -i "input.mp4" -vf "negate" -c:v libx264 -crf 18 -c:a copy "output.mp4"
```

---

## 10. 蒙版

```powershell
# 圆形蒙版画中画（圆形区域 + 模糊背景）
ffmpeg -i "bg.mp4" -i "fg.mp4" \
  -filter_complex "[0:v]boxblur=20[bg_blur];[1:v]scale=640:-2,format=rgba,geq=r='r(X,Y)':a='if(lt((X-320)^2+(Y-360)^2,40000),255,0)'[fg_mask];[bg_blur][fg_mask]overlay=(W-w)/2:(H-h)/2" \
  -c:v libx264 -crf 18 "output.mp4"

# 使用遮罩图片
ffmpeg -i "video.mp4" -i "mask.png" \
  -filter_complex "[0:v][1:v]alphamerge" \
  -c:v libx264 -crf 18 "output.mp4"

# 矩形蒙版（画中画）
ffmpeg -i "bg.mp4" -i "fg.mp4" \
  -filter_complex "[1:v]crop=400:300,format=rgba,geq=r='r(X,Y)':a=255[fg_crop];[0:v][fg_crop]overlay=100:100" \
  -c:v libx264 -crf 18 "output.mp4"
```

---

## 11. 背景

```powershell
# 纯色背景 + 视频居中（竖屏视频放横屏中）
ffmpeg -i "vertical.mp4" \
  -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black" \
  -c:v libx264 -crf 18 "output.mp4"

# 自定义颜色背景（#FF5733）
ffmpeg -i "vertical.mp4" \
  -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:#FF5733" \
  -c:v libx264 -crf 18 "output.mp4"

# 高斯模糊背景（模糊原视频作为背景）
ffmpeg -i "input.mp4" \
  -filter_complex "[0:v]split=2[fg][bg];[bg]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,boxblur=30:10[blur];[fg]scale=1920:1080:force_original_aspect_ratio=decrease[fg_scaled];[blur][fg_scaled]overlay=(W-w)/2:(H-h)/2" \
  -c:v libx264 -crf 18 "output.mp4"
```

---

## 12. 绿幕抠像

```powershell
# 绿幕抠像（chromakey），调 tolerance 和 blend 控制边缘
ffmpeg -i "greenscreen.mp4" -i "background.mp4" \
  -filter_complex "[0:v]chromakey=0x00FF00:similarity=0.1:blend=0.1[fg];[1:v][fg]overlay" \
  -c:v libx264 -crf 18 "output.mp4"

# 纯色背景替换（如白底替换）
ffmpeg -i "input.mp4" \
  -vf "colorkey=0xFFFFFF:similarity=0.3:blend=0.2" \
  -c:v libx264 -crf 18 "output.mp4"
```

---

## 13. 抽帧 / 缩时摄影

```powershell
# 抽取图片序列（每秒 1 帧）
ffmpeg -i "video.mp4" -vf "fps=1" "frame_%04d.png"

# 抽取指定时间范围内的帧
ffmpeg -i "video.mp4" -ss 10 -t 5 -vf "fps=1" "frame_%04d.png"

# 缩时摄影（图片序列 → 视频，30fps）
ffmpeg -framerate 30 -i "frame_%04d.jpg" -c:v libx264 -crf 18 "timelapse.mp4"

# 视频加速为缩时（60 倍速，1 分钟 → 1 秒）
ffmpeg -i "video.mp4" -filter_complex "[0:v]setpts=1/60*PTS[v];[0:a]atempo=2.0,atempo=2.0,atempo=2.0,atempo=2.0,atempo=2.0,atempo=2.0[a]" -map "[v]" -map "[a]" "timelapse.mp4"
```

---

## 14. 转格式

```powershell
# 任意格式 → MP4（H.264 + AAC）
ffmpeg -i "input.mkv" -c:v libx264 -crf 18 -c:a aac -b:a 192k "output.mp4"

# → MOV（适合 Mac / ProRes 兼容）
ffmpeg -i "input.mp4" -c:v libx264 -crf 18 -c:a aac -b:a 192k "output.mov"

# → GIF
ffmpeg -i "input.mp4" -vf "fps=10,scale=480:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" -loop 0 "output.gif"

# → WebM
ffmpeg -i "input.mp4" -c:v libvpx-vp9 -crf 30 -b:v 0 -c:a libopus "output.webm"
```

---

## 15. 编码参数速查

| 参数 | 说明 |
|---|---|
| `-c copy` | **无损首选**：流复制，不重编码，最快 |
| `-c:v libx264 -crf 18` | H.264 视觉无损（0=真无损, 18=视觉无损, 23=默认, 51=最差） |
| `-c:v libx264 -preset slow` | 更小体积、更好质量（ultrafast → veryslow） |
| `-c:a aac -b:a 192k` | AAC 192kbps 音频 |
| `-c:a aac -b:a 320k` | AAC 最高质量音频 |
| `-ss 10 -to 30` | 截取 10s → 30s |
| `-ss 10 -t 20` | 从 10s 取 20s |
| `-vf "..."` | 视频滤镜链，多滤镜用 `,` 连接 |
| `-af "..."` | 音频滤镜链 |
| `-filter_complex "..."` | 复杂滤镜（多输入/多输出） |
| `-an` | 去除所有音频轨道 |
| `-vn` | 去除所有视频轨道 |
| `-y` | 覆盖输出文件不询问 |
| `-shortest` | 以最短输入流为准结束 |
| `-stream_loop -1` | 无限循环输入（如 BGM） |
| `-map 0:v:0` | 选择第一输入的第一个视频流 |
| `-map 0:a:0` | 选择第一输入的第一个音频流 |

---

## 16. 能力对标总表

| 剪映功能 | FFmpeg 能力 | 实现方式 |
|---|---|---|
| 分割/裁剪 | ✅ 完全支持 | `-ss -to -c copy` |
| 拼接 | ✅ 完全支持 | concat demuxer |
| 倒放 | ✅ 完全支持 | `reverse` + `areverse` |
| 定格/冻结帧 | ⚠️ 可实现 | trim + loop + concat，命令较长 |
| 缩放 | ✅ 完全支持 | `scale` filter |
| 裁切 | ✅ 完全支持 | `crop` filter |
| 旋转/翻转 | ✅ 完全支持 | `transpose` / `hflip` / `rotate` |
| 比例转换（横↔竖） | ✅ 完全支持 | crop/scale/pad + boxblur 背景 |
| 匀速变速 | ✅ 完全支持 | `setpts` + `atempo` |
| 曲线变速 | ⚠️ 可实现 | 分段 trim + 分别变速 + concat，需脚本化 |
| 音量调节 | ✅ 完全支持 | `volume` filter |
| 淡入淡出 | ✅ 完全支持 | `fade` / `afade` |
| 替换音轨 | ✅ 完全支持 | `-map` 选择流 |
| 背景音乐混音 | ✅ 完全支持 | `amix` filter |
| 音频降噪 | ✅ 可做 | `anlmdn` / `afftdn` / `highpass`，效果不及专业降噪 |
| 变声 | ✅ 可做 | `asetrate` + `aresample`，简单效果 |
| 图片水印 | ✅ 完全支持 | `overlay` filter |
| 画中画 | ✅ 完全支持 | `overlay` + `scale` |
| 分屏 | ✅ 完全支持 | `hstack` / `vstack` |
| 文字叠加 | ✅ 可做 | `drawtext`，静态文字，无动画 |
| SRT 字幕烧录 | ✅ 完全支持 | `subtitles` filter |
| 转场（xfade） | ✅ 完全支持 | 几十种内置转场 + 自定义 duration |
| 基础调色 | ✅ 完全支持 | `eq` / `colorbalance` / `curves` / `hue` |
| LUT 调色 | ✅ 完全支持 | `lut3d` filter |
| 风格化滤镜 | ✅ 可做 | 十几种内置滤镜（灰度/老电影/模糊/锐化/卡通/负片） |
| 绿幕抠像 | ✅ 可做 | `chromakey` / `colorkey`，纯色背景效果好 |
| 蒙版 | ⚠️ 可实现 | `geq` + `alphamerge`，表达式复杂 |
| 模糊背景 | ✅ 完全支持 | `boxblur` + overlay |
| 抽帧/缩时 | ✅ 完全支持 | `fps` + `setpts` |
| 转格式 | ✅ 完全支持 | libx264 / libx265 / VP9 / GIF |
| 关键帧动画 | ✅ ASS字幕实现 | ASS `\t` 标签，可对字幕做位置/缩放/旋转/颜色/透明度的关键帧插值 |
| 字幕动画 | ✅ ASS字幕实现 | ASS `\move` `\fade` `\t` `\k` `\clip`，全套动画标签 |
| 美颜美体 | ❌ 不支持 | 需 AI/OpenCV，纯 FFmpeg 不行 |
| 智能抠像（AI） | ❌ 不支持 | 需 rembg 等 AI 模型 |
| 动态贴纸/跟踪 | ❌ 不支持 | 需素材库 + 运动跟踪 |
| 模板 | ❌ 不支持 | 工程化需求，超出 CLI 范围 |
| 素材库（音乐/贴纸/音效） | ❌ 不支持 | 需自行准备素材 |

> **结论**：FFmpeg + ASS 覆盖剪映 90%+ 的剪辑能力，字幕关键帧动画补齐了关键短板。美颜、AI 抠像、动态贴纸和模板是仅剩的边界——这些需要 AI 模型补充。

---

## 17. 字幕动画工作流

完整流水线：**音频 → 百炼语音识别 → SRT → Python 转 ASS（加动画标签）→ FFmpeg 烧录**

### 17.1 步骤总览

```powershell
# 第一步：上传音频获取公网 URL
python scripts/main.py file upload "runtime/inputs/audio.mp3"

# 第二步：长音频识别生成 SRT 字幕
python scripts/main.py speech transcribe-long "<返回的URL>" --language zh \
  --timestamp-level sentence --output-srt "runtime/outputs/subtitles.srt"

# 第三步：SRT 转 ASS（Python 脚本，见下方）
python scripts/commands/srt_to_ass.py "runtime/outputs/subtitles.srt" \
  --style pop --output "runtime/outputs/subtitles.ass"

# 第四步：烧录到视频
ffmpeg -i "video.mp4" -vf "ass='C\:/path/to/runtime/outputs/subtitles.ass'" \
  -c:v libx264 -crf 18 -c:a copy "output.mp4"
```

### 17.2 ASS 动画标签速查

| 动画类型 | ASS 标签 | 说明 |
|---|---|---|
| 位置移动 | `\move(x1,y1,x2,y2,t1,t2)` | 从 (x1,y1) 匀速移动到 (x2,y2) |
| 淡入淡出 | `\fade(淡入ms,持续ms,淡出ms)` | 简单透明度过渡 |
| 复杂淡入淡出 | `\fad(淡入ms,淡出ms)` | 只控制头尾 |
| 卡拉OK逐字 | `\k<每字厘秒>` | 填充式逐字变色 |
| 关键帧动画 | `\t(加速,开始ms,结束ms,起始属性,结束属性)` | 对任意属性做缓动插值 |
| 矩形裁切 | `\clip(x1,y1,x2,y2)` | 只显示矩形区域 |
| 矢量裁切 | `\clip(scale,mode,path)` | 任意形状遮罩 |
| 透明度 | `\1a&HXX&` | XX=00(不透明)~FF(完全透明) |
| 模糊 | `\blur<值>` | 数字越大越模糊 |
| 描边粗细 | `\bord<值>` | 像素宽度 |

### 17.3 `\t` 关键帧可动画属性

```
\t(加速系数, 起始ms, 结束ms, 起始值, 结束值)
加速系数: 0=线性  0<值<1=缓出  1=缓入
```

| 属性 | 标签 | 示例（起始→结束） |
|---|---|---|
| 位置 X | `\pos(x,y)` | `\t(0,0,800,\pos(100,540),\pos(1820,540))` |
| 水平缩放 | `\fscx` | `\t(0,0,500,\fscx20,\fscx100)` 弹入 |
| 垂直缩放 | `\fscy` | 配合 fscx 等比或独立 |
| 绕 Z 轴旋转 | `\frz` | `\t(0,0,500,\frz-30,\frz0)` 摇摆归位 |
| 绕 X 轴旋转 | `\frx` | 3D 上下翻转 |
| 绕 Y 轴旋转 | `\fry` | 3D 左右翻转 |
| 主颜色 | `\1c&HBBGGRR&` | `\t(0,0,1000,\1c&HFFFFFF&,\1c&H0000FF&)` 白→红 |
| 主透明度 | `\1a&HXX&` | `\t(0,0,1000,\1a&HFF&,\1a&H00&)` 从不可见到可见 |
| 模糊 | `\blur` | `\t(0,0,800,\blur30,\blur0)` 由模糊变清晰 |
| 间距 | `\fsp` | `\t(0,0,1000,\fsp0,\fsp20)` 文字散开 |
| 切变 | `\fax` `\fay` | 倾斜动画 |
| 描边 | `\bord` | `\t(0,0,500,\bord0,\bord5)` 描边脉冲 |

### 17.4 SRT → ASS 转换脚本

项目内置脚本 `scripts/srt_to_ass.py`，将 SRT 转为带动画的 ASS：

```powershell
# 查看帮助
python scripts/commands/srt_to_ass.py --help

# 基础转换（静态字幕）
python scripts/commands/srt_to_ass.py "subtitles.srt" --output "subtitles.ass"

# 弹入弹出风格（缩放 + 透明度关键帧）
python scripts/commands/srt_to_ass.py "subtitles.srt" --style pop --output "subtitles.ass"

# 滑入风格（从右向左滑入）
python scripts/commands/srt_to_ass.py "subtitles.srt" --style slide --output "subtitles.ass"

# 卡拉OK风格（逐字变色，需提供完整文本）
python scripts/commands/srt_to_ass.py "subtitles.srt" --style karaoke --output "subtitles.ass"

# 自定义样式
python scripts/commands/srt_to_ass.py "subtitles.srt" --style pop \
  --font "微软雅黑" --fontsize 48 --color "#FFFFFF" --outline-color "#000000" \
  --outline 3 --shadow 1 --output "subtitles.ass"
```

**内置动画风格（16 种）：**

| `--style` | 动画属性 | 效果 |
|---|---|---|
| `plain` | — | 静态字幕，无动画 |
| `pop` | \fscx \fscy \1a | 缩放弹性弹入（0→120%→100%）+ 透明度淡入 |
| `slide` | \pos | 从下方 30px 滑入到位 |
| `slide-left` | \pos | 从右边界滑入到位（弹幕风格） |
| `fade` | \fad | 纯淡入淡出 |
| `karaoke` | \k | 逐字变色填充 |
| `bounce` | \pos \fscx \1a | 从上方弹跳落入 + 两次回弹 + 缩放 |
| `rotate-in` | \frz \fscx \1a | 绕 Z 轴旋转 45° 弹入 + 缩放 + 淡入 |
| `flip-3d` | \fry \1a | 绕 Y 轴 3D 翻转 90° 弹入 + 淡入 |
| `typewriter` | \clip \t | clip 矩形从左到右逐字展开 |
| `glow` | \bord | 描边粗细呼吸式脉冲（0→8→2→6→2 循环） |
| `blur-in` | \blur \1a | 从高斯模糊到清晰 + 淡入 |
| `shake` | \pos | 快速左右振荡 + 衰减归位 |
| `color-shift` | \1c | 蓝色→品红→白色渐变过渡 |
| `wipe` | \clip \t | clip 从左向右擦除式出现 |
| `combo` | \frz \fscx \blur \1a | 旋转 + 缩放 + 模糊 + 透明度 四属性同时关键帧 |

### 17.5 ASS 样式参数

```python
from ass import Style
from ass.data import Color

Style(
    Name="Default",
    Fontname="微软雅黑",
    Fontsize=48,
    PrimaryColour=Color(r=255, g=255, b=255, a=0),   # 主色白色
    SecondaryColour=Color(r=0, g=0, b=255, a=0),     # 辅色蓝色（卡拉OK变色目标）
    OutlineColour=Color(r=0, g=0, b=0, a=0),         # 描边黑色
    BackColour=Color(r=0, g=0, b=0, a=128),           # 背景半透明黑色
    Outline=3,      # 描边粗细
    Shadow=1,       # 阴影深度
    Alignment=2,    # 2=底部居中, 5=顶部居中, 7=左上角
    MarginL=20,     # 左右边距
    MarginR=20,
    MarginV=20,     # 上下边距
)
```

### 17.6 自定义关键帧动画（Python）

```python
"""手工构造带自定义关键帧的 ASS 事件"""
from ass import Document, Style, Dialogue
from ass.data import Color

doc = Document()
doc.styles.append(Style(
    Name="Default",
    Fontname="微软雅黑",
    Fontsize=64,
    PrimaryColour=Color(r=255, g=255, b=255, a=0),
    OutlineColour=Color(r=0, g=0, b=0, a=0),
    Outline=3,
    Alignment=2,
))

# 弹幕式出场：从右飞出 + 从小变大 + 不可见到可见
text = (
    "{\\fscx20\\fscy20\\1a&HFF&\\pos(2200,540)"
    "\\t(0,0,800,\\fscx20\\fscy20,\\fscx100\\fscy100)"      # 缩放弹性弹入
    "\\t(0,0,800,\\pos(2200,540),\\pos(960,540))"             # 从右飞到中间
    "\\t(0,100,500,\\1a&HFF&,\\1a&H00&)}"                      # 透明度淡入
    "弹幕式组合出场"
)
doc.events.append(Dialogue(start=1_000, end=4_000, style="Default", text=text))

# 写入文件
with open("custom.ass", "w", encoding="utf-8-sig") as f:
    doc.dump_file(f)
```

### 17.7 ASS 烧录与字体

```powershell
# 烧录 ASS（Windows 上自动使用系统字体）
ffmpeg -i "video.mp4" -vf "ass='C\:/path/to/subtitles.ass'" \
  -c:v libx264 -crf 18 -c:a copy "output.mp4"

# 加载外部字体目录（非系统字体）
ffmpeg -i "video.mp4" \
  -vf "ass='C\:/path/to/subtitles.ass':fontsdir='C\:/path/to/fonts'" \
  -c:v libx264 -crf 18 -c:a copy "output.mp4"
```

> `\move` 和 `\t` 关键帧动画由 libass 引擎在编码时逐帧渲染，性能开销取决于动画复杂度。单条字幕 2-3 个 `\t` 属性无明显影响；批量上百条复杂动画建议用 `-preset faster` 提速。

