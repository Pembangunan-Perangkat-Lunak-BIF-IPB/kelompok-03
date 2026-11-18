"""Paket stages pipeline Human GVC.

WP-2 (Dhafin): qc_trimming, alignment, bam_processing
WP-3 (Yafits): variant_calling, filtering, anotasi
"""
from . import qc_trimming, alignment, bam_processing, variant_calling, filtering, anotasi

__all__ = [
    "qc_trimming",
    "alignment",
    "bam_processing",
    "variant_calling",
    "filtering",
    "anotasi",
]
