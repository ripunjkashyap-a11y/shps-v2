from pydantic import BaseModel, Field, model_validator

class StructureInput(BaseModel):
    construction_year: int = Field(..., ge=1960, le=2025)
    last_inspection_year: int = Field(..., ge=1990, le=2025)
    concrete_grade_mpa: int = Field(..., ge=20, le=50)
    elevation_m: float = Field(..., ge=0.0, le=150.0)
    load_kn: float = Field(..., ge=100.0, le=5000.0)
    cyclic_load_freq: float = Field(..., ge=10.0, le=500.0)
    support_type: int = Field(..., ge=0, le=3)
    env_condition: int = Field(..., ge=0, le=6)
    vibration_mms: float = Field(..., ge=0.1, le=12.0)

    @model_validator(mode='after')
    def validate_physics_logic(self):
        # 1. Temporal Integrity
        if self.last_inspection_year < self.construction_year:
            raise ValueError(
                "Inspection year cannot be before the construction year."
            )

        # 2. Tiered load vs. concrete grade
        #    C20/C25 cannot safely carry 3000+ kN; C30 minimum above 4000 kN.
        if self.load_kn > 4000 and self.concrete_grade_mpa < 30:
            raise ValueError(
                "Physics violation: Load >4000 kN requires at least C30 concrete."
            )
        if self.load_kn > 3000 and self.concrete_grade_mpa < 25:
            raise ValueError(
                "Physics violation: Load >3000 kN requires at least C25 concrete."
            )

        # 3. Support-type load limits
        #    Simply Supported (0): no moment fixity — limited to 3500 kN.
        #    Cantilever (3): fixed at one end only — most vulnerable, limited to 2500 kN.
        if self.support_type == 0 and self.load_kn > 3500:
            raise ValueError(
                "Physics violation: Simply Supported structures cannot sustain loads >3500 kN."
            )
        if self.support_type == 3 and self.load_kn > 2500:
            raise ValueError(
                "Physics violation: Cantilever structures cannot sustain loads >2500 kN."
            )

        # 4. Aggressive environment vs. concrete durability
        #    Hot-Arid (5) / Industrial-Chemical (6): C30 minimum required.
        #    Coastal-Marine (3) / Freeze-Thaw (4): C25 minimum required.
        if self.env_condition >= 5 and self.concrete_grade_mpa < 30:
            raise ValueError(
                "Physics violation: Extreme environments (Hot-Arid / Industrial-Chemical) require at least C30 concrete."
            )
        if self.env_condition >= 3 and self.concrete_grade_mpa < 25:
            raise ValueError(
                "Physics violation: Coastal/Freeze-Thaw environments require at least C25 concrete."
            )

        return self

class WhatIfInput(BaseModel):
    base_params: StructureInput
    changed_field: str
    changed_value: float
