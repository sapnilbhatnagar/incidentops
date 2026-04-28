"""Pipeline runner stub — wired end-to-end in Phase 6."""
from .retrieve import retrieve


def main() -> None:
    print("Building index (first run downloads embedding model)…")
    results = retrieve("SSO login failure SAML certificate", top_k=3)
    for chunk in results:
        print(f"  {chunk.source_id}  [{chunk.span_start}:{chunk.span_end}]  {chunk.text[:80]!r}")


if __name__ == "__main__":
    main()
