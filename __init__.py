"""
ml
==
Standalone risk-scoring package. Deliberately has zero dependency on Flask,
SQLAlchemy, or any web framework so it can be trained, evaluated, versioned
and unit-tested completely on its own — and reused by any future service
(the current lending backend, a batch job, a notebook, etc.) by importing
`ml.risk_model`.
"""
