"""A multi-tool dispatch policy with fake delegated credential metadata.

No OAuth exchange, secret or MCP server is implemented. Trusted test code
supplies identity, verified token metadata and monotonic time. Deployment must
validate issuer, signature, audience, scope and caller through its real stack.
"""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Delegation:
    tenant: str
    subject: str
    audience: str
    scopes: frozenset[str]
    expires: float


class Gateway:
    # No generic execute(), shell, URL fetch or submit_request entry exists.
    TOOLS = {'read_policy': 'policy.read', 'save_draft': 'draft.write'}

    def __init__(self, limit=2):
        if type(limit) is not int or limit < 1:
            raise ValueError('positive integer limit required')
        self.limit = limit
        self.counts = {}

    def admit(self, principal, token, tool, target_tenant, now):
        """Validate identity and tool-specific scope before spending a quota."""
        if (type(now) not in (int, float) or not math.isfinite(now) or now < 0
                or type(token.expires) not in (int, float)
                or not math.isfinite(token.expires)):
            raise ValueError('finite nonnegative clock and finite expiry required')
        required = self.TOOLS.get(tool)
        if required is None:
            raise PermissionError('tool not allowlisted')
        if (token.audience != 'service-desk' or token.tenant != principal.tenant
                or token.subject != principal.subject
                or target_tenant != principal.tenant or now >= token.expires
                or required not in token.scopes
                or (tool == 'save_draft' and not principal.can_save)):
            raise PermissionError('delegation or scope denied')
        # Fixed-minute, per-principal AND per-tool quota. Burst behaviour at a
        # window boundary is deliberate and described in chapter 8.
        key = (principal.tenant, principal.subject, tool, int(now // 60))
        if self.counts.get(key, 0) >= self.limit:
            raise PermissionError('rate budget exhausted')
        self.counts[key] = self.counts.get(key, 0) + 1
        # An admission is not an effect approval. The executor must also call
        # Policy.allow() with the exact operation and payload before saving.
        return required
