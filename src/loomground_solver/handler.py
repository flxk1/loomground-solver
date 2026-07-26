"""Universal reasoning.interop request handler."""
from __future__ import annotations

from .configuration import ConfigurationResolver
from .decision import decision_space
from .evidence import InlineEvidenceProvider, grounded_text
from .result import build_loomground_result, build_request_escalation, build_result
from .structural import CompilerRegistry
from .validation import validate_request, validate_result


class UniversalHandler:
    """Provider-neutral application layer connecting the wire protocol to Solver."""

    def __init__(self, *, evidence_provider=None, compilers=None, configurations=None,
                 signer=None, verifier="loomground-solver", verifier_version="0.1.0"):
        self.evidence_provider = evidence_provider
        self.compilers = compilers if isinstance(compilers, CompilerRegistry) \
            else CompilerRegistry(compilers or ())
        self.configurations = configurations if isinstance(configurations, ConfigurationResolver) \
            else ConfigurationResolver(configurations or ())
        self.signer = signer
        self.verifier = verifier
        self.verifier_version = verifier_version

    def __call__(self, request):
        validate_request(request)
        if request.problem.get("language") == "loomground":
            result = self._loomground(request)
            validate_result(request, result, implementation=self.verifier,
                            implementation_version=self.verifier_version)
            return result
        configuration = self.configurations.resolve(request.solver_profile)
        provider = self.evidence_provider or InlineEvidenceProvider.from_request(request)
        request_errors = self._request_errors(request, provider)
        if request_errors:
            result = build_request_escalation(
                request, request_errors, signer=self.signer,
                verifier=self.verifier, verifier_version=self.verifier_version,
            )
            validate_result(request, result, implementation=self.verifier,
                            implementation_version=self.verifier_version)
            return result
        verification, receipts, compiled, pairs, attacks = {}, [], {}, [], []

        candidate_ids = {c.candidate_id for c in request.candidates}
        for candidate in request.candidates:
            ok, reason = self._verify_candidate(candidate, provider, receipts)
            if ok:
                try:
                    structure = self.compilers.compile(candidate)
                    unknown = {x for edge in structure["attacks"] for x in edge} - candidate_ids
                    if unknown:
                        raise ValueError(f"attack references unknown candidates: {sorted(unknown)}")
                    compiled[candidate.candidate_id] = structure
                    pairs.extend(structure["pairs"])
                    attacks.extend(structure["attacks"])
                except (KeyError, TypeError, ValueError) as exc:
                    ok, reason = False, f"structural verification failed: {exc}"
            verification[candidate.candidate_id] = (ok, reason)

        def verify(candidate):
            return verification[candidate["id"]]

        decision = decision_space(
            [{"id": c.candidate_id} for c in request.candidates],
            attacks=attacks,
            verify=verify,
        )
        result = build_result(
            request, decision, pairs=pairs, receipts=receipts,
            configuration=configuration, signer=self.signer,
            verifier=self.verifier, verifier_version=self.verifier_version,
        )
        validate_result(request, result, implementation=self.verifier,
                        implementation_version=self.verifier_version)
        return result

    def _request_errors(self, request, provider):
        """Classify contract gaps before making any candidate decision."""
        errors = []
        by_schema = {}
        for candidate in request.candidates:
            schema = str((candidate.structural_evidence or {}).get("schema", ""))
            try:
                self.compilers.resolve(schema)
            except KeyError:
                by_schema.setdefault(schema, []).append(candidate.candidate_id)
        for schema, candidate_ids in sorted(by_schema.items()):
            errors.append({
                "code": "unsupported_structural_schema",
                "scope": "request",
                "message": f"no installed structural compiler for {schema!r}",
                "schema": schema,
                "candidate_ids": sorted(candidate_ids),
            })

        provider_snapshot = getattr(provider, "graph_version", None)
        if provider_snapshot is not None:
            missing, stale = [], []
            for candidate in request.candidates:
                for ref in candidate.evidence:
                    record = {"candidate_id": candidate.candidate_id,
                              "source_id": ref.source_id,
                              "graph_version": ref.graph_version}
                    if not ref.graph_version:
                        missing.append(record)
                    elif ref.graph_version != provider_snapshot:
                        stale.append(record)
            if missing:
                errors.append({
                    "code": "evidence_snapshot_missing",
                    "scope": "request",
                    "message": "evidence references name no graph snapshot",
                    "provider_graph_version": str(provider_snapshot),
                    "references": missing,
                })
            if stale:
                errors.append({
                    "code": "evidence_snapshot_mismatch",
                    "scope": "request",
                    "message": "evidence references do not match the provider snapshot",
                    "provider_graph_version": str(provider_snapshot),
                    "references": stale,
                })
        return errors

    def _loomground(self, request):
        from .loomground import reason, require_language_version

        version = require_language_version(request.problem.get("language_version", ""))
        profile = request.solver_profile or "loomground"
        if profile not in ("generic", "loomground", f"loomground@{version}"):
            raise ValueError(f"incompatible Solver profile for Loomground: {profile!r}")
        route = reason(request.problem["source"], request.problem.get("transport"))
        route["language_version"] = version
        return build_loomground_result(
            request, route, signer=self.signer, verifier=self.verifier,
            verifier_version=self.verifier_version,
        )

    @staticmethod
    def _verify_candidate(candidate, provider, receipts):
        matched = False
        for ref in candidate.evidence:
            try:
                if not provider.verify(ref):
                    return False, f"evidence verification failed: {ref.source_id}"
                payload = provider.resolve(ref)
            except Exception as exc:
                return False, f"evidence resolution failed: {type(exc).__name__}"
            grounded = grounded_text(ref, payload).strip()
            if grounded == candidate.claim.strip():
                matched = True
            receipts.append({"candidate_id": candidate.candidate_id,
                             "source_id": ref.source_id, "item_id": ref.item_id,
                             "span_start": ref.span_start, "span_end": ref.span_end,
                             "content_digest": ref.content_digest, "verified": True})
        if not matched:
            return False, "candidate claim does not match its grounded evidence"
        return True, ""


def verify_request(request, *, evidence_provider=None, compilers=None, configurations=None,
                   signer=None, verifier="loomground-solver", verifier_version="0.1.0"):
    return UniversalHandler(
        evidence_provider=evidence_provider, compilers=compilers,
        configurations=configurations, signer=signer,
        verifier=verifier, verifier_version=verifier_version,
    )(request)
