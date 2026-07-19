import io
import json
import pathlib
import sys

# 步骤0：仅在需要时切换为 UTF-8，避免统一入口重复导入时关闭输出流。
standard_output_encoding = getattr(sys.stdout, "encoding", "") or ""
normalized_output_encoding = standard_output_encoding.lower().replace("-", "")
if normalized_output_encoding != "utf8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import av
import click


SCRIPTS_DIRECTORY = pathlib.Path(__file__).resolve().parent.parent
PROJECT_DIRECTORY = SCRIPTS_DIRECTORY.parent

STREAM_COPY_SETTINGS = {
    "aac": {
        "extension": ".m4a",
        "container_format": "mp4",
    },
    "flac": {
        "extension": ".flac",
        "container_format": "flac",
    },
    "mp3": {
        "extension": ".mp3",
        "container_format": "mp3",
    },
    "opus": {
        "extension": ".ogg",
        "container_format": "ogg",
    },
    "vorbis": {
        "extension": ".ogg",
        "container_format": "ogg",
    },
}


# ---------------------------
# 函数说明：取得视频中的指定音轨。
# ---------------------------
def get_audio_stream(media_container, audio_stream_position):
    # 步骤1：按容器顺序收集全部音轨。
    audio_streams = []
    for stream in media_container.streams:
        if stream.type == "audio":
            audio_streams.append(stream)

    # 步骤2：检查视频是否包含请求的音轨。
    if not audio_streams:
        raise click.ClickException("输入媒体文件不包含音轨")
    if audio_stream_position < 0 or audio_stream_position >= len(audio_streams):
        raise click.ClickException(
            "音轨位置超出范围，当前共有 " + str(len(audio_streams)) + " 条音轨"
        )

    # 步骤3：返回用户选择的音轨和总数。
    return audio_streams[audio_stream_position], len(audio_streams)


# ---------------------------
# 函数说明：把兼容编码的压缩数据包原样复制到音频容器。
# ---------------------------
def copy_audio_stream(
    input_file_path,
    output_file_path,
    audio_stream_position,
    container_format,
):
    # 步骤1：打开输入视频并取得音轨属性。
    input_container = av.open(str(input_file_path))
    audio_stream, audio_stream_count = get_audio_stream(
        input_container,
        audio_stream_position,
    )
    source_codec = audio_stream.codec_context.name
    sample_rate = audio_stream.codec_context.sample_rate
    channels = audio_stream.codec_context.channels
    channel_layout = audio_stream.codec_context.layout.name

    # 步骤2：创建临时 M4A 容器并复制音轨模板。
    temporary_output_file = output_file_path.with_name(
        output_file_path.name + ".tmp"
    )
    output_container = None
    packet_count = 0
    try:
        output_container = av.open(
            str(temporary_output_file),
            mode="w",
            format=container_format,
        )
        output_stream = output_container.add_stream_from_template(audio_stream)

        # 步骤3：逐包复用原始 AAC 数据，不执行解码或编码。
        for packet in input_container.demux(audio_stream):
            packet_bytes = bytes(packet)
            if not packet_bytes:
                continue
            if packet.dts is None:
                continue

            packet.stream = output_stream
            output_container.mux(packet)
            packet_count = packet_count + 1
    except Exception as error:
        if output_container is not None:
            output_container.close()
        input_container.close()
        if temporary_output_file.exists():
            temporary_output_file.unlink()
        raise click.ClickException("无损复制音轨失败：" + str(error))

    # 步骤4：关闭容器并原子替换目标文件。
    output_container.close()
    input_container.close()
    temporary_output_file.replace(output_file_path)

    # 步骤5：返回便于验证和后续处理的结构化摘要。
    result = {
        "mode": "stream_copy",
        "bit_exact": True,
        "source_codec": source_codec,
        "output_codec": source_codec,
        "sample_rate": sample_rate,
        "channels": channels,
        "channel_layout": channel_layout,
        "audio_stream_position": audio_stream_position,
        "audio_stream_count": audio_stream_count,
        "packet_count": packet_count,
        "input_file": str(input_file_path.resolve()),
        "output_file": str(output_file_path.resolve()),
        "output_size": output_file_path.stat().st_size,
    }
    return result


