class ExplorationCost:
    """Calculate exploration costs for subsurface project development."""

    def __init__(
        self,
        site_type,
        no_of_exploration_wells,
        acreage,
        ppi_multiplier,
    ):
        self.site_type = str(site_type)
        self.no_of_exploration_wells = int(no_of_exploration_wells)
        self.wellfield_acreage = float(acreage)
        self.ppi_multiplier = float(ppi_multiplier)

    def exploration_cost_calc(self) -> float:
        exploration_permitting_cost = 25_000
        lease_unit_cost = 38
        lease_cost = lease_unit_cost * self.wellfield_acreage

        exp_drilling_permitting = 300_000
        exp_drilling_unit_cost = 150_000
        exp_drilling_cost = exp_drilling_unit_cost * self.no_of_exploration_wells

        if self.site_type == "Greenfield":
            exp_activities_lump_sum = 900_000
        elif self.site_type == "Brownfield":
            exp_activities_lump_sum = 600_000
        else:
            raise ValueError(f"Unsupported site type: {self.site_type}")

        return (
            self.ppi_multiplier * exp_activities_lump_sum
            + exp_drilling_cost
            + exp_drilling_permitting
            + lease_cost
            + exploration_permitting_cost
        )
