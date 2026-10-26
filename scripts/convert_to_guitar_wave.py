import re
import sys
import base64
import numpy as np

def convert_snake_to_guitar_wave(snake_svg_path, char_img_path, output_svg_path, theme='dark'):
    with open(snake_svg_path, 'r', encoding='utf-8') as f:
        svg_content = f.read()

    with open(char_img_path, 'rb') as f:
        char_b64 = base64.b64encode(f.read()).decode('utf-8')
    mime = 'image/webp' if char_img_path.endswith('.webp') else 'image/gif'
    data_uri = f'data:{mime};base64,{char_b64}'

    # Theme colors
    if theme == 'dark':
        bg_card = "#161b22"
        border_color = "#30363d"
        wave_stroke = "#39d353"
        line_color = "rgba(56, 139, 253, 0.15)"
        empty_tile = "#21262d"
        color_map = {
            'c0': '#21262d',
            'c1': '#0e4429',
            'c2': '#006d32',
            'c3': '#26a641',
            'c4': '#39d353',
        }
    else:
        bg_card = "#f6f8fa"
        border_color = "#d0d7de"
        wave_stroke = "#2da44e"
        line_color = "rgba(9, 105, 218, 0.12)"
        empty_tile = "#ebedf0"
        color_map = {
            'c0': '#ebedf0',
            'c1': '#9be9a8',
            'c2': '#40c463',
            'c3': '#30a14e',
            'c4': '#216e39',
        }

    # Extract color mapping from snake SVG stylesheet
    # e.g. .c.c7a{fill:var(--c1)}
    color_class_map = dict(re.findall(r'\.c\.(\w+)\s*\{\s*fill:\s*var\(--(c[0-4])\)', svg_content))

    # Extract all rect cells: <rect class="..." x="..." y="..." rx="2" ry="2"/>
    rect_matches = re.findall(r'<rect\s+class=\"([^\"]*)\"\s+x=\"([0-9.]+)\"\s+y=\"([0-9.]+)\"[^>]*>', svg_content)
    
    # Filter cells that are part of the 53x7 contribution grid (y in [2, 18, 34, 50, 66, 82, 98])
    grid_cells = []
    for cls, x_str, y_str in rect_matches:
        fx, fy = float(x_str), float(y_str)
        if fy in [2.0, 18.0, 34.0, 50.0, 66.0, 82.0, 98.0] and fx <= 850.0:
            grid_cells.append((fx, fy, cls))

    # Group by column x
    col_dict = {}
    for fx, fy, cls in grid_cells:
        col_idx = int(round((fx - 2.0) / 16.0))
        if col_idx not in col_dict:
            col_dict[col_idx] = []
        col_dict[col_idx].append((fx, fy, cls))

    total_cols = max(col_dict.keys()) + 1 if col_dict else 53
    wave_period = 6.0 # Relaxed, gentle tempo (6 seconds)

    # CSS Animations
    css = [f'''
    .board-bg {{
      fill: {bg_card};
      stroke: {border_color};
      stroke-width: 1px;
    }}
    .guide-line {{
      stroke: {line_color};
      stroke-width: 1px;
    }}
    .tile {{
      rx: 2.5px;
      ry: 2.5px;
      shape-rendering: geometricPrecision;
      transition: transform 0.2s, stroke 0.2s;
    }}
    .tile:hover {{
      stroke: {wave_stroke};
      stroke-width: 1.5px;
    }}

    /* Smooth Undulating Wave: Columns gently rise and fall as soundwave travels */
    @keyframes audioWaveBounce {{
      0%, 100% {{
        transform: translateY(0px);
      }}
      25% {{
        transform: translateY(-6.5px);
      }}
      50% {{
        transform: translateY(0px);
      }}
      75% {{
        transform: translateY(3.5px);
      }}
    }}
    .wave-col {{
      animation: audioWaveBounce {wave_period}s cubic-bezier(0.45, 0.05, 0.55, 0.95) infinite;
    }}

    /* Moving Soundwave Line */
    @keyframes waveLineMove {{
      0% {{
        transform: translateX(0px);
      }}
      100% {{
        transform: translateX(-160px);
      }}
    }}
    .soundwave-line {{
      animation: waveLineMove {wave_period}s linear infinite;
    }}
    ''']

    # Column animation delays (wave travels right-to-left from guitar)
    for col in range(total_cols):
        dist = total_cols - 1 - col
        delay = (dist / float(total_cols)) * wave_period
        css.append(f'    .c-col-{col} {{ animation-delay: -{delay:.2f}s; }}')

    svg = []
    svg.append(f'''<svg viewBox="-20 -150 900 340" width="900" height="340" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="waveLineGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="{wave_stroke}" stop-opacity="0" />
      <stop offset="30%" stop-color="{wave_stroke}" stop-opacity="0.3" />
      <stop offset="80%" stop-color="{wave_stroke}" stop-opacity="0.85" />
      <stop offset="100%" stop-color="{wave_stroke}" stop-opacity="0.95" />
    </linearGradient>

    <clipPath id="boardClip">
      <rect x="-10" y="-12" width="875" height="136" rx="8" ry="8" />
    </clipPath>
  </defs>

  <style>
{''.join(css)}
  </style>

  <!-- Clean Soundboard Base Panel -->
  <rect class="board-bg" x="-10" y="-12" width="875" height="136" rx="8" ry="8" />

  <!-- Elegant Guide Lines -->
  <line class="guide-line" x1="0" y1="20" x2="850" y2="20" />
  <line class="guide-line" x1="0" y1="56" x2="850" y2="56" />
  <line class="guide-line" x1="0" y1="92" x2="850" y2="92" />

  <!-- Undulating Real Commit Columns -->
  <g id="commit-grid">''')

    colored_count = 0
    for col in sorted(col_dict.keys()):
        gx = 2 + col * 16
        svg.append(f'    <g class="wave-col c-col-{col}">')
        for fx, fy, cls in col_dict[col]:
            # Determine color from classes
            color_var = None
            for c in cls.split():
                if c in color_class_map:
                    color_var = color_class_map[c]
                    break
            
            if color_var and color_var in color_map:
                c = color_map[color_var]
                if color_var != 'c0':
                    colored_count += 1
            else:
                c = empty_tile
                
            svg.append(f'      <rect class="tile" x="{fx}" y="{fy}" width="11" height="11" fill="{c}" />')
        svg.append('    </g>')

    svg.append('  </g>')

    # Audio Waveform Path: Extended from x=-320 to x=1280 to ensure seamless loop
    # When translateX shifts left by -160px, the right edge is still at 1120px (far past the card boundary 865px)
    wave_path = []
    x_start = -320
    x_end = 1280
    for x in range(x_start, x_end + 1, 4):
        y = 56.0 + 6.0 * np.sin((x / 160.0) * 2.0 * np.pi)
        if x == x_start:
            wave_path.append(f"M {x:.1f},{y:.1f}")
        else:
            wave_path.append(f"L {x:.1f},{y:.1f}")
    d_str = " ".join(wave_path)

    svg.append(f'''
  <!-- Clean Synced Audio Waveform Line -->
  <g clip-path="url(#boardClip)">
    <path class="soundwave-line" d="{d_str}" fill="none" stroke="url(#waveLineGrad)" stroke-width="2.2" stroke-linecap="round" opacity="0.8" />
  </g>

  <!-- Live2D Character Sitting on Top-Right Corner -->
  <g id="live2d-character" style="pointer-events: none;">
    <image href="{data_uri}" x="675" y="-135" width="160" height="270" preserveAspectRatio="xMidYMid meet" />
  </g>
</svg>''')

    with open(output_svg_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(svg))
    print(f"Successfully converted {snake_svg_path} -> {output_svg_path} (Colored tiles: {colored_count})")

if __name__ == '__main__':
    if len(sys.argv) >= 5:
        snake_path = sys.argv[1]
        char_path = sys.argv[2]
        out_path = sys.argv[3]
        theme_arg = sys.argv[4]
        convert_snake_to_guitar_wave(snake_path, char_path, out_path, theme_arg)
    else:
        convert_snake_to_guitar_wave('test-snake-dark.svg', 'assets/char_retina.webp', 'guitar-contribution-dark.svg', 'dark')
        convert_snake_to_guitar_wave('test-snake-light.svg', 'assets/char_retina.webp', 'guitar-contribution-light.svg', 'light')
