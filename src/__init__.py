"""Music Taste Genome - Cross-reference genomic data with music preferences."""

from .genome_linker import (
    MUSIC_RELEVANT_GENES,
    load_genome_findings,
    load_circadian_profile,
    build_genome_context,
)
from .correlator import GenomeMusicCorrelator

__version__ = "0.1.0"

__all__ = [
    "MUSIC_RELEVANT_GENES",
    "load_genome_findings",
    "load_circadian_profile",
    "build_genome_context",
    "GenomeMusicCorrelator",
]
