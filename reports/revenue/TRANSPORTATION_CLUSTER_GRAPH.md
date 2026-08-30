# Transportation Cluster Graph (P1-GROWTH-19G)

Generated: 2026-08-30  |  Deterministic audit, no network

## Nodes
| Node | content_id | Inbound links | Commercial layer |
|---|---|---|---|
| China Transportation Guide | cbt-17c6738ffb32 | 4 | none |
| High-Speed Rail Booking | cbt-cc4549872c92 | 3 | none |
| China Transportation Card | cbt-55aef784e6aa | 5 | comparison-layer |
| China Airport Transfer | cbt-02a3e0d6ed4f | 5 | comparison-layer |

## Link graph (directed, A -> B)
| From | To | Links |
|---|---|---|
| China Transportation Guide | China Transportation Card | 2 |
| China Transportation Guide | China Airport Transfer | 2 |
| High-Speed Rail Booking | China Transportation Guide | 1 |
| High-Speed Rail Booking | China Transportation Card | 2 |
| High-Speed Rail Booking | China Airport Transfer | 2 |
| China Transportation Card | China Transportation Guide | 2 |
| China Transportation Card | High-Speed Rail Booking | 2 |
| China Transportation Card | China Airport Transfer | 1 |
| China Airport Transfer | China Transportation Guide | 1 |
| China Airport Transfer | High-Speed Rail Booking | 1 |
| China Airport Transfer | China Transportation Card | 1 |

## Coverage
- train: transportation_guide, high_speed_rail, transportation_card, airport_transfer
- metro: transportation_guide, high_speed_rail, transportation_card, airport_transfer
- card: transportation_guide, high_speed_rail, transportation_card, airport_transfer
- airport: transportation_guide, high_speed_rail, transportation_card, airport_transfer
- payment: transportation_guide, high_speed_rail, transportation_card, airport_transfer
- apps: transportation_guide, high_speed_rail, transportation_card, airport_transfer

## Metrics
- orphan pages (inbound == 0): 0 
- min inbound across cluster: 3
- total inbound links: 17

## Rules
- REV002 CTA frozen; Drive/GA4/affiliate shortcodes unchanged.
- This is an internal measurement, not a Google ranking signal.
