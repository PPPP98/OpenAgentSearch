class DomainPolicyBlocked(Exception):
    def __init__(self, domain: str) -> None:
        self.domain = domain
        super().__init__(f"domain is blocked by policy: {domain}")
