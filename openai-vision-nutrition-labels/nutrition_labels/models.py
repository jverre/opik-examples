"""The typed record the model must return, and its strict JSON schema."""

from pydantic import BaseModel, Field


class NutritionFacts(BaseModel):
    """Values for ONE serving, as printed on the label."""

    product_name: str
    serving_size_g: float = Field(description="grams in one serving")
    calories: float = Field(description="kcal per serving, not kJ")
    total_fat_g: float
    total_carbs_g: float
    protein_g: float
    sodium_mg: float
    allergens: list[str] = Field(description="lowercase names from the 'Contains' statement only")


def json_schema() -> dict:
    """Schema for OpenAI structured outputs (strict mode needs additionalProperties=false)."""
    schema = NutritionFacts.model_json_schema()
    schema["additionalProperties"] = False
    return schema
