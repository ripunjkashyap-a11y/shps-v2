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
            raise ValueError("Inspection year cannot be before the construction year.")
        
        # 2. Structural Capacity (Domain Logic)
        if self.load_kn > 4000 and self.concrete_grade_mpa < 30:
            raise ValueError("Physical Impossibility: Load of 4000kN+ requires at least C30 grade concrete.")

        return self

class WhatIfInput(BaseModel):
    base_params: StructureInput
    changed_field: str
    changed_value: float
