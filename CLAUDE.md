# CLAUDE.md -- Music Taste Genome

## Project
Local-first system that maps Spotify listening patterns against audio features to build a "sonic DNA" profile, then cross-references with genomic findings from genome-insight for fun correlations.

## Stack
- Python 3.11+, requests, python-dotenv
- Spotify Web API (PKCE OAuth)
- Genome data: reads findings.json from genome-insight project

## Key Rules
- All genome x music correlations are SPECULATIVE -- never claim causation
- Genome data stays in genome-insight -- this project reads via file path, never copies
- Privacy-first: no cloud storage of listening or genome data
- Tone in reports: playful skeptic, self-aware humor

## CLI
```
.\run.ps1 auth                                    # One-time Spotify setup
.\run.ps1 collect                                  # Fetch Spotify data
.\run.ps1 analyze --genome path\to\findings.json   # Analyze + report
.\run.ps1 full --genome path\to\findings.json      # End-to-end
```

## Structure
- src/auth/ -- Spotify OAuth PKCE
- src/collectors/ -- Spotify API data fetching
- src/analyzers/ -- Sonic profiler + temporal analysis
- src/genome_linker.py -- Read genome-insight findings
- src/correlator.py -- 7 genome x music hypotheses
- src/reporter.py -- Markdown report with ASCII viz
