from dataclasses import dataclass

@dataclass
class Product:
    chapters: list[str]
    name: str
    small_img_url: str | None
    img_url: str | None
    release_year: int | None
    piece_per_pkg: str | None
    prices_per_piece: list[str]
    description: list[str]
    tech_conditions: str | None
    case: str | None
    marking: str | None
    weight: str | None
    pr_id: str
    execution: str | None
    producer: str | None
    features: list[str]
    labels: list[str]
    documents: list[str]
    dimensions: str | None
    coefficient: str | None