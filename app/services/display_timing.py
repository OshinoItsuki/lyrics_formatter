from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TimingResult:
    available_ms: int
    requested_ms: int
    pre_ms: int
    post_ms: int
    interval_ms: int
    protection_ms: int
    forced_cut_ms: int

    @property
    def reduction_ms(self) -> int:
        return self.requested_ms - (self.pre_ms + self.post_ms + self.interval_ms)

    @property
    def is_full(self) -> bool:
        return self.reduction_ms == 0 and self.forced_cut_ms == 0

    @property
    def severity(self) -> int:
        if self.forced_cut_ms > 0:
            return 5
        if self.pre_ms < self.protection_ms or self.post_ms < self.protection_ms:
            return 4
        if self.pre_ms < self.requested_pre_ms:
            return 3
        if self.post_ms < self.requested_post_ms:
            return 2
        if self.interval_ms < self.requested_interval_ms:
            return 1
        return 0

    requested_pre_ms: int = 0
    requested_post_ms: int = 0
    requested_interval_ms: int = 0


def simulate_gap(
    available_ms: int,
    pre_ms: int,
    post_ms: int,
    interval_ms: int,
    protection_ms: int,
) -> TimingResult:
    available_ms = max(0, int(available_ms))
    pre = max(0, int(pre_ms))
    post = max(0, int(post_ms))
    interval = max(0, int(interval_ms))
    protection = max(0, min(int(protection_ms), pre, post))
    requested = pre + post + interval
    deficit = max(0, requested - available_ms)

    cut = min(interval, deficit)
    interval -= cut
    deficit -= cut

    cut = min(max(0, post - protection), deficit)
    post -= cut
    deficit -= cut

    cut = min(max(0, pre - protection), deficit)
    pre -= cut
    deficit -= cut

    cut = min(post, deficit)
    post -= cut
    deficit -= cut

    cut = min(pre, deficit)
    pre -= cut
    deficit -= cut

    return TimingResult(
        available_ms=available_ms,
        requested_ms=requested,
        pre_ms=pre,
        post_ms=post,
        interval_ms=interval,
        protection_ms=protection,
        forced_cut_ms=deficit,
        requested_pre_ms=pre_ms,
        requested_post_ms=post_ms,
        requested_interval_ms=interval_ms,
    )
