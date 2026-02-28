"""
UniBillCal 命令行入口

用法:
    python main.py --platform alipay
    python main.py --config config/alipay.yaml
    python main.py --config config/alipay.yaml config/wechat.yaml  # 批量处理
"""

import argparse
import logging
import sys
from pathlib import Path

from unibillcal import BillPipeline, PlatformConfig


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("main")


def parse_args():
    parser = argparse.ArgumentParser(
        description="UniBillCal - 多平台账单统一处理框架"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--platform",
        help="平台名称（自动在 config/ 目录下查找 <platform>.yaml）",
    )
    group.add_argument(
        "--config",
        nargs="+",
        help="配置文件路径（支持多个文件批量处理）",
    )
    parser.add_argument(
        "--config-dir",
        default="config",
        help="配置文件目录（与 --platform 配合使用，默认 config/）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只执行到 Map 步骤，不写出文件（用于验证配置）",
    )
    return parser.parse_args()


def run_config(config_path: str, dry_run: bool = False) -> bool:
    """运行单个配置文件，返回是否成功"""
    try:
        logger.info("加载配置: %s", config_path)
        config = PlatformConfig.from_file(config_path)
        pipeline = BillPipeline(config)

        if dry_run:
            raw_df = pipeline.load()
            filtered = pipeline.filter(raw_df)
            mapped = pipeline.map(filtered)
            logger.info(
                "[%s] DRY-RUN 完成，映射后共 %d 行，列: %s",
                config.platform,
                len(mapped),
                list(mapped.columns),
            )
        else:
            result = pipeline.run()
            logger.info(
                "[%s] 处理完成，输出 %d 行",
                config.platform,
                len(result),
            )
        return True
    except Exception as exc:
        logger.error("处理 %s 失败: %s", config_path, exc, exc_info=True)
        return False


def main():
    args = parse_args()

    config_files = []
    if args.platform:
        config_path = Path(args.config_dir) / f"{args.platform}.yaml"
        if not config_path.exists():
            logger.error("配置文件不存在: %s", config_path)
            sys.exit(1)
        config_files = [str(config_path)]
    else:
        config_files = args.config

    success_count = 0
    for cfg_path in config_files:
        if run_config(cfg_path, dry_run=args.dry_run):
            success_count += 1

    total = len(config_files)
    logger.info("完成 %d/%d 个平台处理", success_count, total)
    if success_count < total:
        sys.exit(1)


if __name__ == "__main__":
    main()
