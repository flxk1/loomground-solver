"""Optional Solver extensions; the deterministic core does not import this package."""

from .runtime import AddonRuntime, load_addons
from . import advisor as _advisor

AddonRecommendation = _advisor.AddonRecommendation
AdvisorPolicy = _advisor.AdvisorPolicy
advise = _advisor.advise
advise_metacognition = _advisor.advise_metacognition
advise_world_model = _advisor.advise_world_model
skill_manifest = _advisor.skill_manifest

__all__ = ["AddonRuntime", "load_addons", "AddonRecommendation", "AdvisorPolicy",
           "advise", "advise_metacognition", "advise_world_model", "skill_manifest"]
