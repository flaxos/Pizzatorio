# Pizzatorio UI Wireframe -- Factorio-Style Build Interface

## Viewport: 1280x720

## Master Layout

```
+------------------------------------------------------------------+
| TOP BAR  (full width, 40px, dark bg #1a1a2e)                     |
| [$1,250] [Rep: 72] [RP: 45.2] [Exp: T2] [Orders: 3] [Main (1/3)]|
+--------------------------------------------------+---------------+
|                                                  | RIGHT PANEL   |
|                                                  | (200px wide)  |
|              FACTORY GRID                        |               |
|              (main play area)                    | [Tab: Build ] |
|              ~1080 x ~616 px                     | [Tab: Orders] |
|                                                  | [Tab: R&D   ] |
|                                                  | [Tab: Commerc]|
|              Mouse interaction here:             | [Tab: Locatns]|
|              - Left click = place                |               |
|              - Right click = delete              | (tab content  |
|              - Scroll = zoom                     |  area below   |
|              - Middle drag = pan                 |  tabs)        |
|                                                  |               |
|                                                  | [Event Log   ]|
|                                                  | (bottom 200px)|
+--------------------------------------------------+---------------+
| BOTTOM TOOLBAR  (full width, 64px, dark bg #1a1a2e)              |
|                                                                  |
| [1:Conv][2:Proc][3:Oven][4:Bot][5:Del][6:Asm][7:Spl][8:Ins][9:PL]|
|                                                                  |
| Rotation: -->  |  Speed: [1x]  |  Selected: Conveyor ($10)      |
+------------------------------------------------------------------+
```

## Detailed Component Specs

### 1. Top Bar (40px tall, full width)

```
+--------+---------+---------+---------+----------+------------------+
| $1,250 | Rep: 72 | RP: 45.2| Exp: T2 | Ord: 3/5 | Main Shop (1/3) |
+--------+---------+---------+---------+----------+------------------+
  120px     100px     100px     100px     120px       flex-fill
```

- Background: `#1a1a2e` (dark navy) with subtle bottom border `#2a2a4e`
- Font: 14px monospace, color `#c8ccd4` (light gray)
- Money uses gold color `#f0c040` when positive, red `#e04040` when negative
- Reputation changes color: green > 70, yellow 40-70, red < 40
- Location label shows `[<] Name (N/M) [>]` with clickable arrows for switching

### 2. Bottom Toolbar (64px tall, full width)

```
+--------------------------------------------------------------+
|  +------+ +------+ +------+ +------+ +------+ +------+ ...  |
|  |  [1] | |  [2] | |  [3] | |  [4] | |  [5] | |  [6] |     |
|  | icon | | icon | | icon | | icon | | icon | | icon |     |
|  | Conv | | Proc | | Oven | | Bot  | | Del  | | Assm |     |
|  | $10  | | $80  | | $150 | | $200 | | free | | $120 |     |
|  +------+ +------+ +------+ +------+ +------+ +------+     |
|                                                              |
|  Rot: -->    Speed: [1x][2x][3x]    Selected: Conveyor $10  |
+--------------------------------------------------------------+
```

#### Individual Build Button (48x48 clickable area)

```
+----------+
|[1]       |   <-- shortcut hint (top-left corner, 10px font, #888)
|          |
|  [icon]  |   <-- 32x32 tool sprite centered
|          |
|  Conv    |   <-- tool name (bottom, 9px, #aaa)
|  $10     |   <-- cost (bottom line, 9px, #f0c040)
+----------+
```

Button states:
- **Normal**: border `#3a3a5e`, bg `#222244`
- **Hover**: border `#5a7ade`, bg `#2a2a5e`, slight glow
- **Selected**: border `#7ab0ff`, bg `#2a3a6e`, pulsing glow
- **Disabled** (insufficient funds): bg `#1a1a1a`, icon dimmed 50%, cost red

#### Build Tools (left to right):

| Key | Tool          | Tile Kind      | Cost | Icon Description              |
|-----|---------------|----------------|------|-------------------------------|
| 1   | Conveyor      | conveyor       | $10  | Belt with arrow               |
| 2   | Processor     | processor       | $80  | Food processor machine        |
| 3   | Oven          | oven           | $150 | Pizza oven with flame         |
| 4   | Bot Dock      | bot_dock       | $200 | Robot charging station        |
| 5   | Delete        | empty          | free | Red X                         |
| 6   | Assembly      | assembly_table | $120 | Assembly workbench            |
| 7   | Splitter      | splitter       | $40  | Y-shaped belt fork            |
| 8   | Inserter      | inserter       | $60  | Robotic arm                   |
| 9   | Priority Lane | priority_lane  | $30  | Gold-striped fast belt        |

#### Status Line (below buttons):

```
  Rotation: [-->]      Speed: [1x] [2x] [3x]      Selected: Conveyor ($10)
```

- Rotation indicator shows arrow matching current direction (0=right, 1=down, 2=left, 3=up)
- Speed toggle buttons: currently active one is highlighted
- Selected tool name + cost shown for confirmation

### 3. Right Panel (200px wide, full height minus top/bottom bars)

```
+----------------------+
| [Build][Orders][R&D] |  <-- tab row (3 visible, scroll for more)
| [Commerce][Locations]|
+----------------------+
|                      |
|   (Tab Content)      |
|   ~400px tall        |
|                      |
|                      |
|                      |
+----------------------+
| Event Log            |
| - Order fulfilled    |
| - Research unlocked  |
| - Hygiene event!     |
| (scrolling, 200px)   |
+----------------------+
```

