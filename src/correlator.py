"""
Genome-Music Correlator - Cross-reference genomic traits with music preferences.

Each correlation is a fun hypothesis with honest confidence rating.
"""


class GenomeMusicCorrelator:
    """Cross-reference genomic traits with music preferences."""

    def __init__(self, sonic_dna: dict, genome_context: dict, temporal: dict = None):
        self.sonic = sonic_dna
        self.genome = genome_context
        self.temporal = temporal  # temporal analysis results

    def _make_result(
        self,
        correlation_id: str,
        gene: str,
        gene_status: str,
        metric_name: str,
        metric_value,
        expected_ranges: dict,
        verdict: str,
        why_matters: str,
        why_bs: str,
        confidence: str,
    ) -> dict:
        """Standard correlation result format."""
        return {
            "id": correlation_id,
            "gene": gene,
            "gene_status": gene_status,
            "metric": metric_name,
            "value": metric_value,
            "expected_ranges": expected_ranges,
            "verdict": verdict,
            "why_matters": why_matters,
            "why_bs": why_bs,
            "confidence": confidence,  # "speculative", "weak", "moderate"
        }

    def correlate_caffeine_tempo(self) -> dict | None:
        """
        CYP1A2 x Average Tempo
        Hypothesis: Fast caffeine metabolizers prefer higher BPM.
        Theory: Higher stimulation tolerance -> seek energetic music.

        Expected ranges:
        - fast: 125-140 BPM
        - intermediate: 110-125 BPM
        - slow: 95-115 BPM
        """
        genes = self.genome.get("genes", {})
        if "CYP1A2" not in genes:
            return None

        gene_info = genes["CYP1A2"]
        status = gene_info["status"]

        # Get average tempo from sonic DNA
        audio_features = self.sonic.get("audio_features", {})
        avg_tempo = audio_features.get("tempo", {}).get("mean", 0)

        if avg_tempo == 0:
            return None

        expected_ranges = {
            "fast": {"min": 125, "max": 140},
            "intermediate": {"min": 110, "max": 125},
            "slow": {"min": 95, "max": 115},
        }

        # Generate verdict
        range_info = expected_ranges.get(status, {"min": 0, "max": 999})
        in_range = range_info["min"] <= avg_tempo <= range_info["max"]

        if in_range:
            verdict = f"Textbook case! Your {status} metabolism matches your {avg_tempo:.0f} BPM preference perfectly. Science wins today."
        else:
            if avg_tempo > range_info["max"]:
                verdict = f"Plot twist: Your {status} metabolism says {range_info['max']} BPM max, but you're vibing at {avg_tempo:.0f}. Clearly caffeine isn't your only stimulant."
            else:
                verdict = f"Unexpected chill: {status} metabolizers usually rock harder, but you're cruising at {avg_tempo:.0f} BPM. Maybe you're burnt out?"

        why_matters = (
            "CYP1A2 controls how fast you break down caffeine. Fast metabolizers clear it quickly, "
            "potentially seeking more stimulation. Slow metabolizers stay wired longer, might avoid "
            "additional intensity. Tempo is a proxy for musical energy."
        )

        why_bs = (
            "Tempo preferences are shaped by culture, mood, genre exposure, and what you were "
            "listening to when you fell in love / got dumped / aced an exam. Genes are like 5% of this story, max."
        )

        return self._make_result(
            correlation_id="caffeine_tempo",
            gene="CYP1A2",
            gene_status=status,
            metric_name="Average Tempo (BPM)",
            metric_value=round(avg_tempo, 1),
            expected_ranges=expected_ranges,
            verdict=verdict,
            why_matters=why_matters,
            why_bs=why_bs,
            confidence="weak",
        )

    def correlate_chronotype_hours(self) -> dict | None:
        """
        Chronotype (ME score) x Peak Listening Hour
        Hypothesis: Morning types listen earlier in the day.

        Requires temporal data + circadian profile.

        Expected:
        - Morning type (ME > 0): peak before 14:00
        - Evening type (ME < 0): peak after 16:00
        - Intermediate (ME = 0): flexible
        """
        chronotype = self.genome.get("chronotype")
        if not chronotype or not self.temporal:
            return None

        me_score = chronotype.get("me_score", 0)
        me_label = chronotype.get("me_label", "Unknown")

        # Get peak hour from temporal analysis
        peak_hour_int = self.temporal.get("peak_hour")
        if peak_hour_int is None:
            return None

        expected_ranges = {
            "Morning": {"min": 6, "max": 14, "me_range": "ME > 0"},
            "Evening": {"min": 16, "max": 23, "me_range": "ME < 0"},
            "Intermediate": {"min": 10, "max": 20, "me_range": "ME ~ 0"},
        }

        # Determine chronotype category
        if me_score > 0:
            chrono_category = "Morning"
        elif me_score < 0:
            chrono_category = "Evening"
        else:
            chrono_category = "Intermediate"

        range_info = expected_ranges[chrono_category]
        in_range = range_info["min"] <= peak_hour_int <= range_info["max"]

        if in_range:
            verdict = f"Clockwork precision! Your {me_label} chronotype peaks at {peak_hour_int}:00. You're living on biological time."
        else:
            verdict = f"Rebellion detected: {me_label} people usually peak {range_info['min']}-{range_info['max']}:00, but you're jamming at {peak_hour_int}:00. Work schedule? Night shifts? Chaos?"

        why_matters = (
            "Chronotype (morningness-eveningness) affects when you're most alert and receptive. "
            "Morning types have earlier cortisol peaks and prefer daytime activity. Evening types "
            "hit their stride later. Music listening often aligns with peak alertness windows."
        )

        why_bs = (
            "Work schedules, kids, insomnia, time zones, and 'I only listen during commute' destroy "
            "any clean genetic signal. Also, streaming data is biased toward active listening, "
            "not background/sleep playlists."
        )

        return self._make_result(
            correlation_id="chronotype_hours",
            gene="Circadian Rhythm Genes",
            gene_status=me_label,
            metric_name="Peak Listening Hour",
            metric_value=f"{peak_hour_int}:00",
            expected_ranges=expected_ranges,
            verdict=verdict,
            why_matters=why_matters,
            why_bs=why_bs,
            confidence="moderate",
        )

    def correlate_comt_valence(self) -> dict | None:
        """
        COMT x Average Valence
        Hypothesis: Fast COMT (rapid dopamine breakdown) -> prefer high-valence (positive) music to compensate.

        Expected:
        - fast: 0.55-0.75 valence (seek positivity)
        - intermediate: 0.40-0.60
        - slow: 0.35-0.55 (already dopamine-rich, tolerate darker music)
        """
        genes = self.genome.get("genes", {})
        if "COMT" not in genes:
            return None

        gene_info = genes["COMT"]
        status = gene_info["status"]

        # Get average valence
        audio_features = self.sonic.get("audio_features", {})
        avg_valence = audio_features.get("valence", {}).get("mean", 0)

        if avg_valence == 0:
            return None

        expected_ranges = {
            "fast": {"min": 0.55, "max": 0.75},
            "intermediate": {"min": 0.40, "max": 0.60},
            "slow": {"min": 0.35, "max": 0.55},
        }

        range_info = expected_ranges.get(status, {"min": 0, "max": 1})
        in_range = range_info["min"] <= avg_valence <= range_info["max"]

        if in_range:
            verdict = f"Dopamine economics confirmed: {status} COMT, {avg_valence:.2f} valence. You're chasing the neurochemical balance your genes dictate."
        else:
            if avg_valence > range_info["max"]:
                verdict = f"Suspiciously happy playlist for {status} COMT. Valence at {avg_valence:.2f} suggests you're either faking it or found a great therapist."
            else:
                verdict = f"Darker than expected: {status} COMT usually runs {range_info['min']:.2f}-{range_info['max']:.2f}, but you're at {avg_valence:.2f}. Embracing the void, are we?"

        why_matters = (
            "COMT breaks down dopamine in the prefrontal cortex. Fast variants clear it quickly, "
            "potentially leading to reward-seeking behavior and preference for uplifting stimuli. "
            "Slow variants maintain higher baseline dopamine, tolerating lower-valence emotional content."
        )

        why_bs = (
            "Valence is Spotify's guess at 'positivity' based on musical features, not lyrical content. "
            "Also, your mood, life events, and the fact that sad songs can feel good (catharsis!) make "
            "this correlation extremely noisy."
        )

        return self._make_result(
            correlation_id="comt_valence",
            gene="COMT",
            gene_status=status,
            metric_name="Average Valence",
            metric_value=round(avg_valence, 2),
            expected_ranges=expected_ranges,
            verdict=verdict,
            why_matters=why_matters,
            why_bs=why_bs,
            confidence="speculative",
        )

    def correlate_bdnf_diversity(self) -> dict | None:
        """
        BDNF x Diversity Index
        Hypothesis: Normal BDNF (good neuroplasticity) -> higher musical diversity.

        Expected:
        - normal: diversity 55-85
        - reduced: diversity 30-55 (prefer familiar)
        """
        genes = self.genome.get("genes", {})
        if "BDNF" not in genes:
            return None

        gene_info = genes["BDNF"]
        status = gene_info["status"]

        # Get diversity index
        diversity_data = self.sonic.get("diversity", {})
        diversity_index = diversity_data.get("diversity_index", 0)

        if diversity_index == 0:
            return None

        expected_ranges = {
            "normal": {"min": 55, "max": 85},
            "reduced": {"min": 30, "max": 55},
        }

        range_info = expected_ranges.get(status, {"min": 0, "max": 100})
        in_range = range_info["min"] <= diversity_index <= range_info["max"]

        if in_range:
            verdict = f"Neuroplasticity wins: {status} BDNF predicts diversity of {range_info['min']}-{range_info['max']}, you scored {diversity_index:.0f}. Your brain's wiring matches your wandering ears."
        else:
            if diversity_index > range_info["max"]:
                verdict = f"Genre omnivore alert: {status} BDNF says {range_info['max']}, but you hit {diversity_index:.0f}. Clearly your neurons didn't read the manual."
            else:
                verdict = f"Comfort zone specialist: {status} BDNF expected {range_info['min']}-{range_info['max']}, but you're at {diversity_index:.0f}. Found your lane and staying in it."

        why_matters = (
            "BDNF (Brain-Derived Neurotrophic Factor) supports neuroplasticity - the brain's ability "
            "to form new connections and adapt. Higher BDNF activity correlates with openness to new "
            "experiences. Musical diversity is a behavioral proxy for novelty-seeking."
        )

        why_bs = (
            "Diversity scores are biased by: genre classification quirks, algorithmic recommendations, "
            "how long you've been using the platform, and whether you let your kids use your account. "
            "Also, BDNF's role is way more complex than 'novelty gene'."
        )

        return self._make_result(
            correlation_id="bdnf_diversity",
            gene="BDNF",
            gene_status=status,
            metric_name="Diversity Index",
            metric_value=round(diversity_index, 1),
            expected_ranges=expected_ranges,
            verdict=verdict,
            why_matters=why_matters,
            why_bs=why_bs,
            confidence="speculative",
        )

    def correlate_serotonin_emotional_range(self) -> dict | None:
        """
        SLC6A4 x Valence Standard Deviation
        Hypothesis: Short serotonin transporter -> wider emotional range in music choices.

        Expected:
        - normal: valence std 0.15-0.25 (stable preferences)
        - short: valence std 0.25-0.40 (emotional extremes - both very happy and very sad music)
        """
        genes = self.genome.get("genes", {})
        if "SLC6A4" not in genes:
            return None

        gene_info = genes["SLC6A4"]
        status = gene_info["status"]

        # Get valence standard deviation
        audio_features = self.sonic.get("audio_features", {})
        valence_std = audio_features.get("valence", {}).get("std", 0)

        if valence_std == 0:
            return None

        expected_ranges = {
            "normal": {"min": 0.15, "max": 0.25},
            "short": {"min": 0.25, "max": 0.40},
        }

        range_info = expected_ranges.get(status, {"min": 0, "max": 1})
        in_range = range_info["min"] <= valence_std <= range_info["max"]

        if in_range:
            verdict = f"Emotional volatility confirmed: {status} transporter, valence swing of {valence_std:.2f}. Your serotonin wiring matches your emotional soundtrack range."
        else:
            if valence_std > range_info["max"]:
                verdict = f"Extreme emotional whiplash: {status} variant expected {range_info['max']:.2f} max, you're at {valence_std:.2f}. Bipolar playlist energy."
            else:
                verdict = f"Surprisingly stable: {status} transporter usually shows {range_info['min']:.2f}-{range_info['max']:.2f} range, but you're only at {valence_std:.2f}. Found your emotional equilibrium?"

        why_matters = (
            "SLC6A4 (serotonin transporter) regulates serotonin reuptake. Short variants are linked "
            "to higher emotional reactivity and stress sensitivity. This might manifest as preference "
            "for both extremely positive and extremely negative music - wide emotional range."
        )

        why_bs = (
            "Emotional range in music could equally be: eclectic taste, mood playlists, sharing account "
            "with partner, or just having a 'sad songs' folder next to 'gym bangers'. Valence variance "
            "is not a clinical mood measure."
        )

        return self._make_result(
            correlation_id="serotonin_emotional_range",
            gene="SLC6A4",
            gene_status=status,
            metric_name="Valence Standard Deviation",
            metric_value=round(valence_std, 2),
            expected_ranges=expected_ranges,
            verdict=verdict,
            why_matters=why_matters,
            why_bs=why_bs,
            confidence="speculative",
        )

    def correlate_drd2_repeat_plays(self) -> dict | None:
        """
        DRD2/ANKK1 x Repeat Ratio
        Hypothesis: Reduced dopamine receptors -> more repeat plays (reward-seeking through familiarity).

        Expected:
        - normal: repeat ratio < 0.15
        - reduced: repeat ratio > 0.20
        """
        genes = self.genome.get("genes", {})
        if "DRD2" not in genes and "ANKK1" not in genes:
            return None

        # Prefer DRD2, fall back to ANKK1
        gene_name = "DRD2" if "DRD2" in genes else "ANKK1"
        gene_info = genes[gene_name]
        status = gene_info["status"]

        # Get repeat ratio from diversity metrics
        diversity = self.sonic.get("diversity", {})
        repeat_ratio = diversity.get("repeat_ratio", 0)

        expected_ranges = {
            "normal": {"min": 0.00, "max": 0.15},
            "reduced": {"min": 0.20, "max": 1.00},
        }

        range_info = expected_ranges.get(status, {"min": 0, "max": 1})
        in_range = range_info["min"] <= repeat_ratio <= range_info["max"]

        if in_range:
            verdict = f"Dopamine reward loop detected: {status} receptors, {repeat_ratio:.2f} repeat ratio. You're hitting replay because your brain chemistry demands it."
        else:
            if repeat_ratio > range_info["max"]:
                verdict = f"Obsessive replay behavior: {status} variant says {range_info['max']:.2f} max, you're at {repeat_ratio:.2f}. Found 'the song' and can't let go?"
            else:
                verdict = f"Novelty hunter: {status} dopamine receptors usually repeat more, but you're only at {repeat_ratio:.2f}. Immune to earworms?"

        why_matters = (
            "DRD2/ANKK1 variants affect dopamine D2 receptor density. Reduced receptor availability "
            "may lead to reward-seeking through repetition - replaying familiar, rewarding songs to "
            "compensate for lower baseline dopamine signaling."
        )

        why_bs = (
            "Repeat plays are confounded by: algorithm loops, workout playlists, kids demanding "
            "'Baby Shark' 47 times, and that one song that got you through a breakup. Dopamine "
            "receptors don't explain why Spotify autoplays the same 5 songs."
        )

        return self._make_result(
            correlation_id="drd2_repeat_plays",
            gene=gene_name,
            gene_status=status,
            metric_name="Repeat Play Ratio",
            metric_value=round(repeat_ratio, 2),
            expected_ranges=expected_ranges,
            verdict=verdict,
            why_matters=why_matters,
            why_bs=why_bs,
            confidence="speculative",
        )

    def correlate_oprm1_sad_music(self) -> dict | None:
        """
        OPRM1 x Low-Valence Track Percentage
        Hypothesis: Enhanced opioid receptor -> more low-valence (sad) music.
        The "sweet sadness" effect: enhanced receptor means more pleasure from emotional catharsis.

        Low valence = valence < 0.35

        Expected:
        - normal: 15-25% low-valence tracks
        - enhanced: 25-40% low-valence tracks
        """
        genes = self.genome.get("genes", {})
        if "OPRM1" not in genes:
            return None

        gene_info = genes["OPRM1"]
        status = gene_info["status"]

        # Get low-valence percentage from audio features
        audio_features = self.sonic.get("audio_features", {})
        low_valence_pct = audio_features.get("low_valence_pct", 0)

        if low_valence_pct == 0:
            return None

        expected_ranges = {
            "normal": {"min": 15, "max": 25},
            "enhanced": {"min": 25, "max": 40},
        }

        range_info = expected_ranges.get(status, {"min": 0, "max": 100})
        in_range = range_info["min"] <= low_valence_pct <= range_info["max"]

        if in_range:
            verdict = f"Sweet sadness confirmed: {status} OPRM1, {low_valence_pct:.1f}% sad tracks. Your opioid receptors are milking emotional catharsis for all it's worth."
        else:
            if low_valence_pct > range_info["max"]:
                verdict = f"Melancholy addict: {status} variant expected {range_info['max']:.0f}% max sad music, you're at {low_valence_pct:.1f}%. Living in your feelings much?"
            else:
                verdict = f"Avoiding the void: {status} OPRM1 usually embraces sad music more ({range_info['min']:.0f}%+), but you're only at {low_valence_pct:.1f}%. Toxically positive?"

        why_matters = (
            "OPRM1 (mu-opioid receptor) mediates emotional and physical pain relief. Enhanced variants "
            "may experience stronger pleasure from emotional catharsis, making sad music more rewarding. "
            "This is the neuroscience behind 'why sad songs feel good'."
        )

        why_bs = (
            "Low valence doesn't mean 'sad lyrics' - it's just musical features. Also, cultural "
            "context, personal history, and whether you're using music to process emotions vs. "
            "avoid them completely muddy this. Not everyone with OPRM1 variants is crying to Adele."
        )

        return self._make_result(
            correlation_id="oprm1_sad_music",
            gene="OPRM1",
            gene_status=status,
            metric_name="Low-Valence Track Percentage",
            metric_value=round(low_valence_pct, 1),
            expected_ranges=expected_ranges,
            verdict=verdict,
            why_matters=why_matters,
            why_bs=why_bs,
            confidence="speculative",
        )

    def run_all(self) -> list[dict]:
        """Run all correlations, skip those with missing gene data. Return sorted by confidence."""
        methods = [
            self.correlate_caffeine_tempo,
            self.correlate_chronotype_hours,
            self.correlate_comt_valence,
            self.correlate_bdnf_diversity,
            self.correlate_serotonin_emotional_range,
            self.correlate_drd2_repeat_plays,
            self.correlate_oprm1_sad_music,
        ]
        results = []
        for method in methods:
            result = method()
            if result is not None:
                results.append(result)

        confidence_order = {"moderate": 0, "weak": 1, "speculative": 2}
        results.sort(key=lambda r: confidence_order.get(r["confidence"], 3))
        return results
