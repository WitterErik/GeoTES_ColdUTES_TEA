class DrillingCostUpdated:
    """Calculate updated drilling and completion costs for subsurface wells."""

    def __init__(
        self,
        PWells,
        IWells,
        Depth,
        ProdThickness,
        CasingSize,
        SuccessRate,
        PPI,
        Profile,
        CompType,
    ):
        self.NoOfProductionWells = int(PWells)
        self.NoOfInjectionWells = int(IWells)
        self.WellDepth = float(Depth)
        self.ProductionThickness = float(ProdThickness)
        self.CasingSize = str(CasingSize)
        self.SuccessRate = float(SuccessRate)
        self.PPImultiplier = float(PPI)
        self.WellProfile = str(Profile)
        self.CompletionType = str(CompType)
        self.TotalDrillingCost = 0.0

    def WellCost(self) -> float:
        if (
            self.WellProfile == "Vertical"
            and self.CompletionType == "Openhole"
            and self.CasingSize == "Small"
        ):
            return (
                0.129294 * self.WellDepth ** 2
                + 121.90572 * self.WellDepth
                + 619928.376659
            )

        if (
            self.WellProfile == "Vertical"
            and self.CompletionType == "Openhole"
            and self.CasingSize == "Large"
        ):
            return (
                0.138493 * self.WellDepth ** 2
                + 363.789891 * self.WellDepth
                + 575820.337456
            )

        if (
            self.WellProfile == "Deviated"
            and self.CompletionType == "Openhole"
            and self.CasingSize == "Small"
        ):
            return (
                0.132716 * self.WellDepth ** 2
                + 148.795084 * self.WellDepth
                + 786108.246876
            )

        if (
            self.WellProfile == "Deviated"
            and self.CompletionType == "Openhole"
            and self.CasingSize == "Large"
        ):
            return (
                0.141821 * self.WellDepth ** 2
                + 394.446239 * self.WellDepth
                + 863756.505516
            )

        if (
            self.WellProfile == "Vertical"
            and self.CompletionType == "Liner"
            and self.CasingSize == "Small"
        ):
            return (
                0.128944 * self.WellDepth ** 2
                + 131.009017 * self.WellDepth
                + 660304.471681
            )

        if (
            self.WellProfile == "Vertical"
            and self.CompletionType == "Liner"
            and self.CasingSize == "Large"
        ):
            return (
                0.138087 * self.WellDepth ** 2
                + 373.355967 * self.WellDepth
                + 630723.904561
            )

        if (
            self.WellProfile == "Deviated"
            and self.CompletionType == "Liner"
            and self.CasingSize == "Small"
        ):
            return (
                0.132809 * self.WellDepth ** 2
                + 154.165493 * self.WellDepth
                + 836859.95667
            )

        if (
            self.WellProfile == "Deviated"
            and self.CompletionType == "Liner"
            and self.CasingSize == "Large"
        ):
            return (
                0.143118 * self.WellDepth ** 2
                + 388.858041 * self.WellDepth
                + 951705.503869
            )

        raise ValueError(
            f"Unsupported profile '{self.WellProfile}', completion '{self.CompletionType}', or casing size '{self.CasingSize}'"
        )

    def TotalDC(self, WellCostCalc: float) -> float:
        self.TotalDrillingCost = (
            WellCostCalc
            * (self.NoOfProductionWells + self.NoOfInjectionWells)
            * self.SuccessRate
            * self.PPImultiplier
        )
        IndirectCost = 0.05 * self.TotalDrillingCost
        return self.TotalDrillingCost + IndirectCost