# ---------------------------
# 函数说明：把不能直接复用的音轨转为无损 FLAC。
# ---------------------------
def transcode_audio_to_flac(
    input_file_path,
    output_file_path,
    audio_stream_position,
):
    # 步骤1：打开输入媒体并读取原始音频属性。
    input_container = av.open(str(input_file_path))
    audio_stream, audio_stream_count = get_audio_stream(
        input_container,
        audio_stream_position,
    )
    source_codec = audio_stream.codec_context.name
    sample_rate = audio_stream.codec_context.sample_rate
    channels = audio_stream.codec_context.channels
    channel_layout = audio_stream.codec_context.layout.name

    # 步骤2：创建保持原采样率和声道布局的 FLAC 编码器。
    temporary_output_file = output_file_path.with_name(
        output_file_path.name + ".tmp"
    )
    output_container = None
    frame_count = 0
    packet_count = 0
    try:
        output_container = av.open(
            str(temporary_output_file),
            mode="w",
            format="flac",
        )
        output_stream = output_container.add_stream("flac", rate=sample_rate)
        output_stream.layout = channel_layout

        # 步骤3：只转换编码格式，不降采样也不混合声道。
        output_format = output_stream.codec_context.format.name
        audio_resampler = av.AudioResampler(
            format=output_format,
            layout=channel_layout,
            rate=sample_rate,
        )
        for decoded_frame in input_container.decode(audio_stream):
            resampled_frames = audio_resampler.resample(decoded_frame)
            for resampled_frame in resampled_frames:
                encoded_packets = output_stream.encode(resampled_frame)
                for encoded_packet in encoded_packets:
                    output_container.mux(encoded_packet)
                    packet_count = packet_count + 1
                frame_count = frame_count + 1

        # 步骤4：刷新重采样器和编码器中的剩余数据。
        remaining_frames = audio_resampler.resample(None)
        for remaining_frame in remaining_frames:
            encoded_packets = output_stream.encode(remaining_frame)
            for encoded_packet in encoded_packets:
                output_container.mux(encoded_packet)
                packet_count = packet_count + 1
            frame_count = frame_count + 1

        final_packets = output_stream.encode(None)
        for final_packet in final_packets:
            output_container.mux(final_packet)
            packet_count = packet_count + 1
    except Exception as error:
        if output_container is not None:
            output_container.close()
        input_container.close()
        if temporary_output_file.exists():
            temporary_output_file.unlink()
        raise click.ClickException("转为无损 FLAC 失败：" + str(error))

    # 步骤5：关闭容器并原子替换目标文件。
    output_container.close()
    input_container.close()
    temporary_output_file.replace(output_file_path)

    # 步骤6：返回明确标识无损转码而非压缩包原样复制的摘要。
    result = {
        "mode": "lossless_flac",
        "bit_exact": False,
        "source_codec": source_codec,
        "output_codec": "flac",
        "sample_rate": sample_rate,
        "channels": channels,
        "channel_layout": channel_layout,
        "audio_stream_position": audio_stream_position,
        "audio_stream_count": audio_stream_count,
        "frame_count": frame_count,
        "packet_count": packet_count,
        "input_file": str(input_file_path.resolve()),
        "output_file": str(output_file_path.resolve()),
        "output_size": output_file_path.stat().st_size,
    }
    return result


