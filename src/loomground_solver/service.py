"""Reference transport-neutral service wrapper for any solver implementation."""
from __future__ import annotations

from collections.abc import Callable

from .interop import (
    Candidate, ProtocolManifest, ReasoningRequest, ReasoningResult,
    missing_capabilities,
)


DEFAULT_CAPABILITIES = (
    "candidate-adjudication",
    "decision-space",
    "evidence-verification",
    "signed-replay",
    "loomground-governance",
)


def manifest(*, implementation="loomground-solver", implementation_version="0.1.0",
             capabilities=DEFAULT_CAPABILITIES) -> dict:
    return ProtocolManifest(
        implementation=implementation,
        implementation_version=implementation_version,
        roles=("verifier",),
        capabilities=tuple(capabilities),
        schemas={"reasoning_fingerprint": "loomground.solver.fingerprint/v1",
                 "loomground_problem": "reasoning.interop.loomground/v1"},
    ).to_dict()


class SolverService:
    """Validate the neutral envelope, negotiate capabilities, then call a solver handler.

    The handler receives a typed :class:`ReasoningRequest` and returns a
    :class:`ReasoningResult`. It may use Loomground Solver or any other reasoning engine.
    """

    def __init__(self, handler: Callable[[ReasoningRequest], ReasoningResult], *,
                 implementation="loomground-solver", implementation_version="0.1.0",
                 capabilities=DEFAULT_CAPABILITIES):
        self.handler = handler
        self.implementation = implementation
        self.implementation_version = implementation_version
        self.capabilities = tuple(capabilities)

    def manifest(self) -> dict:
        return manifest(implementation=self.implementation,
                        implementation_version=self.implementation_version,
                        capabilities=self.capabilities)

    def verify(self, request: dict) -> dict:
        req = ReasoningRequest.from_dict(request)
        missing = missing_capabilities(
            ProtocolManifest.from_dict(self.manifest()), req.required_capabilities)
        if missing:
            return ReasoningResult(
                request_id=req.request_id,
                status="escalate",
                trace={"reason": "unsupported_capabilities", "missing": list(missing)},
                verifier=self.implementation,
                verifier_version=self.implementation_version,
            ).to_dict()
        result = self.handler(req)
        if not isinstance(result, ReasoningResult):
            raise TypeError("solver handler must return ReasoningResult")
        return result.to_dict()


def default_service(**handler_options) -> SolverService:
    """A complete standalone service using the universal request handler."""
    from .handler import UniversalHandler
    implementation = handler_options.pop("verifier", "loomground-solver")
    version = handler_options.pop("verifier_version", "0.1.0")
    handler = UniversalHandler(verifier=implementation, verifier_version=version,
                               **handler_options)
    return SolverService(handler, implementation=implementation,
                         implementation_version=version)
