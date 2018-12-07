
class RplMrHof(object):

    # Constants defined in RFC 6550
    INFINITE_RANK = 65535

    # Constants defined in RFC 8180
    UPPER_LIMIT_OF_ACCEPTABLE_ETX = 3
    MINIMUM_STEP_OF_RANK = 1
    MAXIMUM_STEP_OF_RANK = 9

    # Custom constants
    MAX_NUM_OF_CONSECUTIVE_FAILURES_WITHOUT_ACK = 10
    ETX_DEFAULT = UPPER_LIMIT_OF_ACCEPTABLE_ETX
    # if we have a "good" link to the parent, stay with the parent even if the
    # rank of the parent is worse than the best neighbor by more than
    # PARENT_SWITCH_RANK_THRESHOLD. rank_increase is computed as per Section
    # 5.1.1. of RFC 8180.
    ETX_GOOD_LINK = 2
    PARENT_SWITCH_RANK_INCREASE_THRESHOLD = (
        ((3 * ETX_GOOD_LINK) - 2) * d.RPL_MINHOPRANKINCREASE
    )

    def __init__(self, rpl):
        self.rpl = rpl
        self.neighbors = []
        self.rank = None
        self.preferred_parent = None

    @property
    def parents(self):
        # a parent should have a lower rank than us by MinHopRankIncrease at
        # least. See section 3.5.1 of RFC 6550:
        #    "MinHopRankIncrease is the minimum increase in Rank between a node
        #     and any of its DODAG parents."
        _parents = []
        for neighbor in self.neighbors:
            if self._calculate_rank(neighbor) is None:
                # skip this one
                continue

            if (
                    (self.rank is None)
                    or
                    (
                        d.RPL_MINHOPRANKINCREASE <=
                        self.rank - neighbor['advertised_rank']
                    )
                ):
                _parents.append(neighbor)

        return _parents

    def update(self, dio):
        mac_addr = dio['mac']['srcMac']
        rank = dio['app']['rank']

        # update neighbor's rank
        neighbor = self._find_neighbor(mac_addr)
        if neighbor is None:
            neighbor = self._add_neighbor(mac_addr)
        self._update_neighbor_rank(neighbor, rank)

        # if we received the infinite rank from our preferred parent,
        # invalidate our rank
        if (
                (self.preferred_parent == neighbor)
                and
                (rank == d.RPL_INFINITE_RANK)
            ):
            self.rank = None

        # change preferred parent if necessary
        self._update_preferred_parent()

    def get_preferred_parent(self):
        if self.preferred_parent is None:
            return None
        else:
            return self.preferred_parent['mac_addr']

    def update_etx(self, cell, mac_addr, isACKed):
        neighbor = self._find_neighbor(mac_addr)
        if neighbor is None:
            # we've not received DIOs from this neighbor; ignore the neighbor
            return
        elif (
                (cell.mac_addr == mac_addr)
                and
                (d.CELLOPTION_TX in cell.options)
                and
                (d.CELLOPTION_SHARED not in cell.options)
            ):
            neighbor['numTx'] += 1
            if isACKed is True:
                neighbor['numTxAck'] += 1
            self._update_neighbor_rank_increase(neighbor)
            self._update_preferred_parent()

    def _add_neighbor(self, mac_addr):
        assert self._find_neighbor(mac_addr) is None

        neighbor = {
            'mac_addr': mac_addr,
            'advertised_rank': None,
            'rank_increase': None,
            'numTx': 0,
            'numTxAck': 0
        }
        self.neighbors.append(neighbor)
        self._update_neighbor_rank_increase(neighbor)
        return neighbor

    def _find_neighbor(self, mac_addr):
        for neighbor in self.neighbors:
            if neighbor['mac_addr'] == mac_addr:
                return neighbor
        return None

    def _update_neighbor_rank(self, neighbor, new_advertised_rank):
        neighbor['advertised_rank'] = new_advertised_rank

    def _update_neighbor_rank_increase(self, neighbor):
        if neighbor['numTxAck'] == 0:
            if neighbor['numTx'] > self.MAX_NUM_OF_CONSECUTIVE_FAILURES_WITHOUT_ACK:
                etx = self.UPPER_LIMIT_OF_ACCEPTABLE_ETX + 1 # set invalid ETX
            else:
                # ETX is not available
                etx = None
        else:
            etx = float(neighbor['numTx']) / neighbor['numTxAck']

        if etx is None:
            etx = self.ETX_DEFAULT

        if etx > self.UPPER_LIMIT_OF_ACCEPTABLE_ETX:
            step_of_rank = None
        else:
            step_of_rank = (3 * etx) - 2
        if step_of_rank is None:
            # this neighbor will not be considered as a parent
            neighbor['rank_increase'] = None
        else:
            assert self.MINIMUM_STEP_OF_RANK <= step_of_rank
            # step_of_rank never exceeds 7 because the upper limit of acceptable
            # ETX is 3, which is defined in Section 5.1.1 of RFC 8180
            assert step_of_rank <= self.MAXIMUM_STEP_OF_RANK
            neighbor['rank_increase'] = step_of_rank * d.RPL_MINHOPRANKINCREASE

        if neighbor == self.preferred_parent:
            self.rank = self._calculate_rank(self.preferred_parent)

    def _calculate_rank(self, neighbor):
        if (
                (neighbor is None)
                or
                (neighbor['advertised_rank'] is None)
                or
                (neighbor['rank_increase'] is None)
            ):
            return None
        elif neighbor['advertised_rank'] == self.INFINITE_RANK:
            # this neighbor should be ignored
            return None
        else:
            rank = neighbor['advertised_rank'] + neighbor['rank_increase']

            if rank > self.INFINITE_RANK:
                return self.INFINITE_RANK
            else:
                return rank

    def _update_preferred_parent(self):
        if (
                (self.preferred_parent is not None)
                and
                (self.preferred_parent['advertised_rank'] is not None)
                and
                (self.rank is not None)
                and
                (
                    (self.preferred_parent['advertised_rank'] - self.rank) <
                    d.RPL_PARENT_SWITCH_RANK_THRESHOLD
                )
                and
                (
                    self.preferred_parent['rank_increase'] <
                    self.PARENT_SWITCH_RANK_INCREASE_THRESHOLD
                )
            ):
            # stay with the current parent. the link to the parent is
            # good. but, if the parent rank is higher than us and the
            # difference is more than d.RPL_PARENT_SWITCH_RANK_THRESHOLD, we dump
            # the parent. otherwise, we may create a routing loop.
            return

        try:
            candidate = min(self.parents, key=self._calculate_rank)
            new_rank = self._calculate_rank(candidate)
        except ValueError:
            # self.parents is empty
            candidate = None
            new_rank = None

        if new_rank is None:
            # we don't have any available parent
            new_parent = None
        elif self.rank is None:
            new_parent = candidate
            self.rank = new_rank
        else:
            # (new_rank is not None) and (self.rank is None)
            rank_difference = self.rank - new_rank

            # Section 6.4, RFC 8180
            #
            #   Per [RFC6552] and [RFC6719], the specification RECOMMENDS the
            #   use of a boundary value (PARENT_SWITCH_RANK_THRESHOLD) to avoid
            #   constant changes of the parent when ranks are compared.  When
            #   evaluating a parent that belongs to a smaller path cost than
            #   the current minimum path, the candidate node is selected as the
            #   new parent only if the difference between the new path and the
            #   current path is greater than the defined
            #   PARENT_SWITCH_RANK_THRESHOLD.

            if rank_difference is not None:
                if d.RPL_PARENT_SWITCH_RANK_THRESHOLD < rank_difference:
                    new_parent = candidate
                    self.rank = new_rank
                else:
                    # no change on preferred parent
                    new_parent = self.preferred_parent

        if (
                (new_parent is not None)
                and
                (new_parent != self.preferred_parent)
            ):
            # change to the new preferred parent

            if self.preferred_parent is None:
                old_parent_mac_addr = None
            else:
                old_parent_mac_addr = self.preferred_parent['mac_addr']

            self.preferred_parent = new_parent
            if new_parent is None:
                new_parent_mac_addr = None
            else:
                new_parent_mac_addr = self.preferred_parent['mac_addr']

            self.rpl.indicate_preferred_parent_change(
                old_preferred = old_parent_mac_addr,
                new_preferred = new_parent_mac_addr
            )

            # reset Trickle Timer
            self.rpl.trickle_timer.reset()
        elif (
                (new_parent is None)
                and
                (self.preferred_parent is not None)
            ):
            old_parent_mac_addr = self.preferred_parent['mac_addr']
            self.neighbors = []
            self.preferred_parent = None
            self.rank = None
            self.rpl.indicate_preferred_parent_change(
                old_preferred = old_parent_mac_addr,
                new_preferred = None
            )
            self.rpl.local_repair()
        else:
            # do nothing
            pass