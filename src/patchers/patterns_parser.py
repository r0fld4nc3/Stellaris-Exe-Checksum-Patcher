"""
Turns the contents of the patterns file into the patcher's models.

The file is organised as game -> version -> platform -> patches:

    {
        "Stellaris": {
            "latest": {
                "windows": {
                    "exe_filename": "stellaris.exe",
                    "patches": {...}
                }
            }
        }
    }
"""

import logging
from typing import Dict, List

from patchers import auto_patch
from patchers.models import (
    PatchPattern,
    PatchPatternProperties,
    PlatformConfig,
    PlatformConfigProperties,
)

log = logging.getLogger("Patterns Parser")

# {
#   game: {
#       version: {
#           platform: PlatformConfig
#           }
#       }
# }
ParsedPatterns = Dict[str, Dict[str, Dict[str, PlatformConfig]]]


def parse_patterns(patterns_data: Dict) -> ParsedPatterns:
    """Parse the whole patterns file."""
    patterns = {}

    for game, versions_data in patterns_data.items():
        patterns[game] = {}
        for version, platforms_data in (versions_data or {}).items():
            patterns[game][version] = _parse_platforms(platforms_data or {})

    return patterns


def _parse_platforms(platforms_data: Dict) -> Dict[str, PlatformConfig]:
    platforms = {}

    for platform_key, platform_data in platforms_data.items():
        platforms[platform_key] = PlatformConfig(
            platform_name=platform_key,
            description=platform_data.get(PlatformConfigProperties.description, "N/A"),
            exe_filename=platform_data.get(PlatformConfigProperties.exe_filename, ""),
            path_postfix=platform_data.get(PlatformConfigProperties.path_postfix, ""),
            patches=_parse_patches(platform_key, platform_data.get(PlatformConfigProperties.patches, {})),
        )

    log.debug(f"{platforms=}")
    return platforms


def _parse_patches(platform_key: str, patches_data: Dict) -> Dict[str, PatchPattern]:
    patches = {}

    for patch_name, patch_data in patches_data.items():
        if "replace_call_with" not in patch_data:
            # Entry from the old regex-based patterns.json. "Update Patterns" fetches the new format
            log.warning(f"Skipping '{patch_name}' ({platform_key}): outdated patterns file format.")
            continue

        patches[patch_name] = PatchPattern(
            display_name=patch_data.get(PatchPatternProperties.display_name, "N/A"),
            description=patch_data.get(PatchPatternProperties.description, "N/A"),
            required=patch_data.get(PatchPatternProperties.required, False),
            enabled=patch_data.get(PatchPatternProperties.enabled, False),
            target_string=patch_data.get(PatchPatternProperties.target_string, auto_patch.DEFAULT_TARGET_STRING),
            replace_call_with=patch_data[PatchPatternProperties.replace_call_with],
            site_rule=auto_patch.SiteRule(
                near_strings=patch_data.get(PatchPatternProperties.near_strings, []),
                site_overrides=_parse_site_overrides(
                    patch_name, patch_data.get(PatchPatternProperties.site_overrides, {})
                ),
                takes_unmatched_sites=patch_data.get(PatchPatternProperties.takes_unmatched_sites, False),
            ),
        )

    return patches


def _parse_site_overrides(patch_name: str, overrides_data: Dict) -> Dict[str, List[int]]:
    """{build checksum: ["0x1ad54e", ...]} -> {build checksum: [0x1ad54e, ...]}. Invalid offsets are skipped."""
    overrides = {}

    for checksum, offsets in overrides_data.items():
        overrides[checksum] = []
        for offset in offsets:
            try:
                overrides[checksum].append(int(offset, 16))
            except TypeError, ValueError:
                log.warning(f"Skipping invalid site override '{offset}' of '{patch_name}'. Use hex, ex.: '0x1ad54e'.")

    return overrides
