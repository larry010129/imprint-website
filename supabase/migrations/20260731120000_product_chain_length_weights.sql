-- Per-product chain/necklace wax weights by thickness × length (cm).
-- Shape: { "1.0mm": { "36": 0.014, "46": 0.018, ... }, ... }
alter table products add column if not exists length_weights jsonb;
