# Antigravity Sprite Generation Prompt

Copy-paste this into Google Antigravity to generate sprites for Pizzatorio.

---

## Prompt

Generate pixel art sprites for a 2D top-down factory automation game called Pizzatorio (think Factorio but with pizza). All sprites should be:
- Pixel art style, clean and readable at small sizes
- Top-down / slight isometric perspective (matching Factorio aesthetic)
- Transparent PNG background (alpha channel)
- Consistent warm industrial color palette
- Each sprite isolated, no background scenery

### BATCH 1: UI Build Tool Icons (48x48 px each)

These are toolbar button icons for the build menu. Each should clearly represent the machine/tool at a glance:

1. **conveyor_button.png** (48x48) — Conveyor belt segment with directional arrows, steel grey with blue side rails
2. **processor_button.png** (48x48) — Food processor machine, circular blade/grinder, soft blue-white housing
3. **oven_button.png** (48x48) — Pizza brick oven, warm orange with flame glow inside
4. **bot_dock_button.png** (48x48) — Robot charging dock/station, green with small robot silhouette
5. **assembly_button.png** (48x48) — Assembly workbench/table, purple-tinted, with pizza base on top
6. **splitter_button.png** (48x48) — Y-shaped belt fork splitting into two paths, olive/yellow
7. **inserter_button.png** (48x48) — Robotic mechanical arm, tan/orange, articulated gripper
8. **priority_button.png** (48x48) — Fast conveyor belt with gold racing stripes, speed lines
9. **delete_button.png** (48x48) — Red X demolish icon, construction/warning style
10. **source_button.png** (48x48) — Green input hopper/spawn point, items emerging
11. **sink_button.png** (48x48) — Red output/delivery chute, items entering

### BATCH 2: UI Panel Elements