# ---------------------------
# 函数说明：按最高保真策略抽取视频音轨。
# ---------------------------
def extract_audio_track(
    input_file_path,
    output_file_path,
    audio_stream_position,
    overwrite,
):
    # 步骤1：解析路径并检查覆盖规则。
    resolved_input_file = input_file_path.resolve()
    resolved_output_file = output_file_path.resolve()
    if resolved_output_file.exists() and not overwrite:
        raise click.ClickException(
            "输出文件已存在，请更换路径或使用 --overwrite："
            + str(resolved_output_file)
        )
    resolved_output_file.parent.mkdir(parents=True, exist_ok=True)

    # 步骤2：检查源编码并确定输出文件是否匹配复制策略。
    inspection_container = av.open(str(resolved_input_file))
    audio_stream, unused_audio_stream_count = get_audio_stream(
        inspection_container,
        audio_stream_position,
    )
    source_codec = audio_stream.codec_context.name
    inspection_container.close()

    stream_copy_setting = STREAM_COPY_SETTINGS.get(source_codec)
    output_extension = resolved_output_file.suffix.lower()
    if stream_copy_setting:
        expected_extension = stream_copy_setting["extension"]
        if output_extension == expected_extension:
            return copy_audio_stream(
                resolved_input_file,
                resolved_output_file,
                audio_stream_position,
                stream_copy_setting["container_format"],
            )

    # 步骤3：无法按目标扩展名直接复制时只允许无损 FLAC。
    if output_extension != ".flac":
        raise click.ClickException(
            "当前编码不能直接复制到该扩展名，请使用 .flac 输出"
        )
    return transcode_audio_to_flac(
        resolved_input_file,
        resolved_output_file,
        audio_stream_position,
    )


# ---------------------------
# 函数说明：根据源编码确定默认输出文件。
# ---------------------------
def resolve_audio_output_file(
    input_file_path,
    output_file_path,
    audio_stream_position,
):
    # 步骤1：用户指定输出路径时直接使用。
    if output_file_path is not None:
        return output_file_path.resolve()

    # 步骤2：读取源音轨编码并选择无损复制扩展名。
    inspection_container = av.open(str(input_file_path))
    audio_stream, unused_audio_stream_count = get_audio_stream(
        inspection_container,
        audio_stream_position,
    )
    source_codec = audio_stream.codec_context.name
    inspection_container.close()

    stream_copy_setting = STREAM_COPY_SETTINGS.get(source_codec)
    output_extension = ".flac"
    if stream_copy_setting:
        output_extension = stream_copy_setting["extension"]

    # 步骤3：默认把产物写入 runtime/outputs。
    output_file_name = input_file_path.stem + "-audio" + output_extension
    return PROJECT_DIRECTORY / "runtime" / "outputs" / output_file_name


# ---------------------------
# 函数说明：创建本地媒体处理命令组。
# ---------------------------
@click.group()
def cli():
    """执行不依赖 AI 模型的本地媒体处理。"""
    pass


# ---------------------------
# 函数说明：以最高保真策略从视频或媒体文件抽取音轨。
# ---------------------------
@cli.command(name="extract-audio")
@click.argument(
    "media_file",
    type=click.Path(
        exists=True,
        file_okay=True,
        dir_okay=False,
        path_type=pathlib.Path,
    ),
    metavar="<本地视频或媒体文件>",
)
@click.option(
    "--output",
    "output_file",
    type=click.Path(path_type=pathlib.Path),
    default=None,
    metavar="<音频文件>",
    help="输出路径；默认按源编码写入 runtime/outputs",
)
@click.option(
    "--audio-stream",
    "audio_stream_position",
    type=click.IntRange(min=0),
    default=0,
    show_default=True,
    metavar="<音轨位置>",
    help="按音轨出现顺序选择，从 0 开始",
)
@click.option(
    "--overwrite",
    is_flag=True,
    help="允许覆盖已存在的输出文件",
)
def extract_audio_command(
    media_file,
    output_file,
    audio_stream_position,
    overwrite,
):
    """无损抽取音轨，不能直接复制时转为 FLAC。"""
    # 步骤1：确定输出路径和自动策略。
    resolved_input_file = media_file.resolve()
    resolved_output_file = resolve_audio_output_file(
        resolved_input_file,
        output_file,
        audio_stream_position,
    )

    # 步骤2：执行抽取并输出结构化摘要。
    result = extract_audio_track(
        resolved_input_file,
        resolved_output_file,
        audio_stream_position,
        overwrite,
    )
    click.echo(json.dumps(result, ensure_ascii=False, indent=2))


# ---------------------------
# 主流程：运行本地媒体处理 Click 命令组。
# ---------------------------
if __name__ == "__main__":
    # 步骤1：启动本地媒体处理命令组。
    cli()
