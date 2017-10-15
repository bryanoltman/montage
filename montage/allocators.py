
"""
Differences between allocation for ratings and allocation for rankings:

* Rankings must have a quorum = number of jurors
"""
import random

from rdb import Vote, RoundEntry, joinedload, ACTIVE_STATUS

QUORUM_DISCARD_STRATEGIES = ('random', 'keep_best')


class VoteAllocator(object):
    def __init__(self, session, rnd, jury_weight_map, quorum,
                 discard_vote_jurors=None, quorum_discard_strategy='random'):
        self.session = session
        self.rnd = rnd
        if not sum(jury_weight_map.values()) == quorum:
            raise ValueError('expected sum of jury weights to be'
                             ' equal to quorum (%r): not %r'
                             % (quorum, sum(jury_weight_map.values())))
        self.jury_weight_map = jury_weight_map
        self.old_jury_weight_map = None
        self.quorum = quorum
        self.old_quorum = rnd.quorum
        self.discard_vote_jurors = set(discard_vote_jurors or [])
        if quorum_discard_strategy not in QUORUM_DISCARD_STRATEGIES:
            raise ValueError('expected one of %r for quorum_discard_strategy, not %r'
                             % (QUORUM_DISCARD_STRATEGIES, quorum_discard_strategy))
        self.quorum_discard_strategy = quorum_discard_strategy

        self.votes = None
        self.entries = None
        self.ufg_votes = None

    def plan(self):  # dry run
        return {'disqualified_entry_count': 0,
                'requalified_entry_count': 0,
                'open_votes_per_juror': {'JurorName': 123},
                'total_votes_per_juror': {'JurorName': 124}}

    def process(self):
        self._fetch_or_create_votes()

    def _fetch_or_create_votes(self):
        cur_votes = (self.session
                     .query(Vote)
                     .options(joinedload('round_entry'))
                     .join(RoundEntry)
                     .filter_by(round=self.rnd)
                     .order_by(Vote.id)
                     .all())
        cur_entries = (self.session
                       .query(RoundEntry)
                       .filter_by(round=self.rnd)
                       .order_by(RoundEntry.id)
                       .all())
        cur_entry_count = len(cur_entries)
        quorum_delta = self.quorum - self.old_quorum
        # TODO: sanity check that number of votes is divisible by
        # self.old_quorum and cur_entry_count
        if not cur_votes:
            shuffled_entries = random.shuffle(cur_entries)
            for _ in range(self.quorum):
                cur_votes.extend([Vote(round_entry=re, status=ACTIVE_STATUS)
                                  for re in shuffled_entries])
        elif quorum_delta > 0:
            shuffled_entries = [v.round_entry for v in cur_votes[:cur_entry_count]]
            for _ in range(quorum_delta):
                cur_votes.extend([Vote(round_entry=vote.round_entry,
                                       status=ACTIVE_STATUS)
                                  for vote in shuffled_entries])
        elif quorum_delta < 0:
            raise NotImplementedError()

        self.votes = cur_votes
        self.entries = cur_entries

    def _assign_votes(self):
        votes = self.votes

        for v in votes:
            if v.status == ACTIVE_STATUS or v.user in self.discard_vote_jurors:
                self.ufg_votes.append(v)








"""If votes haven't been created yet, make a big list of Votes with ACTIVE status.
If votes have already been created, select them all, in their id order (the original shuffle order).

If quorum has increased, we need to create a new set of votes _in the same order_ as the existing set.

If quorum has decreased, the weight map is implicitly going to change,
redrawing the vote "territories".

Note: Only allow decreasing quorum alongside removing jurors (maybe
only when it would make the quorum > len(jurors)).

Loop over the votes, canceling ACTIVE votes from removed jurors.


"""