12. **button_normal.png** (48x48) — Dark blue button frame, subtle border (#3a3a5e border, #222244 fill)
13. **button_hover.png** (48x48) — Same button but brighter border (#5a7ade), slight blue glow
14. **button_selected.png** (48x48) — Same button with bright glowing border (#7ab0ff), lit up
15. **tab_active.png** (180x36) — Active tab button, lit blue background, readable
16. **tab_inactive.png** (180x36) — Inactive tab button, dimmed dark navy

### BATCH 3: Missing Tile Sprites (48x48 px each)

Top-down factory tiles to match existing conveyor/processor/oven style:

17. **splitter_tile.png** (48x48) — Belt that forks into two directions (Y-shape), olive-yellow color with belt texture
18. **inserter_tile.png** (48x48) — Robotic arm on a base, can reach to adjacent tiles, tan/mechanical
19. **priority_lane_tile.png** (48x48) — Conveyor belt with gold/yellow racing stripe down the center, faster look

### BATCH 4: Game Item Sprites (16x16 px each)

Small food items visible on conveyor belts. Clear silhouettes at tiny size:

20. **assembled_pizza.png** (16x16) — Uncooked pizza with toppings visible, pale dough color with red/green dots
21. **baked_pizza.png** (16x16) — Golden-brown baked pizza, slightly darker, looks cooked and delicious
22. **drone_delivery.png** (16x16) — Small delivery drone seen from above, 4 rotors, carrying a box
23. **pepperoni_item.png** (16x16) — Red pepperoni slices, circular
24. **mushroom_item.png** (16x16) — Brown/tan sliced mushroom
25. **ham_item.png** (16x16) — Pink chopped ham pieces
26. **pepper_item.png** (16x16) — Green/red bell pepper slices
27. **onion_item.png** (16x16) — White/pale purple diced onion
28. **olive_item.png** (16x16) — Dark green/black sliced olives
29. **chicken_item.png** (16x16) — White/tan diced chicken pieces
30. **bacon_item.png** (16x16) — Red-brown bacon strips
31. **pineapple_item.png** (16x16) — Yellow pineapple chunks
32. **sausage_item.png** (16x16) — Brown sliced sausage rounds
33. **garlic_item.png** (16x16) — White minced garlic
34. **spinach_item.png** (16x16) — Green spinach leaves
35. **jalapeno_item.png** (16x16) — Green sliced jalapeno rings
36. **mozzarella_item.png** (16x16) — White sliced mozzarella
37. **basil_item.png** (16x16) — Green basil leaves
38. **anchovy_item.png** (16x16) — Small silver fish fillets
39. **beef_item.png** (16x16) — Brown cooked beef crumbles
40. **corn_item.png** (16x16) — Yellow corn kernels
41. **artichoke_item.png** (16x16) — Green artichoke hearts
42. **rocket_item.png** (16x16) — Green rocket/arugula leaves

---

## File Destination Mapping

After Antigravity generates these, copy and rename them into the project:

```
# UI tool icons → assets/sprites/ui/tools/
conveyor_button.png    → assets/sprites/ui/tools/conveyor.png
processor_button.png   → assets/sprites/ui/tools/processor.png
oven_button.png        → assets/sprites/ui/tools/oven.png
bot_dock_button.png    → assets/sprites/ui/tools/bot_dock.png
assembly_button.png    → assets/sprites/ui/tools/assembly_table.png
splitter_button.png    → assets/sprites/ui/tools/splitter.png
inserter_button.png    → assets/sprites/ui/tools/inserter.png
priority_button.png    → assets/sprites/ui/tools/priority_lane.png
delete_button.png      → assets/sprites/ui/tools/delete.png
source_button.png      → assets/sprites/ui/tools/source.png
sink_button.png        → assets/sprites/ui/tools/sink.png

# UI panel elements → assets/sprites/ui/
button_normal.png      → assets/sprites/ui/button_normal.png
button_hover.png       → assets/sprites/ui/button_hover.png
button_selected.png    → assets/sprites/ui/button_selected.png
tab_active.png         → assets/sprites/ui/tab_active.png
tab_inactive.png       → assets/sprites/ui/tab_inactive.png

# Missing tiles → assets/sprites/tiles/
splitter_tile.png      → assets/sprites/tiles/splitter.png
inserter_tile.png      → assets/sprites/tiles/inserter.png
priority_lane_tile.png → assets/sprites/tiles/priority_lane.png

# Item sprites → assets/sprites/items/ingredients/
assembled_pizza.png    → assets/sprites/items/assembled/default.png
baked_pizza.png        → assets/sprites/items/baked/pizza.png
drone_delivery.png     → assets/sprites/items/drone.png
pepperoni_item.png     → assets/sprites/items/ingredients/pepperoni.png
mushroom_item.png      → assets/sprites/items/ingredients/mushroom.png
ham_item.png           → assets/sprites/items/ingredients/ham.png
pepper_item.png        → assets/sprites/items/ingredients/pepper.png
onion_item.png         → assets/sprites/items/ingredients/onion.png
olive_item.png         → assets/sprites/items/ingredients/olive.png
chicken_item.png       → assets/sprites/items/ingredients/chicken.png
bacon_item.png         → assets/sprites/items/ingredients/bacon.png
pineapple_item.png     → assets/sprites/items/ingredients/pineapple.png
sausage_item.png       → assets/sprites/items/ingredients/sausage.png
garlic_item.png        → assets/sprites/items/ingredients/garlic.png
spinach_item.png       → assets/sprites/items/ingredients/spinach.png
jalapeno_item.png      → assets/sprites/items/ingredients/jalapeno.png
mozzarella_item.png    → assets/sprites/items/ingredients/mozzarella.png
basil_item.png         → assets/sprites/items/ingredients/basil.png
anchovy_item.png       → assets/sprites/items/ingredients/anchovy.png
beef_item.png          → assets/sprites/items/ingredients/beef.png
corn_item.png          → assets/sprites/items/ingredients/corn.png
artichoke_item.png     → assets/sprites/items/ingredients/artichoke.png
rocket_item.png        → assets/sprites/items/ingredients/rocket.png
```

## Resize Notes

Antigravity generates at 1024x1024. After download, resize:
- 48x48 sprites: `python3 -c "from PIL import Image; img=Image.open('INPUT.png').convert('RGBA').resize((48,48), Image.LANCZOS); img.save('OUTPUT.png')"`
- 16x16 sprites: same but `.resize((16,16), ...)`
- 180x36 tabs: `.resize((180,36), ...)`

Or use the bulk resize script: `python3 tools/generate_placeholders.py`