#### Tab: Build

Vertical list of all build tools with descriptions:

```
+--------------------+
| > Conveyor    $10  |
|   Moves items      |
|   between tiles    |
+--------------------+
| > Processor   $80  |
|   Raw -> Processed |
+--------------------+
| > Oven       $150  |
|   Bakes pizzas     |
+--------------------+
| ...                |
+--------------------+
```

Each entry is clickable (selects that build tool).

#### Tab: Orders

```
+--------------------+
| ORDER #1           |
| Margherita         |
| SLA: [====--] 42s  |  <-- progress bar, green->yellow->red
| Reward: $35        |
+--------------------+
| ORDER #2           |
| Pepperoni          |
| SLA: [==----] 18s  |
| Reward: $45        |
+--------------------+
| Deliveries: 2      |
+--------------------+
```

- SLA bar turns yellow at 50%, red at 25% remaining
- Completed orders flash green then fade out
- Missed orders flash red

#### Tab: R&D (Tech Tree)

```
+--------------------+
| RESEARCH TREE      |
+--------------------+
| [x] Turbo Belts    |  <-- unlocked (checkmark)
|     Belts +25%     |
+--------------------+
| [ ] Turbo Oven     |  <-- locked, available
|     Ovens +18%     |
|     Cost: 8.0 RP   |
|     [UNLOCK]       |
+--------------------+
| [#] Franchise Exp  |  <-- locked, prereqs missing
|     Needs: Turbo O |
+--------------------+
```

- Unlocked: green checkmark, info only
- Available: blue border, UNLOCK button
- Locked: gray, shows prerequisite name

#### Tab: Commerce

```
+--------------------+
| COMMERCIAL         |
+--------------------+
| [ ] Social Media   |
|     +20% demand    |
|     30s duration   |
|     [ACTIVATE]     |
+--------------------+
| [*] Happy Hour     |  <-- currently active
|     -15% prices    |
|     18s remaining  |
+--------------------+
```

#### Tab: Locations

```
+--------------------+
| LOCATIONS          |
+--------------------+
| * Main Pizza Shop  |  <-- active (star)
|   20x15 grid       |
|   Orders: 3        |
+--------------------+
|   Dough Factory    |
|   16x12 grid       |
|   [SWITCH]         |
+--------------------+
| + BUY NEW LOCATION |
|   Farm ($1000)     |
|   Sauce Plant ($600|
+--------------------+
```

#### Event Log (bottom 200px of right panel)

- Scrolling RichTextLabel
- Color-coded entries:
  - Green: deliveries, unlocks
  - Yellow: warnings, SLA pressure
  - Red: missed orders, hygiene events
- Max 50 entries, FIFO

### 4. Notification Toast (bottom-center overlay)

```
         +---------------------------+
         | Order fulfilled! +$35     |
         +---------------------------+
              (fades after 3s)
```

- Position: bottom center, 60px from bottom edge
- Semi-transparent bg `#1a1a2ecc`
- Auto-fades after 3 seconds
- Color matches notification type (success/warning/error/info)

### 5. Placement Preview (on grid, follows cursor)

```
   +------+
   | tile |  <-- green tint = valid placement
   | prev |      red tint = blocked/insufficient funds
   +------+
     ^--- follows mouse position, snaps to grid
```

- Shows ghost of selected tile at cursor position
- Green modulate when placement is valid
- Red modulate when blocked (tile occupied, insufficient funds, not allowed)
- Rotation arrow overlay showing direction

## Color Palette

| Element           | Color     | Hex       |
|-------------------|-----------|-----------|
| Panel background  | Dark navy | `#1a1a2e` |
| Panel border      | Muted blue| `#2a2a4e` |
| Button normal bg  | Dark blue | `#222244` |
| Button hover bg   | Med blue  | `#2a2a5e` |
| Button selected   | Bright bl | `#2a3a6e` |
| Text primary      | Light gray| `#c8ccd4` |
| Text secondary    | Mid gray  | `#888899` |
| Money gold        | Gold      | `#f0c040` |
| Success green     | Green     | `#4cde80` |
| Warning yellow    | Yellow    | `#f0c040` |
| Error red         | Red       | `#e04040` |
| SLA bar full      | Green     | `#4cde80` |
| SLA bar mid       | Yellow    | `#e0c040` |
| SLA bar low       | Red       | `#e04040` |

## Interaction Model

| Input              | Action                                    |
|--------------------|-------------------------------------------|
| Left click grid    | Place selected tool tile                  |
| Left drag grid     | Paint conveyors (conveyor tool only)      |
| Right click grid   | Delete tile at position                   |
| Middle drag        | Pan camera                                |
| Scroll wheel       | Zoom in/out (0.5x to 3.0x)               |
| Keys 1-9           | Select build tool                         |
| R                  | Rotate placement direction                |
| Q / E             | Rotate left / right (alternative)         |
| Tab                | Next location                             |
| Shift+Tab          | Previous location                         |
| Ctrl+S             | Save game                                 |
| Ctrl+L             | Load game                                 |
| Click toolbar btn  | Select build tool (same as keyboard)      |
| Click right tab    | Switch right panel content                |
| Escape             | Deselect tool / close panel               |

## Responsive Notes

- At viewport widths < 1024px, right panel collapses to icon-only tabs
- Bottom toolbar scrolls horizontally on small screens
- Top bar items can truncate with ellipsis
- Touch: long-press = right-click equivalent, pinch = zoom
