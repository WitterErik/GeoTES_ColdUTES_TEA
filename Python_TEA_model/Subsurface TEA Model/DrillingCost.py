class DrillingCost:
    """Calculate drilling and completion costs for subsurface wells."""

    def __init__(
        self,
        production_wells,
        injection_wells,
        depth,
        production_thickness,
        casing_size,
        success_rate,
        ppi_multiplier,
        well_profile,
        completion_type,
    ):
        self.no_of_production_wells = int(production_wells)
        self.no_of_injection_wells = int(injection_wells)
        self.well_depth = float(depth)
        self.production_thickness = float(production_thickness)
        self.casing_size = str(casing_size)
        self.success_rate = float(success_rate)
        self.ppi_multiplier = float(ppi_multiplier)
        self.well_profile = str(well_profile)
        self.completion_type = str(completion_type)
        self.total_drilling_cost = 0.0

    def well_cost(self) -> float:
        if (
            self.well_profile == "Vertical"
            and self.completion_type == "Openhole"
            and self.casing_size == "Small"
        ):
            return (
                0.13709983 * self.well_depth ** 2
                + 129.610328 * self.well_depth
                + 1_205_587.571
            )

        if (
            self.well_profile == "Vertical"
            and self.completion_type == "Openhole"
            and self.casing_size == "Large"
        ):
            return (
                0.189267288 * self.well_depth ** 2
                + 293.4517365 * self.well_depth
                + 1_326_526.313
            )

        if (
            self.well_profile == "Deviated"
            and self.completion_type == "Openhole"
            and self.casing_size == "Small"
        ):
            return (
                0.153396734 * self.well_depth ** 2
                + 120.3169953 * self.well_depth
                + 1_431_801.544
                - (105 * self.production_thickness + 12_300)
            )

        if (
            self.well_profile == "Deviated"
            and self.completion_type == "Openhole"
            and self.casing_size == "Large"
        ):
            return (
                0.199504332 * self.well_depth ** 2
                + 296.1301091 * self.well_depth
                + 1_697_867.709
                - (189 * self.production_thickness + 12_300)
            )

        if (
            self.well_profile == "Vertical"
            and self.completion_type == "Liner"
            and self.casing_size == "Small"
        ):
            return (
                0.13709983 * self.well_depth ** 2
                + 129.610328 * self.well_depth
                + 1_205_587.571
                + (105 * self.production_thickness + 12_300)
            )

        if (
            self.well_profile == "Vertical"
            and self.completion_type == "Liner"
            and self.casing_size == "Large"
        ):
            return (
                0.189267288 * self.well_depth ** 2
                + 293.4517365 * self.well_depth
                + 1_326_526.313
                + (189 * self.production_thickness + 12_300)
            )

        if (
            self.well_profile == "Deviated"
            and self.completion_type == "Liner"
            and self.casing_size == "Small"
        ):
            return (
                0.153396734 * self.well_depth ** 2
                + 120.3169953 * self.well_depth
                + 1_431_801.544
            )

        if (
            self.well_profile == "Deviated"
            and self.completion_type == "Liner"
            and self.casing_size == "Large"
        ):
            return (
                0.199504332 * self.well_depth ** 2
                + 296.1301091 * self.well_depth
                + 1_697_867.709
            )

        raise ValueError(
            f"Unsupported profile '{self.well_profile}', completion '{self.completion_type}', or casing size '{self.casing_size}'"
        )

    def total_dc(self, well_cost_calc: float) -> float:
        self.total_drilling_cost = (
            well_cost_calc
            * (self.no_of_production_wells + self.no_of_injection_wells)
            * self.success_rate
            * self.ppi_multiplier
        )
        indirect_cost = 0.05 * self.total_drilling_cost
        return self.total_drilling_cost + indirect_cost
