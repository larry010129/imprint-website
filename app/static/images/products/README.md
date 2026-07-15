# Product images (`images/products/`)

Ring product photos are synced from **diamond-calculator** renders (Node — no Python):

```bash
cd scripts && npm install && npm run sync:ring-images
```

Or from repo root after a one-time `npm install` in `scripts/`:

```bash
node scripts/sync_ring_images_from_calculator.mjs
```

Mapping (calculator `metal_ring-{slug}` → V3 filename prefix):

| Calculator | V3 slug |
|---|---|
| A | `ring-classic-solitaire` |
| B | `ring-pave-halo` |
| C | `ring-vintage-vine` |
| D | `ring-modern-band` |

Gallery slots 1–3 = K白 / K黃 / K玫瑰; slot 4 repeats K白.  
`category-ring.jpg` uses style A (white).

Re-run the script after updating source PNGs in  
`diamond-calculator/static/images/{white,yellow,rose}/`.
