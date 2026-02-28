"""
UniBillCal 命令行入口

用法:
  # 处理指定平台配置 + 统一处理配置
  python main.py --processing config/processing.yaml --platforms config/alipay.yaml config/wechat.yaml

  # 扫描 config/ 目录下所有平台配置（自动排除 processing.yaml）
  python main.py --processing config/processing.yaml --platform-dir config/

  # 只标准化单个平台（调试用，验证字段映射是否正确）
  python main.py --normalize config/alipay.yaml
"""

import argparse
import logging
import sys
from pathlib import Path

from unibillcal import BillPipeline, BillNormalizer, PlatformConfig


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("main")


def parse_args():
    parser = argparse.ArgumentParser(
        description="UniBillCal - 多平台账单统一处理框架",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--processing",
        metavar="PROCESSING_YAML",
        default="config/processing.yaml",
        help="统一处理配置文件路径（含关联表 + 最终输出配置，默认 config/processing.yaml）",
    )

    source_group = parser.add_mutually_exclusive_group()
    source_group.add_argument(
        "--platforms",
        nargs="+",
        metavar="PLATFORM_YAML",
        help="一个或多个平台配置文件路径",
    )
    source_group.add_argument(
        "--platform-dir",
        metavar="DIR",
        default="config",
        help="扫描目录下所有 *.yaml 文件作为平台配置（默认 config/）",
    )
    source_group.add_argument(
        "--normalize",
        metavar="PLATFORM_YAML",
        help="只标准化单个平台（调试模式，不执行汇总）",
    )

    return parser.parse_args()


def cmd_normalize(platform_yaml: str) -> None:
    """只执行单平台标准化，打印结果（用于验证配置）"""
    config = PlatformConfig.from_file(platform_yaml)
    normalizer = BillNormalizer(config)
    raw = normalizer.load()
    filtered = normalizer.filter(raw)
    unified = normalizer.map(filtered)
    logger.info(
        "[%s] 标准化完成：%d 行 → %d 行，统一字段: %s",
        config.platform, len(raw), len(unified), list(unified.columns),
    )
    print(unified.head(10).to_string(index=False))


def main():
    args = parse_args()

    try:
        if args.normalize:
            cmd_normalize(args.normalize)
            return

        processing_path = args.processing if Path(args.processing).exists() else None

        if args.platforms:
            pipeline = BillPipeline.from_files(
                platform_config_paths=args.platforms,
                processing_config_path=processing_path,
            )
        else:
            pipeline = BillPipeline.from_platform_dir(
                args.platform_dir,
                processing_config_path=processing_path,
            )

        result = pipeline.run()
        logger.info("处理完成，最终输出 %d 行", len(result))

    except Exception as exc:
        logger.error("执行失败: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
